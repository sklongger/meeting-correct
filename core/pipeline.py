import json
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, List, Dict

from graph.extract_graph import build_extract_graph
from graph.verify_graph import build_verify_graph
from core.sentence_buffer import SentenceBuffer, Sentence


RESULTS_JSON = "data/fact_check_results.json"
RESULTS_MD = "data/fact_check_results.md"
TRANSCRIPT_FILE = "data/transcript.txt"


class FactCheckPipeline:
    def __init__(
        self,
        min_sentence_length: int = 15,
        max_sentence_length: int = 500,
        sentence_timeout: float = 2.0,
        max_verify_workers: int = 5,
    ):
        self.sentence_buffer = SentenceBuffer(
            min_length=min_sentence_length,
            max_length=max_sentence_length,
            timeout_seconds=sentence_timeout,
        )

        self.fact_queue: queue.Queue = queue.Queue(maxsize=100)

        self.extract_lock = threading.Lock()
        self.extracting = False

        self.full_text = ""
        self.verified_results: List[Dict] = []
        self.results_lock = threading.Lock()

        self.running = False
        self.verify_thread: Optional[threading.Thread] = None
        self.timeout_thread: Optional[threading.Thread] = None
        self.verify_executor = ThreadPoolExecutor(max_workers=max_verify_workers)

        self.extract_graph = build_extract_graph()
        self.verify_graph = build_verify_graph()

    def start(self):
        self.running = True

        self.verify_thread = threading.Thread(target=self._verify_worker, daemon=True)
        self.verify_thread.start()

        self.timeout_thread = threading.Thread(
            target=self._timeout_checker, daemon=True
        )
        self.timeout_thread.start()

        print("[Pipeline] 已启动")

    def stop(self):
        self.running = False

        if self.verify_thread:
            self.verify_thread.join(timeout=5)
        if self.timeout_thread:
            self.timeout_thread.join(timeout=5)

        self.verify_executor.shutdown(wait=False)

        print("[Pipeline] 已停止")

    def submit_text(self, text: str):
        self.full_text += text + " "

        sentence = self.sentence_buffer.append(text, self.full_text)

        if sentence:
            self._try_start_extract(sentence)

    def _try_start_extract(self, sentence: Sentence):
        with self.extract_lock:
            if self.extracting:
                print(f"[跳过] 当前有提取任务: {sentence.text[:30]}...")
                return

            self.extracting = True

        threading.Thread(
            target=self._do_extract,
            args=(sentence,),
            daemon=True,
        ).start()

    def _do_extract(self, sentence: Sentence):
        try:
            result = self.extract_graph.invoke(
                {
                    "text": sentence.text,
                    "corrected_text": "",
                    "facts": [],
                }
            )

            facts = result.get("facts", [])

            if facts:
                for fact in facts:
                    try:
                        self.fact_queue.put_nowait(
                            {
                                "claim": fact.get("claim", ""),
                                "original_text": fact.get("fact", ""),
                            }
                        )
                        print(f"[提取] {fact.get('claim', '')[:40]}...")
                    except queue.Full:
                        print(f"[队列满] 跳过: {fact.get('claim', '')[:30]}...")

        except Exception as e:
            print(f"[提取错误] {e}")
        finally:
            with self.extract_lock:
                self.extracting = False

    def _timeout_checker(self):
        while self.running:
            time.sleep(0.5)

            sentence = self.sentence_buffer.check_timeout()
            if sentence:
                self._try_start_extract(sentence)

    def _verify_worker(self):
        while self.running:
            try:
                fact = self.fact_queue.get(timeout=1)
            except queue.Empty:
                continue

            self.verify_executor.submit(self._do_verify, fact)

    def _do_verify(self, fact: dict):
        try:
            result = self.verify_graph.invoke(
                {
                    "claim": fact["claim"],
                    "original_text": fact.get("original_text", ""),
                    "search_result": "",
                    "verified": False,
                    "summary": "",
                }
            )

            self._save_result(result)

            status = "✅" if result["verified"] else "❌"
            print(f"[{status}] {result['claim'][:40]}...")

        except Exception as e:
            print(f"[验证错误] {e}")

    def _save_result(self, new_result: dict):
        with self.results_lock:
            claim = new_result["claim"]

            for i, existing in enumerate(self.verified_results):
                if self._should_merge(claim, existing["claim"]):
                    if len(claim) > len(existing["claim"]):
                        self.verified_results[i] = {
                            "claim": claim,
                            "verified": new_result["verified"],
                            "summary": new_result["summary"],
                        }
                        print(f"[合并更新] {existing['claim'][:30]}...")
                    return

            self.verified_results.append(
                {
                    "claim": claim,
                    "verified": new_result["verified"],
                    "summary": new_result["summary"],
                    "time": datetime.now().strftime("%H:%M:%S"),
                }
            )

            self._write_to_file()

    def _should_merge(self, claim1: str, claim2: str) -> bool:
        if claim1 == claim2:
            return True

        if claim1 in claim2 or claim2 in claim1:
            return True

        words1 = set(claim1)
        words2 = set(claim2)
        if words1 and words2:
            overlap = len(words1 & words2) / min(len(words1), len(words2))
            if overlap > 0.8:
                return True

        return False

    def _write_to_file(self):
        import os

        os.makedirs(os.path.dirname(RESULTS_JSON), exist_ok=True)

        with open(RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(self.verified_results, f, ensure_ascii=False, indent=2)

        with open(RESULTS_MD, "w", encoding="utf-8") as f:
            f.write(f"# 事实核查结果\n生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
            for i, r in enumerate(self.verified_results, 1):
                status = "✅" if r.get("verified") else "❌"
                f.write(
                    f"## {i}. {status}\n**主张**: {r.get('claim', '')}\n\n**摘要**: {r.get('summary', '')}\n\n---\n\n"
                )

    def get_results(self) -> List[Dict]:
        with self.results_lock:
            return self.verified_results.copy()

    def get_full_text(self) -> str:
        return self.full_text
