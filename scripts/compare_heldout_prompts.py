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
from bootcamp_agent.config import load_settings  # noqa: E402
from bootcamp_agent.ollama import DEFAULT_MODEL as OLLAMA_DEFAULT_MODEL  # noqa: E402
from bootcamp_agent.retrieval import retrieve  # noqa: E402
from compare_topk import _git_commit, _sha256  # noqa: E402
from controlled_cases import (  # noqa: E402
    ITEM_DETAIL_INSTRUCTION,
    OllamaOptionsClient,
    SystemInstructionClient,
)

from agent import YourAgent  # noqa: E402

CASE_FILE = ROOT / "data" / "evals" / "heldout_item_detail.json"


def _load_cases(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "my-final-assignment.heldout-review-set.v1":
        raise ValueError(f"unexpected held-out case-set schema in {path}")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("held-out case set must contain at least one case")
    seen: set[str] = set()
    for case in cases:
        if (
            not isinstance(case, dict)
            or not isinstance(case.get("id"), str)
            or not isinstance(case.get("question"), str)
            or not isinstance(case.get("review_reference"), dict)
        ):
            raise ValueError("each case needs an id, question, and review_reference")
        if case["id"] in seen:
            raise ValueError(f"duplicate held-out case id: {case['id']}")
        seen.add(case["id"])
    return payload


def _run_case(
    agent: YourAgent,
    case: dict,
    condition: str,
    top_k: int,
) -> dict:
    started = time.perf_counter()
    result = agent.run(case["question"])
    elapsed_s = time.perf_counter() - started
    retrieved = retrieve(case["question"], agent.documents, top_k=top_k)
    provider_failures = [
        event.detail
        for event in result.trace
        if event.kind == "llm_call" and event.detail.startswith("provider call failed:")
    ]
    return {
        "condition": condition,
        "case_id": case["id"],
        "question_sha256": hashlib.sha256(case["question"].encode("utf-8")).hexdigest(),
        "review_reference": case["review_reference"],
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
        "provider_failures": provider_failures,
        "elapsed_s": round(elapsed_s, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run a paired baseline/item-detail comparison on an independent "
            "source-anchored review set."
        )
    )
    parser.add_argument("--model", help="model tag; defaults to BOOTCAMP_MODEL or provider default")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds per provider call")
    parser.add_argument("--cases", type=Path, default=CASE_FILE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "runs" / "heldout-prompts",
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

    try:
        case_set = _load_cases(args.cases)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    settings = load_settings()
    if settings.provider != "ollama":
        parser.error("set BOOTCAMP_PROVIDER=ollama to run this experiment")
    model = args.model or settings.model or OLLAMA_DEFAULT_MODEL
    base_client = OllamaOptionsClient(
        model=model,
        base_url=settings.base_url,
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
    results = []
    for condition, client in conditions:
        for case in case_set["cases"]:
            agent = YourAgent(client=client)
            agent.top_k = args.top_k
            run = _run_case(agent, case, condition, args.top_k)
            results.append(run)
            failures = run["provider_failures"]
            print(
                f"{condition} {case['id']}: "
                f"{'provider_failure' if failures else 'completed'} "
                f"elapsed={run['elapsed_s']:.1f}s"
            )

    course_root = Path(bootcamp_agent.__file__).resolve().parent
    artifact = {
        "schema": "my-final-assignment.heldout-prompt-comparison.v1",
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "git_commit": _git_commit(),
        "provider": settings.provider,
        "model": model,
        "base_url": settings.base_url,
        "top_k": args.top_k,
        "sampling_options_requested": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "seed": args.seed,
        },
        "timeout_s_per_call": args.timeout,
        "case_set": {
            "id": case_set["schema"],
            "sha256": _sha256(args.cases),
            "case_count": len(case_set["cases"]),
        },
        "item_detail_instruction": ITEM_DETAIL_INSTRUCTION,
        "source_sha256": {
            "agent.py": _sha256(ROOT / "agent.py"),
            "safety.py": _sha256(ROOT / "safety.py"),
            "Modelfile": _sha256(ROOT / "Modelfile"),
            "heldout_cases": _sha256(args.cases),
            "grader.py": _sha256(course_root / "final_grade.py"),
            "compare_heldout_prompts.py": _sha256(Path(__file__).resolve()),
        },
        "evaluation_note": (
            "No public practice grader score is computed. Review each answer against "
            "the source-anchored checklist and retrieved evidence; review_reference "
            "is metadata and is never sent to the model."
        ),
        "results": results,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / (f"heldout_{started_at.strftime('%Y%m%dT%H%M%S%fZ')}.json")
    with output.open("x", encoding="utf-8") as report_file:
        report_file.write(json.dumps(artifact, indent=2) + "\n")
    print(f"Saved held-out comparison artifact: {output}")


if __name__ == "__main__":
    main()
