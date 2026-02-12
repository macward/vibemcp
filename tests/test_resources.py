"""Tests for MCP resources."""

import tempfile
import warnings
from pathlib import Path

import pytest

from vibe_mcp.config import Config, reset_config
from vibe_mcp.indexer.database import Database
from vibe_mcp.resources import (
    _count_files_in_folder,
    _count_open_tasks,
    _get_last_session_date,
    _validate_path,
    get_file_resource,
    get_project_detail_resource,
    get_projects_resource,
)


def _reset_config_silent():
    """Reset config singleton without triggering deprecation warning.

    This is needed because resources.py still uses get_config() internally,
    and we need to reset the cached config between tests to pick up different
    environment variables. Once resources.py is migrated to DI, this can be removed.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        reset_config()


@pytest.fixture
def vibe_root(monkeypatch):
    """Create a temporary vibe root with sample projects."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vibe_path = Path(tmpdir)
        db_path = vibe_path / "index.db"

        # Create a sample project structure
        project_path = vibe_path / "test-project"
        project_path.mkdir()

        # Create folders
        (project_path / "tasks").mkdir()
        (project_path / "plans").mkdir()
        (project_path / "sessions").mkdir()
        (project_path / "reports").mkdir()

        # Create some task files
        task1 = project_path / "tasks" / "001-task.md"
        task1.write_text("# Task 1\n\nStatus: pending\n\nSome content")

        task2 = project_path / "tasks" / "002-task.md"
        task2.write_text("# Task 2\n\nStatus: done\n\nCompleted task")

        # Create a session file
        session = project_path / "sessions" / "2026-02-09.md"
        session.write_text("# Session notes\n\nSome notes")

        # Set environment variables for Config.from_env() in tests
        monkeypatch.setenv("VIBE_ROOT", str(vibe_path))
        monkeypatch.setenv("VIBE_DB", str(db_path))

        # Reset config to pick up new env vars (needed because resources.py uses get_config())
        _reset_config_silent()

        # Initialize database and index the project
        db = Database(db_path)
        db.initialize()
        project_id = db.get_or_create_project("test-project", str(project_path))
        db.close()

        yield vibe_path

        _reset_config_silent()


class TestPathValidation:
    def test_valid_path(self):
        base = Path("/base/path")
        requested = Path("/base/path/subdir/file.txt")
        result = _validate_path(base, requested)
        assert result == requested.resolve()

    def test_invalid_path_traversal(self):
        base = Path("/base/path")
        requested = Path("/base/path/../../../etc/passwd")
        with pytest.raises(ValueError, match="outside allowed directory"):
            _validate_path(base, requested)

    def test_valid_relative_path(self):
        base = Path("/base/path")
        # This is a relative path that should resolve within base
        requested = Path("/base/path/./subdir/../file.txt")
        result = _validate_path(base, requested)
        assert result == Path("/base/path/file.txt")


class TestHelperFunctions:
    def test_count_files_in_folder(self, vibe_root):
        project_path = vibe_root / "test-project"
        assert _count_files_in_folder(project_path, "tasks") == 2
        assert _count_files_in_folder(project_path, "sessions") == 1
        assert _count_files_in_folder(project_path, "plans") == 0

    def test_count_files_nonexistent_folder(self, vibe_root):
        project_path = vibe_root / "test-project"
        assert _count_files_in_folder(project_path, "nonexistent") == 0

    def test_get_last_session_date(self, vibe_root):
        project_path = vibe_root / "test-project"
        last_session = _get_last_session_date(project_path)
        assert last_session is not None
        assert "2026-02-09" in last_session or last_session.startswith("2026-02")

    def test_get_last_session_no_sessions(self, vibe_root):
        project_path = vibe_root / "test-project"
        (project_path / "sessions" / "2026-02-09.md").unlink()
        last_session = _get_last_session_date(project_path)
        assert last_session is None

    def test_count_open_tasks(self, vibe_root):
        project_path = vibe_root / "test-project"
        count = _count_open_tasks(project_path)
        assert count == 1  # Only task 001 is pending


class TestProjectsResource:
    def test_get_projects_resource(self, vibe_root):
        result = get_projects_resource()

        assert "# Vibe Projects" in result
        assert "test-project" in result
        assert "Total projects: 1" in result
        assert "Open tasks: 1" in result
        assert "tasks=2" in result
        assert "sessions=1" in result

    def test_get_projects_resource_empty(self, monkeypatch):
        with tempfile.TemporaryDirectory() as tmpdir:
            vibe_path = Path(tmpdir)
            db_path = vibe_path / "index.db"
            monkeypatch.setenv("VIBE_ROOT", str(vibe_path))
            monkeypatch.setenv("VIBE_DB", str(db_path))

            _reset_config_silent()

            db = Database(db_path)
            db.initialize()
            db.close()

            result = get_projects_resource()
            assert "Total projects: 0" in result

            _reset_config_silent()


class TestProjectDetailResource:
    def test_get_project_detail(self, vibe_root):
        result = get_project_detail_resource("test-project")

        assert "# Project: test-project" in result
        assert "Available Folders" in result
        assert "`tasks/` (2 files)" in result
        assert "`sessions/` (1 file)" in result
        assert "Task Status" in result
        assert "pending: 1" in result
        assert "done: 1" in result

    def test_get_project_detail_not_found(self, vibe_root):
        with pytest.raises(ValueError, match="Project 'nonexistent' not found"):
            get_project_detail_resource("nonexistent")


class TestFileResource:
    def test_get_file_resource(self, vibe_root):
        result = get_file_resource("test-project", "tasks", "001-task.md")

        assert "# 001-task.md" in result
        assert "**Project:** test-project" in result
        assert "**Folder:** tasks" in result
        assert "Status: pending" in result
        assert "Some content" in result

    def test_get_file_resource_not_found(self, vibe_root):
        with pytest.raises(ValueError, match="File not found"):
            get_file_resource("test-project", "tasks", "nonexistent.md")

    def test_get_file_resource_project_not_found(self, vibe_root):
        with pytest.raises(ValueError, match="Project 'nonexistent' not found"):
            get_file_resource("nonexistent", "tasks", "001-task.md")

    def test_get_file_resource_path_traversal(self, vibe_root):
        with pytest.raises(ValueError, match="Invalid path"):
            get_file_resource("test-project", "..", "../../etc/passwd")

    def test_get_file_resource_directory(self, vibe_root):
        with pytest.raises(ValueError, match="Path is not a file"):
            get_file_resource("test-project", "tasks", ".")
