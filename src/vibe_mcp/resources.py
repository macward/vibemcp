"""MCP Resources for vibeMCP.

Resources expose the vibe workspace structure as read-only URIs.
"""

import os
from datetime import datetime
from pathlib import Path

from vibe_mcp.config import get_config
from vibe_mcp.indexer.database import Database


def _validate_path(base_path: Path, requested_path: Path) -> Path:
    """Validate that requested_path is within base_path (prevent directory traversal).

    Args:
        base_path: The base directory that contains all valid paths
        requested_path: The path to validate

    Returns:
        The resolved absolute path

    Raises:
        ValueError: If the path is outside base_path
    """
    # Resolve to absolute paths
    base_abs = base_path.resolve()
    requested_abs = requested_path.resolve()

    # Check if requested path is within base path
    try:
        requested_abs.relative_to(base_abs)
    except ValueError as e:
        raise ValueError(f"Path '{requested_path}' is outside allowed directory") from e

    return requested_abs


def _get_database() -> Database:
    """Get initialized database instance."""
    config = get_config()
    db = Database(config.vibe_db)
    db.initialize()
    return db


def _count_files_in_folder(project_path: Path, folder_name: str) -> int:
    """Count markdown files in a specific folder."""
    folder_path = project_path / folder_name
    if not folder_path.exists() or not folder_path.is_dir():
        return 0
    return len(list(folder_path.glob("*.md")))


def _get_last_session_date(project_path: Path) -> str | None:
    """Get the date of the most recent session file."""
    sessions_path = project_path / "sessions"
    if not sessions_path.exists() or not sessions_path.is_dir():
        return None

    session_files = list(sessions_path.glob("*.md"))
    if not session_files:
        return None

    # Find the most recent by mtime
    most_recent = max(session_files, key=lambda f: f.stat().st_mtime)
    mtime = most_recent.stat().st_mtime
    return datetime.fromtimestamp(mtime).isoformat()


def _count_open_tasks(project_path: Path) -> int:
    """Count tasks with status != 'done' in frontmatter or filename."""
    tasks_path = project_path / "tasks"
    if not tasks_path.exists() or not tasks_path.is_dir():
        return 0

    count = 0
    for task_file in tasks_path.glob("*.md"):
        # Quick heuristic: check first few lines for "Status:" field
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read(500)  # Read first 500 chars
                # Simple check - not parsing YAML, just looking for status line
                if "status: done" not in content.lower() and "status:done" not in content.lower():
                    count += 1
        except Exception:
            # If we can't read it, skip it
            continue

    return count


def get_projects_resource() -> str:
    """Resource: vibe://projects

    Lists all projects with metadata.
    """
    config = get_config()
    db = _get_database()

    projects = db.list_projects()

    result_lines = ["# Vibe Projects\n"]
    result_lines.append(f"Total projects: {len(projects)}\n")
    result_lines.append("\n")

    for project in projects:
        project_path = Path(project.path)

        # Get metadata
        last_updated = project.updated_at.isoformat() if project.updated_at else "unknown"
        open_tasks = _count_open_tasks(project_path)
        last_session = _get_last_session_date(project_path)

        # Count files by folder
        tasks_count = _count_files_in_folder(project_path, "tasks")
        plans_count = _count_files_in_folder(project_path, "plans")
        sessions_count = _count_files_in_folder(project_path, "sessions")
        reports_count = _count_files_in_folder(project_path, "reports")

        result_lines.append(f"## {project.name}\n")
        result_lines.append(f"- Path: `{project.path}`\n")
        result_lines.append(f"- Last updated: {last_updated}\n")
        result_lines.append(f"- Open tasks: {open_tasks}\n")
        if last_session:
            result_lines.append(f"- Last session: {last_session}\n")
        result_lines.append(f"- Files: tasks={tasks_count}, plans={plans_count}, sessions={sessions_count}, reports={reports_count}\n")
        result_lines.append("\n")

    db.close()
    return "".join(result_lines)


def get_project_detail_resource(name: str) -> str:
    """Resource: vibe://projects/{name}

    Shows detail of a specific project including folder structure and task status.
    """
    config = get_config()
    db = _get_database()

    project = db.get_project(name)
    if not project:
        db.close()
        raise ValueError(f"Project '{name}' not found")

    project_path = Path(project.path)
    if not project_path.exists():
        db.close()
        raise ValueError(f"Project path '{project.path}' does not exist")

    result_lines = [f"# Project: {project.name}\n\n"]
    result_lines.append(f"**Path:** `{project.path}`\n")
    result_lines.append(f"**Created:** {project.created_at.isoformat() if project.created_at else 'unknown'}\n")
    result_lines.append(f"**Updated:** {project.updated_at.isoformat() if project.updated_at else 'unknown'}\n\n")

    # List available folders
    result_lines.append("## Available Folders\n\n")
    standard_folders = ["tasks", "plans", "sessions", "reports", "changelog", "references", "scratch", "assets"]

    for folder_name in standard_folders:
        folder_path = project_path / folder_name
        if folder_path.exists() and folder_path.is_dir():
            file_count = len(list(folder_path.glob("*.md")))
            file_word = "file" if file_count == 1 else "files"
            result_lines.append(f"- `{folder_name}/` ({file_count} {file_word})\n")

    # Task status breakdown
    result_lines.append("\n## Task Status\n\n")
    tasks_path = project_path / "tasks"

    if tasks_path.exists() and tasks_path.is_dir():
        status_counts = {"pending": 0, "in-progress": 0, "blocked": 0, "done": 0, "unknown": 0}

        for task_file in tasks_path.glob("*.md"):
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    content = f.read(1000)
                    content_lower = content.lower()

                    if "status: done" in content_lower or "status:done" in content_lower:
                        status_counts["done"] += 1
                    elif "status: in-progress" in content_lower or "status:in-progress" in content_lower:
                        status_counts["in-progress"] += 1
                    elif "status: blocked" in content_lower or "status:blocked" in content_lower:
                        status_counts["blocked"] += 1
                    elif "status: pending" in content_lower or "status:pending" in content_lower:
                        status_counts["pending"] += 1
                    else:
                        status_counts["unknown"] += 1
            except Exception:
                status_counts["unknown"] += 1

        for status, count in status_counts.items():
            if count > 0:
                result_lines.append(f"- {status}: {count}\n")
    else:
        result_lines.append("No tasks folder found.\n")

    db.close()
    return "".join(result_lines)


def get_file_resource(name: str, folder: str, file: str) -> str:
    """Resource: vibe://projects/{name}/{folder}/{file}

    Reads a specific file from a project folder.
    """
    config = get_config()
    db = _get_database()

    # Get project
    project = db.get_project(name)
    if not project:
        db.close()
        raise ValueError(f"Project '{name}' not found")

    project_path = Path(project.path)
    if not project_path.exists():
        db.close()
        raise ValueError(f"Project path '{project.path}' does not exist")

    # Construct requested file path
    requested_file_path = project_path / folder / file

    # Validate path to prevent directory traversal
    try:
        validated_path = _validate_path(project_path, requested_file_path)
    except ValueError as e:
        db.close()
        raise ValueError(f"Invalid path: {e}")

    # Check if file exists
    if not validated_path.exists():
        db.close()
        raise ValueError(f"File not found: {folder}/{file}")

    if not validated_path.is_file():
        db.close()
        raise ValueError(f"Path is not a file: {folder}/{file}")

    # Read file content
    try:
        with open(validated_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        db.close()
        raise ValueError(f"Error reading file: {e}")

    db.close()

    # Return content with metadata header
    header = f"# {file}\n\n"
    header += f"**Project:** {name}\n"
    header += f"**Folder:** {folder}\n"

    # Use resolve() on both paths to handle symlinks like /var vs /private/var on macOS
    try:
        rel_path = validated_path.resolve().relative_to(config.vibe_root.resolve())
        header += f"**Path:** `{rel_path}`\n\n"
    except ValueError:
        # If relative_to fails, just use the absolute path
        header += f"**Path:** `{validated_path}`\n\n"

    header += "---\n\n"

    return header + content


def register_resources(mcp):
    """Register all resources with the FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.resource("vibe://projects")
    def list_projects():
        """List all vibe projects with metadata."""
        return get_projects_resource()

    @mcp.resource("vibe://projects/{name}")
    def project_detail(name: str):
        """Get detailed information about a specific project."""
        return get_project_detail_resource(name)

    @mcp.resource("vibe://projects/{name}/{folder}/{file}")
    def read_file(name: str, folder: str, file: str):
        """Read a specific file from a project folder."""
        return get_file_resource(name, folder, file)
