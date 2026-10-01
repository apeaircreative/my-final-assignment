"""Application-level safety checks for retrieved corpus content."""

from collections.abc import Iterable
from bootcamp_agent.retrieval import ScoredChunk

def contains_instruction_like_text(chunks: Iterable[ScoredChunk]) -> bool:
    """Return True when retrieved text contains an instruction-like prompt injection."""
    for scored_chunk in chunks:
        text = scored_chunk.chunk.text.casefold()
        if "ignore previous instructions" in text:
            return True
    return False