# Next Task Command

Selects and starts the next available pending task. Checks dependencies, confirms with user, and marks the task as in-progress.

## Setup

**Read the vibe workspace from CLAUDE.md:**
1. Look for `vibe: <project-name>` in the project's CLAUDE.md
2. If not found, inform user and suggest running `/vibe-init` first

## Process

### 1. Get Pending Tasks

```
mcp__vibeMCP__list_tasks(project=<project>, status="pending")
```

- List all pending tasks
- If no pending tasks, check for in-progress tasks to continue

### 2. Check for In-Progress Tasks

```
mcp__vibeMCP__list_tasks(project=<project>, status="in-progress")
```

- If tasks are already in-progress, suggest completing those first
- Ask user if they want to start a new task anyway

### 3. Get Execution Plan (for dependencies)

```
mcp__vibeMCP__get_plan(project=<project>)
```

- Parse task dependencies from the plan
- Identify which pending tasks are blocked
- Find the first unblocked pending task

### 4. Select Next Task

Priority order:
1. First pending task with no blockers (all dependencies done)
2. First pending task by number if no dependencies defined
3. If all pending tasks are blocked, show blocker info

### 5. Confirm with User

Show the selected task and ask for confirmation:

```
Next available task: 004-auth-tests

Objective: Add unit tests for auth module
Dependencies: 003-auth-middleware (done)

Start this task? [Y/n]
```

### 6. Mark as In-Progress

If user confirms:
```
mcp__vibeMCP__tool_update_task_status(
    project=<project>,
    task_file="004-auth-tests.md",
    new_status="in-progress"
)
```

### 7. Provide Next Steps

```
Task 004-auth-tests marked as in-progress

Run: /solve-task 004
```

## Output Format

### Task available:
```
Next available task: <NNN>-<task-name>

Objective: <from task file>
Dependencies: <list of dependencies and their status>

Start this task? [Y/n]

---
(after confirmation)

Task <NNN>-<task-name> marked as in-progress

Next: /solve-task <NNN>
```

### Already have in-progress tasks:
```
You have tasks in progress:
- 003-auth-middleware

Finish current task first?
- /solve-task 003 — continue current task
- /status — see full project state

Or start new task anyway? [y/N]
```

### All tasks blocked:
```
No unblocked tasks available.

Blocked tasks:
- 005-integration: blocked by 004-tests (pending)
- 006-deploy: blocked by 005-integration (blocked)

Complete 004-tests first to unblock others.
Run: /solve-task 004
```

### No pending tasks:
```
No pending tasks found.

Current state:
- Done: 5 tasks
- In Progress: 0 tasks

All tasks complete! Consider:
- /task-breakdown — to add new tasks
- /status — to review completed work
```

## Rules

1. **Always use MCP tools** - Never access filesystem directly
2. **Respect dependencies** - Don't suggest blocked tasks
3. **Confirm before changing status** - Ask user before marking in-progress
4. **Handle edge cases** - No tasks, all blocked, already in-progress
5. **Suggest clear action** - Always end with a concrete next step

## Dependency Resolution

When checking if a task is blocked:
1. Parse execution plan for `blockedBy` relationships
2. Check if all blocking tasks have status `done`
3. If any blocker is not done, task is blocked

Example plan parsing:
```
| Order | Task | Blocked By |
|-------|------|------------|
| 1 | 001-setup | - |
| 2 | 002-models | 001 |
| 3 | 003-service | 002 |
```

- 001 can start immediately (no blockers)
- 002 blocked until 001 is done
- 003 blocked until 002 is done

## Examples

**Simple next task:**
```
Next available task: 002-database-schema

Objective: Create database models for user and session tables
Dependencies: 001-project-setup (done)

Start this task? [Y/n]
> Y

Task 002-database-schema marked as in-progress

Next: /solve-task 002
```

**Multiple options (no plan):**
```
Next available tasks (no execution plan found):
1. 003-api-routes
2. 004-frontend-setup
3. 005-documentation

These tasks have no defined order. Which to start?
> 1

Task 003-api-routes marked as in-progress

Next: /solve-task 003
```

**With in-progress warning:**
```
You have a task in progress:
- 002-database-schema (started yesterday)

Recommended: Complete current task first
- /solve-task 002 — continue

Start a new task anyway? [y/N]
> y

Next available task: 003-api-routes
...
```
