import json
from core.qwen_client import create_client
from core.config import Config

CORRECT_PROMPT = """检查文本是否有 ASR 识别错误（拼音、外文、乱码）。
如果没有明显错误，返回原文。
重要：绝对不要修改数字、时间、人名、地名、事件等事实内容。

文本：{text}

返回 JSON：{{"corrected": "修正后的文本", "changes": ["修改 1", "修改 2"]}}，如果没有修改，changes 为空数组。"""

EXTRACT_PROMPT = """从文本中提取需要核查的事实主张（数字、日期、人物、地点、事件等）。
输出 JSON 数组，每个元素包含：
- fact: 原文引用
- claim: 需要核查的具体主张（简洁陈述，不要包含核查结果）
- reason: 为什么需要核查

只输出 JSON，不要其他内容。

示例：
文本："昨天周杰伦在成都举办了演唱会"
输出：[{"fact": "昨天周杰伦在成都举办了演唱会", "claim": "周杰伦昨天在成都举办演唱会", "reason": "需要确认演出信息"}]"""

MERGE_PROMPT = """判断新主张是否与已有事实重复或可合并。
已有事实（{recent_count}条）：
{recent_facts}

新主张：
{new_claims}

返回 JSON：
{{"duplicates": ["重复 claim"], "merged": [{{"original_claim": "...", "merged_claim": "...", "merged_into_claim": "...", "verified": true/false, "summary": "..."}}], "new": ["新 claim"]}}"""

VERIFY_PROMPT = """验证事实真假：
事实：{fact}
搜索结果：{search_result}

返回 JSON：{{"verified": true/false, "summary": "简要总结"}}"""


class IncrementalFactChecker:
    def __init__(self, overlap_chars=200, min_new_chars=50, window_size=None):
        self.client = create_client()
        self.checked_position = 0
        self.overlap_chars = overlap_chars
        self.min_new_chars = min_new_chars
        self.window_size = window_size or Config.MERGE_WINDOW_SIZE
        self.verified_results = []

    def correct_text(self, text):
        """修正 ASR 识别错误（拼音、外文、乱码），保留原始事实内容"""
        prompt = CORRECT_PROMPT.format(text=text)
        try:
            response = json.loads(
                self.client.chat([{"role": "user", "content": prompt}])
            )
            corrected = response.get("corrected", text)
            changes = response.get("changes", [])
            if changes:
                print(f"[✏️ 修正] {', '.join(changes)}")
            return corrected
        except:
            return text

    def extract_facts(self, text):
        """从文本中提取事实主张"""
        messages = [
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": text},
        ]
        return json.loads(self.client.chat(messages))

    def verify_fact(self, fact):
        search_result = self.client.search(f"请搜索并返回结果：{fact}")
        prompt = VERIFY_PROMPT.format(fact=fact, search_result=search_result)
        data = json.loads(self.client.chat([{"role": "user", "content": prompt}]))
        data["sources"] = [search_result]
        return data

    def merge_claims(self, new_claims, recent_facts):
        if not recent_facts:
            return new_claims, [], []
        prompt = MERGE_PROMPT.format(
            recent_count=len(recent_facts),
            recent_facts=json.dumps(recent_facts, ensure_ascii=False, indent=2),
            new_claims=json.dumps(new_claims, ensure_ascii=False, indent=2),
        )
        data = json.loads(self.client.chat([{"role": "user", "content": prompt}]))
        return data.get("new", []), data.get("merged", []), data.get("duplicates", [])

    def check(self, full_text):
        if len(full_text[self.checked_position :]) < self.min_new_chars:
            return []

        # 步骤 1：修正 ASR 错误
        check_text = full_text[max(0, self.checked_position - self.overlap_chars) :]
        corrected_text = self.correct_text(check_text)
        if corrected_text != check_text:
            print(f"[✏️ 修正] {check_text[:30]}... → {corrected_text[:30]}...")

        # 步骤 2：从修正后的文本中提取事实
        facts = self.extract_facts(corrected_text)
        new_claims = [{"claim": f["claim"]} for f in facts]

        new_only, merged, dups = self.merge_claims(
            new_claims, self.verified_results[-self.window_size :]
        )

        for dup in dups:
            print(f"[⏭️] {dup}")

        new_facts = []
        for m in merged:
            for i, f in enumerate(self.verified_results):
                if f["claim"] == m["merged_into_claim"]:
                    self.verified_results[i] = {
                        "claim": m["merged_claim"],
                        "verified": m["verified"],
                        "summary": m["summary"],
                    }
                    new_facts.append(self.verified_results[i])
                    print(f"[🔄] {m['merged_claim'][:40]}...")
                    break

        for claim in new_only:
            claim_str = claim if isinstance(claim, str) else claim.get("claim")
            result = self.verify_fact(claim_str)
            fact = {
                "claim": claim_str,
                "verified": result.get("verified"),
                "summary": result.get("summary", ""),
            }
            new_facts.append(fact)
            self.verified_results.append(fact)
            status = "✅" if result.get("verified") else "❌"
            print(f"[{status}] {claim_str}: {result.get('summary', '')[:50]}")

        self.checked_position = len(full_text)
        return new_facts

    def get_summary(self):
        return {
            "verified": sum(1 for r in self.verified_results if r.get("verified")),
            "results": self.verified_results,
        }


def create_fact_checker(overlap_chars=200, min_new_chars=50, window_size=None):
    return IncrementalFactChecker(overlap_chars, min_new_chars, window_size)
