# API Reference

Complete reference for vibeMCP's MCP interface.

## Overview

vibeMCP exposes its functionality through three MCP primitives:

- **Tools** - Functions that can be called by AI agents
- **Resources** - Read-only URIs for accessing content
- **Prompts** - Templates that combine information for specific use cases

---

## Tools

### Read Tools

#### `search`

Full-text search across all projects using SQLite FTS5.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `query` | string | Yes | - | FTS5 search query |
| `project` | string | No | null | Filter results to specific project |
| `limit` | integer | No | 20 | Maximum number of results |

**FTS5 Query Syntax:**

```
# Simple terms
"authentication"

# Phrase search (exact match)
"user authentication"

# Boolean operators
auth AND token
auth OR session
auth NOT deprecated

# Prefix search
auth*

# Column-specific search
heading:objective    # Search only in headings
content:api          # Search only in content
```

**Response:**

```json
[
  {
    "project_name": "vibeMCP",
    "document_path": "vibeMCP/tasks/007-auth.md",
    "folder": "tasks",
    "heading": "## Objective",
    "snippet": "...implement >>>bearer token<<< authentication for...",
    "score": 7.65
  }
]
```

**Snippet Format:**
- Matches are highlighted with `>>>match<<<`
- Ellipsis `...` indicates truncated content
- Maximum 64 tokens per snippet

---

#### `read_doc`

Read a complete document from a project.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project` | string | Yes | Project name |
| `folder` | string | Yes | Folder name (tasks, plans, sessions, etc.) |
| `filename` | string | Yes | File name (e.g., "001-setup.md") |

**Response (success):**

```json
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
  "content": "# Task: Setup\n\nStatus: in-progress\n\n## Objective\n...",
  "exists": true,
  "error": null
}
```

**Response (not found):**

```json
{
  "project": "vibeMCP",
  "folder": "tasks",
  "filename": "999-missing.md",
  "path": "vibeMCP/tasks/999-missing.md",
  "metadata": null,
  "content": null,
  "exists": false,
  "error": "Document not found"
}
```

**Security:**
- Path traversal attempts are blocked
- Files outside `VIBE_ROOT` return an error

---

#### `list_tasks`

List tasks from a project or across all projects.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | No | null | Filter by project name |
| `status` | string | No | null | Filter by status |

**Valid Status Values:**
- `pending`
- `in-progress`
- `done`
- `blocked`

**Response:**

```json
[
  {
    "project_name": "vibeMCP",
    "path": "vibeMCP/tasks/001-setup.md",
    "filename": "001-setup.md",
    "status": "done",
    "owner": "max",
    "updated": "2025-02-08"
  },
  {
    "project_name": "vibeMCP",
    "path": "vibeMCP/tasks/002-indexer.md",
    "filename": "002-indexer.md",
    "status": "in-progress",
    "owner": null,
    "updated": "2025-02-09"
  }
]
```

---

#### `get_plan`

Read the execution plan for a project.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | Yes | - | Project name |
| `filename` | string | No | "execution-plan.md" | Plan file name |

**Response (success):**

```json
{
  "project": "vibeMCP",
  "filename": "execution-plan.md",
  "path": "vibeMCP/plans/execution-plan.md",
  "exists": true,
  "metadata": {
    "type": "plan",
    "updated": "2025-02-09"
  },
  "content": "# Execution Plan\n\n## Phase 1\n..."
}
```

**Response (not found):**

```json
{
  "project": "vibeMCP",
  "filename": "execution-plan.md",
  "path": "vibeMCP/plans/execution-plan.md",
  "exists": false,
  "metadata": null,
  "content": null
}
```

---

### Write Tools

All write tools require the server to NOT be in read-only mode.

#### `tool_create_task`

Create a new task with auto-generated number and standard format.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project` | string | Yes | Project name |
| `title` | string | Yes | Task title |
| `objective` | string | Yes | Task objective |
| `steps` | array[string] | No | List of steps |

**Response:**

```json
{
  "status": "created",
  "task_number": 5,
  "filename": "005-implement-auth.md",
  "path": "vibeMCP/tasks/005-implement-auth.md",
  "absolute_path": "/Users/max/.vibe/vibeMCP/tasks/005-implement-auth.md"
}
```

**Generated File Format:**

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

**Numbering:**
- Tasks are auto-numbered: `001-name.md`, `002-name.md`, etc.
- The next available number is determined by scanning existing files
- Title is sanitized for filename (lowercase, hyphens, no special chars)

---

#### `tool_log_session`

Create or append to today's session log.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project` | string | Yes | Project name |
| `content` | string | Yes | Content to log |

**Response:**

```json
{
  "status": "created",  // or "appended"
  "date": "2025-02-09",
  "path": "vibeMCP/sessions/2025-02-09.md",
  "absolute_path": "/Users/max/.vibe/vibeMCP/sessions/2025-02-09.md"
}
```

**Behavior:**
- Creates `sessions/YYYY-MM-DD.md` if it doesn't exist
- Appends with timestamp separator if file exists

**New File Format:**

```markdown
# Session Log - 2025-02-09

Your content here...
```

**Append Format:**

```markdown
# Session Log - 2025-02-09

Earlier content...

---
**14:30:15**

New content appended here...
```

---

#### `tool_update_task_status`

Update the status of a task.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project` | string | Yes | Project name |
| `task_file` | string | Yes | Task filename (e.g., "001-setup.md") |
| `new_status` | string | Yes | New status value |

**Valid Status Values:**
- `pending`
- `in-progress`
- `done`
- `blocked`

**Response:**

```json
{
  "status": "updated",
  "new_status": "done",
  "path": "vibeMCP/tasks/001-setup.md",
  "absolute_path": "/Users/max/.vibe/vibeMCP/tasks/001-setup.md"
}
```

**Behavior:**
- Finds and replaces `Status: <old>` line with `Status: <new>`
- If no status line exists, adds one after the title

---

#### `tool_create_doc`

Create a new document in any project folder.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project` | string | Yes | Project name |
| `folder` | string | Yes | Folder name |
| `filename` | string | Yes | File name (`.md` added if missing) |
| `content` | string | Yes | Document content |

**Response:**

```json
{
  "status": "created",
  "path": "vibeMCP/references/api-spec.md",
  "absolute_path": "/Users/max/.vibe/vibeMCP/references/api-spec.md"
}
```

**Errors:**
- `ValueError` if file already exists
- `ValueError` if path traversal attempted

---

#### `tool_reindex`

Force a full reindex of all projects.

**Parameters:** None

**Response:**

```json
{
  "status": "reindexed",
  "document_count": 42
}
```

**Behavior:**
- Clears all existing index data
- Walks entire `VIBE_ROOT` directory
- Indexes all `.md` files

---

## Resources

### `vibe://projects`

List all projects with summary metadata.

**Response Format (Markdown):**

```markdown
# Vibe Projects

Total projects: 3

## vibeMCP
- Path: `/Users/max/.vibe/vibeMCP`
- Last updated: 2025-02-09T14:30:00
- Open tasks: 5
- Last session: 2025-02-09T12:00:00
- Files: tasks=12, plans=2, sessions=8, reports=1

## demo-api
...
```

### `vibe://projects/{name}`

Detailed information about a specific project.

**Response Format (Markdown):**

```markdown
# Project: vibeMCP

**Path:** `/Users/max/.vibe/vibeMCP`
**Created:** 2025-01-15T10:00:00
**Updated:** 2025-02-09T14:30:00

## Available Folders

- `tasks/` (12 files)
- `plans/` (2 files)
- `sessions/` (8 files)
- `reports/` (1 file)
- `references/` (3 files)

## Task Status

- pending: 3
- in-progress: 2
- blocked: 1
- done: 6
```

### `vibe://projects/{name}/{folder}/{file}`

Read a specific file with metadata header.

**Response Format (Markdown):**

```markdown
# 001-setup.md

**Project:** vibeMCP
**Folder:** tasks
**Path:** `vibeMCP/tasks/001-setup.md`

---

# Task: Setup Project

Status: done

## Objective
...
```

---

## Prompts

### `project_briefing`

Get a concise briefing of a project's current state.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project` | string | Yes | Project name |

**Response includes:**
1. Current status (from `status.md`)
2. Active tasks with objectives:
   - In-progress tasks
   - Blocked tasks
   - Pending tasks
3. Recent sessions (last 2-3)
   - What was done
   - Blockers encountered
   - Next steps

**Example:**

```markdown
# Project Briefing: vibeMCP

## Current Status
Working on Phase 1 - Core MCP implementation.
Indexer complete, now implementing tools.

## Active Tasks

- **[in-progress]** 007-auth.md: Add bearer token authentication
- **[blocked]** 008-deploy.md: Set up VPS deployment
- **[pending]** 009-cursor.md: Configure Cursor MCP client

## Recent Sessions

### 2025-02-09

**Done:** Implemented search tool with FTS5 ranking
**Next:** Add write tools

### 2025-02-08

**Done:** Completed indexer module
**Blocked by:** Waiting for FastMCP update
```

---

### `session_start`

Load complete context to start working on a project.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `project` | string | Yes | Project name |

**Response includes:**
1. Current status (from `status.md`)
2. Execution plan (full content)
3. In-progress tasks (full content)
4. Blocked tasks (full content)
5. Pending tasks (objectives only, first 5)
6. Latest session log (full content)

**Use Case:**
Call this prompt at the start of a work session to load all relevant context into the AI agent's context window.

---

## Error Handling

### Authentication Errors

When `VIBE_AUTH_TOKEN` is set and request has no/invalid token:

```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing authentication token"
}
```

### Read-Only Mode Errors

When server is in read-only mode and write tool is called:

```
AuthError: Server is in read-only mode
```

### Path Validation Errors

```
ValueError: Path is outside VIBE_ROOT
ValueError: Invalid project name: ../etc
ValueError: Path traversal not allowed
```

### File Errors

```
ValueError: File already exists: vibeMCP/tasks/001-setup.md
ValueError: File not found: 999-missing.md
ValueError: Invalid status: unknown. Must be one of: pending, in-progress, done, blocked
```

---

## Rate Limiting

Currently no built-in rate limiting. For production deployments, implement rate limiting at the reverse proxy level (e.g., Caddy, nginx).

---

## Versioning

The API follows semantic versioning:
- Schema version is stored in `meta` table
- Current version: `1.0`

Breaking changes will increment the major version.
