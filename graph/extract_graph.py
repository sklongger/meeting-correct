from langgraph.graph import StateGraph, END
from graph.state import ExtractState
from graph.nodes import CorrectNode, ExtractNode


def build_extract_graph():
    graph = StateGraph(ExtractState)

    graph.add_node("correct", CorrectNode())
    graph.add_node("extract", ExtractNode())

    graph.set_entry_point("correct")
    graph.add_edge("correct", "extract")
    graph.add_edge("extract", END)

    return graph.compile()
