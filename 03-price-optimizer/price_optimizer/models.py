from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


class ProductIntent(BaseModel):
    raw_query: str
    normalized_query: str
    product_name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    attributes: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    location: str = "United States"
    num_results: int = 12
    sort_by: Optional[Literal["price_low_to_high", "price_high_to_low"]] = None
    free_shipping: bool = False
    on_sale: bool = False
    confidence: float = 0.0


class ProductSearchInput(BaseModel):
    query: str
    location: str = "United States"
    num_results: int = 12
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sort_by: Optional[Literal["price_low_to_high", "price_high_to_low"]] = None
    free_shipping: bool = False
    on_sale: bool = False


class ProductOffer(BaseModel):
    title: Optional[str] = None
    price: Optional[str] = None
    extracted_price: Optional[float] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    source: Optional[str] = None
    link: Optional[str] = None
    thumbnail: Optional[str] = None
    delivery: Optional[str] = None
    product_id: Optional[str] = None
    source_type: Literal["shopping", "lens"] = "shopping"
    position: Optional[int] = None
    query_used: Optional[str] = None
    currency: Optional[str] = None
    in_stock: Optional[bool] = None


class ProductSearchOutput(BaseModel):
    products: List[ProductOffer]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExecutionStep(BaseModel):
    stage: str
    status: Literal["started", "completed", "retry", "skipped", "error"]
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class SupervisorDecision(BaseModel):
    next_action: Literal[
        "extract_query",
        "shopping_search",
        "image_search",
        "rank_results",
        "recommend",
        "end",
    ]
    rationale: str
    should_retry: bool = False
    retry_search_term: Optional[str] = None


class RankedProduct(BaseModel):
    rank: int
    title: str
    source: Optional[str] = None
    source_type: Literal["shopping", "lens"] = "shopping"
    price: Optional[str] = None
    extracted_price: Optional[float] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    confidence: float
    weightage: float
    reasons: List[str] = Field(default_factory=list)
    link: Optional[str] = None
    thumbnail: Optional[str] = None


class Recommendation(BaseModel):
    recommended_price: Optional[float] = None
    recommended_product_title: Optional[str] = None
    reasoning: str
    summary: str


class PricingState(TypedDict, total=False):
    query: str
    image_url: Optional[str]
    intent: Optional[ProductIntent]
    shopping_results: List[ProductOffer]
    lens_results: List[ProductOffer]
    ranked_products: List[RankedProduct]
    recommendation: Optional[Recommendation]
    avg_price: Optional[float]
    min_price: Optional[float]
    max_price: Optional[float]
    retry_count: int
    next_action: str
    completed: bool
    errors: List[str]
    steps: List[ExecutionStep]
