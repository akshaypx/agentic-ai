from __future__ import annotations

import os
from typing import Any, Dict, List

import serpapi

from price_optimizer.env import load_local_env
from price_optimizer.models import ProductOffer, ProductSearchInput, ProductSearchOutput

load_local_env()


SORT_MAPPING = {
    "price_low_to_high": 1,
    "price_high_to_low": 2,
}


def _build_search(params: Dict[str, Any], api_key: str | None = None):
    key = api_key or os.getenv("SERPAPI_API_KEY")
    if not key:
        raise RuntimeError("SERPAPI_API_KEY is required")
    return serpapi.GoogleSearch({**params, "api_key": key})


def google_product_search(
    search_input: ProductSearchInput,
    api_key: str | None = None,
) -> ProductSearchOutput:
    params: Dict[str, Any] = {
        "engine": "google_shopping",
        "q": search_input.query,
        "location": search_input.location,
        "num": search_input.num_results,
    }

    if search_input.min_price is not None:
        params["min_price"] = search_input.min_price
    if search_input.max_price is not None:
        params["max_price"] = search_input.max_price
    if search_input.sort_by:
        params["sort_by"] = SORT_MAPPING[search_input.sort_by]
    if search_input.free_shipping:
        params["free_shipping"] = True
    if search_input.on_sale:
        params["on_sale"] = True

    search = _build_search(params, api_key)
    results = search.get_dict()
    shopping_results = results.get("shopping_results", [])

    products: List[ProductOffer] = []
    for item in shopping_results[: search_input.num_results]:
        products.append(
            ProductOffer(
                title=item.get("title"),
                price=item.get("price"),
                extracted_price=item.get("extracted_price"),
                rating=item.get("rating"),
                reviews=item.get("reviews"),
                source=item.get("source"),
                link=item.get("product_link"),
                thumbnail=item.get("thumbnail"),
                delivery=item.get("delivery"),
                product_id=item.get("product_id"),
                source_type="shopping",
                position=item.get("position"),
                query_used=search_input.query,
            )
        )

    return ProductSearchOutput(
        products=products,
        metadata={
            "filters": results.get("filters", []),
            "search_parameters": results.get("search_parameters", {}),
        },
    )


def google_lens_search(
    image_url: str,
    query: str | None = None,
    location_country: str = "us",
    num_results: int = 10,
    api_key: str | None = None,
) -> ProductSearchOutput:
    params: Dict[str, Any] = {
        "engine": "google_lens",
        "url": image_url,
        "type": "products",
        "country": location_country,
    }
    if query:
        params["q"] = query

    search = _build_search(params, api_key)
    results = search.get_dict()
    candidates = (
        results.get("products")
        or results.get("visual_matches")
        or results.get("exact_matches")
        or []
    )

    products: List[ProductOffer] = []
    for item in candidates[:num_results]:
        price_block = item.get("price") or {}
        products.append(
            ProductOffer(
                title=item.get("title"),
                price=price_block.get("value") or item.get("price"),
                extracted_price=price_block.get("extracted_value"),
                rating=item.get("rating"),
                reviews=item.get("reviews"),
                source=item.get("source"),
                link=item.get("link"),
                thumbnail=item.get("thumbnail"),
                source_type="lens",
                position=item.get("position"),
                query_used=query,
                currency=price_block.get("currency"),
                in_stock=item.get("in_stock"),
            )
        )

    return ProductSearchOutput(
        products=products,
        metadata={
            "search_parameters": results.get("search_parameters", {}),
            "search_information": results.get("search_information", {}),
        },
    )
