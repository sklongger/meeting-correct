import time
import threading
from typing import Optional
from dataclasses import dataclass


@dataclass
class Sentence:
    text: str
    position_start: int
    position_end: int
    timestamp: float


class SentenceBuffer:
    SENTENCE_ENDINGS = (
        "。",
        "！",
        "！",
        "？",
        "？",
        "；",
        "；",
        ".",
        "!",
        "?",
        ";",
        "\n",
    )

    def __init__(
        self,
        min_length: int = 15,
        max_length: int = 500,
        timeout_seconds: float = 2.0,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.timeout_seconds = timeout_seconds
        self.lock = threading.Lock()

        self.buffer = ""
        self.buffer_start_pos = 0
        self.last_append_time = 0.0
        self.full_text_len = 0

    def append(self, text: str, full_text: str) -> Optional[Sentence]:
        with self.lock:
            now = time.time()
            self.full_text_len = len(full_text)

            if not self.buffer:
                self.buffer_start_pos = max(0, self.full_text_len - len(text))

            self.buffer += text
            self.last_append_time = now

            return self._try_flush()

    def check_timeout(self) -> Optional[Sentence]:
        with self.lock:
            if not self.buffer:
                return None

            elapsed = time.time() - self.last_append_time
            if (
                elapsed >= self.timeout_seconds
                and len(self.buffer) >= self.min_length // 2
            ):
                return self._flush()
            return None

    def _try_flush(self) -> Optional[Sentence]:
        buffer_len = len(self.buffer)

        if buffer_len >= self.max_length:
            return self._flush()

        if buffer_len >= self.min_length and self.buffer.rstrip().endswith(
            self.SENTENCE_ENDINGS
        ):
            return self._flush()

        return None

    def _flush(self) -> Sentence:
        sentence = Sentence(
            text=self.buffer.strip(),
            position_start=self.buffer_start_pos,
            position_end=self.buffer_start_pos + len(self.buffer),
            timestamp=time.time(),
        )
        self.buffer = ""
        self.buffer_start_pos = 0
        return sentence

    def get_pending_length(self) -> int:
        with self.lock:
            return len(self.buffer)
