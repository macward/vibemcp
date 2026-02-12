---
name: run-plan
description: "Use when the user wants to execute all pending tasks in sequence. Default is autonomous (runs all without pausing). If the user asks to confirm, review, or go step-by-step, pause between tasks for approval. Uses solve-task for each task."
---

# Run Plan

Execute all pending tasks in sequence.

## Prerequisites

- vibeMCP server with tools: `list_tasks`, `get_plan`, `list_plans`, `log_session`
- Skill available: `solve-task`

If any prerequisite is missing, inform the user and stop.

## Parameters

- **feature** (optional): Execute only tasks for a specific feature. When specified:
  - Loads feature plan from `feature-<name>.md` instead of master plan
  - Filters tasks by `feature` field

## Setup

1. Find the workspace: look for `vibe: <project>` in CLAUDE.md
2. Find the base branch: look for `branch: <n>` in CLAUDE.md (default: `main`)
3. Determine mode from user's request:
   - **Autonomous** (default): "run the plan", "execute all tasks"
   - **Confirm**: "run the plan step by step", "run with confirmation", "one at a time"
4. Check for feature scope:
   - "run feature auth", "execute auth plan" → feature="auth"
   - No feature mentioned → run master plan

## Process

### 1. Gather Context

**If feature specified:**
```
get_plan(project=<project>, filename=f"feature-{feature}.md")
list_tasks(project, status="pending", feature=feature)
list_tasks(project, status="in-progress", feature=feature)
```

**Otherwise (master plan):**
```
get_plan(project=<project>)
list_tasks(project, status="pending")
list_tasks(project, status="in-progress")
```

If no pending or in-progress tasks → inform user and stop.

### 2. Build Execution Queue

From the execution plan:
- Respect `blockedBy` dependencies
- Skip tasks already `done`
- Put `in-progress` tasks first
- If no plan exists, use task number order

If all tasks are blocked → show what's blocking and stop.

### 3. Announce

```
run-plan started (N tasks)
Mode: autonomous | confirm
```

### 4. Execute Loop

For each task in the queue:

**If confirm mode** — present and ask before each task:
```
[2/N] Next: <NNN>-<task-name>
Objective: <from task>

Continue? [Y / skip / abort]
```
- **Y** → proceed
- **skip** → skip, move to next
- **abort** → stop entirely

**Then** (both modes): run `solve-task` for this task.

```
[2/N] <NNN>-<task-name> ── done ✓
```

After each task, log progress:
```
log_session(project, "## run-plan progress\n\n- Completed: <NNN>\n- Remaining: N tasks")
```

Re-check dependencies before starting the next task.

### 5. Handle Failures

**Autonomous mode**: stop the entire run. Log what failed, inform user.

**Confirm mode**: give the user options:
```
[3/N] <NNN>-<task-name> ── FAILED ✗
Reason: <what failed>

Options: retry / skip / abort
```

Log regardless of choice:
```
log_session(project, "## run-plan: <NNN> failed\n\n- Reason: <e>\n- Action: <what happened>")
```

### 6. Completion

```
run-plan completed

✓ 001-task-name    PR #12
✓ 002-task-name    PR #13
✓ 003-task-name    PR #14

N/N tasks completed
```

If confirm mode had skips:
```
✓ 001-task-name    PR #12
⊘ 002-task-name    skipped
✓ 003-task-name    PR #13

2/3 completed, 1 skipped
```

Log final summary:
```
log_session(project, "## run-plan completed\n\n- Done: N\n- Skipped: N\n- PRs: ...")
```

## Key Principles

- **Delegate to solve-task** — don't duplicate its logic
- **Re-check dependencies** — completing a task may unblock the next
- **Autonomous stops on failure** — don't skip broken tasks silently
- **Confirm mode gives choice** — retry, skip, or abort
- **Log everything** — session logs enable recovery
- **Clean state between tasks** — each starts on fresh base branch
