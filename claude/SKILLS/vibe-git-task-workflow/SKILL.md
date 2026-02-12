---
name: git-task-workflow
description: "Use when you need to deliver code changes through git: create branch, commit, push, PR, and merge. Does not manage task state — it only handles the git lifecycle. Requires git and gh CLI."
---

# Git Task Workflow

Branch, commit, PR, and merge workflow for a unit of work.

## Prerequisites

- Git repository with a remote
- `gh` CLI authenticated
- Clean working directory

If `gh` is not authenticated, prompt `gh auth login` and stop.

## Inputs

This skill expects to be called with:
- **name**: short identifier for the branch (e.g., "003-auth-service")
- **title**: human-readable title for commit and PR
- **description**: summary for the PR body
- **base_branch**: branch to merge into (default: `main`)

## Process

### 1. Create Branch

```bash
git checkout <base_branch>
git pull
git checkout -b task/<name>
```

### 2. Do the Work

The caller handles implementation. This skill resumes after changes are made.

### 3. Commit

```bash
git add .
git commit -m "<title>

<description>

Task: <name>
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 4. Push & Create PR

```bash
git push -u origin task/<name>

gh pr create \
    --base <base_branch> \
    --title "<title>" \
    --body "## Summary
<description>

## Task
Closes task <name>"
```

### 5. Merge & Cleanup

```bash
gh pr merge --squash

git checkout <base_branch>
git pull
git branch -d task/<name>
```

## Error Handling

| Error | Action |
|-------|--------|
| Merge conflict | Show conflicting files, stop, let caller decide |
| Push rejected | Pull and rebase, retry once |
| PR checks fail | Show status, stop, let caller decide |
| `gh` not authenticated | Prompt `gh auth login`, stop |

## Key Principles

- **No task state** — this skill doesn't know about vibeMCP
- **Squash merge** — always, keep history clean
- **Clean up** — delete branch after merge
- **Stop on conflict** — don't try to auto-resolve
