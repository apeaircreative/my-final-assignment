# Application contract
---

**Current contract status**
- Q1–Q4 verification is recorded per rule below.
- B5/B6 controlled offline characterization is integrated; it does not establish
  production corrections.
- The B5 trace-fidelity gap and B6 provider-lifecycle limitations remain
  unresolved.
- Live-model quality remains unverified. A passing full suite alone does not
  establish every contract guarantee.

Status reconciled: 2026-11-02
Decision date: 2026-10-21
Baseline reviewed: [`7d6513a`](https://github.com/aprewards35-coder/my-final-assignment/commit/7d6513a)

---

This document records the intended behavior of the supported application
interfaces.

The owner has accepted the four decisions below. Acceptance establishes
requirements; it does not establish that the implementation already
satisfies them.

For historical results, see [CURRENT_STATE.md](CURRENT_STATE.md).
For sequential implementation and verification, see
[GAP_CLOSING_PLAN.md](GAP_CLOSING_PLAN.md).

**How to read this contract**

The Q1–Q4 sections below state accepted requirements, their rationale,
limitations, and the revision-scoped verification records. Verification
observations describe behavior at the identified revisions and worktree
states; they do not silently amend the accepted requirements or establish
current implementation behavior beyond that evidence.

**Q1–Q4 overview**
- [Q1 — Supported entry points](#q1--supported-entry-points)
- [Q2 — Citation requirement](#q2--citation-requirement)
- [Q3 — Review-to-refusal policy](#q3--review-to-refusal-policy)
- [Q4 — Retrieved-content instruction check](#q4--retrieved-content-instruction-check)

## Terms

### Supported interfaces

`YourAgent.run(question)` and `YourAgent.__call__(question)`.

### Substantive answer

An answer that attempts to provide an answer to the user's question rather
than abstaining because the question is unsupported or the system cannot
safely answer.

The application must not depend solely on a model's review flag to determine
that a substantive answer is safe to return.

### Valid retrieved citation

A citation naming a document ID present in the retrieved set used by the
answer pipeline.

This establishes citation provenance, not semantic support for every claim.

### Standard flagged refusal

The existing application refusal shape:

- The standard corpus-based refusal text.
- No citations.
- Confidence `0.0`.
- `needs_human_review=True`.

### Review flag

A status marker indicating that an output requires human review.

The flag does not establish that a human-review queue, notification, or
operational workflow exists.

## Q1 — Supported entry points

### Accepted rule

The supported hardened application interfaces are:

- `YourAgent.run()`, which returns the full result.
- `YourAgent.__call__()`, which delegates to `run()` and returns its answer.

`__call__()` must forward the question unchanged to that instance's `run()`
and return `result.answer`.

### Excluded interfaces

`answer_with_state()` remains a teaching helper outside this hardened
application contract.

Registered tools, including `summarize_document`, are not invoked by `run()`
and must not be described as sharing its protections.

Exclusion from this contract is not a requirement to preserve weaker behavior.
Future hardening is allowed, but promotion to a supported interface requires
an explicit scope decision and verification.

### Rationale

Users and maintainers need one clearly identified supported answer path.
An internal helper must not silently become a supported product interface.

If `answer_with_state()` is promoted later, the implementation must preserve
its intended state, preference, retrieval, and episode behavior while
enforcing the accepted answer contract.

### Verification status

Verified by `test_call_delegates_to_run_and_returns_its_answer` in
`tests/test_contract.py` at revision
`3a8ac9420769a5fb71abe5939e9acc552efa8e02`. The test verifies that
`__call__()` forwards the question unchanged to that instance's `run()` exactly
once and returns the same `result.answer` object.

This verifies Q1 delegation only; it does not independently verify Q2–Q4 or
timeout behavior.

## Q2 — Citation requirement

### Accepted rule

A substantive answer must contain at least one valid retrieved citation.

If no valid retrieved citations remain, return the standard flagged refusal.

This rule applies both when:

- The model initially supplies no citations.
- Citation sanitization removes every supplied citation.

### Rationale

The application promises source-checkable answers. An uncited substantive
answer provides no source breadcrumb for the user to inspect.

Refusing an uncited answer is a visible bounded failure. Returning it
unflagged silently weakens the product's source-grounding promise.

### Limit

A valid document ID does not prove that an answer is correct, complete, or
entailed by the retrieved passage.

### Verification status

Verified at HEAD
`e843309b20790e9f3a42f520a62bfb29e0220975`, with uncommitted implementation
and test changes in `agent.py` and `tests/test_contract.py` present during
verification.

- `test_uncited_substantive_answer_returns_standard_refusal`: initially empty
  citations produce the standard flagged refusal; passed in the focused Q2
  run.
- `test_all_citations_removed_returns_standard_refusal`: citation
  sanitization removes the fabricated ID, preserves its trace event, and the
  application returns the standard flagged refusal; passed in the focused Q2
  run.
- `test_citation_retrieval_never_returned_is_stripped_and_flagged`: existing
  partial-sanitization behavior with a valid citation remaining; passed.
- Full offline suite: `BOOTCAMP_PROVIDER=fake uv run pytest` — 26 passed.

These checks establish the required refusal when no valid citation remains;
they do not verify semantic claim support or complete Q3/Q4 behavior.

## Q3 — Review-to-refusal policy

### Accepted rule

Apply the following dispositions:

| Situation | Required disposition |
|---|---|
| Substantive answer has no valid retrieved citations | Standard flagged refusal |
| Model itself requests review | Standard flagged refusal, even if citation sanitization also occurs |
| Only citation sanitization caused review, and at least one valid citation remains | Preserve the cleaned answer, retain review, and cap confidence at 0.2 |
| Sanitization removes every citation | Standard flagged refusal under Q2 |

The citation-sanitization exception must not clear the review flag.

### Rationale

A citation-ID error may be partially recoverable when valid citations remain,
but the cleaned answer still requires review.

Model-requested review is a separate reason to refuse. The presence of a
citation-sanitization event must not conceal that reason.

### Interface constraint

The pinned course result may not preserve the distinction between:

- Review originally requested by the model.
- Review introduced only during citation sanitization.

The B3 investigation inspected the interface and exercised controlled mixed
cases. Its recorded outcome and the verification section below describe the
implemented observation approach and its limits.

Do not promise a structured-reason solution until its compatibility with
the pinned interface has been established.

### Limit

Removing an invented citation does not remove or validate the associated
claim. The retained answer remains low-confidence and flagged.

### Verification status

Verified at HEAD `7c193fb3397f93333313d6ab3ed550b0e11645a9`, with uncommitted
implementation and test changes in `agent.py` and `tests/test_contract.py`
present during verification.

- `test_model_requested_review_returns_standard_refusal` and
  `test_model_requested_review_with_sanitization_returns_standard_refusal`:
  model-requested review produces the standard refusal with and without
  citation sanitization.
- `test_citation_retrieval_never_returned_is_stripped_and_flagged`:
  sanitization-only review with a valid citation remaining preserves the
  cleaned, low-confidence, flagged answer; the controlled model input has
  `needs_human_review=False`.
- `test_parse_repair_uses_review_flag_from_valid_response`: malformed first
  output is rejected by the course parser; the valid repair's review flag
  controls the result.
- `test_review_observation_is_isolated_between_runs`: both review-flag orders
  on the same agent and client produce their expected outcomes.
- `test_unknown_review_provenance_returns_standard_refusal`: missing observer
  state fails closed; this test uses a controlled local seam.
- `test_two_parse_failures_preserve_course_refusal_without_provenance_event`:
  the course refusal is preserved without an extra provenance-failure event.
- Q3/observer focused cases: 9 passed; Q2 plus refusal/provider-error/timeout
  checks: 5 passed; full offline suite: 34 passed; `git diff --check` passed.

The application observer uses the exact course parser and retains only the
parsed review boolean. It is request-scoped and sits outside `TimeoutClient`.
Successive-run tests verify outcomes; request-local construction is also
established by code inspection. These offline tests do not establish timeout
cancellation, concurrent-provider safety, or live-model quality. Q4 boundary
coverage was pending at this historical verification point; see Q4's
subsequent verification record below.

## Q4 — Retrieved-content instruction check

### Accepted rule

Retain the post-generation retrieved-content check on the supported answer
path.

If the configured detector matches retrieved content, discard the generated
answer and return the standard flagged refusal.

This is a returned-answer guarantee for detector matches. It is not a
model-exposure guarantee.

### Guarantee boundaries

The application does not claim that:

- No untrusted text reaches the model.
- No detector-matching text reaches the model.
- Every malicious instruction is detected.
- The generated answer itself is inspected by this detector.
- Unmatched attacks are rejected by this check.

The detector examines retrieved input after generation. It is not a semantic
classifier and is not a generated-output scanner.

### Known detector behavior

The reviewed implementation matches configured exact phrases even in benign
quotations, matches some regex variants, and misses other phrasings.

These are characterization boundaries, not claims of comprehensive security
and not a requirement that the detector remain unchanged forever.

### Rationale

The accepted scope concerns the answer returned by the current bounded
pipeline. That path does not execute the registered tools.

With the same detector and equivalent retrieval, moving the check earlier
would change model exposure, calls, latency, cost, and traces—not inherently
the matching set or false-refusal set.

Earlier gating remains a legitimate future option. Revisit the decision if
the application gains action-taking capabilities or different data-exposure
requirements.

### Verification status

Verified at HEAD `d21895acb2e8d737113e3f7ae9b3ba1d15ea01f8`, with uncommitted
test changes in `tests/test_contract.py` present during verification.

The parameterized `test_instruction_detector_characterization` covers seven
direct `Chunk`/`ScoredChunk` inputs without retrieval. The
`test_prompt_injection_corpus_example_detector_characterization` test loads
the versioned `prompt-injection` document and scans its full text as a
constructed chunk; the detector does not match that quoted example.

The strengthened existing `test_injection_cannot_dictate_an_unflagged_answer`
establishes that matching content reaches the controlled model, which
attempts to answer `ACCESS GRANTED`; `YourAgent.run()` returns the canonical
refusal shape and records the application instruction-content refusal
decision.

Verification: focused detector/injection tests — 10 passed, 26 deselected;
full offline suite — 42 passed; `git diff --check` — passed. Collection
reported 36 cases in `tests/test_contract.py` and 6 across the other two test
files.

Detector misses and quote-sensitive false positives remain. Characterization
expectations may change with an intentional detector improvement; they are
not permanent desired security requirements. The integration test verifies
the returned result, not prevention of model exposure or comprehensive
injection resistance. These are offline checks, not live-model quality
evidence. Q1–Q4 offline checks are complete; Phase A A2 and reliability tasks
B5/B6 retain their separate statuses in the plan.

## Cross-cutting reliability verification

B5 and B6 have received controlled offline characterization. These observations
record tested behavior; they do not establish production corrections.

- **B5 — Failed parse repair:** The controlled case returned the standard flagged
  refusal after malformed initial output and a repair `ConnectionError`. The
  replacement trace omitted the initial completion and parse-failure/repair
  history. The trace-fidelity gap remains unresolved.
- **B6 — Caller timeout and provider operation:** The caller returned a flagged
  refusal while the controlled operation remained incomplete before explicit
  release. After release, the operation reached its completion signal. This
  does not establish provider cancellation, worker-thread termination,
  comprehensive cleanup, concurrent-provider safety, strict end-to-end timing,
  or production resource impact.

Future verification must still examine the caller-waiting bound separately from
provider-request cancellation and inspect the failure trace when malformed
initial output is followed by a failed repair call. Describe only guarantees
supported by the evidence. Revision-specific commands, outcomes, and limitations
remain in [GAP_CLOSING_PLAN.md](GAP_CLOSING_PLAN.md).

## Change and verification rules

- Use offline controlled clients for these contract checks.
- Do not run a live model merely to characterize deterministic behavior.
- Distinguish characterization tests from unmet-requirement tests.
- Do not weaken assertions to make a demonstrated violation pass.
- Do not silently combine test-writing with production fixes.
- Keep corpus files and historical run artifacts unchanged.
- Record actual commands, outcomes, changed files, and remaining limitations.
- Review changes before committing.

A passing contract suite does not establish live-model grounded-answer
quality or private-grader success.