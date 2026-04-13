from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from price_optimizer.models import PricingState
from price_optimizer.nodes import (
    extract_query_node,
    image_search_node,
    rank_results_node,
    recommend_node,
    shopping_search_node,
    supervisor_node,
)


EventEmitter = Optional[Callable[[str, Dict[str, Any]], None]]

NODE_REGISTRY = {
    "extract_query": extract_query_node,
    "shopping_search": shopping_search_node,
    "image_search": image_search_node,
    "rank_results": rank_results_node,
    "recommend": recommend_node,
}


def run_agentic_workflow(
    query: str,
    image_url: str | None = None,
    emit: EventEmitter = None,
    max_iterations: int = 10,
) -> PricingState:
    state: PricingState = {
        "query": query,
        "image_url": image_url,
        "shopping_results": [],
        "lens_results": [],
        "ranked_products": [],
        "retry_count": 0,
        "completed": False,
        "errors": [],
        "steps": [],
    }

    _emit(emit, "workflow_started", {"query": query, "image_url": image_url})

    for iteration in range(max_iterations):
        supervisor_update = supervisor_node(state)
        state = _merge_state(state, supervisor_update)
        _emit_latest_step(emit, state)

        action = state.get("next_action", "end")
        if action == "end":
            state["completed"] = True
            break

        node = NODE_REGISTRY[action]
        _emit(emit, "node_started", {"action": action, "iteration": iteration + 1})
        node_update = node(state)
        state = _merge_state(state, node_update)
        _emit_latest_step(emit, state)

        if action == "recommend":
            state["completed"] = True
            break

    if not state.get("completed"):
        node_update = recommend_node(state)
        state = _merge_state(state, node_update)
        _emit_latest_step(emit, state)
        state["completed"] = True

    final_payload = {
        "intent": state.get("intent").model_dump() if state.get("intent") else None,
        "stats": {
            "avg_price": state.get("avg_price"),
            "min_price": state.get("min_price"),
            "max_price": state.get("max_price"),
        },
        "recommendation": state.get("recommendation").model_dump() if state.get("recommendation") else None,
        "ranked_products": [item.model_dump() for item in state.get("ranked_products", [])],
        "shopping_results": [item.model_dump() for item in state.get("shopping_results", [])],
        "lens_results": [item.model_dump() for item in state.get("lens_results", [])],
        "errors": state.get("errors", []),
        "steps": [item.model_dump() for item in state.get("steps", [])],
    }
    _emit(emit, "workflow_completed", final_payload)
    return state


def _merge_state(state: PricingState, update: Dict[str, Any]) -> PricingState:
    merged: Dict[str, Any] = dict(state)
    for key, value in update.items():
        if key in {"steps", "errors"}:
            merged[key] = value
        else:
            merged[key] = value
    return merged  # type: ignore[return-value]


def _emit(emit: EventEmitter, event_type: str, payload: Dict[str, Any]) -> None:
    if emit:
        emit(event_type, payload)


def _emit_latest_step(emit: EventEmitter, state: PricingState) -> None:
    if emit and state.get("steps"):
        emit("step", state["steps"][-1].model_dump())
