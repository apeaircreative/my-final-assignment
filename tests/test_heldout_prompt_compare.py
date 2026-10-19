from __future__ import annotations

import json

from bootcamp_agent.documents import load_corpus
from bootcamp_agent.retrieval import retrieve

from agent import CORPUS_DIR, YourAgent
from scripts.compare_heldout_prompts import CASE_FILE, _load_cases, _run_case


def test_heldout_cases_retrieve_their_expected_source() -> None:
    case_set = _load_cases(CASE_FILE)
    documents = load_corpus(CORPUS_DIR)

    for case in case_set["cases"]:
        retrieved_ids = {
            item.chunk.doc_id for item in retrieve(case["question"], documents, top_k=4)
        }
        assert set(case["review_reference"]["source_ids"]) <= retrieved_ids, case["id"]


def test_review_reference_is_not_included_in_the_model_prompt() -> None:
    case_set = _load_cases(CASE_FILE)
    case = case_set["cases"][0]
    calls = []

    class RecordingClient:
        def complete(self, system: str, user: str) -> str:
            calls.append((system, user))
            return json.dumps(
                {
                    "answer": "A concise answer.",
                    "citations": ["agent-loops"],
                    "confidence": 0.9,
                    "needs_human_review": False,
                }
            )

    _run_case(YourAgent(client=RecordingClient()), case, "baseline", top_k=4)

    assert len(calls) == 1
    _, user_prompt = calls[0]
    for point in case["review_reference"]["key_points"]:
        assert point not in user_prompt
