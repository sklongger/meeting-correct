import json
from graph.nodes.base import BaseNode
from graph.state import ExtractState
from graph.prompts.extract import EXTRACT_PROMPT


class ExtractNode(BaseNode[ExtractState]):
    def __call__(self, state: ExtractState) -> dict:
        text = state["corrected_text"] or state["text"]
        messages = [
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": text},
        ]

        try:
            response = self.llm.chat(messages)
            facts = json.loads(response)

            if not isinstance(facts, list):
                facts = []

            return {"facts": facts}
        except Exception as e:
            print(f"[提取错误] {e}")
            return {"facts": []}
