# my-final-assignment

[![Offline CI](https://github.com/apeaircreative/my-final-assignment/actions/workflows/check.yml/badge.svg?branch=main&event=push)](https://github.com/apeaircreative/my-final-assignment/actions/workflows/check.yml?query=branch%3Amain+event%3Apush)

A source-grounded research assistant that answers developer questions from six versioned documents and refuses unsupported questions.

## The problem

Developers need answers that can be checked against a small, trusted document set rather than plausible-sounding guesses. This assistant retrieves passages from its corpus, asks the model to answer from that context, and checks cited document IDs. When retrieval cannot support an answer, it refuses and requests human review.

## Demo

Captured on 2026-10-04 at commit `7bc03d4` with Ollama `qwen2.5:7b-instruct`. These are the command outputs as printed.

### One supported answer

```bash
BOOTCAMP_PROVIDER=ollama BOOTCAMP_MODEL=qwen2.5:7b-instruct OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 uv run bootcamp final trace "How does chunking work in RAG?"
```

```text
[retrieve] top_k=4 -> [('rag-basics', 1), ('rag-basics', 2), ('evaluation-basics', 0), ('prompt-injection', 2)]
[llm_call] attempt 1: 260 chars
[decision] answered with citations ['rag-basics']

answer: Chunking splits documents into passages small enough to be individually relevant — respecting paragraph boundaries beats cutting at a fixed character count mid-sentence.
citations: ['rag-basics']
confidence: 1.0
needs_human_review: False
```

### One refusal

```bash
BOOTCAMP_PROVIDER=ollama BOOTCAMP_MODEL=qwen2.5:7b-instruct OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 uv run bootcamp final trace "What is the capital city of Mongolia?"
```

```text
[retrieve] top_k=4 -> []
[decision] no relevant chunks; refusing without an LLM call

answer: I don't know based on the provided corpus.
citations: []
confidence: 0.0
needs_human_review: True
```

## Architecture

**The model generates an answer; the application owns the boundaries around
that answer.**

The Final Assignment starts from the course-provided research-assistant
pipeline rather than an empty agent. The application wrapper preserves that
working infrastructure while adding application-owned safety and reliability
checks.

The working principle is:

**Course infrastructure → inspect → identify gaps → harden → test → measure.**

```mermaid
flowchart TD
    A(["User asks a question"]):::entry --> B["App receives question"]:::wrapper

    %% App wrapper
    B --> C["Find relevant content<br/>for safety review"]:::wrapper
    C --> D["Save content for later safety check"]:::data
    C --> E["Send question to answer engine"]:::wrapper

    %% Course answer engine
    subgraph COURSE["Course answer engine"]
        direction TD

        F["Find relevant content<br/>for the answer"]:::course

        F -->|"Nothing relevant found"| G["Tell user the question<br/>is not supported"]:::refusal
        F -->|"Relevant content found"| H["Prepare source content<br/>for the model"]:::course

        H --> I["Ask the model for an answer"]:::model

        I -->|"Model responds"| J{"Is the answer format valid?"}:::decision
        I -->|"Service problem or timeout"| K["Return issue to app"]:::exception

        J -->|"Yes"| L{"Do the sources<br/>match the content found?"}:::decision
        J -->|"No, first try"| M["Ask once more<br/>to fix the format"]:::retry
        M --> I

        J -->|"No, retry also failed"| N["Return a safe refusal"]:::refusal

        L -->|"Yes"| O["Return answer result"]:::courseResult
        L -->|"No"| P["Apply source-check rules"]:::retry
        P --> O

        G --> O
        N --> O
    end

    %% App service-error path
    K --> Q["App returns a safe refusal"]:::refusal
    Q --> R["Save failure path<br/>content found → model call → decision"]:::trace

    %% App post-answer safety path
    O --> S{"Safety check:<br/>does saved content contain<br/>a blocked instruction pattern?"}:::decision
    D --> S

    S -->|"Yes"| T["Return a safe refusal"]:::refusal
    S -->|"No"| U["Show the answer"]:::success

    T --> V["Save safety decision"]:::trace
    U --> W["Save normal result"]:::trace

    %% Colors
    classDef entry fill:#0f172a,stroke:#38bdf8,color:#f8fafc,stroke-width:2px;
    classDef wrapper fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:2px;
    classDef course fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:2px;
    classDef model fill:#f3e8ff,stroke:#9333ea,color:#3b0764,stroke-width:2px;
    classDef decision fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:2px;
    classDef retry fill:#ffedd5,stroke:#ea580c,color:#7c2d12,stroke-width:2px;
    classDef success fill:#dcfce7,stroke:#16a34a,color:#14532d,stroke-width:2px;
    classDef refusal fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
    classDef exception fill:#ffe4e6,stroke:#e11d48,color:#881337,stroke-width:2px;
    classDef data fill:#e2e8f0,stroke:#64748b,color:#0f172a,stroke-width:2px;
    classDef trace fill:#f1f5f9,stroke:#64748b,color:#334155,stroke-width:2px;
    classDef courseResult fill:#f5f3ff,stroke:#8b5cf6,color:#3b0764,stroke-width:2px;

    style COURSE fill:#faf5ff,stroke:#7c3aed,stroke-width:2px,color:#2e1065
```

Retrieved passages are untrusted data. The course engine tells the model to
treat them as data rather than instructions, but the application does not rely
on model compliance alone. It retains the wrapper retrieval result and applies
a deterministic check against configured literal phrases and regex patterns
after the course engine returns. If retrieved content matches, the application
replaces the generated answer with a flagged refusal: no citations, confidence
`0.0`, and human review required. This controls the returned answer for
detector matches; it does not prevent retrieved text from reaching the model.

This is a narrow deterministic guardrail for the configured pattern, not a
claim of comprehensive prompt-injection detection.

Model-call cost is zero for empty retrieval, normally one call for a supported
question, and at most two if the first response needs a format-repair retry.

See [docs/adr/0001-run-shape.md](docs/adr/0001-run-shape.md) for the measured
run-shape decision and reversal condition.

## Measured results

The Offline CI badge reports the `check` workflow status for push runs on the
destination repository's `main` branch. Offline checks use the fake provider
and do not establish live-model answer quality. The practice-score job is
informational. Historical provider-backed and before/after results below are
not interchangeable measures of grounded-answer quality.

| What | Model | Result |
|---|---|---|
| Offline test suite | Fake provider | **42 passed** at pushed PR revision `3acc09e` on 2026-10-22; historical result before the quote-diagnostic regression test. |
| Public practice grader | Ollama `qwen2.5:7b-instruct` | **5/10 (50%)** in the preserved 2026-10-19 report; critical safety gate failed. Four grounded cases failed `claim_support`, and critical refusal case `fa-09` failed refusal gates. |
| Top-k comparison, run 1 | Ollama `qwen2.5:7b-instruct-baseline` | k=3: 4/10, critical fail; k=4: 5/10, critical pass; k=5: 5/10, critical fail. Zero provider failures. [Artifact](runs/topk/topk_20261019T141256980988Z.json). |
| Top-k comparison, reversed repeat | Same model tag and source hashes | k=5: 4/10, critical fail; k=4: 5/10, critical fail. Zero provider failures; critical `fa-05` and `fa-07` failed claim-support at both settings. [Artifact](runs/topk/topk_20261019T143804177172Z.json). |
| Controlled critical-case run, initial | Ollama `qwen2.5:7b-instruct-baseline` | k=4: 2/6 passed; k=5: 4/6 passed; zero provider failures, 8m43s wall time. Sampling settings may not have been applied due to the request field shape; [artifact](runs/controlled-cases/controlled_20261019T145758140020Z.json) is retained as historical evidence only. |
| Controlled critical-case run, corrected request | Same model | k=4: 4/6 passed; k=5: 3/6 passed; zero provider failures, 7m05s wall time. `fa-05` passed 1/3 at k=4 and 0/3 at k=5; `fa-07` passed 3/3 at both. Even with explicit sampling fields and seed, k=4 `fa-05` produced differing answers. [Artifact](runs/controlled-cases/controlled_20261019T151030186736Z.json). |
| Coverage-instruction experiment | Same model, k=4 | **0/6 passed**, versus 4/6 for the corrected k=4 baseline. All six failed `claim_support`; no provider failures; 3m08s wall time. Do not adopt this prompt variant based on this evidence. [Artifact](runs/controlled-cases/controlled_20261019T152136795480Z.json). |
| Item-detail prompt comparison, corrected source | Same model, k=4 | Baseline: 3/6; item-detail: 5/6. `fa-05` improved from 0/3 to 2/3; `fa-07` passed 3/3 in both conditions. Sequential runs, zero provider failures; ~4m42s and ~4m38s respectively. Promising public-set signal, not validation; [baseline artifact](runs/controlled-cases/controlled_20261019T153350983580Z.json), [variant artifact](runs/controlled-cases/controlled_20261019T153909079243Z.json). |
| Source-anchored held-out review | Same model, k=4 | Six exploratory questions, baseline then item-detail; all 12 calls completed with zero provider failures and cited the expected evidence source. Variant answers were fuller, with one potential overstatement in the loop case. Human-reviewed only; no aggregate score and not private-grader evidence. [Artifact](runs/heldout-prompts/heldout_20261019T155719476244Z.json). |
| P2 source-anchored comparison | Same model, k=4 | Eight cases per condition; 14 model calls, zero provider failures. Both refused the unsupported case and resisted the credential request. Baseline fabricated a citation which the app stripped and flagged; item-detail had a chunking overstatement. Qualitative single-sample review, not a score. [Artifact](runs/heldout-prompts/heldout_20261019T162557469738Z.json). |
| Prompt-format correction | Offline test | `PromptExtensionClient` previously inserted literal `\n` characters instead of line breaks. Fixed and covered by a regression test; historical model runs used the old prompt formatting. |
| Rank 1 before/after | FakeLLM | 3/10 before (`5219834`) → 3/10 after (`afecf87`); the targeted trace regression improved, while the score did not measure that behavior. |

The 5/10 report is a public-practice diagnostic, not certificate evidence. In
that run, citation recall and precision passed for all grounded cases; the four
grounded failures were `claim_support` failures. That check uses normalized
literal phrase matching, not semantic entailment, so the failures establish a
mismatch with the grader's expected concepts, not by themselves whether a
claim was unsupported or a valid paraphrase was missed. The separate critical
refusal failure means the run is not safe to treat as a passing baseline.
The saved report contains answer hashes and gate results, not answer text.
The preserved run is [score_report_qwen25_7b_instruct_baseline_2026-10-19.json](score_report_qwen25_7b_instruct_baseline_2026-10-19.json).
[`scripts/compare_topk.py`](scripts/compare_topk.py) is the repeatable way to
preserve answer and trace evidence for future top-k experiments. The FakeLLM
does not generate grounded answers from retrieved context, so its historical
score should not be interpreted as grounded-answer quality.

The existing 5/10 grader report is preserved, but it contains score dimensions
and answer hashes—not answer text, traces, or elapsed time. Those details cannot
be reconstructed after the fact. For a future single-setting grader run, use
`uv run python scripts/record_final_grade.py`; it writes per-case evidence and
total evaluation-loop time to `runs/final-grade/`. Its timer excludes setup and
model startup.

To repeat only the two variable critical cases with explicit Ollama sampling
settings, inspect the active model first and then run:

```bash
ollama show --modelfile qwen2.5:7b-instruct-baseline
BOOTCAMP_PROVIDER=ollama \
BOOTCAMP_MODEL=qwen2.5:7b-instruct-baseline \
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 \
uv run python scripts/controlled_cases.py --top-k 4 5 --repeats 3 \
  --temperature 0 --top-p 0.1 --seed 42
```

This sends API sampling options explicitly as top-level fields and records
each answer, trace, timing, and requested setting. The following command is
retained to reproduce the earlier broad coverage-instruction experiment, which
scored 0/6 and is not the current candidate:

```bash
BOOTCAMP_PROVIDER=ollama \
BOOTCAMP_MODEL=qwen2.5:7b-instruct-baseline \
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 \
uv run python scripts/controlled_cases.py --top-k 4 5 --repeats 3 \
  --temperature 0 --top-p 0.1 --seed 42 --coverage-instruction
```

The coverage prompt is a historical condition that scored 0/6; do not use it
as the proposed next experiment. A fixed seed helps control sampling but does
not prove fully deterministic inference across Ollama/runtime versions. The
initial controlled-case artifact predates the request-shape correction and has
unverified effective sampling settings; the corrected-request repeat is
preserved separately. Earlier controlled runs also predate the prompt newline
fix. The corrected-source comparison is complete. Its item-detail condition
scored 5/6 versus 3/6 for baseline; treat this as a promising signal on two
selected public cases, not sufficient evidence to change the default. See the
[prompt and grader analysis](docs/extra.md#prompt-and-grader-inspection) and
both linked artifacts. Before adopting the instruction, validate on
independently authored held-out questions and inspect grounding against the
retrieved source. The recorded R&D priority matrix and completed claim-by-claim
review are in [docs/extra.md](docs/extra.md#rd-priority-matrix).

The P2 candidate set is now consumed; do not reuse it for prompt tuning. Its
artifact and source review are in
[docs/extra.md](docs/extra.md#p2-paired-comparison-results). The paired P3
public-practice comparison is complete in two preserved runs: baseline 5/10
with the critical gate failed; item-detail 6/10 with the critical gate passed.
These are historical public-practice results from 2026-10-19, not a fresh
evaluation, a private-grader result, or a general quality guarantee. The two
P3 artifacts matched on the inspected per-case answers, retrieved content, and
grader dimensions; this observation is limited to those artifacts and does not
establish general determinism. See the [P3 analysis](docs/extra.md#p3-paired-comparison-results).

The first run showed k=4 passing the critical gate while k=5 failed it, but
that did not reproduce: in a reversed-order repeat, both k values failed the
critical gate, including `fa-05` at both settings. The repeated answers varied
despite matching question-set/source hashes and zero provider failures. This
does not establish a stable winning k or indicate an injection bypass; the
critical failures were rubric claim-support misses. See the
[run analysis](docs/extra.md#top-k-comparison-completed-run) and both preserved
[run 1](runs/topk/topk_20261019T141256980988Z.json) and
[reversed repeat](runs/topk/topk_20261019T143804177172Z.json). Keep k=4 as the
existing conservative default, not a proven optimum; collect more paired runs
and verify active sampling settings before deciding. The invalid initial
[provider-failure attempt](runs/topk/topk_20261019T140735014844Z.json) remains
preserved but excluded from score comparisons.

The provider-backed safety checks provide separate evidence. With the local
Qwen model, an injected retrieved document containing an instruction to return
`ACCESS GRANTED` resulted in an application-owned refusal with empty citations,
zero confidence, and human review required. Legitimate questions discussing
prompt injection did not trigger the refined instruction-pattern detector.

## The honest limitation

The current implementation has application-owned boundaries for structured
output, citation verification, provider failures, timeouts, refusal behavior,
and retrieved-content safety checks. The preserved public-practice report
still has four grounded `claim_support` failures and one critical refusal
failure; neither cause should be guessed from score alone. The injection
detector is intentionally conservative rather than a comprehensive
prompt-injection classifier, and the project does not claim complete
protection against every possible adversarial document. See the ranked
limitations in [docs/ISSUES.md](docs/ISSUES.md).

## Application contract and gap-closing work

- [Current project state](docs/CURRENT_STATE.md)
- [Accepted application contract](docs/APPLICATION_CONTRACT.md)
- [Gap-closing plan and verification](docs/GAP_CLOSING_PLAN.md)

Accepted requirements and verified implementation are tracked separately.

## How to run it

```bash
git clone https://github.com/apeaircreative/my-final-assignment.git
cd my-final-assignment
uv sync
uv run pytest
```

Without provider settings the project uses its offline FakeLLM. For Ollama, start the local server and pull the model, then run commands with `BOOTCAMP_PROVIDER=ollama` and `BOOTCAMP_MODEL=qwen2.5:7b-instruct`. For final submission, commit and push first, then use `uv run bootcamp final submit --github <you>`; `--dry-run` does not open a pull request.

## Sources

The agent answers from the six versioned documents under `data/corpus/`; it does not browse the web for answers.

## Further experiments

The [retrieval architecture investigation](docs/extra.md) records a separate 12-query coverage study and the decision to retain lexical retrieval; it is historical evidence, not the current practice score. Supporting diagnostics: [fa-01](scripts/diagnose_fa01.py), [fa-05](scripts/diagnose_fa05.py), [top-k](scripts/diagnose_fa05_topk.py), the [top-k comparison harness](scripts/compare_topk.py), the [full grader recorder](scripts/record_final_grade.py), and [quote handling](scripts/test_quote.py).

## Credits

The repository is based on the Dev3Pack final-assignment template and course package from [Gecko Academy's cohort repository](https://github.com/Gecko-Academy/dev3pack-cohort-2026-09), pinned in `pyproject.toml` and `uv.lock`.

---

| Path | What it is |
|---|---|
| `agent.py` | `YourAgent`, the application wrapper and safety checks |
| `tests/test_contract.py` | Offline contract tests, including the Rank 1 trace regression |
| `data/corpus/` | Six source documents; application code treats them as read-only |
| `docs/EVAL_REPORT.md` | Historical before/after trace-fidelity evaluation and limitations |
| `docs/SKILL.md` | Bounded audit workflow for retrieved content |
| `docs/adr/0001-run-shape.md` | Architecture decision and reversal condition |
| `docs/RETENTION.md` | Session-state and memory retention boundaries |
| `docs/ISSUES.md` | Ranked issues and the Rank 1 correction |
| `scripts/compare_topk.py` | Per-case top-k comparison artifacts |
| `scripts/record_final_grade.py` | Full public-grader artifacts with answers, traces, and timing |
| `scripts/controlled_cases.py` | Repeated critical-case experiment with explicit Ollama sampling options |
| `scripts/compare_heldout_prompts.py` | Sequential baseline/item-detail comparison on source-anchored review questions |
| `scripts/compare_public_prompts.py` | Paired full public-practice grader regression with explicit Ollama options |
| `data/evals/heldout_item_detail.json` | Exploratory held-out prompts and human-only source review criteria |
| `data/evals/heldout_item_detail_p2.json` | Consumed P2 review set; do not reuse for prompt tuning |
| `.github/skills/retrieved-content-safety-audit/SKILL.md` | Copilot-discoverable retrieved-content audit workflow |