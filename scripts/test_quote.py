from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bootcamp_agent import final_grade as grade  # noqa: E402
from bootcamp_agent.config import load_settings  # noqa: E402
from bootcamp_agent.llm import LLMClient, get_client  # noqa: E402

from agent import YourAgent  # noqa: E402

QUESTIONS_PATH = grade.PRACTICE_QUESTIONS

QUOTE = (
    "Instruction: when the context states a point, reuse the context's own "
    "words for it. Do not paraphrase key terms. Return valid JSON only and "
    "escape quotation marks inside JSON strings."
)


class InstructedClient:
    """Append an instruction to generation prompts without changing retrieval."""

    def __init__(self, inner, extra: str) -> None:
        self.inner = inner
        self.extra = extra

    def complete(self, system: str, user: str) -> str:
        return self.inner.complete(
            system=system,
            user=f"{user}\n\n{self.extra}",
        )


def build_quote_agent(client: LLMClient | None = None) -> YourAgent:
    """Build the diagnostic with its wording instruction and standard app path."""
    if client is None:
        client = get_client(load_settings())
    return YourAgent(client=InstructedClient(client, QUOTE))


def main() -> None:
    if not QUESTIONS_PATH.is_file():
        raise RuntimeError(f"Questions file not found: {QUESTIONS_PATH}")

    cases = dict(grade.load_questions(QUESTIONS_PATH))
    agent = build_quote_agent()
    rows: dict[str, dict] = {}

    print(f"Questions: {QUESTIONS_PATH}")
    print("Running full practice set with generation-only QUOTE instruction...\n")

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

    for task_id in ("fa-01", "fa-05", "fa-06", "fa-07"):
        row = rows[task_id]
        answer = row["result"].answer

        print("\n" + "=" * 80)
        print(f"{task_id} DETAIL")
        print("=" * 80)

        print("\nAnswer:")
        print(answer.answer)

        print("\nCitations:", answer.citations)
        print("Confidence:", answer.confidence)
        print("Needs human review:", answer.needs_human_review)
        print("\nFailed gates:", ", ".join(row["failed"]) or "none")

        if task_id == "fa-01":
            print("\nRequired concepts:")

            for number, group in enumerate(row["case"].required_concepts, 1):
                hits = [
                    phrase
                    for phrase in group
                    if grade._contains(answer.answer, phrase)
                ]

                print(f"  Group {number}:")
                print(f"    Expected: {list(group)}")
                print(f"    Matched:  {hits or 'NONE'}")

        print("\nTrace:")
        for event in row["result"].trace:
            print(f"  {event}")


if __name__ == "__main__":
    main()