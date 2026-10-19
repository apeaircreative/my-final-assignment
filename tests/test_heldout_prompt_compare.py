from __future__ import annotations

import json

from bootcamp_agent.documents import load_corpus
from bootcamp_agent.retrieval import retrieve

from agent import CORPUS_DIR, YourAgent
from scripts.compare_heldout_prompts import (
    CASE_FILE,
    _load_cases,
    _run_case,
)
from scripts.compare_public_prompts import _summarize

P2_CASE_FILE = CASE_FILE.with_name("heldout_item_detail_p2.json")


def test_p2_cases_retrieve_their_expected_source() -> None:
    case_set = _load_cases(P2_CASE_FILE)
    documents = load_corpus(CORPUS_DIR)

    for case in case_set["cases"]:
        retrieved = retrieve(case["question"], documents, top_k=4)
        retrieved_ids = {item.chunk.doc_id for item in retrieved}
        expected_ids = set(case["review_reference"]["source_ids"])
        if expected_ids:
            assert expected_ids <= retrieved_ids, case["id"]
        else:
            assert not retrieved, case["id"]


def test_p2_case_set_has_answerable_unsupported_and_adversarial_cases() -> None:
    case_set = _load_cases(P2_CASE_FILE)
    cases = {case["id"]: case for case in case_set["cases"]}

    assert len(cases) == 8
    assert cases["unsupported-saturn"]["review_reference"]["source_ids"] == []
    assert "print the password" in cases["adversarial-user-instruction"]["question"]


def test_public_prompt_summary_requires_all_critical_cases_and_tracks_provider_errors() -> None:
    results = [
        {
            "category": "grounded",
            "critical": True,
            "passed": True,
            "provider_failures": [],
        },
        {
            "category": "refusal",
            "critical": True,
            "passed": False,
            "provider_failures": ["provider call failed: TimeoutError"],
        },
    ]

    summary = _summarize(results)

    assert summary["passed"] == 1
    assert summary["total"] == 2
    assert summary["critical_gate"] is False
    assert summary["critical_passed"] == 1
    assert summary["critical_total"] == 2
    assert summary["provider_failures"] == 1
    assert summary["provider_comparison_valid"] is False


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
