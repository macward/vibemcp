# vibeMCP — Architecture Diagram

## Component Overview

```mermaid
graph TB
    subgraph Clients["MCP Clients"]
        CC[Claude Code]
        CAI[Claude.ai]
        CUR[Cursor]
        WS[Windsurf]
    end

    subgraph Server["FastMCP Server"]
        AUTH[Auth<br/>Bearer Token]

        subgraph Interface["MCP Interface"]
            RT[Read Tools<br/>search, read_doc,<br/>list_tasks, get_plan]
            WT[Write Tools<br/>create_task, create_doc,<br/>update_status, log_session]
            RES[Resources<br/>vibe://projects/*]
            PR[Prompts<br/>project_briefing,<br/>session_start]
        end

        subgraph Webhooks["Webhook System"]
            WM[Webhook Manager]
            WR[Register / Unregister]
        end

        subgraph Indexer["Indexer System"]
            WK[Walker<br/>File Discovery]
            PA[Parser<br/>Frontmatter + Metadata]
            CH[Chunker<br/>Heading-based splitting]
            OR[Orchestrator<br/>sync / reindex]
        end
    end

    subgraph Storage["Storage Layer"]
        DB[(SQLite + FTS5<br/>index.db<br/>Disposable)]
        FS[("Filesystem<br/>~/.vibe/<br/>Source of Truth")]
    end

    EXT[External Webhook URLs]

    CC & CAI & CUR & WS -->|SSE / HTTP| AUTH
    AUTH --> RT & WT & RES & PR

    WT --> OR
    RT -->|search query| DB
    RT -->|read file| FS

    WK -->|FileInfo| PA
    PA -->|FrontmatterData| CH
    CH -->|Chunks| OR
    OR -->|upsert| DB
    OR -->|scan .md| FS

    WT -->|fire event| WM
    WM -->|POST + HMAC-SHA256| EXT

    style Clients fill:#dbe4ff,stroke:#4a9eed
    style Server fill:#e5dbff,stroke:#8b5cf6
    style Interface fill:#d0bfff,stroke:#8b5cf6
    style Indexer fill:#d3f9d8,stroke:#22c55e
    style Webhooks fill:#fff3bf,stroke:#f59e0b
    style Storage fill:#f8f9fa,stroke:#999

    style DB fill:#c3fae8,stroke:#06b6d4
    style FS fill:#fff3bf,stroke:#f59e0b
    style AUTH fill:#ffc9c9,stroke:#ef4444
    style EXT fill:#ffd8a8,stroke:#f59e0b
```

## Search Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant S as FastMCP Server
    participant A as Auth
    participant T as Tools
    participant DB as SQLite FTS5

    C->>S: MCP request (SSE)
    S->>A: Validate Bearer Token
    A-->>S: OK
    S->>T: search(query, project?)
    T->>DB: FTS5 query + BM25
    Note over DB: Score = BM25 × type_boost<br/>× recency_boost<br/>× heading_boost<br/>× status_boost
    DB-->>T: SearchResult[]
    T-->>S: Results + snippets
    S-->>C: MCP response
```

## Write Flow (Create Task)

```mermaid
sequenceDiagram
    participant C as Client
    participant T as Write Tools
    participant FS as Filesystem
    participant IX as Indexer
    participant DB as SQLite
    participant WH as Webhooks

    C->>T: create_task(project, title, ...)
    T->>T: Validate path (no traversal)
    T->>FS: Write tasks/NNN-title.md
    T->>IX: Index new file
    IX->>IX: Parse frontmatter
    IX->>IX: Chunk content
    IX->>DB: Upsert document + chunks
    T->>WH: fire_event("task.created")
    WH-->>WH: POST to subscribers (async)
    T-->>C: Task metadata
```

## Filesystem Structure

```mermaid
graph LR
    VIBE["~/.vibe/"] --> P1["project-a/"]
    VIBE --> P2["project-b/"]
    VIBE --> DB[("index.db")]

    P1 --> T1["tasks/"]
    P1 --> PL1["plans/"]
    P1 --> S1["sessions/"]
    P1 --> R1["reports/"]
    P1 --> CL1["changelog/"]
    P1 --> RF1["references/"]
    P1 --> SC1["scratch/"]
    P1 --> AS1["assets/"]

    style VIBE fill:#fff3bf,stroke:#f59e0b
    style DB fill:#c3fae8,stroke:#06b6d4
    style P1 fill:#ffd8a8,stroke:#f59e0b
    style P2 fill:#ffd8a8,stroke:#f59e0b
```

## Search Scoring

| Boost | Factor | Values |
|-------|--------|--------|
| **Type** | Folder location | tasks: 2.0, plans: 1.8, sessions: 1.5, scratch: 0.5 |
| **Recency** | Document age | 0-1d: 2.0, 2-7d: 1.5, 8-30d: 1.2, 90+d: 0.8 |
| **Heading** | Priority sections | "Current Status", "Blockers": 2.5, others: 1.0 |
| **Status** | Task state | in-progress: 2.0, blocked: 1.8, done: 0.6 |

> `final_score = BM25 × type × recency × heading × status`
