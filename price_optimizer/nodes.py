


import os
import serpapi
import json
import re
from price_optimizer.llm import llm
from price_optimizer.models import PricingState, Product, ProductSearchInput, ProductSearchOutput
from price_optimizer.utils import clean_json
from price_optimizer.prompts import pricing_prompt


def google_product_search(
    input: ProductSearchInput,
    api_key: str,
) -> ProductSearchOutput:
    """
    Google Shopping search via SerpAPI
    """

    client = serpapi.Client(api_key=api_key)

    results = client.search({
        "engine": "google_shopping",
        "q": input.query,
        "location": input.location,
    })

    shopping_results = results.get("shopping_results", [])

    products = []
    for item in shopping_results[: input.num_results]:
        products.append(
            Product(
                title=item.get("title"),
                price=item.get("price"),
                extracted_price=item.get("extracted_price"),
                rating=item.get("rating"),
                reviews=item.get("reviews"),
                source=item.get("source"),
                link=item.get("product_link"),
                thumbnail=item.get("thumbnail"),
            )
        )

    return ProductSearchOutput(products=products)

def search_node(state: PricingState):
    results = google_product_search(
        ProductSearchInput(query=state["query"]),
        api_key=os.getenv("SERPAPI_API_KEY")
    )

    return {
        "products": results.products
    }

def analyze_node(state: PricingState):
    prices = [
        p.extracted_price
        for p in state["products"]
        if p.extracted_price is not None
    ]

    if not prices:
        return {}

    prices.sort()

    # Remove outliers (basic trimming)
    trimmed = prices[int(len(prices)*0.1): int(len(prices)*0.9)] or prices

    avg_price = sum(trimmed) / len(trimmed)
    min_price = min(prices)
    max_price = max(prices)

    return {
        "avg_price": avg_price,
        "min_price": min_price,
        "max_price": max_price,
    }

def recommend_node(state: PricingState):
    prices = [
        p.extracted_price
        for p in state["products"]
        if p.extracted_price is not None
    ]

    if not prices:
        return {}

    prompt = pricing_prompt.format(
        query=state["query"],
        prices=prices,
        avg_price=state["avg_price"],
        min_price=state["min_price"],
        max_price=state["max_price"],
    )

    response = llm.invoke(prompt)

    try:
        cleaned = clean_json(response.content)
        parsed = json.loads(cleaned)

        recommended_price = parsed.get("recommended_price")
        reasoning = parsed.get("reasoning")

    except Exception:
        # fallback logic
        recommended_price = state["avg_price"] * 0.97 if state["avg_price"] else None
        reasoning = "Fallback pricing used due to parsing error"

    # psychological pricing
    if recommended_price:
        recommended_price = int(recommended_price) - 0.01

    return {
        "recommended_price": recommended_price,
        "reasoning": reasoning,
    }
