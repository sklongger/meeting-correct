import json
from graph.nodes.base import BaseNode
from graph.state import VerifyState
from graph.prompts.verify import VERIFY_PROMPT


class VerifyNode(BaseNode[VerifyState]):
    def __call__(self, state: VerifyState) -> dict:
        claim = state["claim"]
        search_result = state["search_result"]
        prompt = VERIFY_PROMPT.format(fact=claim, search_result=search_result)

        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            data = json.loads(response)

            return {
                "verified": data.get("verified", False),
                "summary": data.get("summary", ""),
                "original_text": state.get("original_text", ""),
            }
        except Exception as e:
            print(f"[验证错误] {e}")
            return {
                "verified": False,
                "summary": f"验证失败: {e}",
                "original_text": state.get("original_text", ""),
            }
