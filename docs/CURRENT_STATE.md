# Current state of the project
---

Status: reviewed snapshot
Reviewed: 2026-10-21
Baseline reviewed: [`7d6513a`](https://github.com/aprewards35-coder/my-final-assignment/commit/7d6513a)
Verification status: [state exactly what was checked]

---

This document consolidates the project's reported state and the accepted
gap-closing decisions. It does not establish that every requirement is
implemented or verified.

Historical results and test counts below are carried forward from the
Phase A review. Before committing this snapshot, verify them against the
repository and retained artifacts. Documentation corrections are listed
separately because identifying a correction is not the same as applying it.

## What the system is

A bounded, source-grounded research assistant. `YourAgent` in
[`agent.py`](../agent.py) answers developer questions using six versioned
documents in [`data/corpus/`](../data/corpus/).

Its intended behavior is to cite retrieved sources and refuse questions the
corpus does not support. Enforcement is narrower than that product goal.
Accepted requirements and known gaps are recorded in
[APPLICATION_CONTRACT.md](APPLICATION_CONTRACT.md).

### Ownership boundaries

The pinned course dependency owns:

- Retrieval and context construction.
- Strict-JSON parsing with at most one repair retry.
- Citation-ID normalization and verification against retrieved document IDs.

The application wrapper owns:

- The source-terminology prompt extension.
- Per-call timeout handling.
- Provider-failure refusal traces.
- Review-to-refusal conversion.
- The post-generation instruction-pattern check on retrieved content.

The course dependency is pinned to commit:

`1de8649529156c35bdeafacfbbef40726a9b0fba`

### Execution shape

The supported answer path is a fixed retrieve-then-generate chain:

- No retrieved chunks: refuse without calling the model.
- Retrieved chunks: one model call.
- Invalid response format: at most one repair call.

The registered tools are not invoked by `YourAgent.run()`. The
`max_tool_calls=3` argument is accepted but unused by the pinned course
answer pipeline. It must not be described as an enforced tool budget on
this execution path.

## Reported verification and experimental evidence

These results belong to their recorded revisions and configurations.
They are not automatically measurements of a later working tree.

### Offline tests

The Phase A review reports:

- 17 collected cases in `tests/test_contract.py`.
- 23 collected cases across the full suite.
- All cases passing at the reviewed checkout.

Verify collection counts and actual test outcomes before updating the README.
These tests establish controlled offline behavior, not live-model answer quality.

### Historical public practice report

The preserved
[2026-10-19 report](../score_report_qwen25_7b_instruct_baseline_2026-10-19.json)
records:

- 5/10 passed.
- Critical gate failed.
- Critical refusal case `fa-09` failed.

This summary artifact contains answer hashes and gate results, not complete
answer text, retrieved passages, or execution traces.

### Top-k experiments

No tested setting established a stable winner across the recorded comparisons.
`top_k=4` remains the conservative existing default, not a proven optimum.

Provider-failure attempts must remain excluded from model-quality comparisons.

### Sampling and prompt corrections

The experimental Ollama request shape was corrected from nested `options`
to top-level sampling fields.

The prompt extension was corrected to use actual line breaks rather than
literal backslash-n characters. A regression test covers that separator.

Historical runs must retain their original configuration caveats. A later
correction does not retroactively validate earlier settings.

### Prompt experiments

The reported results are:

| Experiment | Result | Interpretation |
|---|---|---|
| Broad coverage instruction | 0/6 | Rejected wording for the tested condition |
| Corrected-source selected-case comparison | Baseline 3/6; item-detail 5/6 | Promising selected-case signal, not general validation |
| P3 full public-set comparison | Baseline 5/10 with critical fail; item-detail 6/10 with critical pass | Public-practice regression evidence, not private-grader evidence |

The Phase A review reports that P3 was repeated and that answers, retrievals,
and grader outcomes were byte-identical between its two runs. This comparison
claim must be checked against both complete artifacts before being presented
as verified in updated documentation.

P3 artifacts are retained under
[`runs/public-prompt-comparison/`](../runs/public-prompt-comparison/).

The P3 repeat is a different experiment from the corrected-source
selected-case comparison. Their repeatability claims must not be conflated.

### Prompt decision

Keep the baseline prompt as the default.

The item-detail instruction remains a preserved candidate, not an adopted
application change. Future adoption requires a newly authored, independently
reviewed evaluation set and a frozen comparison protocol.

The six-question exploratory set and eight-question P2 set are consumed
evaluation material, not untouched holdouts.

## Accepted application decisions

The accepted contract is recorded in
[APPLICATION_CONTRACT.md](APPLICATION_CONTRACT.md).

In summary:

1. `YourAgent.run()` and its delegating `__call__()` are the supported
   hardened interfaces.
2. A substantive answer must retain at least one valid retrieved citation;
   otherwise return the standard flagged refusal.
3. Model-requested review requires refusal, even when citation sanitization
   also occurs. Sanitization-only review may preserve a cleaned answer
   only when at least one valid citation remains.
4. Retain the post-generation retrieved-content check. Its guarantee
   concerns the returned answer for detector matches, not prevention of
   model exposure or comprehensive injection detection.

Acceptance does not mean these requirements are already implemented.

## Detector characterization

The reviewed detector:

- Matches configured exact phrases, including those inside benign quotes.
- Matches some regex variants.
- Excludes regex-only matches when a quote directly precedes the matched
  instruction.
- Misses other phrasings, such as "ignore your instructions".
- Does not match the corpus's own quoted example under the reviewed wording.

The check runs after generation. Existing injection tests verify that the
instruction reaches the controlled model and that the returned answer is
overridden for the tested matching content.

They do not prove that the model was protected from exposure, or that
unmatched attacks are rejected.

Preserve executable boundary tests and their actual output rather than
relying only on a prose characterization.

## Documentation reconciliation checklist

- [ ] Verify the reported test counts and passing outcomes.
- [ ] Inspect both complete P3 artifacts and verify their comparison results.
- [ ] Replace the README's stale "P3 is ready" wording with completed results
      and the keep-baseline decision.
- [ ] Replace the README's stale "16/16" test count with verified counts.
- [ ] Correct the selected-case repeatability statement in `docs/extra.md`.
- [ ] Link the current-state summary, accepted contract, and gap-closing plan
      from the README.

### Selected-case repeatability correction

The corrected-source section of `docs/extra.md` reportedly states that answers
were identical across repeats within each condition and task.

The Phase A review identifies variation in:

- Item-detail `fa-05`: repeat 1 differs from repeats 2–3 and has a different
  `claim_support` outcome.
- Baseline `fa-07`: repeat 1 differs from later repeats.

Verify these differences against the controlled-case artifacts and replace
the blanket identical-repeats claim.

Keep this correction separate from the reported byte-identical P3 repeat.

## Remaining work

Follow [GAP_CLOSING_PLAN.md](GAP_CLOSING_PLAN.md) sequentially.

- Phase A: reconcile evidence, record accepted scope, and correct documentation.
- Phase B: add focused offline tests for accepted rules and known boundaries.
- Phase C: fix demonstrated contract violations with the smallest appropriate
  changes.
- Subsequent quality evaluation: use a freshly frozen protocol before
  quality-affecting experiments.

## Tracked limitations

See [ISSUES.md](ISSUES.md).

- The timeout bounds caller waiting but does not cancel the underlying
  provider worker.
- The memory/retention contract remains incompletely demonstrated.
- Citation-ID validation is not semantic claim verification.
- The detector is deliberately narrow.

No model evaluation, test execution, or implementation change is established
merely by adding this document.