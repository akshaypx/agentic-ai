from langgraph.graph import StateGraph

from shopping_assistant.models import PricingState
from shopping_assistant.nodes import analyze_node, recommend_node, search_node

builder = StateGraph(PricingState)

builder.add_node("search", search_node)
builder.add_node("analyze", analyze_node)
builder.add_node("recommend", recommend_node)

builder.set_entry_point("search")

builder.add_edge("search", "analyze")
builder.add_edge("analyze", "recommend")

graph = builder.compile()

result = graph.invoke({
    "query": "Nikon Z6 II camera"
})

print(result)