"""MCP prompts for vibemcp.

Prompts are templates that help AI agents understand project context.
They combine information from multiple sources (status, tasks, sessions)
to provide a coherent view of the project state.
"""

from pathlib import Path

from fastmcp import FastMCP

from vibe_mcp.config import get_config
from vibe_mcp.indexer.database import Database


def register_prompts(mcp: FastMCP) -> None:
    """Register all prompts with the FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.prompt()
    def project_briefing(project: str) -> str:
        """Get a concise briefing of a project's current state.

        Args:
            project: Name of the project to brief

        Returns:
            A structured summary including status, active tasks, and recent sessions.
        """
        config = get_config()
        db = Database(config.vibe_db)

        # Check if project exists
        project_obj = db.get_project(project)
        if not project_obj:
            return (
                f"# Project Briefing: {project}\n\n"
                f"⚠️  Project '{project}' not found in index.\n\n"
                f"The project may not exist or hasn't been indexed yet."
            )

        project_path = Path(config.vibe_root) / project
        briefing_parts = [f"# Project Briefing: {project}\n"]

        # 1. Read status.md if it exists
        status_file = project_path / "status.md"
        if status_file.exists():
            try:
                status_content = status_file.read_text().strip()
                briefing_parts.append("## Current Status\n")
                briefing_parts.append(status_content)
                briefing_parts.append("\n")
            except Exception:
                briefing_parts.append(
                    "## Current Status\n\n_Status file exists but could not be read_\n\n"
                )
        else:
            briefing_parts.append("## Current Status\n\n_No status file found_\n\n")

        # 2. Get active tasks (in-progress and pending)
        active_tasks = db.list_documents(
            project_name=project,
            folder="tasks",
        )

        # Filter for active statuses
        in_progress = [t for t in active_tasks if t.status == "in-progress"]
        pending = [t for t in active_tasks if t.status == "pending"]
        blocked = [t for t in active_tasks if t.status == "blocked"]

        briefing_parts.append("## Active Tasks\n\n")
        if in_progress or pending or blocked:
            for task in in_progress:
                task_file = project_path / task.path
                try:
                    content = task_file.read_text()
                    # Extract objective (first line after "## Objective")
                    objective = _extract_section(content, "## Objective")
                    briefing_parts.append(
                        f"- **[in-progress]** {task.filename}: {objective}\n"
                    )
                except Exception:
                    briefing_parts.append(
                        f"- **[in-progress]** {task.filename}: _(could not read)_\n"
                    )

            for task in blocked:
                task_file = project_path / task.path
                try:
                    content = task_file.read_text()
                    objective = _extract_section(content, "## Objective")
                    briefing_parts.append(
                        f"- **[blocked]** {task.filename}: {objective}\n"
                    )
                except Exception:
                    briefing_parts.append(
                        f"- **[blocked]** {task.filename}: _(could not read)_\n"
                    )

            for task in pending:
                task_file = project_path / task.path
                try:
                    content = task_file.read_text()
                    objective = _extract_section(content, "## Objective")
                    briefing_parts.append(
                        f"- **[pending]** {task.filename}: {objective}\n"
                    )
                except Exception:
                    briefing_parts.append(
                        f"- **[pending]** {task.filename}: _(could not read)_\n"
                    )

            briefing_parts.append("\n")
        else:
            briefing_parts.append("_No active tasks_\n\n")

        # 3. Get recent sessions (last 2-3)
        sessions = db.list_documents(project_name=project, folder="sessions")
        # Sort by filename (which are dates like 2025-02-09.md) in descending order
        sessions_sorted = sorted(sessions, key=lambda s: s.filename, reverse=True)
        recent_sessions = sessions_sorted[:3]

        briefing_parts.append("## Recent Sessions\n\n")
        if recent_sessions:
            for session in recent_sessions:
                session_file = project_path / session.path
                try:
                    content = session_file.read_text()
                    # Get the date from filename
                    date = session.filename.replace(".md", "")
                    briefing_parts.append(f"### {date}\n\n")

                    # Extract key sections
                    done = _extract_section(content, "## Lo que hice")
                    blocked_by = _extract_section(content, "## Bloqueado por")
                    next_steps = _extract_section(content, "## Próximo")

                    if done:
                        briefing_parts.append(f"**Done:** {done}\n\n")
                    if blocked_by:
                        briefing_parts.append(f"**Blocked by:** {blocked_by}\n\n")
                    if next_steps:
                        briefing_parts.append(f"**Next:** {next_steps}\n\n")
                except Exception:
                    briefing_parts.append(f"_{session.filename}: could not read_\n\n")
        else:
            briefing_parts.append("_No recent sessions_\n\n")

        return "".join(briefing_parts)

    @mcp.prompt()
    def session_start(project: str) -> str:
        """Get complete context to start working on a project.

        Args:
            project: Name of the project to start session for

        Returns:
            A comprehensive context including status, execution plan,
            active tasks, blockers, and next steps.
        """
        config = get_config()
        db = Database(config.vibe_db)

        # Check if project exists
        project_obj = db.get_project(project)
        if not project_obj:
            return (
                f"# Session Start: {project}\n\n"
                f"⚠️  Project '{project}' not found in index.\n\n"
                f"The project may not exist or hasn't been indexed yet."
            )

        project_path = Path(config.vibe_root) / project
        context_parts = [f"# Session Start: {project}\n\n"]

        # 1. Read status.md
        status_file = project_path / "status.md"
        if status_file.exists():
            try:
                status_content = status_file.read_text().strip()
                context_parts.append("## Current Status\n\n")
                context_parts.append(status_content)
                context_parts.append("\n\n")
            except Exception:
                context_parts.append(
                    "## Current Status\n\n_Status file exists but could not be read_\n\n"
                )
        else:
            context_parts.append("## Current Status\n\n_No status file found_\n\n")

        # 2. Read execution plan if it exists
        plan_file = project_path / "plans" / "execution-plan.md"
        if plan_file.exists():
            try:
                plan_content = plan_file.read_text().strip()
                context_parts.append("## Execution Plan\n\n")
                context_parts.append(plan_content)
                context_parts.append("\n\n")
            except Exception:
                context_parts.append(
                    "## Execution Plan\n\n_Plan file exists but could not be read_\n\n"
                )

        # 3. Get all tasks organized by status
        all_tasks = db.list_documents(project_name=project, folder="tasks")

        in_progress = [t for t in all_tasks if t.status == "in-progress"]
        blocked = [t for t in all_tasks if t.status == "blocked"]
        pending = [t for t in all_tasks if t.status == "pending"]

        # In-progress tasks
        context_parts.append("## In-Progress Tasks\n\n")
        if in_progress:
            for task in in_progress:
                task_file = project_path / task.path
                try:
                    content = task_file.read_text()
                    context_parts.append(f"### {task.filename}\n\n")
                    context_parts.append(content)
                    context_parts.append("\n\n")
                except Exception:
                    context_parts.append(
                        f"### {task.filename}\n\n_Could not read task_\n\n"
                    )
        else:
            context_parts.append("_No tasks in progress_\n\n")

        # Blocked tasks (critical!)
        context_parts.append("## Blocked Tasks\n\n")
        if blocked:
            for task in blocked:
                task_file = project_path / task.path
                try:
                    content = task_file.read_text()
                    context_parts.append(f"### {task.filename}\n\n")
                    context_parts.append(content)
                    context_parts.append("\n\n")
                except Exception:
                    context_parts.append(
                        f"### {task.filename}\n\n_Could not read task_\n\n"
                    )
        else:
            context_parts.append("_No blocked tasks_\n\n")

        # Pending tasks (next up)
        context_parts.append("## Pending Tasks\n\n")
        if pending:
            for task in pending[:5]:  # Show first 5 pending tasks
                task_file = project_path / task.path
                try:
                    content = task_file.read_text()
                    objective = _extract_section(content, "## Objective")
                    context_parts.append(
                        f"- **{task.filename}**: {objective or '_No objective found_'}\n"
                    )
                except Exception:
                    context_parts.append(f"- **{task.filename}**: _Could not read_\n")

            if len(pending) > 5:
                context_parts.append(f"\n_...and {len(pending) - 5} more pending tasks_")

            context_parts.append("\n\n")
        else:
            context_parts.append("_No pending tasks_\n\n")

        # 4. Most recent session for continuity
        sessions = db.list_documents(project_name=project, folder="sessions")
        if sessions:
            sessions_sorted = sorted(sessions, key=lambda s: s.filename, reverse=True)
            latest_session = sessions_sorted[0]
            session_file = project_path / latest_session.path
            try:
                content = session_file.read_text()
                date = latest_session.filename.replace(".md", "")
                context_parts.append(f"## Latest Session ({date})\n\n")
                context_parts.append(content)
                context_parts.append("\n\n")
            except Exception:
                context_parts.append(
                    "## Latest Session\n\n_Could not read latest session_\n\n"
                )

        context_parts.append("---\n\n")
        context_parts.append("**Ready to work!** The context above should help you ")
        context_parts.append(
            "understand where the project is and what needs to be done next.\n"
        )

        return "".join(context_parts)


def _extract_section(content: str, heading: str) -> str:
    """Extract content under a specific heading.

    Args:
        content: Full markdown content
        heading: Heading to look for (e.g., "## Objective")

    Returns:
        Content under the heading until the next heading or end of file.
        Returns empty string if heading not found.
    """
    lines = content.split("\n")
    result = []
    in_section = False

    for line in lines:
        if line.strip() == heading:
            in_section = True
            continue

        if in_section:
            # Stop at next heading of same or higher level
            if line.startswith("#"):
                break
            result.append(line)

    # Join and clean up
    text = "\n".join(result).strip()
    # Collapse multiple newlines to at most 2
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")

    return text
