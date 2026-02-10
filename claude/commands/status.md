# Status Command

Provides a comprehensive overview of the project's current state: tasks by status, execution plan progress, and overall health.

## Setup

**Read the vibe workspace from CLAUDE.md:**
1. Look for `vibe: <project-name>` in the project's CLAUDE.md
2. If not found, inform user and suggest running `/vibe-init` first

## Process

### 1. Get All Tasks

```
mcp__vibeMCP__list_tasks(project=<project>)
```

- Retrieve all tasks regardless of status
- Group by status: done, in-progress, pending, blocked

### 2. Get Execution Plan

```
mcp__vibeMCP__get_plan(project=<project>)
```

- Read the execution plan if it exists
- Parse the task graph and dependencies
- Identify current position in the plan

### 3. Calculate Statistics

- Count tasks by status
- Calculate completion percentage
- Identify any blocked tasks and their blockers

### 4. Generate Status Report

Display a comprehensive status:

```
Project: <project>

Tasks:
  Done:        5
  In Progress: 1 (003-auth-middleware)
  Pending:     3 (004, 005, 006)
  Blocked:     0
  ─────────────
  Total:       9
  Progress:    55% complete

Execution Plan:
001 -> 002 -> 003 -> 004
              |
              +-> 005 -> 006

Current: 003-auth-middleware

Next available: 004-tests (unblocked)
```

## Output Format

### Minimal (no execution plan):
```
Project: <project>

Tasks:
  Done:        <N>
  In Progress: <N> (<task names>)
  Pending:     <N>
  Blocked:     <N>
  ─────────────
  Progress:    <X>% complete
```

### With Execution Plan:
```
Project: <project>

Tasks:
  Done:        <N>
  In Progress: <N> (<task names>)
  Pending:     <N>
  Blocked:     <N>
  ─────────────
  Progress:    <X>% complete

Execution Plan:
<visual graph showing done/current/pending>

Current: <in-progress task>
Next available: <next unblocked pending task>
```

### With Blockers:
```
Project: <project>

Tasks:
  Done:        <N>
  In Progress: <N>
  Pending:     <N>
  Blocked:     <N>
  ─────────────
  Progress:    <X>% complete

Blockers:
- 005-integration blocked by: 003-auth (in-progress)
- 006-deploy blocked by: 004-tests (pending), 005-integration (blocked)
```

## Rules

1. **Always use MCP tools** - Never access filesystem directly
2. **Show actionable info** - Highlight what can be worked on now
3. **Visualize dependencies** - When plan exists, show the graph
4. **Identify bottlenecks** - Call out blocked tasks and their blockers
5. **Calculate progress** - Show percentage based on done vs total

## Visual Conventions

For task status in graphs:
- `[x]` or checkmark for done
- `[>]` or arrow for in-progress
- `[ ]` or empty for pending
- `[!]` or warning for blocked

Example graph:
```
001[x] -> 002[x] -> 003[>] -> 004[ ]
                    |
                    +-> 005[ ] -> 006[ ]
```

## Examples

**Healthy progress:**
```
Project: vibeMCP

Tasks:
  Done:        4
  In Progress: 1 (005-auth-tests)
  Pending:     2
  Blocked:     0
  ─────────────
  Progress:    57% complete

Execution Plan:
001[x] -> 002[x] -> 003[x] -> 004[x] -> 005[>] -> 006[ ] -> 007[ ]

Current: 005-auth-tests
Next available: 006-integration (after 005 completes)
```

**Project with blockers:**
```
Project: backend-api

Tasks:
  Done:        2
  In Progress: 0
  Pending:     3
  Blocked:     1
  ─────────────
  Progress:    33% complete

Blockers:
- 004-deploy blocked by: external dependency (noted in task)

Next available: 003-tests (no blockers)
Suggested: Run /solve-task 003
```

**New project:**
```
Project: new-feature

Tasks:
  Done:        0
  In Progress: 0
  Pending:     5
  Blocked:     0
  ─────────────
  Progress:    0% complete

Execution Plan:
001[ ] -> 002[ ] -> 003[ ]
          |
          +-> 004[ ] -> 005[ ]

Next available: 001-setup
Suggested: Run /solve-task 001 to begin
```
