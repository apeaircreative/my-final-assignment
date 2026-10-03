# Retrieval Architecture Investigation

**Status:** Investigation complete — no architecture change

This document records a focused investigation into the retrieval architecture of the Source-Grounded Research Assistant and how the course material informs possible improvements.

The final assignment remains on the course-provided lexical retrieval baseline. This investigation does **not** authorize an architecture change. Any future retrieval change should be supported by independent evaluation evidence and, where appropriate, a separate ADR.

***

## Why We Investigated

A real-model public-practice evaluation scored 4/10, with failures involving citation recall and claim-support checks.

The investigation asked whether those failures demonstrate a retrieval-architecture problem, rather than changing retrieval simply to improve a grader result. It considered:

- The current final-assignment retrieval implementation
- Retrieval lessons and examples across the cohort
- Optional and advanced RAG material
- LangChain, ChromaDB, embeddings, hybrid retrieval, reranking, and query expansion
- An independent retrieval-coverage experiment

***

## Current Baseline

The final assignment uses the course’s deterministic lexical retrieval baseline:

- Six provided corpus documents
- Paragraph-based chunks
- Non-stopword token overlap
- IDF-weighted scoring
- Deterministic top-\(k\) retrieval
- Stable document and chunk identifiers
- Document-level citation validation
- No additional database, dependency, network service, or retrieval model in the answer path

A known limitation is that a passage with no qualifying shared lexical vocabulary cannot be retrieved, even when it is semantically relevant.

***

## Course-Supported Options

| Approach | Course role | Assignment fit |
|---|---|---|
| Lexical retrieval | Required baseline | Compatible |
| Chunking and top-\(k\) experiments | Baseline tuning | Compatible |
| Query expansion | Demonstrated experiment | Possible, but regression risk |
| BM25-style lexical ranking | Course-owned improvement | Compatible candidate |
| Embeddings and ChromaDB | Optional project / runnable demonstration | Conflicts with current answer-path constraints |
| Hybrid lexical + semantic retrieval | Advanced concept | Requires additional architecture |
| Reranking | Advanced technique | Adds complexity and model cost |
| Graph RAG | Advanced / optional | Not justified for six-document QA |

The course also teaches that retrieval improvements should be measured on held-out queries rather than assumed to generalize from a few successful examples.

***

## LangChain Finding

The cohort does **not** demonstrate LangChain as the retrieval or vector-store abstraction for this final-assignment path.

LangChain appears elsewhere in the course for model/provider integration, prompts, and external search tooling. The course’s ChromaDB examples interact with ChromaDB directly rather than through LangChain retrievers or vector-store wrappers.

The presence of LangChain-related dependencies is therefore not evidence that the final assignment should migrate to a LangChain retriever.

***

## Investigation Evidence

An independent set of 12 concept-level questions was evaluated against the existing retrieval implementation. The audit did not modify the project or run the model, grader, or corpus through a new path.

| Measure | Result |
|---|---:|
| Questions tested | 12 |
| Intended answer-bearing passages in top 3 | 11 |
| Top-3 coverage | 91.7% |
| Confirmed misses | 1 |
| Miss rate in this sample | 8.3% |

One query missed its intended answer-bearing passage even when retrieval expanded to top 40. The query and target passage lacked sufficient lexical overlap for the current scorer.

This confirms a real lexical-retrieval limitation outside the final-practice questions. It does **not** establish that retrieval is broadly failing across the assignment or that the observed sample estimates general user behavior.

The investigation also distinguishes three different questions:

- **Retrieval coverage:** Did the needed passage reach the model context?
- **Retrieval quality:** Was the returned context relevant, precise, and appropriately ranked?
- **Grounding:** Are the final answer’s claims actually supported by the retrieved evidence?

The current evidence is strongest for the first question.

***

## What 4/10 Means

The public-practice result confirms that the system can run end to end and pass some evaluated cases. It also identifies failures involving citation recall, citation precision, and the grader’s claim-support checks.

However, the result does not prove that all failures originate in retrieval.

The grader uses mechanical checks, including expected citation IDs and normalized text matching. These are useful signals, but they are not equivalent to semantic claim-to-passage entailment. Valid citation IDs only establish that a cited source was retrieved; they do not prove that every generated claim follows from that source.

The 4/10 result should therefore be treated as evidence for further diagnosis, not as a reason to tune retrieval toward final-practice questions or grader behavior.

***

## Alternatives Considered

### Keep lexical retrieval

This is the current decision.

The baseline is deterministic, lightweight, inspectable, and compatible with the final-assignment constraints. Its known limitation is lexical vocabulary mismatch.

### BM25-style lexical ranking

The course coach implements a stronger lexical ranker using term frequency, length normalization, title weighting, and result diversification. The course reports improved development and held-out page-retrieval results for that separate course-page corpus.

This is the most relevant contract-compatible alternative. It could improve ranking or reduce duplicate results, but it cannot retrieve a passage with true zero lexical overlap. It has not been evaluated on the final-assignment corpus.

### Embeddings and semantic retrieval

Optional course projects demonstrate that local embeddings can improve paraphrase retrieval and retain stable passage IDs for citations.

However, the demonstrated approach adds an embedding model, vector storage/indexing, and additional runtime requirements. Those costs do not fit the current final-assignment answer-path constraints without an explicit contract change or clarification.

### Hybrid retrieval

Hybrid lexical-plus-semantic retrieval is conceptually well suited to a mix of exact identifiers and paraphrased questions. It would require semantic infrastructure, an explicit merge policy, score or relevance thresholds, and corpus-specific evaluation.

No current evidence justifies that complexity for this fixed six-document assignment.

### Reranking and Graph RAG

Reranking can improve the ordering of candidates that already entered the retrieval pool. It cannot recover a passage excluded because of zero lexical overlap, and it adds latency or additional model work.

Graph RAG addresses relationship and multi-hop retrieval problems. It is not justified by the current prose-question-answering corpus or the demonstrated failure mode.

***

## Decision Gate

**Decision: Keep the current lexical retrieval architecture for the final assignment.**

This is not a claim that the lexical baseline is optimal. It means the present evidence does not justify changing the architecture under the assignment’s constraints.

The confirmed lexical limitation should remain documented rather than patched around for individual public-practice questions.

A future retrieval change should require independently authored evaluation showing meaningful improvement in:

- Answer-bearing passage recall
- Retrieval precision and irrelevant-context rate
- Robustness on unseen questions
- Grounding of final claims against retrieved evidence
- Preservation of citation behavior and unsupported-question refusal behavior

Any adopted architecture change should be recorded in a separate ADR.

***

## Evidence Still Needed

If retrieval is revisited after the assignment, the next useful experiment is a larger, held-out, passage-level comparison of:

1. The current lexical baseline
2. A contract-compatible alternative, such as the course’s BM25-style lexical ranker
3. Semantic or hybrid retrieval only if the assignment contract permits additional model/runtime infrastructure

The comparison should use pre-labeled answer-bearing passages and measure retrieval independently from both model generation and grader behavior.

No retrieval architecture change is required for the current submission.