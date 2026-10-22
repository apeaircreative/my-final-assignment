from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bootcamp_agent import final_grade as grade  # noqa: E402
from bootcamp_agent.retrieval import retrieve  # noqa: E402

from agent import YourAgent  # noqa: E402

QUESTIONS_PATH = grade.PRACTICE_QUESTIONS


def main() -> None:
    if not QUESTIONS_PATH.is_file():
        raise RuntimeError(
            "Could not find final_practice.jsonl.\n"
            f"Expected the installed course package at: {QUESTIONS_PATH}"
        )

    cases = dict(grade.load_questions(QUESTIONS_PATH))
    agent = YourAgent()
    rows: dict[str, dict] = {}

    print(f"Questions: {QUESTIONS_PATH}")
    print("Running the full practice set once with Ollama...\n")

    for task_id, case in cases.items():
        result = agent.run(case.question)
        passed, dimensions, _ = grade.evaluate_answer(case, result.answer)
        failed = [name for name, ok in dimensions.items() if not ok]

        rows[task_id] = {
            "case": case,
            "result": result,
            "passed": passed,
            "dimensions": dimensions,
            "failed": failed,
        }

    print(f"{'Task':<8} {'Critical':<10} {'Result':<8} Failed gates")
    print("-" * 80)

    for task_id, row in rows.items():
        status = "PASS" if row["passed"] else "FAIL"
        failed = ", ".join(row["failed"]) or "-"

        print(
            f"{task_id:<8} "
            f"{str(row['case'].critical):<10} "
            f"{status:<8} "
            f"{failed}"
        )

    total = sum(row["passed"] for row in rows.values())
    critical_ok = all(
        row["passed"]
        for row in rows.values()
        if row["case"].critical
    )

    print("\nSUMMARY")
    print(f"Passed: {total}/{len(rows)}")
    print(f"Critical safety: {critical_ok}")

    row = rows["fa-01"]
    case = row["case"]
    result = row["result"]
    answer = result.answer

    print("\n" + "=" * 80)
    print("fa-01 DIAGNOSTIC")
    print("=" * 80)

    print("\nQuestion:")
    print(case.question)

    print("\nPassed:", row["passed"])

    print("\nDimensions:")
    for name, value in row["dimensions"].items():
        print(f"  {name}: {value}")

    print("\nFailed gates:", ", ".join(row["failed"]) or "none")

    print("\nAnswer:")
    print(answer.answer)

    print("\nCitations:", answer.citations)
    print("Confidence:", answer.confidence)
    print("Needs human review:", answer.needs_human_review)

    print("\nRequired concepts:")
    for number, group in enumerate(case.required_concepts, 1):
        hits = [
            phrase
            for phrase in group
            if grade._contains(answer.answer, phrase)
        ]

        print(f"  Group {number}:")
        print(f"    Expected: {list(group)}")
        print(f"    Matched:  {hits or 'NONE'}")

    print("\nRetrieved chunks:")
    retrieved = retrieve(
        case.question,
        agent.documents,
        top_k=agent.top_k,
    )

    for rank, scored in enumerate(retrieved, 1):
        print(
            f"  {rank}. "
            f"doc={scored.chunk.doc_id!r} "
            f"position={scored.chunk.position} "
            f"score={scored.score:.4f}"
        )
        print(f"     {scored.chunk.text[:300]!r}")

    print("\nTrace:")
    for event in result.trace:
        print(f"  {event}")


if __name__ == "__main__":
    main()