# Evaluation report

**Filled by:** session 7 (the baseline, and the evaluator's weakness), session 9
(failures named from traces), session 14 (one fix, measured after).

Every number below has the command that produced it, the commit it ran on, and
the model. A number without its command is an impression, and this file holds
none. CI has no keys, so any number CI printed is the offline fake model's.

## Evaluation lane

The comparable before/after lane is the offline practice evaluator using the
`FakeLLM`. This was chosen because the baseline result was produced with this
deterministic setup and the same evaluator command can be rerun after the Rank 1
fix.

An Ollama run was also explored during development, including installing and
running Ollama, but it is not used as the before/after measurement because that
run does not have a documented comparable baseline result with the same
evaluation command and commit metadata.

## Before

- model: offline `FakeLLM` practice model
- commit: `5219834`
- command: `uv run bootcamp final grade`
- result: 3/10 passed (30%)

### The evaluator's weakness (session 7)

The offline practice evaluator can verify refusal behavior, but the `FakeLLM`
does not produce grounded answers from the retrieved corpus. The baseline
therefore passed all 3 refusal cases while passing 0 of 6 grounded cases. The
30% score is a valid result for this practice lane, but it does not measure
real-model grounded-answer quality.

### Failures, named from traces (session 9)

| Case | Bucket | The trace line that decided it |
|---|---|---|
| Provider failure | failure-path trace fidelity | `[decision] provider connection error; flagged refusal` |
| Provider timeout | failure-path trace fidelity | `[decision] provider connection error; flagged refusal` |

The failure investigation reproduced that provider failures and timeouts returned
only a decision event. The retrieval stage and failed provider-call stage were
not represented in the returned trace. Timeout and provider failure were also
collapsed into the same decision wording.

## After

The fix for rank 1 of [ISSUES.md](ISSUES.md) (session 14).

- model: offline `FakeLLM` practice model
- commit: `afecf87`
- command: `uv run bootcamp final grade`
- result: 3/10 passed (30%); critical safety gate failed
- regression test: `test_regression_rank_1_of_the_issue_list`

### What got better (session 7's `improvement`)

The failure path now preserves the retrieval event, records the failed provider
call, and then records the refusal decision, making the execution path available
for diagnosis and verification of the corrective change. The targeted regression
test changed from red to green.

### What got worse, or could (session 7's `regression_or_risk`)

The practice evaluation score did not change: it remained 3/10 (30%), because
the offline evaluator does not measure trace fidelity and the FakeLLM still
cannot demonstrate grounded-answer quality.