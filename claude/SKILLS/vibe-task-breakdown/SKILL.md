---
name: task-breakdown
description: "Use when the user describes a feature, request, or body of work that needs to be broken into actionable tasks. Analyzes the request, creates structured tasks with dependencies, and produces an execution plan. Typically follows brainstorming and leads into solve-task. Requires vibeMCP tools."
---

# Task Breakdown

Turn a feature description or request into structured, actionable tasks with an execution plan.

## Flow

```
brainstorming → [task-breakdown] → solve-task / run-plan
```

- If coming from `brainstorming`, a design doc should already exist in `plans/`. Read it first — it's your spec.
- After creating tasks, suggest `solve-task` for a single task or `run-plan` to execute all.

## Prerequisites

This skill requires a vibeMCP server with these tools available:
- `list_tasks` — check existing tasks
- `get_plan` — read execution plan
- `create_task` — create task files
- `create_doc` / `update_doc` — create or update documents

If the MCP server is not connected, inform the user and stop.

## Before You Start

1. **Find the workspace**: Look for `vibe: <n>` in the project's CLAUDE.md or ask the user
2. **Check for a design doc**: If `brainstorming` was used, read the design from `plans/` — it defines what to build
3. **Check existing state**: Call `list_tasks(project)` to see current tasks and avoid duplicates
4. **Check existing plan**: Call `get_plan(project)` — if a plan exists, you're extending it, not replacing it

## Process

### 1. Analyze the Request

Quick assessment — keep it to one message:
- **What**: One sentence describing the goal
- **Scope**: Files or modules affected
- **Size**: Small (1–2 tasks), Medium (3–5), Large (6+)

If coming from a design doc, extract this from the doc — don't re-ask the user.

If the request is ambiguous, ask **one** clarifying question. Prefer multiple choice.

### 2. Design the Task Graph

Before creating anything, think through dependencies:
- What can run in parallel?
- What blocks what?
- Each task should be completable in one work session
- One responsibility per task — if a task has "and" in the title, split it

### 3. Create Tasks

For each task:
```
create_task(
    project=<project>,
    title="Clear descriptive title",
    objective="One paragraph — what this task accomplishes",
    steps=["Specific actionable step", "Another step", ...]
)
```

Rules for good tasks:
- **Objective**: What, not how. No implementation details.
- **Steps**: Actionable and verifiable. "Create X" not "Think about X".
- **3–7 steps** per task. More than 7? Split the task.
- **No code** in task descriptions.

The tool auto-numbers tasks (001, 002, ...) and creates them in the standard format.

### 4. Create Execution Plan

```
create_doc(
    project=<project>,
    folder="plans",
    filename="execution-plan",
    content=<see format below>
)
```

If a plan already exists, use `update_doc` to merge with existing content.

Plan format:
```markdown
# Execution Plan

## Overview
[One sentence — the goal]

## Task Graph
001-first-task
 └─► 002-depends-on-001
      └─► 004-depends-on-002
 └─► 003-also-depends-on-001

005-independent-task

## Execution Order

| Order | Task | Blocked By | Blocks |
|-------|------|------------|--------|
| 1 | 001-name | - | 002, 003 |
| 2 | 005-name | - | - |
| 3 | 002-name | 001 | 004 |
| 4 | 003-name | 001 | - |
| 5 | 004-name | 002 | - |

## Parallel Opportunities
- 001 + 005 can run in parallel
- 002 + 003 can run after 001

## Current Status
- Pending: all
- In Progress: -
- Done: -
```

### 5. Summarize & Suggest Next

```
Created N tasks in <project>:
- 001-task-name
- 002-task-name
- ...

Execution plan: plans/execution-plan.md

Next:
- solve-task 001 — to start the first task
- run-plan — to execute all tasks in sequence
```

## Key Principles

- **Always use MCP tools** — never write task files directly
- **Check before creating** — duplicates waste everyone's time
- **One session per task** — if it takes more, it's too big
- **Dependencies matter** — always create the execution plan
- **YAGNI** — if the user didn't ask for it, don't add tasks for it
- **Extend, don't replace** — if tasks and plans already exist, build on them
- **Connect the flow** — reference where the user came from and where they can go next
