# my-final-assignment



[![Offline CI](https://github.com/apeaircreative/my-final-assignment/actions/workflows/check.yml/badge.svg?branch=main&event=push)](https://github.com/apeaircreative/my-final-assignment/actions/workflows/check.yml?query=branch%3Amain+event%3Apush)



A source-grounded research assistant that answers developer questions from six versioned documents and refuses unsupported questions.



For guided reading paths through the project's documentation, see the [Documentation Guide](docs/README.md).



## The problem



Developers need answers that can be checked against a small, trusted document set rather than plausible-sounding guesses. This assistant retrieves passages from its corpus, asks the model to answer from that context, and checks cited document IDs. When retrieval cannot support an answer, it refuses and sets a returned human-review flag.



## Demo



Captured on 2026-10-04 at commit `7bc03d4` with Ollama `qwen2.5:7b-instruct`. These are the command outputs as printed.

Read these historical examples and compare each command with its recorded output. They are not freshly reproduced interactions.



### One supported answer

This example records a question about chunking in retrieval-augmented generation (RAG), followed by retrieved chunk identifiers and the answer.



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



The citation value is a recorded ID, not a clickable source link or independent proof of semantic support.

### One refusal

This example records a question for which retrieval returned no chunks.



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



In this recorded example, the empty retrieval result is followed by a refusal without an LLM call. `needs_human_review` is a response flag; its presence does not establish that a reviewer was notified or that an operational handoff occurred.

## Architecture



**The model generates an answer; the application owns the boundaries around that answer.**



The Final Assignment starts from the course-provided research-assistant

pipeline rather than an empty agent. The pinned course pipeline owns answer

retrieval, context preparation, model generation, structured answer parsing,

and citation-ID validation. The application wrapper preserves that

infrastructure and adds provider-failure and timeout handling, application

refusal and human-review policy, and separate retrieved-content safety checks.



**The working principle is:**

> Course infrastructure → inspect → identify gaps → harden → test → measure.

### Responsibility map
![Question-answer flow overview showing the app, answer engine, safety check, and result handling.](docs/diagrams/answer-flow-overview_horizontal.svg)

**1. Application wrapper — entry, execution, and safety boundaries**

- Receives the question, constructs its default client through the course package, and executes the answer pipeline.
- Handles application-level provider failures and bounds how long the caller waits for a provider response.
- Retains retrieved content for a separate safety check and applies the returned refusal and human-review policy.

**2. Course package — provider utilities and answer pipeline**

- Provides settings loading and provider-client construction.
- Retrieves answer content, prepares source context, calls the model, parses structured answers, and validates citation IDs.
- May make one format-repair retry when the first response is invalid.

**3. Application wrapper — final decision and trace**

- Checks saved retrieved content against configured instruction-like patterns.
- Replaces a matching result with a refusal and sets the returned human-review flag.
- Records the normal result, safety decision, or provider-failure path.

**In short:** app entry and safety checks → course provider utilities and answer pipeline → app final safety decision and trace.

[Open overview full-size](docs/diagrams/answer-flow-overview.svg) ·
[Open detailed flow](docs/diagrams/answer-flow-detail.svg)

Retrieved passages are untrusted data. The course engine tells the model to

treat them as data rather than instructions, but the application does not rely

on model compliance alone. It retains the wrapper retrieval result and applies

a deterministic check against configured literal phrases and regex patterns

after the course engine returns. If retrieved content matches, the application

replaces the generated answer with a refusal: no citations, confidence

`0.0`, and the returned human-review flag set. This controls the returned

answer for detector matches; it does not prevent retrieved text from reaching

the model.


This is a narrow deterministic guardrail for the configured pattern, not a

claim of comprehensive prompt-injection detection.



The timeout bounds how long the caller waits for a provider response. It does

not establish that the underlying provider request or worker is cancelled or

terminated when that wait expires.



Model-call cost is zero for empty retrieval, normally one call for a supported

question, and at most two if the first response needs a format-repair retry.



See [docs/adr/0001-run-shape.md](docs/adr/0001-run-shape.md) for the measured

run-shape decision and reversal condition.



## The honest limitation



The pinned course pipeline owns structured answer parsing and citation-ID

validation. The application owns provider-failure and timeout handling,

refusal and returned human-review policy, and retrieved-content safety checks.

The preserved public-practice report still has four grounded `claim_support`

failures and one critical refusal failure; neither cause should be guessed

from score alone. The injection detector is intentionally conservative

rather than a comprehensive prompt-injection classifier, and the project does

not claim complete protection against every possible adversarial document.

The timeout bounds caller wait; it does not establish cancellation or

termination of the underlying provider work. See the ranked limitations in

[docs/ISSUES.md](docs/ISSUES.md).



## Application contract and gap-closing work



- [Current project state](docs/CURRENT_STATE.md)

- [Accepted application contract](docs/APPLICATION_CONTRACT.md)

- [Gap-closing plan and verification](docs/GAP_CLOSING_PLAN.md)



Accepted requirements and verified implementation are tracked separately.



## How to run it



The project requires Python 3.11 or later and `uv`.



Clone the repository and install the locked dependencies:



```bash

git clone https://github.com/apeaircreative/my-final-assignment.git

cd my-final-assignment

uv sync --locked

```



Dependency installation may require network access unless the required

packages are already available in the local cache.



After installation, run the local checks with the fake provider:



```bash

uv run ruff check .

BOOTCAMP_PROVIDER=fake uv run pytest

```



These checks use the fake provider and do not establish live-model answer

quality. For optional Ollama use, start the local server and pull the model,

then run commands with `BOOTCAMP_PROVIDER=ollama` and

`BOOTCAMP_MODEL=qwen2.5:7b-instruct`.



For final submission, commit and push first, then use

`uv run bootcamp final submit --github <you>`; `--dry-run` does not open a pull

request.



## Measured results



The Offline CI badge reports the `check` workflow status for push runs on the

destination repository's `main` branch. Offline checks use the fake provider

and do not establish live-model answer quality. The practice-score job is

informational. Historical provider-backed and before/after results below are

not interchangeable measures of grounded-answer quality.

### At a glance

| Area | Recorded result | How to read it |
|---|---|---|
| Offline test suite | **42 passed** (2026-10-22) | Historical fake-provider result; not live-model quality evidence. |
| Public practice grader | **5/10** (2026-10-19) | Critical safety gate failed; not a passing baseline. |
| Item-detail prompt comparison | Item-detail **5/6**; baseline **3/6** | Promising signal on selected public cases, not validation. |
| Paired P3 public-practice comparison | Item-detail **6/10**; baseline **5/10** | Item-detail passed the critical gate; historical result, not a general quality guarantee. |

The detailed record below preserves the individual runs, artifacts, limitations, and reproduction commands.

<details>
<summary>Historical evidence, artifacts, and reproduction notes</summary>

These records are historical and revision-scoped. They are not a fresh evaluation, certificate evidence, or a current readiness determination.

| Evidence | Recorded result and limitation |
|---|---|
| Offline contract tests | 42 passed at revision `3acc09e` on 2026-10-22, before the quote-diagnostic regression test. Fake-provider tests do not establish live-model answer quality. |
| Public-practice evaluation | Ollama `qwen2.5:7b-instruct` scored 5/10 on 2026-10-19, with the critical gate failed. Four grounded cases failed `claim_support`; refusal case `fa-09` failed refusal gates. |
| Retrieval and prompt experiments | Repeated top-k comparisons did not establish a stable winning setting. The historical P3 comparison recorded baseline 5/10 with the critical gate failed and item-detail 6/10 with it passed; this does not establish a general quality improvement. |

The public grader's `claim_support` check uses normalized literal phrase matching, not semantic entailment. A failure alone does not distinguish an unsupported claim from a valid paraphrase the grader missed. The preserved 5/10 report contains answer hashes and gate results, not answer text, traces, or elapsed time.

### Inspect the evidence

- [Historical evaluation report](docs/EVAL_REPORT.md) — Evaluation context, trace-fidelity findings, and limitations. The FakeLLM score remained 3/10 before and after the targeted trace correction; that score did not measure the corrected behavior.
- [Preserved public-practice report](score_report_qwen25_7b_instruct_baseline_2026-10-19.json) — The recorded 5/10 result and gate outcomes.
- [Retrieval and prompt investigation](docs/extra.md) — Top-k comparisons, sampling and prompt-format corrections, held-out review, P2/P3 results, and linked run artifacts.
- [Current status and verification](docs/CURRENT_STATE.md) — Revision-specific status and readiness references.

### Run artifacts and detailed analysis

| Investigation | Preserved records |
|---|---|
| Top-k comparison | [Run 1](runs/topk/topk_20261019T141256980988Z.json) · [Reversed repeat](runs/topk/topk_20261019T143804177172Z.json) · [Analysis](docs/extra.md#top-k-comparison-completed-run) |
| Excluded provider-failure attempt | [Artifact](runs/topk/topk_20261019T140735014844Z.json) — Preserved but excluded from score comparisons |
| Controlled critical cases | [Initial request](runs/controlled-cases/controlled_20261019T145758140020Z.json) — Effective sampling settings unverified · [Corrected request](runs/controlled-cases/controlled_20261019T151030186736Z.json) |
| Coverage-instruction experiment | [Artifact](runs/controlled-cases/controlled_20261019T152136795480Z.json) — Historical 0/6 condition; not the proposed next experiment |
| Item-detail comparison | [Baseline](runs/controlled-cases/controlled_20261019T153350983580Z.json) · [Variant](runs/controlled-cases/controlled_20261019T153909079243Z.json) · [Prompt and grader analysis](docs/extra.md#prompt-and-grader-inspection) |
| Source-anchored held-out review | [Artifact](runs/heldout-prompts/heldout_20261019T155719476244Z.json) — Exploratory human review, not an aggregate score |
| P2 comparison | [Artifact](runs/heldout-prompts/heldout_20261019T162557469738Z.json) · [Analysis](docs/extra.md#p2-paired-comparison-results) — Consumed set; do not reuse for prompt tuning |
| P3 public-practice comparison | [Analysis](docs/extra.md#p3-paired-comparison-results) |
| R&D priorities and source review | [Priority matrix and review](docs/extra.md#rd-priority-matrix) |

### Reproduction tools

These links identify tools for separately planned runs; they do not indicate that a new run has been authorized or completed.

- [`scripts/record_final_grade.py`](scripts/record_final_grade.py) — Preserve per-case answers, traces, and evaluation-loop timing for a future single-setting public-grader run.
- [`scripts/compare_topk.py`](scripts/compare_topk.py) — Compare retrieval settings while recording answer and trace evidence.
- [`scripts/controlled_cases.py`](scripts/controlled_cases.py) — Repeat selected cases with explicit Ollama sampling options. Consult the [experiment analysis](docs/extra.md#prompt-and-grader-inspection) before selecting a condition; the historical coverage-instruction variant scored 0/6 and is not the proposed next experiment.

</details>


## Sources



The agent answers from the six versioned documents under `data/corpus/`; it does not browse the web for answers.



## Further experiments



The [retrieval architecture investigation](docs/extra.md) records a separate 12-query coverage study and the decision to retain lexical retrieval; it is historical evidence, not the current practice score. Supporting diagnostics: [fa-01](scripts/diagnose_fa01.py), [fa-05](scripts/diagnose_fa05.py), [top-k](scripts/diagnose_fa05_topk.py), the [top-k comparison harness](scripts/compare_topk.py), the [full grader recorder](scripts/record_final_grade.py), and [quote handling](scripts/test_quote.py).



## Credits



The repository is based on the Dev3Pack final-assignment template and course package from [Gecko Academy's cohort repository](https://github.com/Gecko-Academy/dev3pack-cohort-2026-09), pinned in `pyproject.toml` and `uv.lock`.



---



## Repository landmarks

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