# Ranked issues

**Filled by:** session 9 (the first list, `cap01-e5`), kept current until
session 14, which fixes rank 1 and adds its regression test.

At least three rows. Ranks 1, 2, 3... with no gap and no tie: two issues ranked
1 is a list nobody prioritised. The impact is what orders it.

| rank | issue | impact |
|---:|---|---|
| 1 | Failure traces do not faithfully represent the execution path of provider failures and timeouts. | It makes failures harder to diagnose and makes it harder to verify whether a corrective change addressed the actual failure mode. |
| 2 | Provider timeouts stop the agent from waiting but do not stop the underlying provider worker from running. | Repeated timeouts can leave provider work running after the agent has already refused, creating a resource-lifecycle risk that needs further evidence to establish its production impact. |
| 3 | The Session 11 memory/retention contract is not fully demonstrated by the current implementation and test coverage. | It leaves a required course deliverable insufficiently demonstrated and makes the intended retention boundary harder to verify, but it does not currently block the core research-agent execution path. |

## Rank 1, fixed

- The fix: Preserve the retrieval trace and record the failed provider call before returning the flagged refusal.
- The regression test: `test_regression_rank_1_of_the_issue_list` in `tests/test_contract.py`.
- Before and after: see [EVAL_REPORT.md](EVAL_REPORT.md).
