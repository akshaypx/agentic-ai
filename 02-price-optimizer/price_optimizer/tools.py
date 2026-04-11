import serpapi
from price_optimizer.models import Product, ProductSearchInput, ProductSearchOutput


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