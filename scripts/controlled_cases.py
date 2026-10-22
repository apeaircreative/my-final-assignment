from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from bootcamp_agent import final_grade  # noqa: E402
from bootcamp_agent.config import load_settings  # noqa: E402
from bootcamp_agent.ollama import DEFAULT_BASE_URL, DEFAULT_MODEL, OllamaError  # noqa: E402
from compare_topk import _git_commit, _sha256  # noqa: E402

from agent import YourAgent  # noqa: E402

COVERAGE_INSTRUCTION = (
    "Answer every distinct part of the question that the provided context supports. "
    "If a requested part is unsupported, say so instead of guessing. Keep the answer "
    "focused and cite only documents that support the answer."
)
ITEM_DETAIL_INSTRUCTION = (
    "When a question asks for multiple supported items, briefly explain each item "
    "using its distinguishing detail from the context; do not return only a list "
    "of item names."
)


class OllamaOptionsClient:
    """Ollama chat client that makes sampling options explicit for an experiment."""

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        timeout_s: float,
        temperature: float,
        top_p: float,
        seed: int,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.options = {"temperature": temperature, "top_p": top_p, "seed": seed}

    def complete(self, system: str, user: str) -> str:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            **self.options,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise OllamaError(
                f"Ollama answered HTTP {error.code} for model {self.model!r}"
            ) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise OllamaError(f"No Ollama response from {self.base_url}") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise OllamaError("Ollama returned a response that was not valid UTF-8 JSON") from error
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise OllamaError("Ollama returned a response without choices[0].message") from error
        if not isinstance(content, str):
            raise OllamaError("Ollama returned non-text message content")
        return content


class SystemInstructionClient:
    def __init__(self, client, instruction: str) -> None:
        self.client = client
        self.instruction = instruction

    def complete(self, system: str, user: str) -> str:
        return self.client.complete(
            system=f"{system}\n\n{self.instruction}",
            user=user,
        )


def _case_run(agent: YourAgent, task_id: str, case, repeat: int, top_k: int) -> dict:
    started = time.perf_counter()
    result = agent.run(case.question)
    elapsed_s = time.perf_counter() - started
    passed, dimensions, detail = final_grade.evaluate_answer(case, result.answer)
    provider_failures = [
        event.detail
        for event in result.trace
        if event.kind == "llm_call" and event.detail.startswith("provider call failed:")
    ]
    return {
        "repeat": repeat,
        "top_k": top_k,
        "task_id": task_id,
        "category": case.category,
        "critical": case.critical,
        "question_sha256": hashlib.sha256(case.question.encode("utf-8")).hexdigest(),
        "passed": passed,
        "dimensions": dimensions,
        "detail": detail,
        "provider_failures": provider_failures,
        "answer": {
            "text": result.answer.answer,
            "citations": list(result.answer.citations),
            "confidence": result.answer.confidence,
            "needs_human_review": result.answer.needs_human_review,
        },
        "trace": [{"kind": event.kind, "detail": event.detail} for event in result.trace],
        "elapsed_s": round(elapsed_s, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repeat selected public cases with explicit Ollama sampling settings."
    )
    parser.add_argument(
        "--model", help="Ollama model tag; defaults to BOOTCAMP_MODEL or Ollama's default"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        nargs="+",
        default=[4, 5],
        help="top-k values to compare in the given order (default: 4 5)",
    )
    parser.add_argument(
        "--task-ids",
        nargs="+",
        default=["fa-05", "fa-07"],
        help="public-practice cases to repeat (default: fa-05 fa-07)",
    )
    parser.add_argument(
        "--repeats", type=int, default=3, help="repeats per case and k (default: 3)"
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds per provider call")
    parser.add_argument(
        "--coverage-instruction",
        action="store_true",
        help="append the earlier broad answer-completeness instruction",
    )
    parser.add_argument(
        "--item-detail-instruction",
        action="store_true",
        help="ask for a brief explanation of every supported item",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "runs" / "controlled-cases",
        help="directory for the preserved experiment artifact",
    )
    args = parser.parse_args()
    if not args.top_k or any(value < 1 for value in args.top_k):
        parser.error("--top-k values must be positive integers")
    if args.repeats < 1 or args.timeout <= 0:
        parser.error("--repeats and --timeout must be positive")
    if not 0 <= args.temperature <= 2:
        parser.error("--temperature must be between 0 and 2")
    if not 0 < args.top_p <= 1:
        parser.error("--top-p must be greater than 0 and at most 1")
    if len(args.top_k) != len(set(args.top_k)):
        parser.error("--top-k values must not contain duplicates")
    if args.coverage_instruction and args.item_detail_instruction:
        parser.error("--coverage-instruction and --item-detail-instruction are separate conditions")

    settings = load_settings()
    if settings.provider != "ollama":
        parser.error("set BOOTCAMP_PROVIDER=ollama to run this controlled experiment")
    model = args.model or settings.model or DEFAULT_MODEL
    base_url = settings.base_url or DEFAULT_BASE_URL
    cases_by_id = dict(final_grade.load_questions(final_grade.PRACTICE_QUESTIONS))
    unknown = sorted(set(args.task_ids) - set(cases_by_id))
    if unknown:
        parser.error(f"unknown public-practice task IDs: {unknown}")

    client = OllamaOptionsClient(
        model=model,
        base_url=base_url,
        timeout_s=args.timeout,
        temperature=args.temperature,
        top_p=args.top_p,
        seed=args.seed,
    )
    instruction = (
        COVERAGE_INSTRUCTION
        if args.coverage_instruction
        else ITEM_DETAIL_INSTRUCTION
        if args.item_detail_instruction
        else None
    )
    if instruction is not None:
        client = SystemInstructionClient(client, instruction)

    timestamp = datetime.now(UTC)
    results = []
    for repeat in range(1, args.repeats + 1):
        for top_k in args.top_k:
            agent = YourAgent(client=client)
            agent.top_k = top_k
            for task_id in args.task_ids:
                case = cases_by_id[task_id]
                run = _case_run(agent, task_id, case, repeat, top_k)
                results.append(run)
                failed = [name for name, ok in run["dimensions"].items() if not ok]
                provider_status = (
                    f"provider_failure={run['provider_failures']}"
                    if run["provider_failures"]
                    else "provider_ok"
                )
                print(
                    f"repeat={repeat} k={top_k} {task_id}: "
                    f"{'PASS' if run['passed'] else 'FAIL'} "
                    f"failed={failed or '-'} elapsed={run['elapsed_s']:.1f}s {provider_status}"
                )

    course_root = Path(final_grade.__file__).resolve().parent
    artifact = {
        "schema": "my-final-assignment.controlled-cases.v1",
        "started_at": timestamp.isoformat().replace("+00:00", "Z"),
        "finished_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "git_commit": _git_commit(),
        "provider": settings.provider,
        "model": model,
        "base_url": base_url,
        "top_k_order": args.top_k,
        "task_ids": args.task_ids,
        "repeats": args.repeats,
        "sampling_options": {
            "temperature": args.temperature,
            "top_p": args.top_p,
            "seed": args.seed,
        },
        "timeout_s_per_call": args.timeout,
        "prompt_variant": (
            "general_coverage_instruction"
            if args.coverage_instruction
            else "item_detail_instruction"
            if args.item_detail_instruction
            else "baseline"
        ),
        "coverage_instruction": COVERAGE_INSTRUCTION if args.coverage_instruction else None,
        "item_detail_instruction": (
            ITEM_DETAIL_INSTRUCTION if args.item_detail_instruction else None
        ),
        "question_set": {
            "id": "public-practice",
            "sha256": _sha256(final_grade.PRACTICE_QUESTIONS),
        },
        "source_sha256": {
            "agent.py": _sha256(ROOT / "agent.py"),
            "safety.py": _sha256(ROOT / "safety.py"),
            "Modelfile": _sha256(ROOT / "Modelfile"),
            "grader.py": _sha256(course_root / "final_grade.py"),
            "controlled_cases.py": _sha256(Path(__file__).resolve()),
        },
        "results": results,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"controlled_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.json"
    with output.open("x", encoding="utf-8") as report_file:
        report_file.write(json.dumps(artifact, indent=2) + "\n")
    print(f"Saved controlled-case artifact: {output}")


if __name__ == "__main__":
    main()
