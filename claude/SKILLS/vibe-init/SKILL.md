---
name: vibe-init
description: "Use when the user wants to initialize a new vibe workspace for a project. Creates the standard folder structure via vibeMCP. Only use init_project — no other tools, no file creation, no commands."
---

# Vibe Init

Initialize a new vibe workspace for a project via vibeMCP.

## Prerequisites

This skill requires a vibeMCP server with the `init_project` tool available.

If the MCP server is not connected, inform the user and stop.

## Restrictions

This skill uses **only one tool**:
```
init_project(project=<name>)
```

Do NOT:
- Create or modify local files
- Run shell commands
- Use any other MCP tools
- Create CLAUDE.md or modify it

## Process

### 1. Get Project Name

Ask the user for the project name. Validate:
- Only letters, numbers, and hyphens
- No spaces, slashes, dots, or special characters

### 2. Create Workspace

```
init_project(project=<name>)
```

This creates the full structure:
```
~/.vibe/<name>/
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

### 3. Confirm

Tell the user:
- Workspace was created successfully
- They should add `vibe: <name>` to their project's CLAUDE.md to link the repo

Done. Nothing else.
