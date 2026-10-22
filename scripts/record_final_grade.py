from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from bootcamp_agent import final_grade
from bootcamp_agent.config import load_settings
from bootcamp_agent.llm import get_client
from bootcamp_agent.ollama import DEFAULT_MODEL as OLLAMA_DEFAULT_MODEL
from compare_topk import ROOT, _case_result, _git_commit, _sha256, _summary

from agent import YourAgent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the public final grader and preserve answer-level evidence."
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="retrieval count used by both safety and answer retrieval (default: 4)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "runs" / "final-grade",
        help="directory for the preserved run artifact",
    )
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be a positive integer")

    question_path = final_grade.PRACTICE_QUESTIONS
    entries = final_grade.load_questions(question_path)
    settings = load_settings()
    client = get_client(settings)
    model = (
        None
        if settings.provider == "fake"
        else settings.model
        or {
            "ollama": OLLAMA_DEFAULT_MODEL,
            "anthropic": "claude-sonnet-5",
            "openai": "gpt-4o-mini",
        }.get(settings.provider)
    )
    agent = YourAgent(client=client)
    agent.top_k = args.top_k

    started_at = datetime.now(UTC)
    started_clock = time.perf_counter()
    case_results = [_case_result(agent, task_id, case, args.top_k) for task_id, case in entries]
    elapsed_s = time.perf_counter() - started_clock
    finished_at = datetime.now(UTC)
    timestamp = finished_at
    summary = _summary(case_results)

    course_root = Path(final_grade.__file__).resolve().parent
    artifact = {
        "schema": "my-final-assignment.final-grade-run.v1",
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "finished_at": finished_at.isoformat().replace("+00:00", "Z"),
        "elapsed_s": round(elapsed_s, 3),
        "git_commit": _git_commit(),
        "provider": settings.provider,
        "model": model,
        "top_k": args.top_k,
        "timeout_s_per_call": agent.timeout_s,
        "generation_options": (
            "Not reported by the application client; Modelfile hash does not establish "
            "the active Ollama model configuration."
        ),
        "question_set": {
            "id": "public-practice",
            "sha256": _sha256(question_path),
            "case_count": len(entries),
        },
        "source_sha256": {
            "agent.py": _sha256(ROOT / "agent.py"),
            "safety.py": _sha256(ROOT / "safety.py"),
            "Modelfile": _sha256(ROOT / "Modelfile"),
            "grader.py": _sha256(course_root / "final_grade.py"),
        },
        "summary": summary,
        "cases": case_results,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"final_grade_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    with output.open("x", encoding="utf-8") as report_file:
        report_file.write(json.dumps(artifact, indent=2) + "\n")

    print(
        f"score={summary['passed']}/{summary['total']} ({summary['percent']}%), "
        f"critical_safety={summary['critical_safety']}, "
        f"provider_failures={summary['provider_failures']}, "
        f"elapsed={elapsed_s:.1f}s"
    )
    print(f"Saved final-grade artifact: {output}")


if __name__ == "__main__":
    main()
