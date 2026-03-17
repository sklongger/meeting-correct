import json
from unittest.mock import MagicMock
import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import json
from unittest.mock import MagicMock
from graph.nodes.correct import CorrectNode
from graph.nodes.extract import ExtractNode
from graph.state import ExtractState


class MockLLM:
    def __init__(self, responses: list):
        self.responses = responses
        self.index = 0

    def chat(self, messages):
        response = self.responses[self.index]
        self.index += 1
        return response


def test_correct_node():
    mock_llm = MockLLM(['{"corrected": "今天天气很好", "changes": []}'])

    node = CorrectNode().with_llm(mock_llm)
    state: ExtractState = {
        "text": "今天天气很好",
        "corrected_text": "",
        "facts": [],
    }

    result = node(state)
    assert result["corrected_text"] == "今天天气很好"


def test_extract_node():
    mock_llm = MockLLM(
        [
            '[{"fact": "北京举办冬奥会", "claim": "北京举办冬奥会", "reason": "需要验证"}]'
        ]
    )

    node = ExtractNode().with_llm(mock_llm)
    state: ExtractState = {
        "text": "",
        "corrected_text": "北京举办了冬奥会",
        "facts": [],
    }

    result = node(state)
    assert len(result["facts"]) == 1
    assert result["facts"][0]["claim"] == "北京举办冬奥会"


if __name__ == "__main__":
    test_correct_node()
    test_extract_node()
    print("All node tests passed!")
