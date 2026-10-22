from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import bootcamp_agent  # noqa: E402
from bootcamp_agent import final_grade  # noqa: E402
from bootcamp_agent.config import load_settings  # noqa: E402
from bootcamp_agent.ollama import DEFAULT_BASE_URL, DEFAULT_MODEL  # noqa: E402
from bootcamp_agent.retrieval import retrieve  # noqa: E402
from compare_topk import _git_commit, _sha256  # noqa: E402
from controlled_cases import (  # noqa: E402
    ITEM_DETAIL_INSTRUCTION,
    OllamaOptionsClient,
    SystemInstructionClient,
)

from agent import YourAgent  # noqa: E402


def _provider_failures(trace) -> list[str]:
    return [
        event.detail
        for event in trace
        if event.kind == "llm_call" and event.detail.startswith("provider call failed:")
    ]


def _run_case(agent: YourAgent, task_id: str, case, top_k: int) -> dict:
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
        "provider_failures": _provider_failures(result.trace),
        "answer": {
            "text": result.answer.answer,
            "citations": list(result.answer.citations),
            "confidence": result.answer.confidence,
            "needs_human_review": result.answer.needs_human_review,
        },
        "retrieved": [
            {
                "doc_id": item.chunk.doc_id,
                "position": item.chunk.position,
                "score": item.score,
                "text": item.chunk.text,
            }
            for item in retrieved
        ],
        "trace": [{"kind": event.kind, "detail": event.detail} for event in result.trace],
        "elapsed_s": round(elapsed_s, 3),
    }


def _summarize(results: list[dict]) -> dict:
    critical = [result for result in results if result["critical"]]
    categories = sorted({result["category"] for result in results})
    provider_failures = sum(len(result["provider_failures"]) for result in results)
    passed = sum(result["passed"] for result in results)
    return {
        "passed": passed,
        "total": len(results),
        "percent": round(100 * passed / len(results)) if results else 0,
        "critical_passed": sum(result["passed"] for result in critical),
        "critical_total": len(critical),
        "critical_gate": all(result["passed"] for result in critical),
        "provider_failures": provider_failures,
        "provider_comparison_valid": provider_failures == 0,
        "categories": {
            category: {
                "passed": sum(
                    result["passed"] for result in results if result["category"] == category
                ),
                "total": sum(result["category"] == category for result in results),
            }
            for category in categories
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare baseline and item-detail prompts on all public practice cases "
            "with explicit Ollama sampling settings."
        )
    )
    parser.add_argument("--model", help="Ollama model tag; defaults to BOOTCAMP_MODEL or default")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds per provider call")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "runs" / "public-prompt-comparison",
    )
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not 0 <= args.temperature <= 2:
        parser.error("--temperature must be between 0 and 2")
    if not 0 < args.top_p <= 1:
        parser.error("--top-p must be greater than 0 and at most 1")

    settings = load_settings()
    if settings.provider != "ollama":
        parser.error("set BOOTCAMP_PROVIDER=ollama to run this public prompt comparison")
    model = args.model or settings.model or DEFAULT_MODEL
    base_url = settings.base_url or DEFAULT_BASE_URL
    cases = final_grade.load_questions(final_grade.PRACTICE_QUESTIONS)
    base_client = OllamaOptionsClient(
        model=model,
        base_url=base_url,
        timeout_s=args.timeout,
        temperature=args.temperature,
        top_p=args.top_p,
        seed=args.seed,
    )
    conditions = (
        ("baseline", base_client),
        (
            "item_detail_instruction",
            SystemInstructionClient(base_client, ITEM_DETAIL_INSTRUCTION),
        ),
    )

    started_at = datetime.now(UTC)
    condition_reports = []
    for condition, client in conditions:
        agent = YourAgent(client=client)
        agent.top_k = args.top_k
        results = []
        for task_id, case in cases:
            result = _run_case(agent, task_id, case, args.top_k)
            results.append(result)
            failures = result["provider_failures"]
            print(
                f"{condition} {task_id}: "
                f"{'PASS' if result['passed'] else 'FAIL'} "
                f"failed={result['detail'] if not result['passed'] else '-'} "
                f"elapsed={result['elapsed_s']:.1f}s "
                f"{'provider_failure' if failures else 'provider_ok'}"
            )
        summary = _summarize(results)
        condition_reports.append({"condition": condition, "summary": summary, "cases": results})
        print(
            f"{condition} summary: {summary['passed']}/{summary['total']} "
            f"({summary['percent']}%), critical_gate={summary['critical_gate']} "
            f"({summary['critical_passed']}/{summary['critical_total']}), "
            f"provider_failures={summary['provider_failures']}"
        )

    finished_at = datetime.now(UTC)
    course_root = Path(bootcamp_agent.__file__).resolve().parent
    artifact = {
        "schema": "my-final-assignment.public-prompt-comparison.v1",
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "finished_at": finished_at.isoformat().replace("+00:00", "Z"),
        "elapsed_s": round((finished_at - started_at).total_seconds(), 3),
        "git_commit": _git_commit(),
        "provider": settings.provider,
        "model": model,
        "base_url": base_url,
        "top_k": args.top_k,
        "sampling_options_requested": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "seed": args.seed,
        },
        "timeout_s_per_call": args.timeout,
        "question_set": {
            "id": "public-practice",
            "sha256": _sha256(final_grade.PRACTICE_QUESTIONS),
            "case_count": len(cases),
        },
        "item_detail_instruction": ITEM_DETAIL_INSTRUCTION,
        "source_sha256": {
            "agent.py": _sha256(ROOT / "agent.py"),
            "safety.py": _sha256(ROOT / "safety.py"),
            "Modelfile": _sha256(ROOT / "Modelfile"),
            "grader.py": _sha256(course_root / "final_grade.py"),
            "compare_public_prompts.py": _sha256(Path(__file__).resolve()),
        },
        "conditions": condition_reports,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / (f"public_prompts_{started_at.strftime('%Y%m%dT%H%M%S%fZ')}.json")
    with output.open("x", encoding="utf-8") as report_file:
        report_file.write(json.dumps(artifact, indent=2) + "\n")
    print(f"Saved public prompt comparison artifact: {output}")


if __name__ == "__main__":
    main()
