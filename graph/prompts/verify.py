VERIFY_PROMPT = """验证事实真假：

事实：{fact}

搜索结果：
{search_result}

返回 JSON：{{"verified": true/false, "summary": "简要总结验证结果，说明为什么是真或假"}}
只输出 JSON，不要其他内容。"""
