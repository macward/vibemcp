# Write Tools Usage Guide

This document describes the write tools available in vibeMCP for creating and updating documents in the `.vibe` workspace.

## Overview

All write tools automatically:
- Validate paths to prevent directory traversal attacks
- Ensure files stay within the project boundaries
- Trigger re-indexation after writing
- Create parent directories as needed

## Tools

### `create_doc`

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

**Example:**
```python
from vibe_mcp.tools_write import create_doc

create_doc(
    project="myproject",
    folder="references",
    filename="api-spec",
    content="# API Specification\n\n## Endpoints\n..."
)
```

**Errors:**
- Raises `ValueError` if file already exists
- Raises `ValueError` if path contains directory traversal attempts

---

### `update_doc`

Update an existing document.

**Parameters:**
- `project` (str): Project name
- `path` (str): Relative path within project (e.g., "tasks/001-example.md")
- `content` (str): New document content

**Returns:**
```python
{
    "status": "updated",
    "path": "project/path/to/file.md",
    "absolute_path": "/path/to/.vibe/project/path/to/file.md"
}
```

**Example:**
```python
from vibe_mcp.tools_write import update_doc

update_doc(
    project="myproject",
    path="tasks/001-feature.md",
    content="# Task: Feature X\n\nStatus: done\n..."
)
```

**Errors:**
- Raises `ValueError` if file doesn't exist
- Raises `ValueError` if path contains directory traversal attempts

---

### `create_task`

Create a new task with auto-generated sequential number and standard format.

**Parameters:**
- `project` (str): Project name
- `title` (str): Task title
- `objective` (str): Task objective/description
- `steps` (list[str], optional): List of steps

**Returns:**
```python
{
    "status": "created",
    "task_number": 1,
    "filename": "001-task-title.md",
    "path": "project/tasks/001-task-title.md",
    "absolute_path": "/path/to/.vibe/project/tasks/001-task-title.md"
}
```

**Example:**
```python
from vibe_mcp.tools_write import create_task

create_task(
    project="myproject",
    title="Implement Authentication",
    objective="Add JWT-based authentication to the API",
    steps=[
        "Design token structure",
        "Implement token generation",
        "Add middleware for validation",
        "Write tests"
    ]
)
```

**Generated Format:**
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

**Features:**
- Auto-generates sequential task numbers (001, 002, 003, etc.)
- Sanitizes title for filename (removes special characters, converts to lowercase with hyphens)
- Creates `tasks/` directory if it doesn't exist
- Initial status is always "pending"

---

### `update_task_status`

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

**Example:**
```python
from vibe_mcp.tools_write import update_task_status

update_task_status(
    project="myproject",
    task_file="001-implement-authentication.md",
    new_status="in-progress"
)
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

### `create_plan`

Create or update the execution plan for a project.

**Parameters:**
- `project` (str): Project name
- `content` (str): Plan content

**Returns:**
```python
{
    "status": "created",  # or "updated" if plan already exists
    "path": "project/plans/execution-plan.md",
    "absolute_path": "/path/to/.vibe/project/plans/execution-plan.md"
}
```

**Example:**
```python
from vibe_mcp.tools_write import create_plan

plan_content = """# Execution Plan

## Phase 1: Foundation
- [ ] Setup project structure
- [ ] Configure CI/CD
- [ ] Setup database

## Phase 2: Core Features
- [ ] Implement authentication
- [ ] Build API endpoints
- [ ] Add validation

## Phase 3: Polish
- [ ] Write documentation
- [ ] Performance optimization
- [ ] Security audit
"""

create_plan(project="myproject", content=plan_content)
```

**Features:**
- Always uses `execution-plan.md` as filename
- Creates `plans/` directory if it doesn't exist
- Returns "created" on first call, "updated" on subsequent calls

---

### `log_session`

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

**Example:**
```python
from vibe_mcp.tools_write import log_session

# First entry of the day
log_session(
    project="myproject",
    content="Started working on authentication feature. Reviewing JWT libraries."
)

# Later in the day
log_session(
    project="myproject",
    content="Implemented token generation. Moving to validation middleware next."
)
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

### `reindex`

Force a full reindex of all projects.

**Parameters:** None

**Returns:**
```python
{
    "status": "reindexed",
    "document_count": 42
}
```

**Example:**
```python
from vibe_mcp.tools_write import reindex

result = reindex()
print(f"Reindexed {result['document_count']} documents")
```

**When to Use:**
- After manual file modifications outside of the tools
- If search results seem stale or incomplete
- After recovering from database corruption
- For maintenance or troubleshooting

**Note:** This is automatically called by all write tools for the affected files, so manual reindexing is rarely needed.

---

### `init_project`

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

**Example:**
```python
from vibe_mcp.tools_write import init_project

result = init_project(project="new-api")
print(f"Created project at {result['absolute_path']}")
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

**When to Use:**
- To bootstrap a new project with the standard vibe workspace structure
- When starting work on a new codebase that needs task tracking
- To ensure consistent folder organization across all projects

---

## Error Handling

All tools validate inputs and raise `ValueError` with descriptive messages when:
- Project name contains directory traversal (e.g., "../other-project")
- File paths escape the project directory
- Files don't exist (for update operations)
- Files already exist (for create operations)
- Invalid status values (for task status updates)

Example error handling:
```python
from vibe_mcp.tools_write import create_task

try:
    create_task(
        project="myproject",
        title="Test Task",
        objective="Test"
    )
except ValueError as e:
    print(f"Error: {e}")
```

---

## Configuration

All tools use the global configuration from `vibe_mcp.config`:

- `VIBE_ROOT`: Root directory for all projects (default: `~/.vibe`)
- `VIBE_DB`: SQLite database path (default: `~/.vibe/index.db`)

Set via environment variables:
```bash
export VIBE_ROOT=/custom/path/.vibe
export VIBE_DB=/custom/path/index.db
```

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
