import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import time
from core.sentence_buffer import SentenceBuffer


def test_sentence_complete():
    buffer = SentenceBuffer(min_length=5, timeout_seconds=5.0)

    result = buffer.append("今天天气很好。", "今天天气很好。")
    assert result is not None
    assert "今天天气很好" in result.text


def test_sentence_timeout():
    buffer = SentenceBuffer(min_length=5, timeout_seconds=0.5)

    buffer.append("这是一段话", "这是一段话")

    result = buffer.check_timeout()
    assert result is None

    time.sleep(0.6)
    result = buffer.check_timeout()
    assert result is not None


def test_max_length():
    buffer = SentenceBuffer(min_length=10, max_length=20, timeout_seconds=5.0)

    long_text = "这是一段很长的文本没有句末标点需要强制输出"
    result = buffer.append(long_text, long_text)

    assert result is not None
    assert len(result.text) >= 20


if __name__ == "__main__":
    test_sentence_complete()
    test_sentence_timeout()
    test_max_length()
    print("All tests passed!")
