---
name: code-review
description: "Use to review code changes before merging. Spawns a subagent that reviews the diff against the base branch. Checks correctness, bugs, edge cases, test coverage, and code quality. Returns pass or a list of issues to fix."
---

# Code Review

Review code changes via a subagent before merge.

## Prerequisites

- Git repository with changes on a feature branch
- Subagent capability

If subagents are not available, perform the review inline following the same checklist.

## Inputs

- **base_branch**: branch to diff against (e.g., `main`)
- **task_objective**: what the changes are supposed to achieve (optional but recommended)

## Process

### 1. Gather the Diff

```bash
git diff <base_branch>..HEAD
```

If the diff is very large (>2000 lines), also get the list of changed files:
```bash
git diff <base_branch>..HEAD --stat
```

### 2. Spawn Reviewer

Spawn a subagent with the following prompt:

---

**You are a code reviewer. Review this diff and respond with one of:**

- `PASS` — if the code is ready to merge
- `ISSUES` — followed by a numbered list of problems to fix

**Review checklist:**

1. **Correctness**: Does the code do what the task objective says?
2. **Bugs**: Off-by-one errors, null/undefined handling, race conditions
3. **Edge cases**: Empty inputs, large inputs, error paths
4. **Error handling**: Are errors caught and handled appropriately? No silent failures
5. **Security**: SQL injection, path traversal, secrets in code, input validation
6. **Tests**: Are the changes tested? Are edge cases covered? Are tests meaningful (not just happy path)?
7. **Code quality**: Clear naming, no duplication, reasonable function sizes, consistent style

**Rules:**
- Be specific. "This could be better" is not useful. "Line 42: `user_id` is not validated before the database query" is.
- Only flag real issues. Style preferences that don't affect correctness are not issues.
- If you're unsure about something, flag it as a question, not an issue.

**Task objective:** <task_objective or "not provided">

**Diff:**
```
<diff content>
```

---

### 3. Process Result

**If PASS** → return pass to caller.

**If ISSUES** → return the list to caller. Each issue should have:
- File and line (if identifiable from diff)
- What's wrong
- Suggested fix (when obvious)

Example:
```
ISSUES

1. src/auth.py:34 — `token` is used after the expiry check but the check 
   doesn't return early. If token is expired, execution continues with an 
   invalid token. Add `return None` after the expiry log.

2. tests/test_auth.py — No test for expired token path. Add a test that 
   verifies expired tokens are rejected.

3. src/middleware.py:12 — `request.headers.get("Authorization")` can return 
   None, but `.split(" ")` is called without a None check. Will raise 
   AttributeError on requests without auth header.
```

## Key Principles

- **Be specific** — vague feedback wastes everyone's time
- **Focus on correctness** — style is secondary
- **Flag real issues** — don't nitpick
- **Questions are OK** — "Is this intentional?" is valid feedback
- **The reviewer doesn't fix** — it identifies, the caller fixes
