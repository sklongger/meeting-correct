import os


class Config:
    QWEN_API_KEY = "sk-d3c0d98e6e23439c905955610e17efd5"
    QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    ALIYUN_ASR_APPKEY = os.getenv("ALIYUN_ASR_APPKEY", "")
    ALIYUN_ASR_ACCESS_KEY_ID = os.getenv("ALIYUN_ASR_ACCESS_KEY_ID", "")
    ALIYUN_ASR_ACCESS_KEY_SECRET = os.getenv("ALIYUN_ASR_ACCESS_KEY_SECRET", "")

    ASR_LANGUAGE = "zh-CN"
    SAMPLE_RATE = 16000

    FACT_CHECK_MODEL = "qwen-plus"
    SEARCH_MODEL = "qwen-plus"
    MERGE_WINDOW_SIZE = 20
