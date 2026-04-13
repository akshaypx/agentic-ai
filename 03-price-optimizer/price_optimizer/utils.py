from __future__ import annotations

import json
import re
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional

from price_optimizer.models import ExecutionStep, ProductOffer


def clean_json(text: str) -> str:
    text = re.sub(r"```json|```", "", text).strip()
    return text


def safe_json_loads(text: str) -> Dict[str, Any]:
    return json.loads(clean_json(text))


def append_step(
    steps: List[ExecutionStep],
    stage: str,
    status: str,
    message: str,
    **details: Any,
) -> List[ExecutionStep]:
    return steps + [
        ExecutionStep(
            stage=stage,
            status=status,
            message=message,
            details=details,
        )
    ]


def compact_state_summary(state: Dict[str, Any]) -> str:
    intent = state.get("intent")
    return json.dumps(
        {
            "query": state.get("query"),
            "image_url": state.get("image_url"),
            "intent": intent.model_dump() if intent else None,
            "shopping_results": len(state.get("shopping_results", [])),
            "lens_results": len(state.get("lens_results", [])),
            "ranked_products": len(state.get("ranked_products", [])),
            "has_recommendation": bool(state.get("recommendation")),
            "retry_count": state.get("retry_count", 0),
            "errors": state.get("errors", []),
        },
        indent=2,
    )


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def dedupe_products(products: Iterable[ProductOffer]) -> List[ProductOffer]:
    seen = set()
    deduped: List[ProductOffer] = []
    for product in products:
        key = (
            normalize_text(product.title),
            round(product.extracted_price or 0.0, 2),
            normalize_text(product.source),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(product)
    return deduped


def compute_price_stats(products: Iterable[ProductOffer]) -> Dict[str, Optional[float]]:
    prices = sorted(
        product.extracted_price
        for product in products
        if product.extracted_price is not None
    )
    if not prices:
        return {"avg_price": None, "min_price": None, "max_price": None}

    trim = max(1, int(len(prices) * 0.1)) if len(prices) > 4 else 0
    trimmed = prices[trim: len(prices) - trim] if trim else prices

    return {
        "avg_price": round(mean(trimmed), 2),
        "min_price": round(min(prices), 2),
        "max_price": round(max(prices), 2),
    }


def heuristic_match_score(
    query: str,
    product: ProductOffer,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> float:
    score = 0.2
    query_tokens = set(normalize_text(query).split())
    title_tokens = set(normalize_text(product.title).split())
    if query_tokens and title_tokens:
        overlap = len(query_tokens & title_tokens) / max(len(query_tokens), 1)
        score += overlap * 0.45

    if product.rating:
        score += min(product.rating / 5.0, 1.0) * 0.1
    if product.reviews:
        score += min(product.reviews / 2000.0, 1.0) * 0.1
    if product.source_type == "lens":
        score += 0.05
    if min_price is not None and product.extracted_price is not None and product.extracted_price < min_price:
        score -= 0.1
    if max_price is not None and product.extracted_price is not None and product.extracted_price > max_price:
        score -= 0.1

    penalty_terms = {"case", "cover", "replacement", "strap", "protector", "accessory"}
    if title_tokens & penalty_terms:
        score -= 0.25

    return max(0.0, min(score, 1.0))
