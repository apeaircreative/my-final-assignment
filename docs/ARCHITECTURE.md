# Final Assignment Architecture Boundary

## The starting point

The Final Assignment does not start from an empty agent. The course package
provides the core research-assistant pipeline. The student's task is to inspect
that baseline, identify gaps in its reliability contract, and harden those
boundaries without rebuilding working infrastructure.

**Working principle:** Course infrastructure → inspect → identify gaps → harden
→ test → measure.

> ## Observations + Decisions
> - **Run shape:** [0001-run-shape.md](docs/adr/0001-run-shape.md)
> - **Failure behavior and known timeout limitation:** [ISSUES.md](docs/ISSUES.md)
> - **Evaluation and trace-fidelity evidence:** [EVAL_REPORT.md](docs/EVAL_REPORT.md)
> - **Retention boundary:** [RETENTION.md](docs/RETENTION.md)

## Code locations

| Area | Location |
|---|---|
| Application boundary and wrapper flow | `agent.py` — `YourAgent.run()` |
| Wrapper retrieval, timeout adaptation, provider-error handling, and post-return safety decision | `agent.py` |
| Course answer retrieval, context building, model call, parse repair, and citation validation | `bootcamp_agent/agent.py` — `answer_question()` |
| Shared retrieval implementation | `bootcamp_agent/retrieval.py` |
| Provider timeout adapter | `agent.py` — `TimeoutClient` |
| Retrieved-content pattern check | `safety.py` — `contains_instruction_like_text()` |
| Registered reader-tool definitions | `bootcamp_agent/tools.py` |
| Wrapper failure and safety-decision trace events | `agent.py` |
| Course normal-result trace events | `bootcamp_agent/agent.py` |

## Current architecture

The application wrapper surrounds the course-provided `answer_question()`
pipeline. The two layers have different responsibilities.

```mermaid
flowchart TD
    A(["User asks a question"]):::entry --> B["App receives question"]:::wrapper

    %% App wrapper
    B --> C["Find relevant content<br/>for safety review"]:::wrapper
    C --> D["Save content for later safety check"]:::data
    C --> E["Send question to answer engine"]:::wrapper

    %% Course answer engine
    subgraph COURSE["Course answer engine"]
        direction TD

        F["Find relevant content<br/>for the answer"]:::course

        F -->|"Nothing relevant found"| G["Tell user the question<br/>is not supported"]:::refusal
        F -->|"Relevant content found"| H["Prepare source content<br/>for the model"]:::course

        H --> I["Ask the model for an answer"]:::model

        I -->|"Model responds"| J{"Is the answer format valid?"}:::decision
        I -->|"Service problem or timeout"| K["Return issue to app"]:::exception

        J -->|"Yes"| L{"Do the sources<br/>match the content found?"}:::decision
        J -->|"No, first try"| M["Ask once more<br/>to fix the format"]:::retry
        M --> I

        J -->|"No, retry also failed"| N["Return a safe refusal"]:::refusal

        L -->|"Yes"| O["Return answer result"]:::courseResult
        L -->|"No"| P["Apply source-check rules"]:::retry
        P --> O

        G --> O
        N --> O
    end

    %% App service-error path
    K --> Q["App returns a safe refusal"]:::refusal
    Q --> R["Save failure path<br/>content found → model call → decision"]:::trace

    %% App post-answer safety path
    O --> S{"Safety check:<br/>does saved content contain<br/>a blocked instruction pattern?"}:::decision
    D --> S

    S -->|"Yes"| T["Return a safe refusal"]:::refusal
    S -->|"No"| U["Show the answer"]:::success

    T --> V["Save safety decision"]:::trace
    U --> W["Save normal result"]:::trace

    %% Colors
    classDef entry fill:#0f172a,stroke:#38bdf8,color:#f8fafc,stroke-width:2px;
    classDef wrapper fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:2px;
    classDef course fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:2px;
    classDef model fill:#f3e8ff,stroke:#9333ea,color:#3b0764,stroke-width:2px;
    classDef decision fill:#fef3c7,stroke:#d97706,color:#78350f,stroke-width:2px;
    classDef retry fill:#ffedd5,stroke:#ea580c,color:#7c2d12,stroke-width:2px;
    classDef success fill:#dcfce7,stroke:#16a34a,color:#14532d,stroke-width:2px;
    classDef refusal fill:#fee2e2,stroke:#dc2626,color:#7f1d1d,stroke-width:2px;
    classDef exception fill:#ffe4e6,stroke:#e11d48,color:#881337,stroke-width:2px;
    classDef data fill:#e2e8f0,stroke:#64748b,color:#0f172a,stroke-width:2px;
    classDef trace fill:#f1f5f9,stroke:#64748b,color:#334155,stroke-width:2px;
    classDef courseResult fill:#f5f3ff,stroke:#8b5cf6,color:#3b0764,stroke-width:2px;

    style COURSE fill:#faf5ff,stroke:#7c3aed,stroke-width:2px,color:#2e1065
    ```