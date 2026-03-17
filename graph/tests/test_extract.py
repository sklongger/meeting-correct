import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from graph.extract_graph import build_extract_graph


def test_extract_graph():
    graph = build_extract_graph()

    result = graph.invoke(
        {
            "text": "今天天气很好。",
            "corrected_text": "",
            "facts": [],
        }
    )

    print("Result:", result)
    assert "corrected_text" in result
    assert "facts" in result


if __name__ == "__main__":
    test_extract_graph()
    print("Extract graph test passed!")
