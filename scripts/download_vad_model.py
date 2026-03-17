#!/usr/bin/env python3
"""下载/复制 Silero VAD 模型"""

import os
import shutil
import urllib.request

MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"
)
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "silero_vad.onnx")

# 可选：从 baby-english 项目复制
BABY_ENGLISH_MODEL = (
    "/Users/sklongger/work/baby-english/sherpa-onnx-dev/models/vad/silero_vad.onnx"
)


def download_model():
    if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 0:
        print(f"模型已存在：{MODEL_PATH} ({os.path.getsize(MODEL_PATH) / 1024:.1f}KB)")
        return MODEL_PATH

    os.makedirs(MODEL_DIR, exist_ok=True)

    # 优先从 baby-english 项目复制
    if os.path.exists(BABY_ENGLISH_MODEL):
        print(f"从 baby-english 项目复制：{BABY_ENGLISH_MODEL}")
        shutil.copy2(BABY_ENGLISH_MODEL, MODEL_PATH)
        print(f"模型已保存到：{MODEL_PATH}")
        return MODEL_PATH

    # 否则从网络下载
    print(f"正在从网络下载 Silero VAD 模型...")
    print(f"下载链接：{MODEL_URL}")

    def report_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = downloaded * 100 / total_size
            print(
                f"\r下载进度：{percent:.1f}% ({downloaded / 1024 / 1024:.2f}MB / {total_size / 1024 / 1024:.2f}MB)",
                end="",
            )

    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH, reporthook=report_hook)
    print()
    print(f"模型已保存到：{MODEL_PATH}")
    return MODEL_PATH


if __name__ == "__main__":
    download_model()
