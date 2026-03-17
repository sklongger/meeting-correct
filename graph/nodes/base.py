from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any

StateT = TypeVar("StateT")


class BaseNode(ABC, Generic[StateT]):
    def __init__(self):
        self._llm = None

    def with_llm(self, llm: Any) -> "BaseNode[StateT]":
        self._llm = llm
        return self

    @property
    def llm(self) -> Any:
        if self._llm is None:
            from core.qwen_client import create_client

            self._llm = create_client()
        return self._llm

    @abstractmethod
    def __call__(self, state: StateT) -> dict:
        pass
