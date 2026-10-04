# my-final-assignment

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

`YourAgent.run()` retrieves up to four chunks for the application safety check, then calls the course `answer_question()` pipeline, which independently retrieves context for the model. Empty retrieval refuses without a model call. Otherwise the model returns strict JSON; one corrective retry is allowed if parsing fails. Citations are normalized and checked against retrieved document IDs. Unreturned citations are stripped, confidence is capped at `0.2`, and human review is required. The application then checks retrieved text for its configured instruction-like literal. Provider errors and timeouts return a flagged refusal.

Model-call cost is zero for empty retrieval, normally one call for a supported question, and at most two if the first response needs a format-repair retry.

See [docs/adr/0001-run-shape.md](docs/adr/0001-run-shape.md) for the measured run-shape decision and reversal condition.

## Measured results

The current-candidate run and the historical before/after evaluation use different lanes; they are not interchangeable measures of grounded-answer quality.

| What | Command | Model | Result |
|---|---|---|---|
| Contract tests | `uv run pytest` | FakeLLM | Previously passed per the project record; not rerun on current HEAD `7bc03d4` |
| Current public practice grader | `BOOTCAMP_PROVIDER=ollama BOOTCAMP_MODEL=qwen2.5:7b-instruct OLLAMA_BASE_URL=http://127.0.0.1:11434/v1 uv run bootcamp final grade --report /tmp/final-practice-run-current-head-2026-10-04.json` | `ollama:qwen2.5:7b-instruct` | 6/10 (60%); critical safety gate failed. Failed: `fa-01`, `fa-02`, `fa-03`, `fa-05`. Run on `7bc03d4`; report is local under `/tmp`. |
| Rank 1 before/after | See [docs/EVAL_REPORT.md](docs/EVAL_REPORT.md) | FakeLLM | 3/10 before (`5219834`) → 3/10 after (`afecf87`); the targeted trace regression improved, while the score did not measure that behavior. |

The practice grader is a local diagnostic, not certificate evidence. The FakeLLM does not generate grounded answers from retrieved context, so the historical 3/10 does not mean grounded-answer quality was 30%. The Ollama result is provider-backed, but still does not represent the private final set.

## The honest limitation

The top-ranked issue was failure-trace fidelity; the fix and regression test preserve retrieval, provider-call, and decision events. The current practice run still fails critical case `fa-05` on citation recall, citation precision, and claim support. The application injection detector is a narrow literal check, and the existing tests do not establish comprehensive prompt-injection coverage. See the ranked limitations in [docs/ISSUES.md](docs/ISSUES.md).

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

The [retrieval architecture investigation](docs/extra.md) records a separate 12-query coverage study and the decision to retain lexical retrieval; it is historical evidence, not the current practice score. Supporting diagnostics: [fa-01](scripts/diagnose_fa01.py), [fa-05](scripts/diagnose_fa05.py), [top-k](scripts/diagnose_fa05_topk.py), and [quote handling](scripts/test_quote.py).

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