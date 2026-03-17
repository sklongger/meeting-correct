from graph.nodes.base import BaseNode
from graph.state import VerifyState


class SearchNode(BaseNode[VerifyState]):
    def __call__(self, state: VerifyState) -> dict:
        claim = state["claim"]

        try:
            search_result = self.llm.search(f"请搜索：{claim}")
            return {"search_result": search_result}
        except Exception as e:
            print(f"[搜索错误] {e}")
            return {"search_result": f"搜索失败: {e}"}
