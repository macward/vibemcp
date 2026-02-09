# Architecture

Technical deep-dive into vibeMCP's internal architecture.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Clients                             │
│         (Claude Code, Claude.ai, Cursor, Windsurf)              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ MCP Protocol (SSE/HTTP)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastMCP Server                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Tools   │  │Resources │  │ Prompts  │  │ Auth Middleware  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────────────┘ │
│       │             │             │                              │
│       └─────────────┴─────────────┘                              │
│                     │                                            │
│              ┌──────▼──────┐                                     │
│              │   Indexer   │                                     │
│              └──────┬──────┘                                     │
└─────────────────────┼───────────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│    SQLite DB    │      │   Filesystem    │
│    (index.db)   │      │   (~/.vibe/)    │
│                 │      │                 │
│ - FTS5 search   │      │ - Source of     │
│ - Ranking data  │      │   truth         │
│ - Disposable    │      │ - Git-backed    │
└─────────────────┘      └─────────────────┘
```

---

## Core Principles

### 1. Filesystem First

The filesystem is always the source of truth. If the database is deleted or corrupted, everything can be regenerated:

```bash
rm ~/.vibe/index.db
vibe-mcp --reindex
# All data restored from files
```

### 2. Index is Disposable

SQLite is a derived cache. It exists for:
- Fast full-text search
- Pre-computed metadata
- Efficient filtering

But it never contains data that doesn't exist in files.

### 3. Minimal API Surface

The "happy path" covers 80% of use cases with just 4 tools:
- `search` - Find content
- `read_doc` - Read content
- `tool_create_task` - Create tasks
- `tool_log_session` - Log progress

---

## Component Architecture

### Entry Point (`main.py`)

```python
def create_server(read_only: bool | None = None) -> FastMCP:
    """Create and configure the MCP server with all components."""

    # 1. Load configuration from environment
    config = get_config()

    # 2. Initialize authentication (if token configured)
    auth_provider = get_auth_provider()

    # 3. Create FastMCP instance
    mcp = FastMCP(name="vibeMCP", auth=auth_provider)

    # 4. Initialize database and indexer
    db = Database(config.vibe_db)
    db.initialize()
    indexer = Indexer(config.vibe_root, config.vibe_db)
    indexer.initialize()

    # 5. Auto-reindex if database empty
    if len(db.list_projects()) == 0:
        indexer.reindex()

    # 6. Register all MCP components
    register_resources(mcp)
    register_tools(mcp, db)
    register_tools_write(mcp)
    register_prompts(mcp)

    return mcp
```

### Configuration (`config.py`)

Configuration loaded from environment variables with sensible defaults:

```python
@dataclass
class Config:
    vibe_root: Path      # ~/.vibe
    vibe_port: int       # 8080
    vibe_db: Path        # ~/.vibe/index.db
    auth_token: str      # >= 32 chars if set
    read_only: bool      # False by default
```

Priority: CLI flags > Environment variables > Defaults

### Authentication (`auth.py`)

Bearer token authentication using FastMCP's auth system:

```python
class BearerTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(token, config.auth_token):
            return None

        return AccessToken(
            token=token,
            client_id="authenticated",
            scopes=["read", "write"],
        )
```

---

## Indexer Architecture

The indexer is the core component that syncs filesystem to SQLite.

```
┌─────────────────────────────────────────────────────────┐
│                      Indexer                             │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │  Walker  │──▶│  Parser  │──▶│ Chunker  │            │
│  └──────────┘   └──────────┘   └──────────┘            │
│       │                             │                   │
│       ▼                             ▼                   │
│  FileInfo[]                    Chunk[]                  │
│       │                             │                   │
│       └─────────────┬───────────────┘                   │
│                     ▼                                   │
│              ┌──────────┐                               │
│              │ Database │                               │
│              └──────────┘                               │
└─────────────────────────────────────────────────────────┘
```

### Walker (`walker.py`)

Traverses `VIBE_ROOT` to discover all `.md` files:

```python
@dataclass
class FileInfo:
    path: Path              # Absolute path
    relative_path: str      # project/folder/file.md
    project_name: str       # First path component
    folder: str             # Second path component
    filename: str           # File name
    mtime: float            # Modification time
    content_hash: str       # SHA-256 of content
```

Directory structure rules:
- Only processes `.md` files
- Ignores hidden files/directories (`.git`, etc.)
- Validates paths are within `VIBE_ROOT`

### Parser (`parser.py`)

Extracts YAML frontmatter and metadata:

```python
@dataclass
class Frontmatter:
    project: str | None     # From frontmatter or path
    type: str | None        # From frontmatter or folder
    status: str | None      # pending, in-progress, done, blocked
    updated: str | None     # Date string
    tags: list[str] | None  # Tag list
    owner: str | None       # Responsible person
```

Inference rules when frontmatter is missing:
- `project` = directory containing the file
- `type` = folder name (tasks, plans, sessions, etc.)

### Chunker (`chunker.py`)

Splits documents into searchable chunks:

```python
@dataclass
class ChunkerChunk:
    heading: str | None       # "## Objective", "# Task", etc.
    heading_level: int        # 0=none, 1=#, 2=##, etc.
    content: str              # Text content
    chunk_order: int          # Position in document
    char_offset: int          # Character offset from start
    is_priority_heading: bool # True for important headings
```

**Chunking Strategy:**

1. **Split by headings** (level 1 and 2)
2. **Max chunk size:** ~1500 tokens (~6000 characters)
3. **Fallback:** Split large sections by paragraphs
4. **Final fallback:** Split by lines if needed

**Priority Headings:**
- "Current Status"
- "Next" / "Next Steps"
- "Blockers" / "Blocked By"
- "Decisions"

### Database (`database.py`)

SQLite operations with thread-safe access:

```python
class Database:
    def __init__(self, db_path: Path):
        self._local = threading.local()     # Thread-local connections
        self._write_lock = threading.Lock()  # Write synchronization

    @contextmanager
    def _read_cursor(self):
        """Read operations - no lock needed."""
        conn = self._get_connection()
        cursor = conn.cursor()
        yield cursor
        cursor.close()

    @contextmanager
    def _write_cursor(self):
        """Write operations - with lock."""
        with self._write_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
```

**Database Settings:**
- `PRAGMA foreign_keys = ON` - Referential integrity
- `PRAGMA journal_mode = WAL` - Better concurrency

---

## Database Schema

### Entity Relationship

```
projects (1) ──────┬────── (M) documents
                   │
                   │       documents (1) ──── (M) chunks
                   │                               │
                   │                               │
                   │                         chunks_fts
                   │                        (FTS5 virtual)
                   │
                   └────── meta (version info)
```

### Tables

**projects:**
```sql
CREATE TABLE projects (
    id          INTEGER PRIMARY KEY,
    name        TEXT UNIQUE,    -- "vibeMCP"
    path        TEXT UNIQUE,    -- "/Users/x/.vibe/vibeMCP"
    created_at  TEXT,
    updated_at  TEXT
);
```

**documents:**
```sql
CREATE TABLE documents (
    id           INTEGER PRIMARY KEY,
    project_id   INTEGER REFERENCES projects(id),
    path         TEXT UNIQUE,    -- "vibeMCP/tasks/001-setup.md"
    folder       TEXT,           -- "tasks"
    filename     TEXT,           -- "001-setup.md"
    type         TEXT,           -- "task"
    status       TEXT,           -- "in-progress"
    owner        TEXT,
    tags         TEXT,           -- JSON: '["tag1", "tag2"]'
    content_hash TEXT,           -- SHA-256
    mtime        REAL,           -- Unix timestamp
    updated      TEXT,           -- From frontmatter
    indexed_at   TEXT
);
```

**chunks:**
```sql
CREATE TABLE chunks (
    id                  INTEGER PRIMARY KEY,
    document_id         INTEGER REFERENCES documents(id),
    heading             TEXT,      -- "## Objective"
    heading_level       INTEGER,   -- 2
    content             TEXT,      -- Chunk content
    chunk_order         INTEGER,   -- Position
    char_offset         INTEGER,   -- Offset in document
    is_priority_heading INTEGER    -- 1 if priority
);
```

**chunks_fts (FTS5):**
```sql
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    content,
    heading,
    content='chunks',
    content_rowid='id'
);
```

---

## Search Ranking

Search combines FTS5's BM25 score with domain-specific boosts.

### Formula

```
final_score = bm25 × type_boost × recency_boost × heading_boost × status_boost
```

### Boost Values

**Type Boost (document location):**
| Location | Boost | Reasoning |
|----------|-------|-----------|
| status.md | 3.0 | Project overview |
| tasks/ | 2.0 | Active work |
| plans/ | 1.8 | Strategy documents |
| sessions/ | 1.5 | Recent context |
| changelog/ | 1.2 | History |
| reports/ | 1.0 | Neutral |
| references/ | 0.8 | Background info |
| scratch/ | 0.5 | Drafts |

**Recency Boost (document age):**
| Age | Boost |
|-----|-------|
| 0-1 days | 2.0 |
| 2-7 days | 1.5 |
| 8-30 days | 1.2 |
| 31-90 days | 1.0 |
| 90+ days | 0.8 |

**Heading Boost:**
| Heading | Boost |
|---------|-------|
| Priority (Next, Blockers, etc.) | 2.5 |
| Objective, Acceptance | 1.5 |
| Other | 1.0 |

**Status Boost (tasks only):**
| Status | Boost |
|--------|-------|
| in-progress | 2.0 |
| blocked | 1.8 |
| pending | 1.2 |
| done | 0.6 |

### Search Query

```sql
SELECT
    c.id, c.heading, c.content,
    snippet(chunks_fts, 0, '>>>', '<<<', '...', 64) as snippet,
    bm25(chunks_fts) as bm25_score,
    -- Boost calculations...
FROM chunks_fts
JOIN chunks c ON chunks_fts.rowid = c.id
JOIN documents d ON c.document_id = d.id
JOIN projects p ON d.project_id = p.id
WHERE chunks_fts MATCH ?
ORDER BY (bm25_score * type_boost * recency_boost * heading_boost * status_boost)
LIMIT 20;
```

---

## Write Operations Flow

### Creating a Task

```
tool_create_task("vibeMCP", "Implement Auth", "Add bearer tokens")
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Validate project     │
                    │  (path traversal)     │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Get next task number │
                    │  (scan tasks/*.md)    │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Generate content     │
                    │  (standard format)    │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Write file           │
                    │  tasks/003-impl...md  │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Reindex file         │
                    │  (immediate)          │
                    └───────────────────────┘
```

### Reindexing Flow

```
reindex()
    │
    ▼
┌────────────────┐
│ Clear database │
│ (all tables)   │
└───────┬────────┘
        │
        ▼
┌────────────────┐     ┌────────────────┐
│ walk_vibe_root │────▶│ For each file: │
│                │     │ - Parse        │
└────────────────┘     │ - Chunk        │
                       │ - Index        │
                       └───────┬────────┘
                               │
                               ▼
                       ┌────────────────┐
                       │ FTS5 triggers  │
                       │ auto-populate  │
                       └────────────────┘
```

---

## Security Model

### Path Validation

All file operations validate paths:

```python
def _validate_project_path(project: str, vibe_root: Path) -> Path:
    # Block directory traversal
    if ".." in project or "/" in project or "\\" in project:
        raise ValueError(f"Invalid project name: {project}")

    # Resolve and verify containment
    project_path = (vibe_root / project).resolve()
    vibe_root_resolved = vibe_root.resolve()

    if not str(project_path).startswith(str(vibe_root_resolved) + "/"):
        raise ValueError(f"Project path outside vibe_root: {project}")

    return project_path
```

### Authentication

- Bearer token required when `VIBE_AUTH_TOKEN` is set
- Minimum 32 characters enforced
- Constant-time comparison prevents timing attacks
- No token storage/logging

### Read-Only Mode

Write tools check permission before execution:

```python
def check_write_permission() -> None:
    if config.read_only:
        raise AuthError("Server is in read-only mode")
```

---

## Concurrency Model

### Read Operations

- Multiple concurrent reads allowed
- Each thread gets its own connection via `threading.local()`
- WAL mode enables reads during writes

### Write Operations

- Single writer at a time (`threading.Lock()`)
- Automatic rollback on errors
- FTS5 triggers run synchronously

### File System

- Writes are atomic (write temp file, then rename)
- mtime used for change detection
- Content hash for verification

---

## Extension Points

### Adding New Tools

```python
# In tools.py or tools_write.py
def register_tools(mcp: FastMCP, db: Database) -> None:

    @mcp.tool()
    def my_new_tool(param: str) -> dict:
        """Description shown to AI agents."""
        # Implementation
        return {"status": "success"}
```

### Custom Ranking Boosts

Modify `database.py` search query to add new boost factors:

```sql
CASE
    WHEN d.owner = 'priority-user' THEN 2.0
    ELSE 1.0
END as owner_boost
```

### New Document Types

Parser automatically handles new folders. For special parsing:

```python
# In parser.py
def parse_frontmatter(content: str, path: str) -> tuple[Frontmatter, str]:
    # Add custom logic for new document types
    if "/special/" in path:
        # Custom parsing
        pass
```
