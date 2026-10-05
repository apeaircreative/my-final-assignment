"""Application-level safety checks for retrieved corpus content."""

import re
from collections.abc import Iterable

from bootcamp_agent.retrieval import ScoredChunk


INSTRUCTION_PHRASES = (
    "ignore previous instructions",
    "ignore prior instructions",
    "ignore earlier instructions",
    "disregard previous instructions",
    "disregard prior instructions",
    "disregard earlier instructions",
)

INSTRUCTION_PATTERNS = (
    re.compile(
        r'(?<!["\'])\b(?:ignore|disregard)\s+'
        r'(?:(?:all|your)\s+)?'
        r'(?:previous|prior|earlier)\s+instructions\b',
        re.IGNORECASE,
    ),
)


def contains_instruction_like_text(chunks: Iterable[ScoredChunk]) -> bool:
    """Return True when retrieved text contains an instruction-like prompt injection."""

    for scored_chunk in chunks:
        text = scored_chunk.chunk.text
        lowered = text.casefold()

        if any(phrase in lowered for phrase in INSTRUCTION_PHRASES):
            return True

        if any(pattern.search(text) for pattern in INSTRUCTION_PATTERNS):
            return True

    return False