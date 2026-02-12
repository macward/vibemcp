"""DEPRECATED: Backwards compatibility layer for tools_write module-level functions.

These functions use the deprecated singleton pattern and will be removed in v2.0.
Use register_tools_write() with dependency injection instead.

Example migration:
    # Old (deprecated):
    from vibe_mcp.tools_write import create_task
    result = create_task("my-project", "Title", "Objective")

    # New (recommended):
    from vibe_mcp.config import Config
    from vibe_mcp.indexer import Indexer
    from vibe_mcp.webhooks import WebhookManager
    # ... create instances with DI in your server setup
"""

import re
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

from vibe_mcp.auth import check_write_permission
from vibe_mcp.config import get_config
from vibe_mcp.indexer import Indexer
from vibe_mcp.indexer.walker import FileInfo, compute_hash
from vibe_mcp.webhooks import WebhookManager, get_webhook_manager

# Track if deprecation warning has been shown to avoid spam
_deprecation_warned = False


def _get_deprecated_context():
    """Get config, indexer, and webhook_mgr using deprecated singletons."""
    global _deprecation_warned
    if not _deprecation_warned:
        warnings.warn(
            "Module-level write functions are deprecated and will be removed in v2.0. "
            "Use register_tools_write() with dependency injection instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        _deprecation_warned = True

    config = get_config()
    indexer = Indexer(config.vibe_root, config.vibe_db)
    indexer.initialize()
    try:
        webhook_mgr = get_webhook_manager()
    except Exception:
        webhook_mgr = None
    return config, indexer, webhook_mgr


def _validate_project_path(project: str, vibe_root: Path) -> Path:
    """Validate and resolve a project path."""
    if ".." in project or "/" in project or "\\" in project:
        raise ValueError(f"Invalid project name: {project}")

    project_path = (vibe_root / project).resolve()
    vibe_root_resolved = vibe_root.resolve()

    if not str(project_path).startswith(str(vibe_root_resolved) + "/"):
        raise ValueError(f"Project path outside vibe_root: {project}")

    return project_path


def _validate_file_path(project_path: Path, folder: str, filename: str) -> Path:
    """Validate and resolve a file path within a project."""
    if ".." in folder or ".." in filename:
        raise ValueError("Path traversal not allowed")

    if "/" in filename or "\\" in filename:
        raise ValueError("Filename cannot contain path separators")

    if not filename.endswith(".md"):
        filename = f"{filename}.md"

    if folder:
        file_path = (project_path / folder / filename).resolve()
    else:
        file_path = (project_path / filename).resolve()

    if not str(file_path).startswith(str(project_path) + "/"):
        raise ValueError(f"File path outside project: {file_path}")

    return file_path


def _reindex_file(file_path: Path, config, indexer: Indexer) -> None:
    """Reindex a single file after writing."""
    stat = file_path.stat()
    mtime = stat.st_mtime
    content = file_path.read_bytes()
    content_hash = compute_hash(content)

    relative_path = str(file_path.relative_to(config.vibe_root))
    parts = Path(relative_path).parts

    if len(parts) < 1:
        return

    project_name = parts[0]
    if len(parts) > 2:
        folder = parts[1]
    elif len(parts) == 2:
        folder = ""
    else:
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

    indexer._index_file(file_info)


def _fire_webhook(
    webhook_mgr: WebhookManager | None,
    event_type: str,
    project: str | None,
    data: dict[str, Any],
) -> None:
    """Fire a webhook event if webhooks are enabled."""
    if webhook_mgr is None:
        return
    try:
        webhook_mgr.fire_event(event_type, project, data)
    except Exception:
        pass  # Webhook errors should never break the main operation


def _get_next_task_number(project_path: Path) -> int:
    """Get the next task number for a project."""
    tasks_dir = project_path / "tasks"
    if not tasks_dir.exists():
        return 1

    pattern = re.compile(r"^(\d{3})-.*\.md$")
    max_num = 0

    for file_path in tasks_dir.glob("*.md"):
        match = pattern.match(file_path.name)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    return max_num + 1


def create_doc(project: str, folder: str, filename: str, content: str) -> dict:
    """DEPRECATED: Create a new document. Use register_tools_write() instead."""
    config, indexer, webhook_mgr = _get_deprecated_context()
    check_write_permission(config)

    project_path = _validate_project_path(project, config.vibe_root)
    file_path = _validate_file_path(project_path, folder, filename)

    if file_path.exists():
        raise ValueError(f"File already exists: {file_path.relative_to(config.vibe_root)}")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    _reindex_file(file_path, config, indexer)

    result = {
        "status": "created",
        "path": str(file_path.relative_to(config.vibe_root)),
        "absolute_path": str(file_path),
    }
    _fire_webhook(webhook_mgr, "doc.created", project, {
        "folder": folder, "filename": file_path.name, "path": result["path"]
    })
    return result


def update_doc(project: str, path: str, content: str) -> dict:
    """DEPRECATED: Update an existing document. Use register_tools_write() instead."""
    config, indexer, webhook_mgr = _get_deprecated_context()
    check_write_permission(config)

    project_path = _validate_project_path(project, config.vibe_root)
    if ".." in path:
        raise ValueError("Path traversal not allowed")

    file_path = (project_path / path).resolve()
    if not str(file_path).startswith(str(project_path) + "/"):
        raise ValueError(f"File path outside project: {path}")
    if not file_path.exists():
        raise ValueError(f"File not found: {path}")

    file_path.write_text(content, encoding="utf-8")
    _reindex_file(file_path, config, indexer)

    result = {
        "status": "updated",
        "path": str(file_path.relative_to(config.vibe_root)),
        "absolute_path": str(file_path),
    }
    _fire_webhook(webhook_mgr, "doc.updated", project, {
        "filename": file_path.name, "path": result["path"]
    })
    return result


def create_task(
    project: str,
    title: str,
    objective: str,
    steps: list[str] | None = None,
    feature: str | None = None,
) -> dict:
    """DEPRECATED: Create a new task. Use register_tools_write() instead."""
    config, indexer, webhook_mgr = _get_deprecated_context()
    check_write_permission(config)

    project_path = _validate_project_path(project, config.vibe_root)
    task_num = _get_next_task_number(project_path)

    safe_title = re.sub(r"[^\w\s-]", "", title.lower())
    safe_title = re.sub(r"[-\s]+", "-", safe_title).strip("-")
    filename = f"{task_num:03d}-{safe_title}.md"

    content_lines = []
    if feature:
        content_lines.extend([
            "---", "type: task", "status: pending", f"feature: {feature}", "---", ""
        ])
    content_lines.extend([f"# Task: {title}", ""])
    if not feature:
        content_lines.extend(["Status: pending", ""])
    content_lines.extend(["## Objective", objective, ""])
    if steps:
        content_lines.append("## Steps")
        for i, step in enumerate(steps, 1):
            content_lines.append(f"{i}. [ ] {step}")
        content_lines.append("")

    content = "\n".join(content_lines)
    tasks_dir = project_path / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    file_path = tasks_dir / filename

    if file_path.exists():
        raise ValueError(f"Task file already exists: {filename}")

    file_path.write_text(content, encoding="utf-8")
    _reindex_file(file_path, config, indexer)

    result = {
        "status": "created",
        "task_number": task_num,
        "filename": filename,
        "path": str(file_path.relative_to(config.vibe_root)),
        "absolute_path": str(file_path),
        "feature": feature,
    }
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


def update_task_status(project: str, task_file: str, new_status: str) -> dict:
    """DEPRECATED: Update task status. Use register_tools_write() instead."""
    config, indexer, webhook_mgr = _get_deprecated_context()
    check_write_permission(config)

    valid_statuses = {"pending", "in-progress", "done", "blocked"}
    if new_status not in valid_statuses:
        raise ValueError(
            f"Invalid status: {new_status}. Must be one of: {', '.join(valid_statuses)}"
        )

    project_path = _validate_project_path(project, config.vibe_root)
    file_path = (project_path / "tasks" / task_file).resolve()

    if not str(file_path).startswith(str(project_path) + "/"):
        raise ValueError(f"File path outside project: {task_file}")
    if not file_path.exists():
        raise ValueError(f"Task file not found: {task_file}")

    file_content = file_path.read_text(encoding="utf-8")
    updated_content = re.sub(
        r"^Status:.*$", f"Status: {new_status}", file_content, count=1, flags=re.MULTILINE
    )

    if updated_content == file_content:
        lines = file_content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("#"):
                lines.insert(i + 1, "")
                lines.insert(i + 2, f"Status: {new_status}")
                updated_content = "\n".join(lines)
                break

    file_path.write_text(updated_content, encoding="utf-8")
    _reindex_file(file_path, config, indexer)

    result = {
        "status": "updated",
        "new_status": new_status,
        "path": str(file_path.relative_to(config.vibe_root)),
        "absolute_path": str(file_path),
    }
    _fire_webhook(webhook_mgr, "task.updated", project, {
        "filename": task_file, "path": result["path"], "new_status": new_status
    })
    return result


def create_plan(project: str, content: str, filename: str = "execution-plan.md") -> dict:
    """DEPRECATED: Create or update a plan. Use register_tools_write() instead."""
    config, indexer, webhook_mgr = _get_deprecated_context()
    check_write_permission(config)

    project_path = _validate_project_path(project, config.vibe_root)
    if not filename.endswith(".md"):
        filename = f"{filename}.md"
    if "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError("Invalid filename: cannot contain path separators")

    plans_dir = project_path / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    file_path = plans_dir / filename
    action = "updated" if file_path.exists() else "created"

    file_path.write_text(content, encoding="utf-8")
    _reindex_file(file_path, config, indexer)

    result = {
        "status": action,
        "filename": filename,
        "path": str(file_path.relative_to(config.vibe_root)),
        "absolute_path": str(file_path),
    }
    event_type = "plan.created" if action == "created" else "plan.updated"
    _fire_webhook(webhook_mgr, event_type, project, {
        "filename": filename, "path": result["path"]
    })
    return result


def log_session(project: str, content: str) -> dict:
    """DEPRECATED: Log a session entry. Use register_tools_write() instead."""
    config, indexer, webhook_mgr = _get_deprecated_context()
    check_write_permission(config)

    project_path = _validate_project_path(project, config.vibe_root)
    sessions_dir = project_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    file_path = sessions_dir / f"{today}.md"

    if file_path.exists():
        action = "appended"
        existing_content = file_path.read_text(encoding="utf-8")
        timestamp = datetime.now().strftime("%H:%M:%S")
        new_content = f"{existing_content}\n\n---\n**{timestamp}**\n\n{content}\n"
    else:
        action = "created"
        new_content = f"# Session Log - {today}\n\n{content}\n"

    file_path.write_text(new_content, encoding="utf-8")
    _reindex_file(file_path, config, indexer)

    result = {
        "status": action,
        "date": today,
        "path": str(file_path.relative_to(config.vibe_root)),
        "absolute_path": str(file_path),
    }
    _fire_webhook(webhook_mgr, "session.logged", project, {
        "date": today, "path": result["path"], "action": action
    })
    return result


def reindex() -> dict:
    """DEPRECATED: Force a full reindex. Use register_tools_write() instead."""
    config, indexer, webhook_mgr = _get_deprecated_context()
    count = indexer.reindex()
    result = {"status": "reindexed", "document_count": count}
    _fire_webhook(webhook_mgr, "index.reindexed", None, {"document_count": count})
    return result


def init_project(project: str) -> dict:
    """DEPRECATED: Initialize a new project. Use register_tools_write() instead."""
    config, indexer, webhook_mgr = _get_deprecated_context()
    check_write_permission(config)

    project_path = _validate_project_path(project, config.vibe_root)
    if project_path.exists():
        raise ValueError(f"Project already exists: {project}")

    folders = [
        "tasks", "plans", "sessions", "reports",
        "changelog", "references", "scratch", "assets"
    ]
    for folder in folders:
        (project_path / folder).mkdir(parents=True, exist_ok=True)

    status_path = project_path / "status.md"
    status_path.write_text(f"# {project}\n\nStatus: setup\n", encoding="utf-8")
    _reindex_file(status_path, config, indexer)

    result = {
        "status": "initialized",
        "project": project,
        "path": str(project_path.relative_to(config.vibe_root)),
        "absolute_path": str(project_path),
        "folders": folders,
    }
    _fire_webhook(webhook_mgr, "project.initialized", project, {
        "project": project, "path": result["path"], "folders": folders
    })
    return result
