# Solve Task Command

Executes a complete task lifecycle: branch creation, implementation, testing, PR, and merge.

## Syntax

```
/solve-task           # next in-progress or pending task
/solve-task 003       # specific task by number
```

## Setup

**Read configuration from CLAUDE.md:**
1. Look for `vibe: <project-name>` - the vibe workspace
2. Look for `branch: <branch-name>` - base branch (default: `main`)
3. If no vibe workspace found, inform user and suggest `/vibe-init`

## Process

### 1. Select Task

**If task number specified:**
```
mcp__vibeMCP__list_tasks(project=<project>)
```
- Find the task matching the number (e.g., `003-*`)

**If no number specified:**
```
mcp__vibeMCP__list_tasks(project=<project>, status="in-progress")
```
- If found, use first in-progress task
- If none, get first pending task:
```
mcp__vibeMCP__list_tasks(project=<project>, status="pending")
```

### 2. Read Task Details

```
mcp__vibeMCP__read_doc(project=<project>, folder="tasks", filename=<task-file>)
```
- Parse objective and steps from task content
- Understand acceptance criteria

### 3. Mark as In-Progress

```
mcp__vibeMCP__tool_update_task_status(
    project=<project>,
    task_file=<task-file>,
    new_status="in-progress"
)
```

### 4. Create Feature Branch

```bash
# Ensure clean working directory
git status

# Switch to base branch and update
git checkout <base-branch>
git pull

# Create task branch
git checkout -b task/<NNN>-<task-name>
```

Branch naming: `task/003-auth-service` (lowercase, hyphens)

### 5. Implement Task

Follow the steps defined in the task file:
- Read referenced files before modifying
- Make incremental changes
- Test as you go

### 6. Run Tests

Detect and run the project's test suite:

```bash
# Detect test runner
if [ -f "package.json" ]; then
    npm test
elif [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
    pytest
elif [ -f "Cargo.toml" ]; then
    cargo test
fi
```

**If tests fail:**
- Show test output
- Do NOT continue to PR
- Suggest fixes or ask for guidance

### 7. Commit Changes

```bash
git add .
git commit -m "$(cat <<'EOF'
<task-title>

<brief description of changes>

Task: <NNN>-<task-name>

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

### 8. Push and Create PR

```bash
git push -u origin task/<NNN>-<task-name>

gh pr create \
    --base <base-branch> \
    --title "<task-title>" \
    --body "$(cat <<'EOF'
## Summary

<1-3 bullet points from task objective>

## Changes

<list of key changes made>

## Task

Closes task `<NNN>-<task-name>`

---
Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### 9. Merge PR

```bash
# Enable auto-merge with squash
gh pr merge --auto --squash
```

If auto-merge not available:
```bash
# Wait for checks then merge
gh pr merge --squash
```

### 10. Cleanup

```bash
# Return to base branch
git checkout <base-branch>
git pull

# Delete local task branch
git branch -d task/<NNN>-<task-name>
```

### 11. Mark Task Done

```
mcp__vibeMCP__tool_update_task_status(
    project=<project>,
    task_file=<task-file>,
    new_status="done"
)
```

### 12. Log Session

```
mcp__vibeMCP__tool_log_session(
    project=<project>,
    content="## Completed: <NNN>-<task-name>\n\n- <summary of changes>\n- PR: <pr-url>"
)
```

## Output Format

### During Execution

```
/solve-task 003 started

[1/7] Reading task... done
      Objective: Implement auth service

[2/7] Creating branch... done
      Branch: task/003-auth-service

[3/7] Implementing...
      └── Creating auth/service.py
      └── Adding middleware
      └── Writing tests

[4/7] Running tests... done
      ✓ 12 tests passed

[5/7] Committing... done
      Commit: abc1234

[6/7] Creating PR... done
      PR #15: https://github.com/user/repo/pull/15

[7/7] Merging... done
      Merged via squash

Task 003-auth-service completed ✓
```

### On Error

```
[4/7] Running tests... FAILED

2 tests failed:
- test_auth_token_validation
- test_session_expiry

Output:
---
AssertionError: Expected token to be valid
...
---

Options:
1. Fix the failing tests and run /solve-task 003 again
2. Skip tests with caution (not recommended)

Task paused. Fix issues and retry.
```

### Merge Conflict

```
[6/7] Creating PR... done
      PR #15

[7/7] Merging... CONFLICT

Merge conflicts detected on <base-branch>.

Options:
1. Resolve conflicts manually:
   git checkout task/003-auth-service
   git merge <base-branch>
   # resolve conflicts
   git push

2. Rebase:
   git rebase <base-branch>
   git push --force-with-lease

After resolving, PR will auto-merge if checks pass.
```

## Rules

1. **Always use MCP tools for task state** - Never modify task files directly
2. **Never skip tests** - If tests fail, stop and report
3. **Always create PR** - Even for small changes, maintain audit trail
4. **Squash merge** - Keep main branch history clean
5. **Clean up branches** - Delete task branch after merge
6. **Log completion** - Update session log for continuity

## Error Recovery

| Error | Action |
|-------|--------|
| Tests fail | Show output, suggest fix, stop |
| PR checks fail | Show status, wait or suggest fix |
| Merge conflict | Show conflict files, provide resolution steps |
| Push rejected | Pull and rebase, retry |
| gh CLI not authenticated | Prompt `gh auth login` |

## Examples

**Simple task:**
```
> /solve-task 002

/solve-task 002 started

[1/7] Reading task... done
      002-database-models: Create SQLAlchemy models

[2/7] Creating branch... done
[3/7] Implementing... done
[4/7] Running tests... done (8 passed)
[5/7] Committing... done
[6/7] Creating PR... done (#12)
[7/7] Merging... done

Task 002-database-models completed ✓
Next: /solve-task or /next-task
```

**Auto-selecting next task:**
```
> /solve-task

No task number specified.
Found in-progress: 003-auth-service

Continuing with 003-auth-service...
```

**No tasks available:**
```
> /solve-task

No pending or in-progress tasks found.

Options:
- /task-breakdown — create new tasks
- /status — review project state
```
