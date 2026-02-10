# Task Breakdown Command

When the user describes a feature or request, analyze it and create actionable tasks using MCP tools.

## Setup

**First, read the vibe workspace from CLAUDE.md:**
1. Look for `vibe: <project-name>` in the project's CLAUDE.md
2. Verify project exists by calling `mcp__vibeMCP__list_tasks(project=<project-name>)`
3. If project doesn't exist, suggest running `/vibe-init` first

## Process

### 1. Analysis with MCP

**Check existing state:**
```
mcp__vibeMCP__list_tasks(project=<project>)
```
- View existing tasks and their status
- Identify patterns in naming/structure
- Detect potential duplicates before creating new tasks

**Check for existing plans:**
```
mcp__vibeMCP__get_plan(project=<project>)
```
- Review any existing execution plan
- Understand current project state

### 2. Quick Analysis (keep it brief)
- **What**: One sentence describing the goal
- **Scope**: Files/modules affected
- **Complexity**: Small (1-2 tasks) | Medium (3-5 tasks) | Large (6+ tasks)

### 3. Create Tasks via MCP

For each logical unit of work, use the MCP tool:

```
mcp__vibeMCP__tool_create_task(
    project=<project>,
    title="Clear descriptive title",
    objective="One paragraph max describing what this task accomplishes",
    steps=["Step 1 (specific, actionable)", "Step 2", "Step 3"]
)
```

The tool automatically:
- Assigns the next available number (001, 002, etc.)
- Creates the file with standard format and `Status: pending`
- Places it in the correct location

### 4. Create Execution Plan via MCP

```
mcp__vibeMCP__tool_create_doc(
    project=<project>,
    folder="plans",
    filename="execution-plan",
    content=<plan content below>
)
```

**Plan content format:**
```markdown
# Execution Plan

## Overview
[One sentence describing the feature/goal]

## Task Graph

001-task-name
 └─► 002-depends-on-001
      └─► 004-depends-on-002
 └─► 003-depends-on-001

## Execution Order

| Order | Task | Blocked By | Blocks |
|-------|------|------------|--------|
| 1 | 001-task-name | - | 002, 003 |
| 2 | 002-task-name | 001 | 004 |
| 3 | 003-task-name | 001 | - |
| 4 | 004-task-name | 002 | - |

## Current Status
- Pending: 001, 002, 003, 004
- In Progress: -
- Done: -
```

### 5. Output Summary

After creating tasks, provide:
```
Created X tasks in project <project>:
- 001-task-name
- 002-task-name
- 003-task-name

Execution plan: plans/execution-plan.md

Start with: /solve-task <project> 001
```

## Rules

1. **Always use MCP** - Never write files directly, use MCP tools
2. **Verify before creating** - Use `list_tasks` to check existing tasks and avoid duplicates
3. **One responsibility per task** - Each task should be completable in one session
4. **No code in tasks** - Describe what to do, not how to implement it
5. **Always create execution plan** - Document dependencies between tasks
6. **Be specific** - Steps should be actionable
7. **Be realistic** - Break large features into manageable chunks

## Size Guidelines

| Complexity | Tasks | Approach |
|------------|-------|----------|
| Small | 1-2 | Quick focused tasks |
| Medium | 3-5 | Multiple related tasks |
| Large | 6+ | Consider phases or splitting into sub-features |

## Example

User: "Add user authentication with JWT"

Vibe workspace: `backend-api` (from CLAUDE.md)

**Step 1 - Check existing tasks:**
```
mcp__vibeMCP__list_tasks(project="backend-api")
```

**Step 2 - Create tasks:**
```
mcp__vibeMCP__tool_create_task(
    project="backend-api",
    title="Auth models and schemas",
    objective="Create User model and token schemas for JWT authentication",
    steps=["Define User model with email/password", "Create token schemas", "Add password hashing utility"]
)
```
(Repeat for each task)

**Step 3 - Create execution plan:**
```
mcp__vibeMCP__tool_create_doc(
    project="backend-api",
    folder="plans",
    filename="execution-plan",
    content="# Execution Plan\n\n## Overview\nImplement JWT authentication...\n\n## Task Graph\n001-auth-models\n └─► 002-auth-service\n      └─► 003-auth-endpoints\n           └─► 004-auth-middleware\n                └─► 005-auth-tests"
)
```

**Output:**
```
Created 5 tasks in project backend-api:
- 001-auth-models
- 002-auth-service
- 003-auth-endpoints
- 004-auth-middleware
- 005-auth-tests

Execution plan: plans/execution-plan.md

Start with: /solve-task backend-api 001
```
