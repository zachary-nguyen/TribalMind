"""LangGraph state machine builder for the TribalMind agent.

Wires all nodes together:
  START -> monitor -> (error? context : END) -> inference -> (fix? promotion -> ui : END)
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from tribalmind.graph.context import context_node
from tribalmind.graph.inference import inference_node
from tribalmind.graph.monitor import monitor_node
from tribalmind.graph.promotion import promotion_node
from tribalmind.graph.state import TribalState
from tribalmind.graph.ui import ui_node


def _route_after_monitor(state: TribalState) -> str:
    """Route based on whether the command produced an error."""
    return "context" if state.get("is_error") else "__end__"


def _route_after_inference(state: TribalState) -> str:
    """Route based on inference results."""
    if state.get("suggested_fix") and state.get("fix_confidence", 0) > 0.5:
        return "promotion"
    if state.get("context") and state["context"].has_matches:
        return "ui"
    return "__end__"


def build_graph() -> CompiledStateGraph:
    """Build and compile the TribalMind LangGraph state machine."""
    graph = StateGraph(TribalState)

    # Add nodes
    graph.add_node("monitor", monitor_node)
    graph.add_node("context", context_node)
    graph.add_node("inference", inference_node)
    graph.add_node("promotion", promotion_node)
    graph.add_node("ui", ui_node)

    # Wire edges
    graph.add_edge(START, "monitor")
    graph.add_conditional_edges(
        "monitor",
        _route_after_monitor,
        {"context": "context", "__end__": END},
    )
    graph.add_edge("context", "inference")
    graph.add_conditional_edges(
        "inference",
        _route_after_inference,
        {"promotion": "promotion", "ui": "ui", "__end__": END},
    )
    graph.add_edge("promotion", "ui")
    graph.add_edge("ui", END)

    return graph.compile()
