from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bootcamp_agent import final_grade  # noqa: E402
from bootcamp_agent.config import load_settings  # noqa: E402
from bootcamp_agent.llm import get_client  # noqa: E402
from bootcamp_agent.ollama import DEFAULT_MODEL as OLLAMA_DEFAULT_MODEL  # noqa: E402
from bootcamp_agent.retrieval import retrieve  # noqa: E402

from agent import YourAgent  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _case_result(agent: YourAgent, task_id: str, case, top_k: int) -> dict:
    started = time.perf_counter()
    result = agent.run(case.question)
    elapsed_s = time.perf_counter() - started
    passed, dimensions, detail = final_grade.evaluate_answer(case, result.answer)
    retrieved = retrieve(case.question, agent.documents, top_k=top_k)
    return {
        "task_id": task_id,
        "category": case.category,
        "critical": case.critical,
        "question_sha256": hashlib.sha256(case.question.encode("utf-8")).hexdigest(),
        "passed": passed,
        "dimensions": dimensions,
        "detail": detail,
        "answer": {
            "text": result.answer.answer,
            "citations": list(result.answer.citations),
            "confidence": result.answer.confidence,
            "needs_human_review": result.answer.needs_human_review,
        },
        "trace": [{"kind": event.kind, "detail": event.detail} for event in result.trace],
        "retrieved": [
            {
                "doc_id": item.chunk.doc_id,
                "position": item.chunk.position,
                "score": item.score,
            }
            for item in retrieved
        ],
        "elapsed_s": round(elapsed_s, 3),
    }


def _summary(cases: list[dict]) -> dict:
    categories = sorted({case["category"] for case in cases})
    critical = [case for case in cases if case["critical"]]
    provider_failures = sum(
        event["kind"] == "llm_call" and event["detail"].startswith("provider call failed:")
        for case in cases
        for event in case["trace"]
    )
    return {
        "passed": sum(case["passed"] for case in cases),
        "total": len(cases),
        "percent": round(100 * sum(case["passed"] for case in cases) / len(cases)),
        "critical_safety": all(case["passed"] for case in critical),
        "provider_failures": provider_failures,
        "provider_comparison_valid": provider_failures == 0,
        "categories": {
            category: {
                "passed": sum(case["passed"] for case in cases if case["category"] == category),
                "total": sum(case["category"] == category for case in cases),
            }
            for category in categories
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare retrieval top-k values on the shipped public practice set."
    )
    parser.add_argument(
        "--top-k",
        type=int,
        nargs="+",
        default=[3, 4, 5],
        help="retrieval counts to compare (default: 3 4 5)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "runs" / "topk",
        help="directory for the preserved comparison artifact",
    )
    args = parser.parse_args()
    if not args.top_k or any(value < 1 for value in args.top_k):
        parser.error("--top-k values must be positive integers")
    if len(args.top_k) != len(set(args.top_k)):
        parser.error("--top-k values must not contain duplicates")

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
    timestamp = datetime.now(UTC)
    runs = []

    for top_k in args.top_k:
        agent = YourAgent(client=client)
        agent.top_k = top_k
        case_results = [_case_result(agent, task_id, case, top_k) for task_id, case in entries]
        runs.append(
            {
                "top_k": top_k,
                "summary": _summary(case_results),
                "cases": case_results,
            }
        )
        summary = runs[-1]["summary"]
        validity = "valid" if summary["provider_comparison_valid"] else "INVALID"
        print(
            f"top_k={top_k}: {summary['passed']}/{summary['total']} "
            f"({summary['percent']}%), critical_safety={summary['critical_safety']}, "
            f"provider_failures={summary['provider_failures']}, comparison={validity}"
        )

    course_root = Path(final_grade.__file__).resolve().parent
    artifact = {
        "schema": "my-final-assignment.topk-comparison.v1",
        "created_at": timestamp.isoformat().replace("+00:00", "Z"),
        "git_commit": _git_commit(),
        "provider": settings.provider,
        "model": model,
        "timeout_s_per_call": 120.0,
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
        "runs": runs,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"topk_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    with output.open("x", encoding="utf-8") as report_file:
        report_file.write(json.dumps(artifact, indent=2) + "\n")
    print(f"Saved comparison artifact: {output}")


if __name__ == "__main__":
    main()
