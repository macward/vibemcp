"""Write tools for vibeMCP - create and update documents in the vibe workspace."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vibe_mcp.auth import check_write_permission
from vibe_mcp.config import Config
from vibe_mcp.indexer import Indexer
from vibe_mcp.indexer.walker import FileInfo, compute_hash
from vibe_mcp.webhooks import WebhookManager

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def _validate_project_path(project: str, vibe_root: Path) -> Path:
    """
    Validate and resolve a project path.

    Args:
        project: Project name
        vibe_root: VIBE_ROOT path

    Returns:
        Resolved project path

    Raises:
        ValueError: If path is invalid or outside vibe_root
    """
    # Prevent directory traversal
    if ".." in project or "/" in project or "\\" in project:
        raise ValueError(f"Invalid project name: {project}")

    project_path = (vibe_root / project).resolve()
    vibe_root_resolved = vibe_root.resolve()

    # Ensure path is within vibe_root
    if not str(project_path).startswith(str(vibe_root_resolved) + "/"):
        raise ValueError(f"Project path outside vibe_root: {project}")

    return project_path


def _validate_file_path(project_path: Path, folder: str, filename: str) -> Path:
    """
    Validate and resolve a file path within a project.

    Args:
        project_path: Resolved project path
        folder: Folder name (e.g., "tasks", "plans")
        filename: File name

    Returns:
        Resolved file path

    Raises:
        ValueError: If path is invalid or outside project
    """
    # Prevent directory traversal
    if ".." in folder or ".." in filename:
        raise ValueError("Path traversal not allowed")

    if "/" in filename or "\\" in filename:
        raise ValueError("Filename cannot contain path separators")

    # Ensure filename ends with .md
    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    # Build path
    if folder:
        file_path = (project_path / folder / filename).resolve()
    else:
        file_path = (project_path / filename).resolve()

    # Ensure path is within project
    if not str(file_path).startswith(str(project_path) + "/"):
        raise ValueError(f"File path outside project: {file_path}")

    return file_path


def _reindex_file(file_path: Path, config: Config, indexer: Indexer) -> None:
    """
    Reindex a single file after writing.

    Args:
        file_path: Absolute path to the file
        config: Config instance
        indexer: Indexer instance
    """
    # Create FileInfo for the file
    stat = file_path.stat()
    mtime = stat.st_mtime
    content = file_path.read_bytes()
    content_hash = compute_hash(content)

    relative_path = str(file_path.relative_to(config.vibe_root))

    # Parse path to get project_name and folder
    parts = Path(relative_path).parts
    if len(parts) < 1:
        logger.warning("Invalid file path: %s", relative_path)
        return

    project_name = parts[0]
    if len(parts) > 2:
        folder = parts[1]
    elif len(parts) == 2:
        folder = ""
    else:
        logger.warning("Invalid file path structure: %s", relative_path)
        return

    file_info = FileInfo(
        path=file_path,
        relative_path=relative_path,
        project_name=project_name,
        folder=folder,
        filename=file_path.name,
        mtime=mtime,
        content_hash=content_hash,
    )

    # Index the file
    indexer._index_file(file_info)
    logger.info("Reindexed file: %s", relative_path)


def _fire_webhook(
    webhook_mgr: WebhookManager | None,
    event_type: str,
    project: str | None,
    data: dict[str, Any],
) -> None:
    """Fire a webhook event if webhooks are enabled.

    Args:
        webhook_mgr: WebhookManager instance (can be None if webhooks disabled)
        event_type: Event type (e.g., "task.created")
        project: Project name (None for global events like reindex)
        data: Event data
    """
    if webhook_mgr is None:
        return
    try:
        webhook_mgr.fire_event(event_type, project, data)
    except Exception:
        # Webhook errors should never break the main operation
        logger.exception("Failed to fire webhook event %s", event_type)


def _get_next_task_number(project_path: Path) -> int:
    """
    Get the next task number for a project.

    Args:
        project_path: Path to the project directory

    Returns:
        Next task number (e.g., 1, 2, 3...)
    """
    tasks_dir = project_path / "tasks"
    if not tasks_dir.exists():
        return 1

    # Find all task files matching pattern NNN-*.md
    pattern = re.compile(r"^(\d{3})-.*\.md$")
    max_num = 0

    for file_path in tasks_dir.glob("*.md"):
        match = pattern.match(file_path.name)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    return max_num + 1


def register_tools_write(
    mcp: "FastMCP",
    config: Config,
    indexer: Indexer,
    webhook_mgr: WebhookManager | None = None,
) -> None:
    """Register all write tools with the FastMCP server.

    Args:
        mcp: FastMCP server instance
        config: Config instance for path resolution
        indexer: Indexer instance for reindexing after writes
        webhook_mgr: Optional WebhookManager for event notifications
    """

    @mcp.tool()
    def tool_create_task(
        project: str,
        title: str,
        objective: str,
        steps: list[str] | None = None,
        feature: str | None = None,
    ) -> dict:
        """Create a new task with auto-generated number and standard format.

        Args:
            project: Project name
            title: Task title
            objective: Task objective
            steps: Optional list of steps
            feature: Optional feature tag for grouping related tasks

        Returns:
            Dict with status, task number, and file path
        """
        check_write_permission(config)

        # Validate project path
        project_path = _validate_project_path(project, config.vibe_root)

        # Get next task number
        task_num = _get_next_task_number(project_path)

        # Create filename from task number and title
        # Sanitize title for filename
        safe_title = re.sub(r"[^\w\s-]", "", title.lower())
        safe_title = re.sub(r"[-\s]+", "-", safe_title).strip("-")
        filename = f"{task_num:03d}-{safe_title}.md"

        # Build content with optional frontmatter
        content_lines = []

        # Add frontmatter if feature is specified
        if feature:
            content_lines.extend([
                "---",
                "type: task",
                "status: pending",
                f"feature: {feature}",
                "---",
                "",
            ])

        content_lines.extend([
            f"# Task: {title}",
            "",
        ])

        # Only add status line if no frontmatter (to avoid duplication)
        if not feature:
            content_lines.extend([
                "Status: pending",
                "",
            ])

        content_lines.extend([
            "## Objective",
            objective,
            "",
        ])

        if steps:
            content_lines.append("## Steps")
            for i, step in enumerate(steps, 1):
                content_lines.append(f"{i}. [ ] {step}")
            content_lines.append("")

        content = "\n".join(content_lines)

        # Create file
        tasks_dir = project_path / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        file_path = tasks_dir / filename

        # Check if file already exists (shouldn't happen, but be safe)
        if file_path.exists():
            raise ValueError(f"Task file already exists: {filename}")

        file_path.write_text(content, encoding="utf-8")
        logger.info("Created task: %s", file_path.relative_to(config.vibe_root))

        # Reindex
        _reindex_file(file_path, config, indexer)

        result = {
            "status": "created",
            "task_number": task_num,
            "filename": filename,
            "path": str(file_path.relative_to(config.vibe_root)),
            "absolute_path": str(file_path),
            "feature": feature,
        }

        # Fire webhook
        webhook_data = {
            "task_number": task_num,
            "title": title,
            "filename": filename,
            "path": result["path"],
            "status": "pending",
        }
        if feature:
            webhook_data["feature"] = feature

        _fire_webhook(webhook_mgr, "task.created", project, webhook_data)

        return result

    @mcp.tool()
    def tool_log_session(project: str, content: str) -> dict:
        """Create or append to a session log for today.

        Args:
            project: Project name
            content: Session content to log

        Returns:
            Dict with status and file path
        """
        check_write_permission(config)

        # Validate project path
        project_path = _validate_project_path(project, config.vibe_root)

        # Create sessions directory if needed
        sessions_dir = project_path / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)

        # Session file is YYYY-MM-DD.md
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = sessions_dir / f"{today}.md"

        # Determine if creating or appending
        if file_path.exists():
            action = "appended"
            # Read existing content
            existing_content = file_path.read_text(encoding="utf-8")

            # Append with timestamp separator
            timestamp = datetime.now().strftime("%H:%M:%S")
            new_content = f"{existing_content}\n\n---\n**{timestamp}**\n\n{content}\n"
        else:
            action = "created"
            # Create new session log with header
            new_content = f"# Session Log - {today}\n\n{content}\n"

        # Write content
        file_path.write_text(new_content, encoding="utf-8")
        logger.info(
            "%s session log: %s", action.capitalize(), file_path.relative_to(config.vibe_root)
        )

        # Reindex
        _reindex_file(file_path, config, indexer)

        result = {
            "status": action,
            "date": today,
            "path": str(file_path.relative_to(config.vibe_root)),
            "absolute_path": str(file_path),
        }

        # Fire webhook
        _fire_webhook(
            webhook_mgr,
            "session.logged",
            project,
            {
                "date": today,
                "path": result["path"],
                "action": action,
            },
        )

        return result

    @mcp.tool()
    def tool_update_task_status(project: str, task_file: str, new_status: str) -> dict:
        """Update the status of a task.

        Args:
            project: Project name
            task_file: Task filename (e.g., "001-example.md")
            new_status: New status (pending, in-progress, done, blocked)

        Returns:
            Dict with status and file path
        """
        check_write_permission(config)
        valid_statuses = {"pending", "in-progress", "done", "blocked"}
        if new_status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {new_status}. Must be one of: {', '.join(valid_statuses)}"
            )

        # Validate project path
        project_path = _validate_project_path(project, config.vibe_root)

        # Build file path
        file_path = (project_path / "tasks" / task_file).resolve()

        # Ensure path is within project
        if not str(file_path).startswith(str(project_path) + "/"):
            raise ValueError(f"File path outside project: {task_file}")

        # Check if file exists
        if not file_path.exists():
            raise ValueError(f"Task file not found: {task_file}")

        # Read current content
        file_content = file_path.read_text(encoding="utf-8")

        # Update status line
        # Match "Status: <anything until end of line>" to support statuses with hyphens
        updated_content = re.sub(
            r"^Status:.*$",
            f"Status: {new_status}",
            file_content,
            count=1,
            flags=re.MULTILINE,
        )

        # If no status line was found, add it after the title
        if updated_content == file_content:
            lines = file_content.split("\n")
            # Find the title line (starts with #)
            for i, line in enumerate(lines):
                if line.startswith("#"):
                    # Insert status after title and empty line
                    lines.insert(i + 1, "")
                    lines.insert(i + 2, f"Status: {new_status}")
                    updated_content = "\n".join(lines)
                    break

        # Write updated content
        file_path.write_text(updated_content, encoding="utf-8")
        logger.info(
            "Updated task status to '%s': %s",
            new_status,
            file_path.relative_to(config.vibe_root),
        )

        # Reindex
        _reindex_file(file_path, config, indexer)

        result = {
            "status": "updated",
            "new_status": new_status,
            "path": str(file_path.relative_to(config.vibe_root)),
            "absolute_path": str(file_path),
        }

        # Fire webhook
        _fire_webhook(
            webhook_mgr,
            "task.updated",
            project,
            {
                "filename": task_file,
                "path": result["path"],
                "new_status": new_status,
            },
        )

        return result

    @mcp.tool()
    def tool_create_doc(project: str, folder: str, filename: str, content: str) -> dict:
        """Create a new document in a project folder.

        Args:
            project: Project name
            folder: Folder name (e.g., "tasks", "plans", "sessions")
            filename: File name (will add .md if not present)
            content: Document content

        Returns:
            Dict with status and file path
        """
        check_write_permission(config)

        # Validate project path
        project_path = _validate_project_path(project, config.vibe_root)

        # Validate file path
        file_path = _validate_file_path(project_path, folder, filename)

        # Check if file already exists
        if file_path.exists():
            raise ValueError(f"File already exists: {file_path.relative_to(config.vibe_root)}")

        # Create parent directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        file_path.write_text(content, encoding="utf-8")
        logger.info("Created document: %s", file_path.relative_to(config.vibe_root))

        # Reindex
        _reindex_file(file_path, config, indexer)

        result = {
            "status": "created",
            "path": str(file_path.relative_to(config.vibe_root)),
            "absolute_path": str(file_path),
        }

        # Fire webhook
        _fire_webhook(
            webhook_mgr,
            "doc.created",
            project,
            {
                "folder": folder,
                "filename": file_path.name,
                "path": result["path"],
            },
        )

        return result

    @mcp.tool()
    def tool_reindex() -> dict:
        """Force a full reindex of all projects.

        Returns:
            Dict with status and document count
        """
        check_write_permission(config)
        count = indexer.reindex()

        logger.info("Full reindex complete: %d documents indexed", count)

        result = {
            "status": "reindexed",
            "document_count": count,
        }

        # Fire webhook (use None for global/cross-project events)
        _fire_webhook(
            webhook_mgr,
            "index.reindexed",
            None,
            {
                "document_count": count,
            },
        )

        return result

    @mcp.tool()
    def tool_init_project(project: str) -> dict:
        """Initialize a new project with standard directory structure.

        Creates <VIBE_ROOT>/<project>/ with folders:
        tasks, plans, sessions, reports, changelog, references, scratch, assets

        Args:
            project: Project name (no slashes, no ..)

        Returns:
            Dict with status, project name, and paths
        """
        check_write_permission(config)

        # Validate project name (prevents directory traversal)
        project_path = _validate_project_path(project, config.vibe_root)

        # Check if project already exists
        if project_path.exists():
            raise ValueError(f"Project already exists: {project}")

        # Standard folder structure
        folders = [
            "tasks",
            "plans",
            "sessions",
            "reports",
            "changelog",
            "references",
            "scratch",
            "assets",
        ]

        # Create project directory and all standard folders
        for folder in folders:
            (project_path / folder).mkdir(parents=True, exist_ok=True)

        # Create initial status.md
        status_path = project_path / "status.md"
        status_content = f"# {project}\n\nStatus: setup\n"
        status_path.write_text(status_content, encoding="utf-8")

        # Reindex the status file
        _reindex_file(status_path, config, indexer)

        logger.info("Initialized project: %s", project)

        result = {
            "status": "initialized",
            "project": project,
            "path": str(project_path.relative_to(config.vibe_root)),
            "absolute_path": str(project_path),
            "folders": folders,
        }

        # Fire webhook
        _fire_webhook(
            webhook_mgr,
            "project.initialized",
            project,
            {
                "project": project,
                "path": result["path"],
                "folders": folders,
            },
        )

        return result

    @mcp.tool()
    def tool_create_plan(
        project: str,
        content: str,
        filename: str = "execution-plan.md",
    ) -> dict:
        """Create or update a plan file for a project.

        Args:
            project: Project name
            content: Plan content
            filename: Plan filename (default: "execution-plan.md"). Use "feature-<name>.md"
                      for feature-specific plans.

        Returns:
            Dict with status and file path
        """
        check_write_permission(config)

        # Validate project path
        project_path = _validate_project_path(project, config.vibe_root)

        # Ensure filename ends with .md
        if not filename.endswith(".md"):
            filename = f"{filename}.md"

        # Prevent directory traversal in filename
        if "/" in filename or "\\" in filename or ".." in filename:
            raise ValueError("Invalid filename: cannot contain path separators")

        # Create plans directory if needed
        plans_dir = project_path / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)

        file_path = plans_dir / filename

        # Determine if creating or updating
        action = "updated" if file_path.exists() else "created"

        # Write content
        file_path.write_text(content, encoding="utf-8")
        logger.info("%s plan: %s", action.capitalize(), file_path.relative_to(config.vibe_root))

        # Reindex
        _reindex_file(file_path, config, indexer)

        result = {
            "status": action,
            "filename": filename,
            "path": str(file_path.relative_to(config.vibe_root)),
            "absolute_path": str(file_path),
        }

        # Fire webhook
        event_type = "plan.created" if action == "created" else "plan.updated"
        _fire_webhook(
            webhook_mgr,
            event_type,
            project,
            {
                "filename": filename,
                "path": result["path"],
            },
        )

        return result
