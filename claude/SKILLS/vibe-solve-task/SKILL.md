---
name: solve-task
description: "Use when the user wants to work on and complete a specific task. Orchestrates the full lifecycle: viability analysis, implementation, code review, and delivery. Requires vibeMCP tools. Uses git-task-workflow for git operations and code-review for review."
---

# Solve Task

Execute a task end-to-end: analyze, implement, review, and deliver.

## Prerequisites

- vibeMCP server with tools: `list_tasks`, `read_doc`, `update_task_status`, `log_session`, `create_doc`, `update_doc`
- Skills available: `git-task-workflow`, `code-review`
- Subagent capability (for code review)

If any prerequisite is missing, inform the user and stop.

## Setup

1. Find the workspace: look for `vibe: <project>` in CLAUDE.md
2. Find the base branch: look for `branch: <n>` in CLAUDE.md (default: `main`)

## Process

### 0. Clear

```bash
clear
```

### 1. Select Task

**If task number provided** (e.g., "solve-task 003"):
```
read_doc(project, "tasks", "003-*.md")
```

**If no number provided:**
```
list_tasks(project, status="in-progress")
```
- If found, use first in-progress task
- If none, use first pending from `list_tasks(project, status="pending")`
- If nothing, inform user — no tasks available

### 2. Read & Understand

```
read_doc(project, "tasks", <task_file>)
```

Parse: objective, steps, acceptance criteria, context, dependencies.

### 3. Viability Analysis (complex tasks only)

**Skip if the task has fewer than 3 steps.**

For complex tasks, before writing any code:
- Read the related files mentioned in Context
- Assess if the steps are achievable given the current codebase
- Identify risks or unknowns

If not viable → explain why and stop.

If viable but task needs adjustments:
```
update_doc(project, "tasks/<task_file>", content=<updated>)
```
Inform the user what changed and why.

### 4. Mark In-Progress

```
update_task_status(project, <task_file>, "in-progress")
```

### 5. Create Branch

Use `git-task-workflow` to create the branch:
- name: `<NNN>-<task-name>`
- base_branch: from setup

### 6. Implement

Follow the steps from the task file:
- Read before modifying
- Small, focused changes

### 7. Run Tests (attempt 1)

Detect and run the project's test suite.

If tests fail → fix and retry. Maximum 3 total attempts across steps 7–9.

### 8. Code Review (mandatory)

Use the `code-review` skill to review the diff against base branch.

If the review finds issues → fix them → go to step 9.
If the review passes → go to step 10.

### 9. Fix & Retest

Apply fixes, run tests again.

**Maximum 3 total attempts** across steps 7–9. If still failing:
- Stop
- Log what failed
- Leave the branch intact for manual intervention

### 10. Deliver

Use `git-task-workflow` to commit, push, create PR, merge, and cleanup:
- title: task title
- description: summary of changes
- base_branch: from setup

### 11. Changelog

```
create_doc(
    project=<project>,
    folder="changelog",
    filename="<NNN>-<task-name>",
    content="# <task title>\n\nDate: <YYYY-MM-DD>\nPR: <url>\n\n## Changes\n- <what changed>\n\n## Files Affected\n- <key files>"
)
```

### 12. Complete

```
update_task_status(project, <task_file>, "done")

log_session(project, "## Completed: <NNN>-<task-name>\n\n- <summary>\n- PR: <url>")
```

## Error Handling

| Error | Action |
|-------|--------|
| Tests fail (3 attempts) | Stop, log details, inform user |
| Code review fails (3 attempts) | Stop, log issues, leave branch |
| Merge conflict | Delegated to git-task-workflow — stops, informs user |
| Task has unmet dependencies | Inform user, stop |

## Key Principles

- **Delegate git to git-task-workflow** — don't duplicate git logic
- **Delegate review to code-review** — don't inline review logic
- **Always use MCP tools for task state** — never edit task files directly
- **3 attempts max** — surface the problem, don't loop forever
- **Log everything** — session log and changelog for every completed task
