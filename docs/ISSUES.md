# Ranked issues

**Ranking provenance:** The initial list was filled in session 9
(`cap01-e5`) and kept current until session 14, which fixes rank 1
and adds its regression test.

**Ranking rule:** Maintain at least three entries, use consecutive unique
ranks beginning at 1, and order by impact. These are document priority ranks,
not GitHub issue numbers.

| Rank | Issue |
|---:|---|
| 1 | [Failure traces do not faithfully represent the execution path of provider failures and timeouts.](#rank-1--initial-call-failure-covered-repair-failure-gap-demonstrated) |
| 2 | [Provider timeouts stop the agent from waiting but do not stop the underlying provider worker from running.](#rank-2--caller-timeout-characterized-lifecycle-risk-remains) |
| 3 | [The Session 11 memory/retention contract is not fully demonstrated by the current implementation and test coverage.](#rank-3--session-11-memoryretention-contract-remains-incompletely-demonstrated) |

## Rank 1 — Initial-call failure covered; repair-failure gap demonstrated

**Issue**

Failure traces do not faithfully represent the execution path of provider failures and timeouts.

**Impact**

It makes failures harder to diagnose and makes it harder to verify whether a corrective change addressed the actual failure mode.

**Existing implementation and regression coverage**

- Existing fix: reconstruct retrieval, failed-provider-call, and refusal
  decision events when a supported provider exception is caught.
- Existing regression: `test_regression_rank_1_of_the_issue_list` in
  `tests/test_contract.py` exercises failure on the initial provider call.
- Historical before/after evidence: see [EVAL_REPORT.md](EVAL_REPORT.md).

**B5 characterization and approved diagnostic target**

- B5 characterization on 2026-10-26 demonstrated that a malformed initial
  response followed by a repair-provider exception returns the standard
  refusal but loses the initial completion and parse-failure/repair history.
- Controlled coverage:
  `test_failed_parse_repair_trace_characterization` in
  `tests/test_contract.py`. Its passing assertions record the current
  limitation; they do not require preserving that limitation forever.
- Approved diagnostic target: distinguish the initial completion, parse
  failure and repair decision, failed repair call, and final refusal.
  Exact event formatting and implementation require separate Phase C review.
- No production correction for the repair-failure gap is included in B5.

**Evidence boundary**

This B5 case does not establish trace fidelity across every provider-failure
or timeout path.

## Rank 2 — Caller timeout characterized; lifecycle risk remains

**Issue**

Provider timeouts stop the agent from waiting but do not stop the underlying provider worker from running.

**Impact**

Repeated timeouts can leave provider work running after the agent has already refused, creating a resource-lifecycle risk that needs further evidence to establish its production impact.

**Source inspection and test coverage**

- Source inspection: the timeout wrapper bounds its wait for each provider
  invocation and raises `TimeoutError` when the worker remains alive.
  The inspected path does not attempt cancellation or subsequently join
  the timed-out provider worker.
- Existing coverage:
  `test_timeout_on_a_hanging_provider_is_flagged_within_a_second`.
- B6 controlled coverage:
  `test_timeout_returns_before_controlled_provider_operation_completes`.
- The controlled caller returns the standard flagged refusal while the
  provider operation remains incomplete. The operation reaches its
  completion signal after explicit test release.
- That signal does not prove internal worker-thread termination or
  comprehensive resource cleanup.
- A timely refusal is not proof of provider cancellation. Strict
  end-to-end timing, concurrent-provider safety, and production resource
  impact remain unestablished.
- This is characterization, not a lifecycle fix. Any production correction
  requires separately approved Phase C work.
- Verification details and revision context are recorded under B6 in
  [GAP_CLOSING_PLAN.md](GAP_CLOSING_PLAN.md).

## Rank 3 — Session 11 memory/retention contract remains incompletely demonstrated

**Issue**

The Session 11 memory/retention contract is not fully demonstrated by the current implementation and test coverage.

**Impact**

It leaves a required course deliverable insufficiently demonstrated and makes the intended retention boundary harder to verify, but it does not currently block the core research-agent execution path.

**Current implementation evidence**

The retention record distinguishes the research corpus, `SessionState`,
and `MemoryStore`:

- The six versioned corpus documents are the agent's persistent research
  knowledge; they are separate from conversation state.
- `SessionState.preferences` holds the demonstrated answer-style preference.
  `answer_with_state()` uses the short preference in the prompt.
- `SessionState.episodes` records up to five recent question summaries,
  each using `Q: ` plus the first 60 question characters. Reset clears
  preferences and episodes. `answer_with_state()` records episodes but
  does not add them to the prompt.
- `MemoryStore` is a Session 11 per-user memory exercise, not wired into
  the agent run. It stores in-memory `(user_id, key)` values, has no
  automatic expiration or five-item cap, and has no clear method. Remembering
  an existing key replaces its value.

**Test coverage documented in RETENTION.md**

SessionState coverage:

- `test_answer_with_state_applies_preference_and_caps_episodes` — the short
  preference reaches the model prompt and the latest five episodes remain.
- `test_answer_with_state_truncates_long_episode_questions` — episode
  questions use the first 60 characters.
- `test_session_state_reset_clears_preferences_and_episodes` — reset clears
  those two collections.

MemoryStore coverage:

- `test_memory_store_is_isolated_and_returns_none_when_missing` — values
  are isolated by user and key, and a missing entry returns `None`.
- `test_memory_store_defensively_copies_values` — caller mutations do not
  change the stored value.
- `test_memory_store_rejects_empty_user_ids` — `""` and `None` are
  rejected for both remember and recall.

**Evidence limitations**

The implementation does not technically prevent arbitrary values from being
passed to `MemoryStore`, and `answer_with_state()` does not inspect its
question summary for content or add the episode list to the prompt. The
documented product boundary is not enforced by a sensitive-data classifier
or refusal mechanism.

These tests do not establish sensitive-content filtering, confidentiality,
process-restart behavior, or a general deletion guarantee. Persistent
personal memory is not a demonstrated product requirement; this record
does not introduce one.

**Source**

See [RETENTION.md](RETENTION.md) for the retention decisions, implementation
distinctions, and test evidence.
