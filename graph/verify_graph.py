from langgraph.graph import StateGraph, END
from graph.state import VerifyState
from graph.nodes import SearchNode, VerifyNode


def build_verify_graph():
    graph = StateGraph(VerifyState)

    graph.add_node("search", SearchNode())
    graph.add_node("verify", VerifyNode())

    graph.set_entry_point("search")
    graph.add_edge("search", "verify")
    graph.add_edge("verify", END)

    return graph.compile()
