# Documentation Guide

A guided entry point to the project's architecture, development workflow, and evaluation evidence.

The linked documents remain authoritative for their own requirements, decisions, implementation details, evidence, and status.

---

## Choose Your Reading Path

### 01 — Understand the Project

Learn what the assistant does, how its answer flow works, and which design decisions govern its behavior.

**Reading sequence**

1. [Project overview](../README.md) — Introduces the research assistant, its purpose, example behavior, and measured results.
2. [Answer flow](../README.md#architecture) — Explains how the course-provided answer pipeline and application wrapper fit together, including the boundaries around model-generated answers.
3. [Accepted behavior](APPLICATION_CONTRACT.md) — Records accepted rules for supported interfaces and application behavior. Acceptance does not establish that the implementation satisfies every rule.
4. [Status and verification](CURRENT_STATE.md) — Provides reconciled project status and evidence tied to specific revisions.

**Supporting references**

- [Run-shape decision](adr/0001-run-shape.md) — Explains the decision to retain a bounded RAG chain, the alternative considered, and the condition that would justify revisiting it.
- [Retention decisions and boundaries](RETENTION.md) — Explains what information the application is intended to retain, why, and how documented decisions compare with implementation behavior.
- [Retrieval investigation](extra.md) — Records an investigation of retrieval alternatives and why it did not authorize an architecture change.

---

### 02 — Run, Maintain, and Extend

Set up the codebase, understand development conventions, and investigate implementation changes.

**Reading sequence**

1. [Run locally](../README.md#how-to-run-it) — Provides the project's documented setup and execution instructions.
2. [Repository guidance](../AGENTS.md) — Describes the project, coding-assistant conventions, safety boundaries, and documents to consult before changing application behavior.
3. [Accepted behavior](APPLICATION_CONTRACT.md) — Establishes the accepted behavior against which implementation work is considered.
4. [Implementation plan](GAP_CLOSING_PLAN.md) — Describes the sequence for turning accepted decisions into focused checks, investigating gaps, and reviewing proposed corrections.

**Supporting references**

- [Project tests](../tests/) — Browse tests that exercise application behavior and documented boundaries.
- [Tracked work](https://github.com/apeaircreative/my-final-assignment/issues) — Find the repository's current issue discussions.
- [Original ranked issues and characterization](ISSUES.md) — Preserves the original ranked findings and subsequent characterization; it is not the complete live backlog.
- [Audit retrieved content](SKILL.md) — Follow a focused method for examining how retrieved content reaches models and tools, and what the implementation and tests establish.
- [Collect PR evidence](PR_REVIEW_WORKFLOW.md) — Follow the integrated pull-request evidence collection workflow. A collected report supports reviewer assessment; it is not an approval decision.
- [Collector implementation](../scripts/pr_review_report.sh) — Inspect the script used by the PR evidence workflow.
- [Collector tests](../tests/test_pr_review_report.py) — Inspect tests for the collector's behavior and failure cases.

---

### 03 — Evaluation Readiness

Understand the evaluation protocol, implemented controls, recorded evidence, and readiness assessments.

**Reading sequence**

1. [Status and verification](CURRENT_STATE.md) — Provides the consolidated project status and revision-specific evidence. Use this record to locate current readiness-gate references.
2. [Approved evaluation protocol](https://github.com/apeaircreative/my-final-assignment/issues/8) — Defines the planned baseline-versus-candidate comparison and its prerequisites. Approval of the protocol does not itself authorize execution.
3. [Evaluation controls](EVALUATION_CONTROLS.md) — Describes the implemented partial controls, the evidence they record, and the limits of what they establish.

**Supporting references**

- [Historical evaluation report](EVAL_REPORT.md) — Preserves historical, revision-scoped evaluation evidence; it is not a current quality result or readiness determination.
- [Completed readiness assessment](https://github.com/apeaircreative/my-final-assignment/issues/12) — Historical assessment of the evaluation tooling and its limitations.
- [Gap-closing plan](GAP_CLOSING_PLAN.md) — Describes the relationship between accepted requirements, implementation work, and verification.
- [Retrieval investigation](extra.md) — Provides background on the investigation of retrieval-related evaluation findings.