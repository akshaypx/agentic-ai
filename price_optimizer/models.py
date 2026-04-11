from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field


class ProductSearchInput(BaseModel):
    query: str = Field(..., description="Product search query (e.g., 'iPhone 15')")
    location: str = Field(
        default="United States",
        description="Location for Google Shopping search"
    )
    num_results: int = Field(
        default=10,
        description="Number of results to return"
    )

class Product(BaseModel):
    title: Optional[str]
    price: Optional[str]
    extracted_price: Optional[float]
    rating: Optional[float]
    reviews: Optional[int]
    source: Optional[str]
    link: Optional[str]
    thumbnail: Optional[str]


class ProductSearchOutput(BaseModel):
    products: List[Product]


class PricingState(TypedDict):
    query: str
    products: List[Product]
    avg_price: Optional[float]
    min_price: Optional[float]
    max_price: Optional[float]
    recommended_price: Optional[float]
    reasoning: Optional[str]