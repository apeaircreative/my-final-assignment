from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import YourAgent
from bootcamp_agent import final_grade as grade
from bootcamp_agent.retrieval import retrieve


QUESTIONS_PATH = (
    ROOT.parent
    / "dev3pack-cohort-2026-09"
    / "src"
    / "bootcamp_agent"
    / "final_practice.jsonl"
)


def main() -> None:
    cases = dict(grade.load_questions(QUESTIONS_PATH))
    case = cases["fa-05"]

    agent = YourAgent()
    result = agent.run(case.question)
    passed, dimensions, _ = grade.evaluate_answer(case, result.answer)

    print("=" * 80)
    print("fa-05 DIAGNOSTIC")
    print("=" * 80)

    print("\nQuestion:")
    print(case.question)

    print("\nCritical:", case.critical)
    print("Expected behavior:", case.expected_behavior)

    print("\nExpected document IDs:", case.expected_doc_ids)
    print("Allowed document IDs:", case.allowed_doc_ids)

    print("\nRequired concepts:")
    for number, group in enumerate(case.required_concepts, 1):
        print(f"  Group {number}: {list(group)}")

    print("\nForbidden concepts:")
    print(list(case.forbidden_concepts))

    print("\n" + "-" * 80)
    print("GRADER RESULT")
    print("-" * 80)

    print("Passed:", passed)

    for name, value in dimensions.items():
        print(f"  {name}: {value}")

    print("\nFailed gates:")
    print(", ".join(
        name for name, value in dimensions.items()
        if not value
    ) or "none")

    answer = result.answer

    print("\n" + "-" * 80)
    print("ANSWER")
    print("-" * 80)

    print(answer.answer)
    print("\nCitations:", answer.citations)
    print("Confidence:", answer.confidence)
    print("Needs human review:", answer.needs_human_review)

    print("\n" + "-" * 80)
    print("RETRIEVED CHUNKS")
    print("-" * 80)

    retrieved = retrieve(
        case.question,
        agent.documents,
        top_k=4,
    )

    for rank, scored in enumerate(retrieved, 1):
        print(
            f"\n[{rank}] "
            f"doc={scored.chunk.doc_id!r} "
            f"position={scored.chunk.position} "
            f"score={scored.score:.4f}"
        )
        print(scored.chunk.text)

    print("\n" + "-" * 80)
    print("TRACE")
    print("-" * 80)

    for event in result.trace:
        print(event)


if __name__ == "__main__":
    main()