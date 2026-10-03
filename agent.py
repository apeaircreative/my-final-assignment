"""Your capstone agent: the one your README demos and your CI grades.

It starts as the final assignment's starter, unchanged: the same `YourAgent`,
the same `answer_question` pipeline from the course package, the same budget.
Calling it returns a `bootcamp_agent.schema.ResearchAnswer`, the contract the
whole course used, so everything you built in the sessions plugs in here.
`run(question)` returns the whole `AgentResult`, trace included, which is what
`uv run bootcamp capstone trace "<question>"` prints.

As shipped it is honest and insufficient. On the offline `FakeLLM` it refuses
what it should refuse and answers nothing else, and some contract tests in
`tests/test_contract.py` are marked as expected failures on purpose. Making them
pass is the work. What to add, session by session, is in `docs/` (each file
names the session that fills it).

The provider comes from `.env` (`BOOTCAMP_PROVIDER`), and falls back to the
offline `FakeLLM`. Keys live only in `.env`, which git ignores.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from pathlib import Path
from dataclasses import dataclass, field

from bootcamp_agent.agent import AgentResult, TraceEvent, _refusal, answer_question
from bootcamp_agent.retrieval import retrieve
from bootcamp_agent.config import load_settings
from bootcamp_agent.documents import Document, load_corpus
from bootcamp_agent.llm import LLMClient, get_client
from bootcamp_agent.schema import ResearchAnswer
from bootcamp_agent.tools import Tool, build_tools
from bootcamp_agent.ollama import OllamaError


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

class YourAgent:
    """The agent the tests and the grader run. Make it yours."""

    #: How long one provider call may take before the agent gives up with a
    #: flagged refusal. NOT ENFORCED YET: the starter waits for ever, which is
    #: why the `timeout` contract test is marked xfail. The test sets this low
    #: and expects an answer inside a second.
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
        RETRIEVE TOP 3 CHUNKS
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
            top_k=3,
        )

        try:
            timeout_client = TimeoutClient(self.client, self.timeout_s)
            result = answer_question(
                question,
                self.documents,
                timeout_client,
                max_tool_calls=3,
                top_k=3,
        )
        except (ConnectionError, OllamaError, TimeoutError) as error:
            return AgentResult(
                answer=_refusal(),
                trace=(
                    TraceEvent(
                        "retrieve",
                        f"top_k=3 -> {[(s.chunk.doc_id, s.chunk.position) for s in retrieved]}",
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

        return result

    def __call__(self, question: str) -> ResearchAnswer:
        return self.run(question).answer
