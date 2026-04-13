from __future__ import annotations

from langgraph.graph import END, StateGraph

from price_optimizer.models import PricingState
from price_optimizer.nodes import (
    extract_query_node,
    image_search_node,
    rank_results_node,
    recommend_node,
    shopping_search_node,
    supervisor_node,
)


def build_graph():
    builder = StateGraph(PricingState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("extract_query", extract_query_node)
    builder.add_node("shopping_search", shopping_search_node)
    builder.add_node("image_search", image_search_node)
    builder.add_node("rank_results", rank_results_node)
    builder.add_node("recommend", recommend_node)

    builder.set_entry_point("supervisor")
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state["next_action"],
        {
            "extract_query": "extract_query",
            "shopping_search": "shopping_search",
            "image_search": "image_search",
            "rank_results": "rank_results",
            "recommend": "recommend",
            "end": END,
        },
    )

    builder.add_edge("extract_query", "supervisor")
    builder.add_edge("shopping_search", "supervisor")
    builder.add_edge("image_search", "supervisor")
    builder.add_edge("rank_results", "supervisor")
    builder.add_edge("recommend", "supervisor")

    return builder.compile()


graph = build_graph()
