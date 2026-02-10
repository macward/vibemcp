# Run Plan Command

Orchestrates execution of all pending tasks in sequence. Supports autonomous, semi-autonomous, and dry-run modes.

## Syntax

```
/run-plan              # autonomous mode (default)
/run-plan --confirm    # pause between tasks for confirmation
/run-plan --dry-run    # show what would be done without executing
```

## Setup

**Read configuration from CLAUDE.md:**
1. Look for `vibe: <project-name>` - the vibe workspace
2. Look for `branch: <branch-name>` - base branch (default: `main`)
3. If no vibe workspace found, inform user and suggest `/vibe-init`

## Process

### 1. Gather Plan Context

```
mcp__vibeMCP__get_plan(project=<project>)
```
- Read execution plan for task ordering and dependencies

```
mcp__vibeMCP__list_tasks(project=<project>, status="pending")
```
- Get all pending tasks

```
mcp__vibeMCP__list_tasks(project=<project>, status="in-progress")
```
- Check for already in-progress tasks

### 2. Build Execution Queue

Parse the execution plan to determine order:
- Respect `blockedBy` dependencies
- Skip tasks already marked `done`
- Include any `in-progress` tasks first

If no plan exists, use task number order (001, 002, 003...).

### 3. Dry Run Mode (`--dry-run`)

If `--dry-run` flag is present, display the plan and exit:

```
/run-plan --dry-run

Execution Plan for vibeMCP:

Tasks to execute (in order):
1. 003-auth-service (pending)
2. 004-auth-tests (pending, blocked by 003)
3. 005-integration (pending, blocked by 004)

Already done: 001-setup, 002-models
In progress: none

Total: 3 tasks to execute

Run /run-plan to execute.
```

### 4. Confirm Mode Setup (`--confirm`)

If `--confirm` flag is present, pause before each task:

```
[2/5] Next: 004-auth-tests
      Objective: Add unit tests for auth module

Continue? [Y/n/skip/abort]
- Y: proceed with this task
- n: skip this task, continue with next
- skip: same as n
- abort: stop run-plan entirely
```

### 5. Execute Tasks Loop

For each task in the queue:

#### 5.1 Announce Task
```
[2/5] 004-auth-tests ━━━━━━━━━━ starting
```

#### 5.2 Confirm (if --confirm mode)
```
Continue with 004-auth-tests? [Y/n/skip/abort]
```

#### 5.3 Execute Task

Run the full solve-task workflow:
1. Mark as in-progress
2. Create branch
3. Implement
4. Run tests
5. Commit
6. Create PR
7. Merge
8. Mark as done
9. Cleanup

Show progress:
```
[2/5] 004-auth-tests ━━━━━━━━━━ running
      └── Creating branch...
      └── Implementing...
      └── Running tests...
      └── Creating PR (#16)...
      └── Merging...
[2/5] 004-auth-tests ━━━━━━━━━━ done ✓
```

#### 5.4 Handle Errors

If any step fails:
```
[2/5] 004-auth-tests ━━━━━━━━━━ FAILED ✗
      └── Tests failed: 2 assertions

Error details:
---
AssertionError: Expected 200, got 401
  at test_auth_flow (tests/test_auth.py:45)
---

Options:
1. Fix issues and run: /run-plan --continue
2. Retry this task: /solve-task 004
3. Skip and continue: /run-plan --skip 004
4. Abort remaining tasks

Choose [1/2/3/4]:
```

#### 5.5 Log Progress

After each task:
```
mcp__vibeMCP__tool_log_session(
    project=<project>,
    content="## run-plan progress\n\n- Completed: 004-auth-tests (#16)\n- Remaining: 1 task"
)
```

### 6. Completion Summary

```
/run-plan completed

Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ 003-auth-service    PR #15
✓ 004-auth-tests      PR #16
✓ 005-integration     PR #17
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3/3 tasks completed

Merged PRs:
- #15 task/003-auth-service
- #16 task/004-auth-tests
- #17 task/005-integration

All pending tasks done!
```

## Output Format

### Starting

```
/run-plan started (5 pending tasks)

Mode: autonomous
Base branch: develop
```

### Progress

```
[1/5] 001-setup ━━━━━━━━━━ done ✓
[2/5] 002-models ━━━━━━━━ done ✓
[3/5] 003-service ━━━━━━ running...
      └── Creating branch...
      └── Implementing...
      └── Running tests...
      └── Creating PR...
      └── Merging...
[3/5] 003-service ━━━━━━ done ✓
[4/5] 004-tests ━━━━━━━━━ running...
```

### Confirm Mode Pause

```
[3/5] 003-service completed ✓

Next: 004-tests
Objective: Add integration tests for service layer

Continue? [Y/n/skip/abort]
```

### Error State

```
[3/5] 003-service ━━━━━━ FAILED ✗
      └── Tests failed (3 failures)

run-plan paused at task 3/5

To resume:
- Fix issues, then: /run-plan --continue
- Skip this task: /run-plan --skip 003
- Retry just this: /solve-task 003
```

### Completion

```
/run-plan completed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ 001-setup           PR #12
✓ 002-models          PR #13
✓ 003-service         PR #14
✓ 004-tests           PR #15
✓ 005-docs            PR #16
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5/5 tasks completed

All plan tasks done!
```

## Rules

1. **Always use MCP tools for task state** - Never modify task files directly
2. **Respect dependencies** - Don't execute blocked tasks
3. **Stop on failure by default** - Unless user explicitly continues
4. **Log progress** - Update session log for recovery
5. **Provide clear recovery options** - On any failure, show next steps
6. **Squash merge** - Keep branch history clean

## Flags

| Flag | Behavior |
|------|----------|
| (none) | Autonomous mode - run all tasks without pausing |
| `--confirm` | Pause before each task for user confirmation |
| `--dry-run` | Show execution plan without running anything |
| `--continue` | Resume from last failed/paused task |
| `--skip NNN` | Skip specific task number, continue with rest |

## Error Recovery

| Scenario | Recovery |
|----------|----------|
| Tests fail | Show output, pause, offer fix/skip/abort |
| Merge conflict | Show files, provide resolution steps |
| PR checks fail | Show status, wait or suggest fix |
| Network error | Retry once, then pause with error |
| Task blocked | Skip, show blocker, continue with unblocked |

## Examples

**Autonomous run:**
```
> /run-plan

/run-plan started (3 pending tasks)
Mode: autonomous

[1/3] 003-auth ━━━━━━━━━━ done ✓ (#15)
[2/3] 004-tests ━━━━━━━━ done ✓ (#16)
[3/3] 005-docs ━━━━━━━━━ done ✓ (#17)

/run-plan completed
3/3 tasks done
```

**Confirm mode:**
```
> /run-plan --confirm

/run-plan started (3 pending tasks)
Mode: confirm (pause between tasks)

[1/3] 003-auth ━━━━━━━━━━ done ✓ (#15)

Next: 004-tests
Objective: Add unit tests for auth

Continue? [Y/n/skip/abort] Y

[2/3] 004-tests ━━━━━━━━ done ✓ (#16)

Next: 005-docs
Objective: Update API documentation

Continue? [Y/n/skip/abort] n

Skipped 005-docs

/run-plan completed
2/3 tasks done, 1 skipped
```

**Dry run:**
```
> /run-plan --dry-run

Execution Plan for vibeMCP:

Order | Task | Status | Depends On
------|------|--------|------------
1     | 003-auth-service | pending | 002 (done)
2     | 004-auth-tests | pending | 003
3     | 005-integration | pending | 004

3 tasks will be executed in order.
Estimated: ~30 min (depends on implementation complexity)

Run /run-plan to execute.
```

**Recovery after failure:**
```
> /run-plan --continue

Resuming run-plan from task 004-tests

Previous status:
✓ 003-auth-service (done)
✗ 004-tests (failed - tests)

[2/3] 004-tests ━━━━━━━━ running...
```
