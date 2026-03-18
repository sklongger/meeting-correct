import json
from graph.nodes.base import BaseNode
from graph.state import ExtractState
from graph.prompts.correct import CORRECT_PROMPT


class CorrectNode(BaseNode[ExtractState]):
    def __call__(self, state: ExtractState) -> dict:
        text = state["text"]
        prompt = CORRECT_PROMPT.format(text=text)

        try:
            response = self.llm.correct([{"role": "user", "content": prompt}])
            print(f"[修正响应] {response[:200]}...")
            data = json.loads(response)
            corrected = data.get("corrected", text)
            changes = data.get("changes", [])

            if changes:
                print(f"[修正] {', '.join(changes)}")

            return {"corrected_text": corrected}
        except Exception as e:
            print(f"[修正错误] {e}")
            return {"corrected_text": text}
