from typing import TypedDict, List


class ExtractState(TypedDict):
    text: str
    corrected_text: str
    facts: List[dict]


class VerifyState(TypedDict):
    claim: str
    original_text: str
    search_result: str
    verified: bool
    summary: str
