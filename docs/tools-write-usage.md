# Write Tools Usage Guide

This document describes the write tools available in vibeMCP for creating and updating documents in the `.vibe` workspace.

## Overview

All write tools automatically:
- Validate paths to prevent directory traversal attacks
- Ensure files stay within the project boundaries
- Trigger re-indexation after writing
- Create parent directories as needed

## Setup with Dependency Injection

Write tools are registered using the `register_tools_write()` function. This pattern enables proper dependency injection:

```python
from fastmcp import FastMCP
from vibe_mcp.config import Config
from vibe_mcp.indexer import Indexer
from vibe_mcp.webhooks import WebhookManager
from vibe_mcp.indexer.database import Database
from vibe_mcp.tools_write import register_tools_write

# Create dependencies
config = Config.from_env()
db = Database(config.vibe_db)
db.initialize()
indexer = Indexer(config.vibe_root, config.vibe_db)
indexer.initialize()

# Optional: create webhook manager for event notifications
webhook_mgr = WebhookManager(db, config)  # or None to disable webhooks

# Create FastMCP server and register tools
mcp = FastMCP("vibeMCP")
register_tools_write(mcp, config, indexer, webhook_mgr=webhook_mgr)

# Tools are now available as MCP tools
```

## Available Tools

### `tool_create_task`

Create a new task with auto-generated sequential number and standard format.

**Parameters:**
- `project` (str): Project name
- `title` (str): Task title
- `objective` (str): Task objective/description
- `steps` (list[str], optional): List of steps
- `feature` (str, optional): Feature tag for grouping related tasks

**Returns:**
```python
{
    "status": "created",
    "task_number": 1,
    "filename": "001-task-title.md",
    "path": "project/tasks/001-task-title.md",
    "absolute_path": "/path/to/.vibe/project/tasks/001-task-title.md",
    "feature": "auth"  # if feature was provided
}
```

**Generated Format (without feature):**
```markdown
# Task: Implement Authentication

Status: pending

## Objective
Add JWT-based authentication to the API

## Steps
1. [ ] Design token structure
2. [ ] Implement token generation
3. [ ] Add middleware for validation
4. [ ] Write tests
```

**Generated Format (with feature):**
```markdown
---
type: task
status: pending
feature: auth
---

# Task: Implement Authentication

## Objective
Add JWT-based authentication to the API
```

**Features:**
- Auto-generates sequential task numbers (001, 002, 003, etc.)
- Sanitizes title for filename (removes special characters, converts to lowercase with hyphens)
- Creates `tasks/` directory if it doesn't exist
- Initial status is always "pending"
- When `feature` is provided, uses YAML frontmatter format

---

### `tool_update_task_status`

Update the status of a task.

**Parameters:**
- `project` (str): Project name
- `task_file` (str): Task filename (e.g., "001-example.md")
- `new_status` (str): New status (must be one of: "pending", "in-progress", "done", "blocked")

**Returns:**
```python
{
    "status": "updated",
    "new_status": "in-progress",
    "path": "project/tasks/001-example.md",
    "absolute_path": "/path/to/.vibe/project/tasks/001-example.md"
}
```

**Valid Statuses:**
- `pending`: Task is queued but not started
- `in-progress`: Task is currently being worked on
- `done`: Task is completed
- `blocked`: Task is blocked by dependencies or issues

**Errors:**
- Raises `ValueError` if status is not valid
- Raises `ValueError` if task file doesn't exist

---

### `tool_create_plan`

Create or update an execution plan for a project.

**Parameters:**
- `project` (str): Project name
- `content` (str): Plan content
- `filename` (str, optional): Plan filename (default: "execution-plan.md")

**Returns:**
```python
{
    "status": "created",  # or "updated" if plan already exists
    "filename": "execution-plan.md",
    "path": "project/plans/execution-plan.md",
    "absolute_path": "/path/to/.vibe/project/plans/execution-plan.md"
}
```

**Features:**
- Default filename is `execution-plan.md`
- Use `feature-<name>.md` for feature-specific plans
- Creates `plans/` directory if it doesn't exist
- Returns "created" on first call, "updated" on subsequent calls

---

### `tool_log_session`

Create or append to a session log for today's date.

**Parameters:**
- `project` (str): Project name
- `content` (str): Session content to log

**Returns:**
```python
{
    "status": "created",  # or "appended" if log already exists for today
    "date": "2026-02-09",
    "path": "project/sessions/2026-02-09.md",
    "absolute_path": "/path/to/.vibe/project/sessions/2026-02-09.md"
}
```

**Generated Format (First Entry):**
```markdown
# Session Log - 2026-02-09

Started working on authentication feature. Reviewing JWT libraries.
```

**Generated Format (Appended Entry):**
```markdown
# Session Log - 2026-02-09

Started working on authentication feature. Reviewing JWT libraries.

---
**14:30:15**

Implemented token generation. Moving to validation middleware next.
```

**Features:**
- Automatically uses today's date (YYYY-MM-DD) as filename
- First entry creates new file with header
- Subsequent entries append with timestamp separator
- Creates `sessions/` directory if it doesn't exist

---

### `tool_create_doc`

Create a new document in any project folder.

**Parameters:**
- `project` (str): Project name
- `folder` (str): Folder name (e.g., "tasks", "plans", "references") or "" for root
- `filename` (str): File name (`.md` extension added automatically if missing)
- `content` (str): Document content

**Returns:**
```python
{
    "status": "created",
    "path": "project/folder/filename.md",
    "absolute_path": "/path/to/.vibe/project/folder/filename.md"
}
```

**Errors:**
- Raises `ValueError` if file already exists
- Raises `ValueError` if path contains directory traversal attempts

---

### `tool_reindex`

Force a full reindex of all projects.

**Parameters:** None

**Returns:**
```python
{
    "status": "reindexed",
    "document_count": 42
}
```

**When to Use:**
- After manual file modifications outside of the tools
- If search results seem stale or incomplete
- After recovering from database corruption
- For maintenance or troubleshooting

**Note:** This is automatically called by all write tools for the affected files, so manual reindexing is rarely needed.

---

### `tool_init_project`

Initialize a new project with the standard directory structure.

**Parameters:**
- `project` (str): Project name (no slashes, no `..`)

**Returns:**
```python
{
    "status": "initialized",
    "project": "myproject",
    "path": "myproject",
    "absolute_path": "/path/to/.vibe/myproject",
    "folders": ["tasks", "plans", "sessions", "reports", "changelog", "references", "scratch", "assets"]
}
```

**Created Structure:**
```
~/.vibe/new-api/
├── tasks/
├── plans/
├── sessions/
├── reports/
├── changelog/
├── references/
├── scratch/
├── assets/
└── status.md
```

**Generated status.md:**
```markdown
# new-api

Status: setup
```

**Errors:**
- Raises `ValueError` if project name contains directory traversal attempts (`..`, `/`, `\`)
- Raises `ValueError` if project already exists

---

## Error Handling

All tools validate inputs and raise `ValueError` with descriptive messages when:
- Project name contains directory traversal (e.g., "../other-project")
- File paths escape the project directory
- Files don't exist (for update operations)
- Files already exist (for create operations)
- Invalid status values (for task status updates)

---

## Configuration

Tools use the `Config` class loaded from environment variables:

- `VIBE_ROOT`: Root directory for all projects (default: `~/.vibe`)
- `VIBE_DB`: SQLite database path (default: `~/.vibe/index.db`)

Set via environment variables:
```bash
export VIBE_ROOT=/custom/path/.vibe
export VIBE_DB=/custom/path/index.db
```

---

## Integration with Webhooks

When a `WebhookManager` is provided to `register_tools_write()`, events are fired for:
- `task.created` - when a new task is created
- `task.updated` - when a task status is updated
- `plan.created` / `plan.updated` - when a plan is created or updated
- `session.logged` - when a session entry is logged
- `doc.created` - when a document is created
- `project.initialized` - when a new project is initialized
- `index.reindexed` - when a full reindex is completed

If `webhook_mgr=None`, events are silently skipped.

---

## Integration with Indexer

All write operations automatically trigger re-indexation of the affected file. This ensures:
- Search results are always up-to-date
- Metadata changes are immediately reflected
- No manual index management needed

The re-indexation process:
1. Computes content hash
2. Parses frontmatter for metadata
3. Chunks content by headings
4. Updates FTS5 search index

This happens synchronously after each write operation.
