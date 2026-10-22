"""Application wrapper around the course-provided source-grounded assistant.

`YourAgent.run()` adds provider-failure and timeout handling, citation and
review policies, and a post-generation check of retrieved instruction-like
content. Retrieval, context construction, generation, parsing, and citation-ID
validation belong to the pinned course pipeline.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from bootcamp_agent.agent import (
    AgentResult,
    AnswerParseError,
    TraceEvent,
    _refusal,
    answer_question,
    parse_research_answer,
)
from bootcamp_agent.config import load_settings
from bootcamp_agent.documents import Document, load_corpus
from bootcamp_agent.llm import LLMClient, get_client
from bootcamp_agent.ollama import OllamaError
from bootcamp_agent.retrieval import retrieve
from bootcamp_agent.schema import ResearchAnswer
from bootcamp_agent.tools import Tool, build_tools

from safety import contains_instruction_like_text

#: The six course documents, copied in by `bootcamp capstone new`. Versioned
#: input: nothing you build writes to it.
CORPUS_DIR = Path(__file__).resolve().parent / "data" / "corpus"


@dataclass
class SessionState:
    preferences: dict = field(default_factory=dict)
    episodes: list[str] = field(default_factory=list)

    def reset(self) -> None:
        self.preferences.clear()
        self.episodes.clear()


class MemoryStore:
    """
    caller → remember() → copy → store → copy → caller

    Prevents caller mutations from changing stored memory.
    """

    def __init__(self) -> None:
        self._data: dict[tuple[str, str], object] = {}

    def remember(self, user_id: str, key: str, value: object) -> None:
        if not user_id:
            raise ValueError("user_id must not be empty")

        self._data[(user_id, key)] = deepcopy(value)

    def recall(self, user_id: str, key: str) -> object | None:
        if not user_id:
            raise ValueError("user_id must not be empty")

        value = self._data.get((user_id, key))
        return deepcopy(value)


def answer_with_state(
    question: str,
    state: SessionState,
    client: LLMClient,
):
    prompt = question
    if state.preferences.get("answer_style") == "short":
        prompt += " (answer briefly)"

    documents = load_corpus(CORPUS_DIR)
    result = answer_question(
        prompt,
        documents,
        client,
    )

    state.episodes.append(f"Q: {question[:60]}")
    state.episodes = state.episodes[-5:]

    return result


PROMPT_EXTENSION = (
    "When the provided context uses specific technical terminology that directly "
    "supports the answer, preserve that terminology rather than replacing it "
    "with a broader paraphrase.\n"
)


class PromptExtensionClient:
    def __init__(self, client: LLMClient) -> None:
        self.client = client

    def complete(self, system: str, user: str) -> str:
        return self.client.complete(
            system=system + "\n" + PROMPT_EXTENSION,
            user=user,
        )


class TimeoutClient:
    def __init__(self, client: LLMClient, timeout_s: float) -> None:
        self.client = client
        self.timeout_s = timeout_s

    def complete(self, system: str, user: str) -> str:
        result: list[str] = []
        error: list[BaseException] = []

        def call() -> None:
            try:
                result.append(self.client.complete(system=system, user=user))
            except BaseException as exc:
                error.append(exc)

        worker = threading.Thread(target=call, daemon=True)
        worker.start()
        worker.join(timeout=self.timeout_s)

        if worker.is_alive():
            raise TimeoutError(f"LLM call timed out after {self.timeout_s} seconds")
        if error:
            raise error[0]
        return result[0]


class _ReviewFlagObserver:
    """Observe only the parsed review flag for one answer request."""

    def __init__(self, client: LLMClient) -> None:
        self.client = client
        self.review_requested: bool | None = None

    def complete(self, system: str, user: str) -> str:
        raw = self.client.complete(system=system, user=user)
        try:
            answer = parse_research_answer(raw)
        except AnswerParseError:
            return raw
        self.review_requested = answer.needs_human_review
        return raw


def _is_standard_refusal(answer: ResearchAnswer) -> bool:
    refusal = _refusal()
    return (
        answer.answer == refusal.answer
        and answer.citations == refusal.citations
        and answer.confidence == refusal.confidence
        and answer.needs_human_review is refusal.needs_human_review
    )


def _has_citation_sanitization_event(result: AgentResult) -> bool:
    return any(
        event.kind == "decision" and event.detail.startswith("fabricated citations stripped:")
        for event in result.trace
    )


def _apply_review_policy(
    result: AgentResult,
    original_review: bool | None,
) -> AgentResult:
    if _is_standard_refusal(result.answer):
        return result

    if original_review is True:
        decision = "model requested human review; flagged refusal"
    elif original_review is None:
        decision = "review provenance unavailable; flagged refusal"
    elif not result.answer.needs_human_review:
        return result
    elif (
        result.answer.citations
        and result.answer.confidence <= 0.2
        and _has_citation_sanitization_event(result)
    ):
        return result
    else:
        decision = "review state inconsistent with citation sanitization; flagged refusal"

    return AgentResult(
        answer=_refusal(),
        trace=result.trace + (TraceEvent("decision", decision),),
    )


class YourAgent:
    """The agent the tests and the grader run. Make it yours."""

    #: Shared by the pre-answer safety check and the answer pipeline.
    top_k: int = 4

    #: How long one provider call may take before the agent gives up with a
    #: flagged refusal. The contract test sets this low to verify bounded waits.
    timeout_s: float = 120.0

    def __init__(self, client: LLMClient | None = None) -> None:
        self.documents: list[Document] = load_corpus(CORPUS_DIR)
        self.client: LLMClient = client if client is not None else get_client(load_settings())
        # Every tool the agent can reach. Session 4's registry, read-only by
        # construction; session 12 has you classify each one, and the `tools`
        # contract test refuses anything not classified as a reader.
        self.tools: dict[str, Tool] = build_tools(self.documents, self.client)

    def run(self, question: str) -> AgentResult:
        """One question, answered or refused, with the trace of how.

        USER QUESTION
            ↓
        RETRIEVE TOP self.top_k CHUNKS
            ↓
        COURSE PIPELINE
             ↓
        RETRIEVE → BUILD CONTEXT → LLM → PARSE → VERIFY CITATIONS
             ↓
         APPLICATION SAFETY CHECK
             ↓
         instruction-like retrieved content?
             ├── YES → flagged refusal
             └── NO  → return course result
        """
        retrieved = retrieve(
            question,
            self.documents,
            top_k=self.top_k,
        )

        try:
            prompt_client = PromptExtensionClient(self.client)
            timeout_client = TimeoutClient(prompt_client, self.timeout_s)
            review_observer = _ReviewFlagObserver(timeout_client)
            result = answer_question(
                question,
                self.documents,
                review_observer,
                max_tool_calls=3,
                top_k=self.top_k,
            )
        except (ConnectionError, OllamaError, TimeoutError) as error:
            return AgentResult(
                answer=_refusal(),
                trace=(
                    TraceEvent(
                        "retrieve",
                        f"top_k={self.top_k} -> "
                        f"{[(s.chunk.doc_id, s.chunk.position) for s in retrieved]}",
                    ),
                    TraceEvent(
                        "llm_call",
                        f"provider call failed: {type(error).__name__}",
                    ),
                    TraceEvent(
                        "decision",
                        "provider call failed; flagged refusal",
                    ),
                ),
            )

        if contains_instruction_like_text(retrieved):
            return AgentResult(
                answer=_refusal(),
                trace=result.trace
                + (
                    TraceEvent(
                        "decision",
                        "retrieved content contained instruction-like text; flagged refusal",
                    ),
                ),
            )

        if not result.answer.citations:
            if _is_standard_refusal(result.answer):
                return result
            return AgentResult(
                answer=_refusal(),
                trace=result.trace
                + (
                    TraceEvent(
                        "decision",
                        "no valid citations remained; flagged refusal",
                    ),
                ),
            )

        return _apply_review_policy(result, review_observer.review_requested)

    def __call__(self, question: str) -> ResearchAnswer:
        return self.run(question).answer
