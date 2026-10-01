# Corpus Map

The Final Assignment research assistant answers questions from six course documents.

| Document | Main topics |
|---|---|
| `rag-basics.md` | RAG, chunking, indexing, retrieval, generation, citations, retrieval vs. generation failure |
| `structured-outputs.md` | JSON schemas, parsing, validation, retries, typed refusal |
| `agent-loops.md` | Agent loops, budgets, stopping conditions, autonomy, refusal |
| `prompt-injection.md` | Prompt injection, untrusted input, boundaries, defenses |
| `mcp-overview.md` | MCP servers, clients, tools, resources, prompts, trust boundaries |
| `evaluation-basics.md` | Golden sets, code checks, traces, regression testing, measurement |

## Shared design principles

The corpus consistently emphasizes:

- Retrieved documents are evidence/data, not instructions.
- The application owns validation and safety boundaries.
- Unsupported questions should be refused rather than answered from guesswork.
- Citations should correspond to evidence actually retrieved.
- Tool use and agent loops should be bounded.
- Evaluation should be repeatable and evidence-based.

This map is a navigation aid for implementation and evaluation. It does not replace the source documents.
