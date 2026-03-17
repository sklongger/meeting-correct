import argparse
import os
import time
from datetime import datetime

from core.asr import run_asr
from core.pipeline import FactCheckPipeline, TRANSCRIPT_FILE, RESULTS_JSON


class MeetingAssistant:
    def __init__(self):
        os.makedirs(os.path.dirname(TRANSCRIPT_FILE), exist_ok=True)
        self.pipeline = FactCheckPipeline(
            min_sentence_length=15,
            max_sentence_length=500,
            sentence_timeout=2.0,
        )
        self.last_saved_text = ""

    def on_asr_result(self, text: str):
        new_text = self._get_new_text(text)
        if new_text:
            timestamp = datetime.now().strftime("[%H:%M:%S] ")
            with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f:
                f.write(timestamp + new_text + "\n")

        self.pipeline.submit_text(text)

    def _get_new_text(self, text: str) -> str:
        if text.startswith(self.last_saved_text):
            new = text[len(self.last_saved_text) :].strip()
        else:
            new = text.strip()
        self.last_saved_text = text
        return new

    def run(
        self, demo_mode: bool = False, vad_model_path: str = "models/silero_vad.onnx"
    ):
        print(f"会议事实核查助手")
        print(f"  转录文件: {TRANSCRIPT_FILE}")
        print(f"  结果文件: {RESULTS_JSON}")
        print()

        self.pipeline.start()

        try:
            if demo_mode:
                self._run_demo()
            else:
                run_asr(self.on_asr_result, vad_model_path=vad_model_path)
        except KeyboardInterrupt:
            print("\n退出中...")
        finally:
            self.pipeline.stop()
            print("已退出")

    def _run_demo(self):
        demo_texts = [
            "今天我在新闻上看到，",
            "2024年北京举办了冬季奥运会，",
            "现场有超过10万人参加。",
            "周杰伦也会来现场表演。",
            "中国首都是北京。",
        ]

        for text in demo_texts:
            print(f"[ASR] {text}")
            self.on_asr_result(text)
            time.sleep(1)

        print("\n演示完成，按 Ctrl+C 退出")
        while True:
            time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="会议实时语音事实核查助手")
    parser.add_argument("--demo", action="store_true", help="演示模式")
    parser.add_argument(
        "--vad-model", default="models/silero_vad.onnx", help="VAD 模型路径"
    )
    args = parser.parse_args()

    assistant = MeetingAssistant()
    assistant.run(demo_mode=args.demo, vad_model_path=args.vad_model)
