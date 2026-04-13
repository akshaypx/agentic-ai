from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from price_optimizer.llm import invoke_structured
from price_optimizer.models import (
    PricingState,
    ProductIntent,
    ProductOffer,
    ProductSearchInput,
    RankedProduct,
    Recommendation,
    SupervisorDecision,
)
from price_optimizer.prompts import (
    extract_intent_prompt,
    ranking_prompt,
    recommendation_prompt,
    supervisor_prompt,
)
from price_optimizer.tools import google_lens_search, google_product_search
from price_optimizer.utils import (
    append_step,
    compact_state_summary,
    compute_price_stats,
    dedupe_products,
    heuristic_match_score,
)


def supervisor_node(state: PricingState) -> Dict[str, Any]:
    prompt = supervisor_prompt.format(
        state_summary=compact_state_summary(state),
    )
    fallback = lambda: SupervisorDecision(
        next_action=_fallback_next_action(state),
        rationale="Fallback supervisor routing applied.",
        should_retry=False,
        retry_search_term=None,
    )
    decision = invoke_structured(SupervisorDecision, prompt, fallback)

    return {
        "next_action": decision.next_action,
        "steps": append_step(
            state.get("steps", []),
            "supervisor",
            "completed",
            f"Supervisor selected `{decision.next_action}`.",
            rationale=decision.rationale,
            retry_search_term=decision.retry_search_term,
        ),
    }


def extract_query_node(state: PricingState) -> Dict[str, Any]:
    prompt = extract_intent_prompt.format(query=state["query"])
    fallback = lambda: ProductIntent(
        raw_query=state["query"],
        normalized_query=state["query"],
        product_name=state["query"],
        location="United States",
        num_results=12,
        confidence=0.45,
    )
    intent = invoke_structured(ProductIntent, prompt, fallback)

    return {
        "intent": intent,
        "steps": append_step(
            state.get("steps", []),
            "extract_query",
            "completed",
            f"Extracted intent for `{intent.product_name}`.",
            normalized_query=intent.normalized_query,
            filters=intent.filters,
            min_price=intent.min_price,
            max_price=intent.max_price,
        ),
    }


def shopping_search_node(state: PricingState) -> Dict[str, Any]:
    intent = state["intent"]
    search_input = ProductSearchInput(
        query=intent.normalized_query,
        location=intent.location,
        num_results=intent.num_results,
        min_price=intent.min_price,
        max_price=intent.max_price,
        sort_by=intent.sort_by,
        free_shipping=intent.free_shipping,
        on_sale=intent.on_sale,
    )

    try:
        results = google_product_search(search_input)
        products = _maybe_filter_by_budget(results.products, intent.min_price, intent.max_price)
        status = "completed"
        message = f"Collected {len(products)} shopping results."
        retry_count = state.get("retry_count", 0)
        updated_intent = intent
        if not products and retry_count < 2:
            retry_count += 1
            broader_query = _broaden_query(intent.normalized_query)
            updated_intent = intent.model_copy(update={"normalized_query": broader_query})
            status = "retry"
            message = f"No strong shopping hits. Retrying with broader query `{broader_query}`."
        return {
            "intent": updated_intent,
            "shopping_results": products,
            "retry_count": retry_count,
            "steps": append_step(
                state.get("steps", []),
                "shopping_search",
                status,
                message,
                query=search_input.query,
                result_count=len(products),
            ),
        }
    except Exception as exc:
        return {
            "shopping_results": [],
            "errors": state.get("errors", []) + [str(exc)],
            "steps": append_step(
                state.get("steps", []),
                "shopping_search",
                "error",
                "Shopping search failed.",
                error=str(exc),
            ),
        }


def image_search_node(state: PricingState) -> Dict[str, Any]:
    image_url = state.get("image_url")
    if not image_url:
        return {
            "lens_results": [],
            "steps": append_step(
                state.get("steps", []),
                "image_search",
                "skipped",
                "No image URL provided. Lens step skipped.",
            ),
        }

    try:
        intent = state.get("intent")
        query = intent.normalized_query if intent else state["query"]
        results = google_lens_search(
            image_url=image_url,
            query=query,
            num_results=intent.num_results if intent else 10,
        )
        return {
            "lens_results": results.products,
            "steps": append_step(
                state.get("steps", []),
                "image_search",
                "completed",
                f"Collected {len(results.products)} Google Lens matches.",
                image_url=image_url,
                result_count=len(results.products),
            ),
        }
    except Exception as exc:
        return {
            "lens_results": [],
            "errors": state.get("errors", []) + [str(exc)],
            "steps": append_step(
                state.get("steps", []),
                "image_search",
                "error",
                "Google Lens search failed.",
                error=str(exc),
            ),
        }


def rank_results_node(state: PricingState) -> Dict[str, Any]:
    intent = state["intent"]
    all_products = dedupe_products(
        [*state.get("shopping_results", []), *state.get("lens_results", [])]
    )
    if not all_products:
        return {
            "ranked_products": [],
            "steps": append_step(
                state.get("steps", []),
                "rank_results",
                "skipped",
                "No products available to rank.",
            ),
        }

    prompt = ranking_prompt.format(
        intent=intent.model_dump_json(indent=2),
        candidates=_serialize_candidates(all_products),
    )

    fallback = lambda: _fallback_ranking(intent.normalized_query, all_products, intent.min_price, intent.max_price)
    llm_ranking = invoke_structured(_RankingResponse, prompt, fallback)

    ranked = _merge_llm_ranking(all_products, llm_ranking.ranked_products)
    stats = compute_price_stats(all_products)

    return {
        "ranked_products": ranked,
        **stats,
        "steps": append_step(
            state.get("steps", []),
            "rank_results",
            "completed",
            f"Ranked {len(ranked)} products.",
            avg_price=stats["avg_price"],
            min_price=stats["min_price"],
            max_price=stats["max_price"],
        ),
    }


def recommend_node(state: PricingState) -> Dict[str, Any]:
    ranked_products = state.get("ranked_products", [])
    if not ranked_products:
        recommendation = Recommendation(
            recommended_price=None,
            recommended_product_title=None,
            reasoning="No ranked products were available for recommendation.",
            summary="No recommendation available.",
        )
        return {
            "recommendation": recommendation,
            "completed": True,
            "steps": append_step(
                state.get("steps", []),
                "recommend",
                "completed",
                "No recommendation generated because ranking returned no products.",
            ),
        }

    prompt = recommendation_prompt.format(
        intent=state["intent"].model_dump_json(indent=2),
        stats={
            "avg_price": state.get("avg_price"),
            "min_price": state.get("min_price"),
            "max_price": state.get("max_price"),
        },
        ranked_products=[item.model_dump() for item in ranked_products[:5]],
    )
    fallback = lambda: _fallback_recommendation(state)
    recommendation = invoke_structured(Recommendation, prompt, fallback)

    return {
        "recommendation": recommendation,
        "completed": True,
        "steps": append_step(
            state.get("steps", []),
            "recommend",
            "completed",
            "Generated final recommendation.",
            recommended_price=recommendation.recommended_price,
            recommended_product=recommendation.recommended_product_title,
        ),
    }


def _fallback_next_action(state: PricingState) -> str:
    if not state.get("intent"):
        return "extract_query"
    if not state.get("shopping_results"):
        return "shopping_search"
    if state.get("image_url") and not state.get("lens_results"):
        return "image_search"
    if not state.get("ranked_products"):
        return "rank_results"
    if not state.get("recommendation"):
        return "recommend"
    return "end"


def _broaden_query(query: str) -> str:
    tokens = query.split()
    if len(tokens) <= 2:
        return query
    return " ".join(tokens[:-1])


def _maybe_filter_by_budget(
    products: List[ProductOffer],
    min_price: float | None,
    max_price: float | None,
) -> List[ProductOffer]:
    filtered: List[ProductOffer] = []
    for product in products:
        if product.extracted_price is None:
            filtered.append(product)
            continue
        if min_price is not None and product.extracted_price < min_price:
            continue
        if max_price is not None and product.extracted_price > max_price:
            continue
        filtered.append(product)
    return filtered


def _serialize_candidates(products: List[ProductOffer]) -> List[Dict[str, Any]]:
    return [
        {
            "title": product.title,
            "source": product.source,
            "source_type": product.source_type,
            "price": product.price,
            "extracted_price": product.extracted_price,
            "rating": product.rating,
            "reviews": product.reviews,
            "link": product.link,
        }
        for product in products
    ]


class _RankedProductSignal(RankedProduct):
    rank: int = 0


class _RankingResponse(BaseModel):
    ranked_products: List[_RankedProductSignal] = Field(default_factory=list)


def _fallback_ranking(
    query: str,
    products: List[ProductOffer],
    min_price: float | None,
    max_price: float | None,
) -> _RankingResponse:
    ranked_products: List[_RankedProductSignal] = []
    scored = sorted(
        products,
        key=lambda product: heuristic_match_score(query, product, min_price, max_price),
        reverse=True,
    )
    for idx, product in enumerate(scored, start=1):
        score = heuristic_match_score(query, product, min_price, max_price)
        ranked_products.append(
            _RankedProductSignal(
                rank=idx,
                title=product.title or "Unknown product",
                source=product.source,
                source_type=product.source_type,
                price=product.price,
                extracted_price=product.extracted_price,
                rating=product.rating,
                reviews=product.reviews,
                confidence=round(score, 3),
                weightage=round(score, 3),
                reasons=["Heuristic fallback ranking used."],
                link=product.link,
                thumbnail=product.thumbnail,
            )
        )
    return _RankingResponse(
        ranked_products=ranked_products,
    )


def _merge_llm_ranking(
    products: List[ProductOffer],
    ranked_signals: List[_RankedProductSignal],
) -> List[RankedProduct]:
    by_title = {product.title or "": product for product in products}
    ranked: List[RankedProduct] = []
    for idx, signal in enumerate(ranked_signals, start=1):
        product = by_title.get(signal.title or "", None)
        ranked.append(
            RankedProduct(
                rank=idx,
                title=signal.title,
                source=signal.source or (product.source if product else None),
                source_type=signal.source_type if signal.source_type else (product.source_type if product else "shopping"),
                price=signal.price or (product.price if product else None),
                extracted_price=signal.extracted_price if signal.extracted_price is not None else (product.extracted_price if product else None),
                rating=signal.rating if signal.rating is not None else (product.rating if product else None),
                reviews=signal.reviews if signal.reviews is not None else (product.reviews if product else None),
                confidence=signal.confidence,
                weightage=signal.weightage,
                reasons=signal.reasons,
                link=signal.link or (product.link if product else None),
                thumbnail=signal.thumbnail or (product.thumbnail if product else None),
            )
        )
    return ranked


def _fallback_recommendation(state: PricingState) -> Recommendation:
    top_product = state["ranked_products"][0]
    avg_price = state.get("avg_price")
    recommended_price = top_product.extracted_price or avg_price
    if recommended_price:
        recommended_price = round(recommended_price - 0.01, 2)
    return Recommendation(
        recommended_price=recommended_price,
        recommended_product_title=top_product.title,
        reasoning="Top ranked product selected using fallback recommendation logic.",
        summary=f"Best current option is {top_product.title}.",
    )
