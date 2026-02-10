# vibeMCP - Context for AI Agents

## What is vibeMCP?

MCP server that provides centralized access to project workspaces. It exposes tasks, plans, sessions, and documentation across all projects through a unified interface.

**Not a task manager. It's a context fabric for agents.**

---

## Quick Reference

### Most Used Tools (80% of usage)

| Tool | Purpose | Example |
|------|---------|---------|
| `search` | Find anything across projects | `search("auth implementation")` |
| `read_doc` | Read a specific document | `read_doc("vibeMCP", "tasks", "001-setup.md")` |
| `list_tasks` | List tasks with optional status filter | `list_tasks("vibeMCP", status="in-progress")` |
| `create_task` | Create a new task | `create_task("vibeMCP", "Add logging", steps=["..."])` |
| `log_session` | Record session notes | `log_session("vibeMCP", "Implemented auth module")` |

### Write Tools

| Tool | Purpose |
|------|---------|
| `create_doc` | Create document in any folder |
| `update_doc` | Update existing document |
| `update_task_status` | Change task status (pending/in-progress/done) |
| `create_plan` | Create or update execution plan |
| `init_project` | Initialize new project workspace |

### Resources (Read-only URIs)

```
vibe://projects                              → List all projects
vibe://projects/{name}                       → Project details + stats
vibe://projects/{name}/{folder}/{file}       → Read specific file
```

---

## Workspace Structure

Each project has a workspace at `<VIBE_ROOT>/<project>/`:

```
<project>/
├── tasks/       ← Individual tasks (001-name.md, 002-name.md)
├── plans/       ← Execution plans, designs, ADRs
├── sessions/    ← Session notes by date
├── reports/     ← Generated reports
├── changelog/   ← Change history
├── references/  ← External docs, specs
├── scratch/     ← Drafts, exploration
└── assets/      ← Project resources
```

### Task Format

```markdown
# Task Title

status: pending | in-progress | done

## Objective
What needs to be done

## Steps
- [ ] Step 1
- [ ] Step 2

## Notes
Additional context
```

### Task Status Values

| Status | Meaning |
|--------|---------|
| `pending` | Not started |
| `in-progress` | Currently being worked on |
| `done` | Completed |

---

## Common Workflows

### Start a session
1. `list_tasks(project, status="in-progress")` - See active work
2. `search(project, "blockers OR pending")` - Check blockers
3. `log_session(project, "Starting work on X")` - Log start

### Find context
1. `search("keyword")` - Cross-project search
2. `read_doc(project, folder, file)` - Read specific doc
3. Use `vibe://projects/{name}` resource for project overview

### Create work items
1. `create_task(project, title, steps=[...])` - New task
2. `update_task_status(project, task_file, "in-progress")` - Start work
3. `update_task_status(project, task_file, "done")` - Complete

---

## Search Syntax (FTS5)

```
auth                    → Simple term
"user auth"            → Exact phrase
auth AND token         → Both terms
auth OR session        → Either term
auth NOT deprecated    → Exclude term
auth*                  → Prefix match
heading:objective      → Search in headings only
content:api            → Search in content only
```

---

## Prompts

| Prompt | Purpose |
|--------|---------|
| `project_briefing` | Full project context (tasks, plans, recent sessions) |
| `session_start` | Quick briefing to resume work |
