# ADR 0001: the shape of one run

**Filled by:** session 10, informed by the Session 8 shape comparison and the
final-assignment investigations.

- Status: accepted
- Date: 2026-10-02

## Context

Session 8 compared three bounded patterns on the same task using the offline
FakeLLM. The submitted notebook measured 1 model call for the deterministic
chain, 2 for the tool loop, and 3 for reflection. The chain could not refuse
before a model call; the tool loop and reflection pattern could. Session 8 also
showed that additional model calls add latency/cost and introduce additional
failure modes.

The optional graph appendix was not run in the submitted Session 8 notebook,
so no graph call-count measurement is claimed here.

For this final assignment, the current implementation follows the bounded chain
shape with one conditional parse-repair call. The final-assignment investigations
also established that failure traces need to preserve the retrieval, provider
call, and refusal stages, but did not establish a need for model-directed tool
orchestration.

## Decision (`decision`)

We keep the bounded RAG chain with one conditional parse-repair call in
`agent.py`.

## Options considered (`options_considered`)

1. Bounded RAG chain with one conditional parse-repair call.
2. Model-directed tool loop that can choose tools and continue under a call
   budget.

## Why not the other option (`why_not`)

The tool loop adds model-directed decisions and additional call cost without a
demonstrated final-assignment requirement for tool selection. Session 8 measured
2 model calls for the tool-loop pattern versus 1 for the deterministic chain on
the comparison task, while the current research agent already has a bounded
retrieval, validation, repair, and refusal path.

## What would reverse it (`reverses_it`)

Reconsider the chain if a representative evaluation of 10 required questions
shows that more than 2 model calls are needed for more than 2 of the 10 cases,
and a concrete alternative demonstrates that the additional calls are necessary
to complete those tasks without violating the project's safety, latency, call,
or trace requirements.