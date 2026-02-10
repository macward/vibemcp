# MCP Resources

This document describes the MCP resources exposed by vibeMCP.

## Overview

Resources are read-only URIs that expose the vibe workspace structure to MCP clients. They provide a standardized way to access project information, metadata, and file contents.

## Available Resources

### 1. `vibe://projects`

Lists all projects in the vibe workspace with summary metadata.

**Response includes:**
- Total project count
- For each project:
  - Project name and path
  - Last updated timestamp
  - Number of open tasks
  - Last session date (if any)
  - File counts by folder (tasks, plans, sessions, reports)

**Example response:**
```markdown
# Vibe Projects

Total projects: 2

## vibeMCP
- Path: `/Users/username/.vibe/vibeMCP`
- Last updated: 2026-02-09T03:13:00
- Open tasks: 3
- Last session: 2026-02-09T01:30:00
- Files: tasks=7, plans=2, sessions=5, reports=1

## sample-project
- Path: `/Users/username/.vibe/sample-project`
- Last updated: 2026-02-07T21:32:00
- Open tasks: 0
- Files: tasks=0, plans=0, sessions=0, reports=0
```

### 2. `vibe://projects/{name}`

Shows detailed information about a specific project.

**Path parameters:**
- `name`: Project name (e.g., "vibeMCP")

**Response includes:**
- Project metadata (path, created, updated)
- List of available folders with file counts
- Task status breakdown (pending, in-progress, blocked, done)

**Example response:**
```markdown
# Project: vibeMCP

**Path:** `/Users/username/.vibe/vibeMCP`
**Created:** 2026-02-08T23:10:00
**Updated:** 2026-02-09T03:13:00

## Available Folders

- `tasks/` (7 files)
- `plans/` (2 files)
- `sessions/` (5 files)
- `reports/` (1 file)
- `changelog/` (0 files)
- `references/` (3 files)
- `scratch/` (0 files)

## Task Status

- pending: 2
- in-progress: 1
- done: 4
```

**Errors:**
- Returns error if project not found
- Returns error if project path doesn't exist

### 3. `vibe://projects/{name}/{folder}/{file}`

Reads the contents of a specific file from a project.

**Path parameters:**
- `name`: Project name
- `folder`: Folder name (e.g., "tasks", "plans", "sessions")
- `file`: File name (e.g., "001-task.md")

**Response includes:**
- Metadata header (project, folder, relative path)
- Full file contents

**Example response:**
```markdown
# 001-task.md

**Project:** vibeMCP
**Folder:** tasks
**Path:** `vibeMCP/tasks/001-task.md`

---

# Task: Document vibe structure

Status: done

## Objective
Create comprehensive documentation...
```

**Security:**
- Path validation prevents directory traversal attacks
- Only files within the project directory can be accessed
- Returns error if file not found or path is invalid

## Usage with FastMCP

### Basic Setup

```python
from mcp.server.fastmcp import FastMCP
from vibe_mcp.resources import register_resources

# Create MCP server
mcp = FastMCP("my-vibe-server")

# Register all resources
register_resources(mcp)

# Run server
mcp.run()
```

### Using Individual Resources

You can also use the resource functions directly in your code:

```python
from vibe_mcp.resources import (
    get_projects_resource,
    get_project_detail_resource,
    get_file_resource,
)

# List all projects
projects_summary = get_projects_resource()

# Get project details
project_info = get_project_detail_resource("vibeMCP")

# Read a specific file
file_content = get_file_resource("vibeMCP", "tasks", "001-task.md")
```

### Custom Resource Registration

If you want to customize the resource URIs:

```python
from mcp.server.fastmcp import FastMCP
from vibe_mcp.resources import (
    get_projects_resource,
    get_project_detail_resource,
    get_file_resource,
)

mcp = FastMCP("custom-server")

@mcp.resource("custom://all-projects")
def list_all_projects():
    """Custom URI for listing projects."""
    return get_projects_resource()

@mcp.resource("custom://project/{name}")
def project_info(name: str):
    """Custom URI for project details."""
    return get_project_detail_resource(name)
```

## Error Handling

All resource functions raise `ValueError` with descriptive messages when:
- Project is not found
- File is not found
- Path validation fails (directory traversal attempt)
- File path is not a regular file (e.g., directory)

Example error handling:

```python
from vibe_mcp.resources import get_file_resource

try:
    content = get_file_resource("myproject", "tasks", "001-task.md")
except ValueError as e:
    print(f"Error: {e}")
    # Handle error appropriately
```

## Implementation Details

### Path Validation

The resources module implements strict path validation to prevent directory traversal attacks:

```python
# Valid
get_file_resource("project", "tasks", "001-task.md")

# Invalid - raises ValueError
get_file_resource("project", "../..", "etc/passwd")
```

Path validation:
1. Resolves both base path and requested path to absolute paths
2. Handles symlinks (e.g., `/var` vs `/private/var` on macOS)
3. Ensures requested path is within the allowed base directory
4. Raises `ValueError` if validation fails

### Database Access

Resources create their own database connections using the singleton pattern from `vibe_mcp.config.get_config()`. Database connections are properly closed after each resource access.

### Performance Considerations

- File counts are computed on-demand by globbing directories
- Task status parsing uses quick heuristics (first 500-1000 bytes)
- Database queries use indexes for efficient lookups
- Resources are read-only and don't modify any data

## Testing

The resources module includes comprehensive tests in `tests/test_resources.py`:

- Path validation tests
- Helper function tests
- Resource content tests
- Error handling tests
- Security tests (directory traversal)

Run tests with:
```bash
uv run pytest tests/test_resources.py -v
```

## Future Enhancements

Potential improvements for future versions:

1. **Caching**: Cache project metadata and file counts for better performance
2. **Pagination**: Support pagination for large project lists
3. **Filtering**: Add query parameters to filter by status, tags, etc.
4. **Search Integration**: Expose search results as a resource
5. **Binary Files**: Support reading binary files (images, PDFs) with proper encoding
6. **Metadata Enrichment**: Include more detailed statistics and analytics
