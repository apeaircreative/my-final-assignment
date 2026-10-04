from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import TimeoutClient, YourAgent
from bootcamp_agent import final_grade as grade
from bootcamp_agent.agent import answer_question
from bootcamp_agent.retrieval import retrieve


QUESTIONS_PATH = (
    ROOT.parent
    / "dev3pack-cohort-2026-09"
    / "src"
    / "bootcamp_agent"
    / "final_practice.jsonl"
)

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


class QuoteAgent(YourAgent):
    """YourAgent with a generation-only source-wording instruction."""

    def run(self, question: str):
        retrieved = retrieve(
            question,
            self.documents,
            top_k=3,
        )

        try:
            timeout_client = TimeoutClient(self.client, self.timeout_s)
            instructed_client = InstructedClient(timeout_client, QUOTE)

            result = answer_question(
                question,
                self.documents,
                instructed_client,
                max_tool_calls=3,
                top_k=3,
            )
        except (ConnectionError, TimeoutError):
            # This experiment script should not replace your production
            # agent's error handling. Let the exception make the experiment
            # visibly fail rather than silently changing its behavior.
            raise

        # Preserve the exact application safety behavior from YourAgent.
        from safety import contains_instruction_like_text
        from bootcamp_agent.agent import AgentResult, TraceEvent, _refusal

        if contains_instruction_like_text(retrieved):
            return AgentResult(
                answer=_refusal(),
                trace=result.trace
                + (
                    TraceEvent(
                        "decision",
                        "retrieved content contained instruction-like text; "
                        "flagged refusal",
                    ),
                ),
            )

        review_gate = __import__("agent").needs_human_review()
        if review_gate.should_review(result.answer):
            return AgentResult(
                answer=review_gate.fallback(result.answer),
                trace=result.trace,
            )

        return result


def main() -> None:
    if not QUESTIONS_PATH.is_file():
        raise RuntimeError(f"Questions file not found: {QUESTIONS_PATH}")

    cases = dict(grade.load_questions(QUESTIONS_PATH))
    agent = QuoteAgent()
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