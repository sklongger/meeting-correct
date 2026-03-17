import time
import json
import threading
import queue
import sys
from datetime import datetime

from core.asr import run_asr
from core.fact_checker import create_fact_checker

RESULTS_JSON = "fact_check_results.json"
RESULTS_MD = "fact_check_results.md"
TRANSCRIPT_FILE = "transcript.txt"


class MeetingAssistant:
    def __init__(self):
        self.fact_checker = create_fact_checker(overlap_chars=200, min_new_chars=10)
        self.full_text = ""
        self.last_saved_text = ""
        self.text_queue = queue.Queue(maxsize=100)
        self.worker_running = False
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)

    def on_asr_result(self, text):
        self.full_text += text + " "
        new_text = (
            text[len(self.last_saved_text) :].strip()
            if text.startswith(self.last_saved_text)
            else text
        )
        if new_text:
            self.last_saved_text = text
            with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f:
                f.write(new_text + "\n")
        try:
            self.text_queue.put_nowait((text, time.time()))
        except queue.Full:
            pass

    def _worker(self):
        last_check = 0
        busy = False
        while self.worker_running or busy:
            try:
                text, _ = self.text_queue.get(timeout=1)
                if time.time() - last_check < 3:
                    continue
                last_check = time.time()
                busy = True
                print(f"[ASR] {text}")
                facts = self.fact_checker.check(self.full_text)
                busy = False
                if facts:
                    print(f"[✅] 发现 {len(facts)} 条事实")
                self._save()
            except queue.Empty:
                if time.time() - last_check >= 5 and self.full_text:
                    last_check = time.time()
                    busy = True
                    try:
                        facts = self.fact_checker.check(self.full_text)
                    except:
                        facts = []
                    busy = False
                    if facts:
                        print(f"[✅] 发现 {len(facts)} 条事实")
                    self._save()
            except Exception as e:
                busy = False
                print(f"[❌] {e}")

    def _save(self):
        results = self.fact_checker.get_summary()["results"]
        with open(RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        with open(RESULTS_MD, "w", encoding="utf-8") as f:
            f.write(f"# 事实核查结果\n生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
            for i, r in enumerate(results, 1):
                status = "✅" if r.get("verified") else "❌"
                f.write(
                    f"## {i}. {status}\n**主张**: {r.get('claim', '')}\n\n**摘要**: {r.get('summary', '')}\n\n---\n\n"
                )

    def run(self, demo_mode=False):
        print(f"会议事实核查助手 | 文本：{TRANSCRIPT_FILE} | 结果：{RESULTS_JSON}\n")
        self.worker_running = True
        self.worker_thread.start()
        try:
            if demo_mode:
                text = "今天我在新闻上看到，2024 年北京举办了冬季奥运会，现场有超过 10 万人参加。周杰伦也会来现场表演。中国首都是北京。"
                self.full_text = text
                self.text_queue.put((text, time.time()))
                print("按 Ctrl+C 退出")
                while True:
                    time.sleep(1)
            run_asr(self.on_asr_result, vad_model_path="models/silero_vad.onnx")
        except KeyboardInterrupt:
            print("\n退出中...")
        finally:
            self.worker_running = False
            self.worker_thread.join(timeout=60)
            print("已退出")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="会议事实核查助手")
    parser.add_argument("--demo", action="store_true", help="演示模式")
    args = parser.parse_args()

    MeetingAssistant().run(demo_mode=args.demo)
    args = parser.parse_args()

    MeetingAssistant().run(
        demo_mode=args.demo, use_vad=args.vad, vad_model_path=args.vad_model
    )
