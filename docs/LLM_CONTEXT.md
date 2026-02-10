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

---

## Skills / Commands

Slash commands available in Claude Code for working with vibeMCP:

| Command | Purpose |
|---------|---------|
| `/vibe-init` | Initialize a project workspace - creates folder structure and links repo |
| `/task-breakdown` | Analyze a feature request and create actionable tasks with execution plan |
| `/solve-task` | Execute a task: create branch, implement, code review, push, PR, merge |
| `/design` | Generate a design document from research/specs |
| `/session-start` | Resume context quickly at session start - shows active tasks and last session |
| `/status` | Project overview - task counts by status and execution plan progress |
| `/next-task` | Select and start the next available pending task |

### /vibe-init

Initializes a new vibe workspace for the current project:
1. Asks for project name
2. Creates workspace structure via `tool_init_project`
3. Links repo by adding `vibe: <name>` to CLAUDE.md

### /task-breakdown

Analyzes a feature/request and creates tasks:
1. Reads project from CLAUDE.md (`vibe: <name>`)
2. Checks existing tasks via `list_tasks`
3. Creates tasks via `create_task`
4. Creates execution plan via `create_doc`

### /solve-task

Executes a task file end-to-end:
1. Reads task file (e.g., `tasks/001-auth.md`)
2. Creates git branch (`task/001-auth`)
3. Implements the task following steps
4. Runs code review via `code-review-expert` agent
5. Creates changelog entry
6. Pushes branch, creates PR, merges (via `gh` CLI)

### /design

Generates a design document from research:
1. Reads research/specs files provided
2. Analyzes project context (CLAUDE.md, structure)
3. Asks clarifying questions if needed
4. Creates `docs/design/YYYY-MM-DD-<topic>-design.md`

### /session-start

Resumes context quickly at the start of a session:
1. Reads `vibe: <project>` from CLAUDE.md
2. Lists in-progress tasks via `list_tasks`
3. Reads the most recent session log
4. Shows summary with active tasks, last work, and suggested next step

### /status

Provides a project overview:
1. Lists all tasks grouped by status (done, in-progress, pending, blocked)
2. Shows execution plan graph if available
3. Displays progress summary

### /next-task

Selects and starts the next pending task:
1. Lists pending tasks via `list_tasks`
2. Checks execution plan for dependencies
3. Selects first unblocked task
4. Marks as in-progress via `update_task_status`
5. Suggests running `/solve-task` to execute

Use `/vibe-init` first to setup, then `/task-breakdown` to plan work.