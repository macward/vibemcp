# vibeMCP

**MCP server for centralizing project context across AI agents.**

vibeMCP exposes the `.vibe` workspace system via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), enabling AI agents (Claude Code, Claude.ai, Cursor) to access project documentation, tasks, plans, and session logs from any machine.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Stack](#stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
  - [Tools](#tools)
  - [Resources](#resources)
  - [Prompts](#prompts)
- [Workspace Structure](#workspace-structure)
- [Architecture](#architecture)
  - [Indexer](#indexer)
  - [Database Schema](#database-schema)
  - [Search Ranking](#search-ranking)
- [Development](#development)
- [Project Structure](#project-structure)
- [License](#license)

---

## Overview

vibeMCP is **not** a task manager. It's a **context fabric** for AI agents: a unified access layer for project knowledge, independent of vendor or tool.

### Problem

`.vibe` already works as a local system: each project has its workspace with tasks, plans, sessions, reports, and references. AI agents interact with it via `CLAUDE.md` and commands like `/task-decomposer`. The problem is everything lives on one machine. Working remotely, via SSH, from another device, or in a codespace means losing access to that centralized context.

### Solution

The MCP server exposes `.vibe` as-is over the MCP protocol, making it accessible from any compatible client. A SQLite FTS5 index enables fast cross-project search without parsing files on each request.

```
~/.vibe/ (source of truth)
    ↕ read/write
vibeMCP Server (FastMCP + SSE)
    ↕ MCP protocol
Any client: Claude Code, Claude.ai, Cursor
(local or remote, same interface)
```

---

## Features

- **Full-text search** across all projects using SQLite FTS5
- **Intelligent ranking** with boosts for document type, recency, heading importance, and task status
- **Document chunking** by headings for precise search results
- **YAML frontmatter** support with path-based inference fallback
- **Bearer token authentication** with constant-time comparison
- **Read-only mode** for safe deployments
- **Automatic reindexing** on document creation/update

---

## Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| **MCP Server** | Python + FastMCP | Official SDK, simple decorators, built-in SSE |
| **Transport** | SSE (HTTP) | Remotely accessible, handles reconnections |
| **Source of truth** | Filesystem `~/.vibe/` | Already exists, readable, Git-versionable |
| **Index** | SQLite FTS5 | Full-text search with ranking, zero config |
| **Auth** | Bearer token (>= 32 bytes) | Simple, supports rotation without downtime |
| **Deploy** | VPS + Caddy | Always available, HTTPS |

---

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management.

### Prerequisites

- Python 3.11+
- uv package manager

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/vibeMCP.git
cd vibeMCP

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install with dev dependencies
uv pip install -e ".[dev]"

# Run the server
uv run vibe-mcp
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VIBE_ROOT` | `~/.vibe` | Root directory for vibe workspaces |
| `VIBE_PORT` | `8080` | Server port |
| `VIBE_DB` | `~/.vibe/index.db` | SQLite database path |
| `VIBE_AUTH_TOKEN` | (none) | Bearer token for authentication (min 32 chars) |
| `VIBE_READ_ONLY` | `false` | Enable read-only mode (disables write tools) |

### Authentication

To enable authentication, set the `VIBE_AUTH_TOKEN` environment variable:

```bash
# Generate a secure token (32+ characters required)
export VIBE_AUTH_TOKEN=$(openssl rand -hex 32)

# Start the server
uv run vibe-mcp
```

Clients must include the token in the `Authorization` header:

```
Authorization: Bearer <token>
```

Token validation uses constant-time comparison to prevent timing attacks.

### Read-Only Mode

For production deployments where write access should be restricted:

```bash
# Via CLI flag
uv run vibe-mcp --read-only

# Via environment variable
VIBE_READ_ONLY=true uv run vibe-mcp
```

In read-only mode, write operations return an `AuthError`.

---

## Usage

### Starting the Server

```bash
# Basic start (auto-indexes if database is empty)
uv run vibe-mcp

# Force reindex on startup
uv run vibe-mcp --reindex

# Read-only mode
uv run vibe-mcp --read-only
```

### CLI Arguments

| Argument | Description |
|----------|-------------|
| `--reindex` | Force full reindex before starting |
| `--read-only` | Run in read-only mode |

---

## API Reference

### Tools

vibeMCP provides tools organized into read operations and write operations.

#### Read Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `search` | Full-text search across all projects | `query`, `project?`, `limit?` |
| `read_doc` | Read a complete document | `project`, `folder`, `filename` |
| `list_tasks` | List tasks with optional filters | `project?`, `status?` |
| `get_plan` | Read execution plan for a project | `project`, `filename?` |

##### `search`

Search for content across all projects using SQLite FTS5.

```python
search(
    query: str,           # FTS5 search query
    project: str = None,  # Filter by project name
    limit: int = 20       # Max results (default: 20)
) -> list[dict]
```

**Returns:**
```python
[{
    "project_name": "vibeMCP",
    "document_path": "vibeMCP/tasks/001-setup.md",
    "folder": "tasks",
    "heading": "## Objective",
    "snippet": "...implement the >>>indexer<<< module...",
    "score": 7.65
}]
```

##### `read_doc`

Read a complete document from a project.

```python
read_doc(
    project: str,   # Project name
    folder: str,    # Folder (tasks, plans, sessions, etc.)
    filename: str   # File name
) -> dict
```

**Returns:**
```python
{
    "project": "vibeMCP",
    "folder": "tasks",
    "filename": "001-setup.md",
    "path": "vibeMCP/tasks/001-setup.md",
    "metadata": {
        "type": "task",
        "status": "in-progress",
        "updated": "2025-02-09",
        "tags": ["backend", "mcp"],
        "owner": "max"
    },
    "content": "# Task: Setup...",
    "exists": True,
    "error": None
}
```

##### `list_tasks`

List tasks from a project or across all projects.

```python
list_tasks(
    project: str = None,  # Filter by project
    status: str = None    # Filter by status (pending/in-progress/done/blocked)
) -> list[dict]
```

##### `get_plan`

Read the execution plan for a project.

```python
get_plan(
    project: str,                      # Project name
    filename: str = "execution-plan.md"  # Plan file name
) -> dict
```

#### Write Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `tool_create_task` | Create a new task | `project`, `title`, `objective`, `steps?` |
| `tool_log_session` | Log to today's session | `project`, `content` |
| `tool_update_task_status` | Update task status | `project`, `task_file`, `new_status` |
| `tool_create_doc` | Create a document | `project`, `folder`, `filename`, `content` |
| `tool_reindex` | Force full reindex | (none) |

##### `tool_create_task`

Create a new task with auto-generated number and standard format.

```python
tool_create_task(
    project: str,              # Project name
    title: str,                # Task title
    objective: str,            # Task objective
    steps: list[str] = None    # Optional list of steps
) -> dict
```

**Returns:**
```python
{
    "status": "created",
    "task_number": 5,
    "filename": "005-implement-auth.md",
    "path": "vibeMCP/tasks/005-implement-auth.md",
    "absolute_path": "/Users/max/.vibe/vibeMCP/tasks/005-implement-auth.md"
}
```

Generated task format:
```markdown
# Task: Implement Auth

Status: pending

## Objective
Add authentication to the API endpoints

## Steps
1. [ ] Install dependencies
2. [ ] Create auth middleware
3. [ ] Add tests
```

##### `tool_log_session`

Create or append to today's session log.

```python
tool_log_session(
    project: str,  # Project name
    content: str   # Content to log
) -> dict
```

Creates `sessions/YYYY-MM-DD.md` or appends with timestamp separator.

##### `tool_update_task_status`

Update the status of a task.

```python
tool_update_task_status(
    project: str,       # Project name
    task_file: str,     # Task filename (e.g., "001-setup.md")
    new_status: str     # New status: pending/in-progress/done/blocked
) -> dict
```

### Resources

MCP Resources provide read-only access to workspace structure.

| Resource URI | Description |
|--------------|-------------|
| `vibe://projects` | List all projects with metadata |
| `vibe://projects/{name}` | Project detail with folder structure |
| `vibe://projects/{name}/{folder}/{file}` | Read a specific file |

##### `vibe://projects`

Returns all projects with:
- Path
- Last updated timestamp
- Open tasks count
- Last session date
- File counts by folder

##### `vibe://projects/{name}`

Returns project detail:
- Available folders with file counts
- Task status breakdown (pending, in-progress, blocked, done)

### Prompts

MCP Prompts are templates that combine information for AI agents.

| Prompt | Description | Parameters |
|--------|-------------|------------|
| `project_briefing` | Concise project status summary | `project` |
| `session_start` | Complete context for starting work | `project` |

##### `project_briefing`

"Get me up to speed on {project}"

Includes:
- Current status (from `status.md`)
- Active tasks (in-progress, blocked, pending)
- Recent sessions (last 2-3)

##### `session_start`

Load complete context before starting work.

Includes:
- Current status
- Execution plan
- All in-progress and blocked tasks (full content)
- Pending tasks summary
- Latest session log

---

## Workspace Structure

vibeMCP works with the standard `.vibe` workspace structure:

```
~/.vibe/
├── project-name/
│   ├── tasks/          # Task files: 001-name.md, 002-name.md
│   ├── plans/          # Execution plans with dependency graphs
│   ├── sessions/       # Session logs by date: 2025-02-09.md
│   ├── reports/        # Generated reports
│   ├── changelog/      # Change history
│   ├── references/     # External docs, specs, reference material
│   ├── scratch/        # Drafts, exploration, loose ideas
│   ├── assets/         # Resources (diagrams, images, configs)
│   └── status.md       # Project status overview
├── another-project/
│   └── ...
└── index.db            # SQLite FTS5 index (regenerated)
```

### YAML Frontmatter

Any `.md` file can include optional YAML frontmatter:

```yaml
---
project: vibeMCP
type: task
status: in-progress
updated: 2025-02-09
tags: [backend, mcp]
owner: max
---
```

Standard fields: `project`, `type`, `updated`, `tags`, `status`, `owner`. All optional.

If no frontmatter exists, metadata is inferred from the file path:
- `project` = parent directory name
- `type` = folder name (tasks, plans, sessions, etc.)

### Task Format

Tasks follow a standard format:

```markdown
# Task: Task Title

Status: pending

## Objective
What this task accomplishes.

## Steps
1. [ ] First step
2. [ ] Second step
3. [ ] Third step

## Acceptance Criteria
- Criterion 1
- Criterion 2
```

Valid statuses: `pending`, `in-progress`, `done`, `blocked`

---

## Architecture

### Indexer

The indexer is the core component that syncs the filesystem with SQLite FTS5.

```
~/.vibe/ filesystem ──(sync)──→ SQLite FTS5
                                    │
                                    ├── chunking by headings (# / ##)
                                    │   └── max ~1500 tokens per chunk
                                    │       └── fallback: split by paragraphs
                                    ├── change detection: mtime (fast-path) + hash
                                    ├── metadata: project, folder, file, frontmatter
                                    └── ranking: FTS5 + type + recency + heading boosts
```

**Principles:**
1. **Filesystem is truth** - SQLite is derived and can be regenerated
2. **Fast-path detection** - Uses mtime for quick change detection
3. **Hash verification** - Content hash for edge cases (git checkout, rsync)

### Database Schema

```
projects 1───M documents 1───M chunks
                                │
                                ▼
                          chunks_fts (FTS5)
```

#### Tables

| Table | Purpose |
|-------|---------|
| `projects` | Discovered workspaces |
| `documents` | Indexed `.md` files with metadata |
| `chunks` | Content fragments split by headings |
| `chunks_fts` | FTS5 virtual table for full-text search |
| `meta` | Schema versioning |

See [docs/sqlite-schema.md](docs/sqlite-schema.md) for complete schema details.

### Search Ranking

Search results are ranked using a composite formula:

```
final_score = bm25_score × type_boost × recency_boost × heading_boost × status_boost
```

#### Type Boost

| Location | Boost | Reason |
|----------|-------|--------|
| `status.md` | 3.0 | Current project state |
| `tasks/` | 2.0 | Active work items |
| `plans/` | 1.8 | Execution plans and decisions |
| `sessions/` | 1.5 | Recent work context |
| `changelog/` | 1.2 | Change history |
| `reports/` | 1.0 | Neutral |
| `references/` | 0.8 | Background material |
| `scratch/` | 0.5 | Drafts (low priority) |

#### Recency Boost

| Age | Boost |
|-----|-------|
| Today/yesterday | 2.0 |
| Last week | 1.5 |
| Last month | 1.2 |
| Last 3 months | 1.0 |
| Older | 0.8 |

#### Heading Boost

| Heading Contains | Boost |
|------------------|-------|
| Current Status, Next, Blockers, Decisions | 2.5 |
| Objective, Acceptance | 1.5 |
| Other | 1.0 |

#### Status Boost (tasks only)

| Status | Boost |
|--------|-------|
| in-progress | 2.0 |
| blocked | 1.8 |
| pending | 1.2 |
| done | 0.6 |

---

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=vibe_mcp

# Run specific test file
uv run pytest tests/test_tools.py
```

### Code Quality

```bash
# Check code style
uv run ruff check .

# Format code
uv run ruff format .
```

### Testing with Fixtures

The test suite includes fixture workspaces in `tests/fixtures/`:

```
tests/fixtures/
├── demo-api/           # Example API project
│   ├── tasks/
│   ├── plans/
│   ├── sessions/
│   └── ...
└── demo-frontend/      # Example frontend project
    ├── tasks/
    └── ...
```

---

## Project Structure

```
vibeMCP/
├── src/vibe_mcp/
│   ├── __init__.py
│   ├── main.py              # Entry point, server creation
│   ├── config.py            # Configuration from env vars
│   ├── auth.py              # Bearer token authentication
│   ├── tools.py             # MCP read tools
│   ├── tools_write.py       # MCP write tools
│   ├── resources.py         # MCP resources
│   ├── prompts.py           # MCP prompts
│   └── indexer/
│       ├── __init__.py
│       ├── database.py      # SQLite operations
│       ├── indexer.py       # Sync coordinator
│       ├── walker.py        # Filesystem traversal
│       ├── parser.py        # Frontmatter parsing
│       ├── chunker.py       # Document chunking
│       └── models.py        # Data models
├── tests/
│   ├── fixtures/            # Test workspaces
│   ├── test_indexer/        # Indexer tests
│   ├── test_tools.py
│   ├── test_tools_write.py
│   ├── test_resources.py
│   ├── test_prompts.py
│   ├── test_auth.py
│   └── test_config.py
├── docs/
│   └── sqlite-schema.md     # Database schema documentation
├── references/
│   ├── 01-vibe-mcp-project-v2.md
│   └── 02-vibe-mcp-plan-v2.md
├── pyproject.toml
├── CLAUDE.md                # Claude Code instructions
└── README.md
```

---

## License

TBD
