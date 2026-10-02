# Retention policy

This record states the project's retention decisions and distinguishes them
from the current implementation.

STORED: The six versioned corpus documents are the agent's persistent research
knowledge. During a process, session state holds an answer-style preference and
up to five question summaries; MemoryStore holds explicitly keyed values.

WHY: Corpus documents ground research answers. The preference shapes the
response prompt. Episode summaries retain bounded interaction history;
`answer_with_state()` currently records them but does not add them to the prompt.
MemoryStore demonstrates the Session 11 per-user memory exercise; persistent
personal memory is not a demonstrated product requirement.

CORRECTED BY: SessionState.reset() clears that instance's preferences and
episodes. Setting a preference or remembering an existing MemoryStore key
replaces its value; MemoryStore has no clear method.

EXPIRES: SessionState retains at most 5 episode records, each based on the first
60 question characters. In-memory state ends with the process; no time-based
expiration is implemented.

WE REFUSE TO REMEMBER: We do not make personal memory a product retention
feature without a demonstrated need. MemoryStore remains a Session 11 exercise;
this is an intended product boundary, not content filtering.

## Retention matrix

| Information / state | Product purpose | Retention boundary | Implementation evidence |
|---|---|---|---|
| Six corpus documents | Persistent knowledge used to ground research answers | Versioned corpus files; separate from conversation state | `CORPUS_DIR`; `YourAgent` loads corpus documents |
| `SessionState.preferences` | Currently, `answer_style == "short"` modifies the question prompt | Held by a `SessionState` instance; no size or time limit | `answer_with_state()`; reset test |
| `SessionState.episodes` | Bounded record of recent interaction | Latest 5 records; each records `Q: ` plus `question[:60]`; cleared by reset | `answer_with_state()`; cap, truncation, and reset tests |
| `MemoryStore` values | Session 11 per-user memory exercise; not wired into the agent run | In-memory `(user_id, key)` values; no automatic expiration or five-item cap | `MemoryStore`; isolation, missing-value, copy, and invalid-ID tests |

## Decision rationale

The research agent needs the six-document corpus as persistent knowledge. Its
interaction state is separate: the demonstrated preference changes the prompt,
and episode summaries are bounded to five records and 60 question characters.
Persistent personal memory is not currently a demonstrated product requirement.
`MemoryStore` is present to demonstrate Session 11's application-level memory
mechanism, not to establish a product need for retaining arbitrary personal
information.

The implementation does not technically prevent arbitrary values from being
passed to `MemoryStore`, and `answer_with_state()` does not inspect its question
summary for content or add the episode list to the prompt. The product boundary
above is not enforced by a sensitive-data classifier or refusal mechanism.

## Implementation evidence

The tests in `tests/test_contract.py` establish:

- `test_answer_with_state_applies_preference_and_caps_episodes`: the short
  preference reaches the model prompt and the latest five episodes remain.
- `test_answer_with_state_truncates_long_episode_questions`: episode questions
  use the first 60 characters.
- `test_session_state_reset_clears_preferences_and_episodes`: reset clears
  those two collections.
- `test_memory_store_is_isolated_and_returns_none_when_missing`: values are
  isolated by user and key, and a missing entry returns `None`.
- `test_memory_store_defensively_copies_values`: caller mutations do not
  change the stored value.
- `test_memory_store_rejects_empty_user_ids`: `""` and `None` are rejected for
  both remember and recall.

These tests do not establish sensitive-content filtering, confidentiality,
process-restart behavior, or a general deletion guarantee.

## Course references

- **Session 11 — State and Memory:** `units/en/unit3/session-11-state-and-memory/`
  defines the state and memory exercises and the five-line retention-policy
  deliverable. `concepts-2.mdx`, “What a memory must refuse to remember,” gives
  an example refusal list; `ch11-e2` checks that the policy fields are filled,
  not that code enforces their contents.
- **Final Assignment capstone guide:** Session 11 calls for `docs/RETENTION.md`
  and a test for the memory cap. The Session 11 store exercise is distinct from
  the agent's `YourAgent.run(question)` interface.
