"""Tests for write tools."""

import re
from datetime import datetime
from pathlib import Path

import pytest
from fastmcp import FastMCP

from vibe_mcp.config import Config
from vibe_mcp.indexer import Indexer
from vibe_mcp.tools_write import register_tools_write


@pytest.fixture
def vibe_root_and_tools(tmp_path, monkeypatch):
    """Create a temporary vibe root with tools registered for testing."""
    vibe_root = tmp_path / ".vibe"
    vibe_root.mkdir()
    db_path = vibe_root / "test.db"

    # Create a test project
    test_project = vibe_root / "test_project"
    test_project.mkdir()

    # Set environment variables
    monkeypatch.setenv("VIBE_ROOT", str(vibe_root))
    monkeypatch.setenv("VIBE_DB", str(db_path))

    # Create config and indexer
    config = Config.from_env()
    indexer = Indexer(config.vibe_root, config.vibe_db)
    indexer.initialize()

    # Register tools with FastMCP
    mcp = FastMCP()
    register_tools_write(mcp, config, indexer, webhook_mgr=None)

    # Extract tool functions
    tools = {}
    for tool in mcp._tool_manager._tools.values():
        tools[tool.fn.__name__] = tool.fn

    yield vibe_root, tools

    indexer.close()


class TestCreateDoc:
    """Tests for tool_create_doc function."""

    def test_create_doc_in_folder(self, vibe_root_and_tools):
        """Test creating a document in a folder."""
        vibe_root, tools = vibe_root_and_tools
        create_doc = tools["tool_create_doc"]

        result = create_doc(
            project="test_project",
            folder="references",
            filename="test-doc",
            content="# Test Document\n\nThis is a test.",
        )

        assert result["status"] == "created"
        assert result["path"] == "test_project/references/test-doc.md"

        file_path = vibe_root / "test_project" / "references" / "test-doc.md"
        assert file_path.exists()
        assert file_path.read_text() == "# Test Document\n\nThis is a test."

    def test_create_doc_in_root(self, vibe_root_and_tools):
        """Test creating a document in project root."""
        vibe_root, tools = vibe_root_and_tools
        create_doc = tools["tool_create_doc"]

        result = create_doc(
            project="test_project",
            folder="",
            filename="status.md",
            content="# Status\n\nAll good.",
        )

        assert result["status"] == "created"
        assert result["path"] == "test_project/status.md"

        file_path = vibe_root / "test_project" / "status.md"
        assert file_path.exists()

    def test_create_doc_auto_adds_md_extension(self, vibe_root_and_tools):
        """Test that .md extension is added if missing."""
        vibe_root, tools = vibe_root_and_tools
        create_doc = tools["tool_create_doc"]

        result = create_doc(
            project="test_project",
            folder="scratch",
            filename="notes",
            content="# Notes",
        )

        assert result["path"] == "test_project/scratch/notes.md"

    def test_create_doc_fails_if_exists(self, vibe_root_and_tools):
        """Test that creating an existing file raises an error."""
        vibe_root, tools = vibe_root_and_tools
        create_doc = tools["tool_create_doc"]

        # Create first time
        create_doc(
            project="test_project",
            folder="scratch",
            filename="test.md",
            content="# Test",
        )

        # Try to create again
        with pytest.raises(ValueError, match="already exists"):
            create_doc(
                project="test_project",
                folder="scratch",
                filename="test.md",
                content="# Test 2",
            )

    def test_create_doc_prevents_directory_traversal(self, vibe_root_and_tools):
        """Test that directory traversal is prevented."""
        vibe_root, tools = vibe_root_and_tools
        create_doc = tools["tool_create_doc"]

        with pytest.raises(ValueError, match="Invalid project name"):
            create_doc(
                project="../evil",
                folder="tasks",
                filename="hack.md",
                content="# Evil",
            )

        with pytest.raises(ValueError, match="Path traversal"):
            create_doc(
                project="test_project",
                folder="../evil",
                filename="hack.md",
                content="# Evil",
            )

        with pytest.raises(ValueError, match="Path traversal"):
            create_doc(
                project="test_project",
                folder="tasks",
                filename="../hack.md",
                content="# Evil",
            )


class TestCreateTask:
    """Tests for tool_create_task function."""

    def test_create_first_task(self, vibe_root_and_tools):
        """Test creating the first task in a project."""
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]

        result = create_task(
            project="test_project",
            title="Implement Feature X",
            objective="Build the amazing feature X",
            steps=["Design API", "Write tests", "Implement code"],
        )

        assert result["status"] == "created"
        assert result["task_number"] == 1
        assert result["filename"] == "001-implement-feature-x.md"
        assert result["path"] == "test_project/tasks/001-implement-feature-x.md"

        file_path = vibe_root / "test_project" / "tasks" / "001-implement-feature-x.md"
        assert file_path.exists()

        content = file_path.read_text()
        assert "# Task: Implement Feature X" in content
        assert "Status: pending" in content
        assert "## Objective" in content
        assert "Build the amazing feature X" in content
        assert "## Steps" in content
        assert "1. [ ] Design API" in content
        assert "2. [ ] Write tests" in content
        assert "3. [ ] Implement code" in content

    def test_create_task_auto_increments(self, vibe_root_and_tools):
        """Test that task numbers auto-increment."""
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]

        # Create first task
        result1 = create_task(
            project="test_project",
            title="Task One",
            objective="First task",
        )
        assert result1["task_number"] == 1

        # Create second task
        result2 = create_task(
            project="test_project",
            title="Task Two",
            objective="Second task",
        )
        assert result2["task_number"] == 2
        assert result2["filename"] == "002-task-two.md"

    def test_create_task_without_steps(self, vibe_root_and_tools):
        """Test creating a task without steps."""
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]

        create_task(
            project="test_project",
            title="Simple Task",
            objective="Just do it",
        )

        file_path = vibe_root / "test_project" / "tasks" / "001-simple-task.md"
        content = file_path.read_text()
        assert "## Steps" not in content

    def test_create_task_sanitizes_title(self, vibe_root_and_tools):
        """Test that task title is sanitized for filename."""
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]

        result = create_task(
            project="test_project",
            title="Fix Bug #123 (Critical!)",
            objective="Fix the critical bug",
        )

        assert result["filename"] == "001-fix-bug-123-critical.md"


class TestUpdateTaskStatus:
    """Tests for tool_update_task_status function."""

    def test_update_task_status(self, vibe_root_and_tools):
        """Test updating a task's status."""
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]
        update_task_status = tools["tool_update_task_status"]

        # Create a task
        create_task(
            project="test_project",
            title="Test Task",
            objective="Test objective",
        )

        # Update status
        result = update_task_status(
            project="test_project",
            task_file="001-test-task.md",
            new_status="in-progress",
        )

        assert result["status"] == "updated"
        assert result["new_status"] == "in-progress"

        file_path = vibe_root / "test_project" / "tasks" / "001-test-task.md"
        content = file_path.read_text()
        assert "Status: in-progress" in content

    def test_update_task_status_multiple_times(self, vibe_root_and_tools):
        """Test updating status multiple times."""
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]
        update_task_status = tools["tool_update_task_status"]

        create_task(
            project="test_project",
            title="Test Task",
            objective="Test objective",
        )

        # pending -> in-progress -> done
        update_task_status("test_project", "001-test-task.md", "in-progress")
        update_task_status("test_project", "001-test-task.md", "done")

        file_path = vibe_root / "test_project" / "tasks" / "001-test-task.md"
        content = file_path.read_text()
        assert "Status: done" in content
        assert content.count("Status:") == 1  # Only one status line

    def test_update_task_status_invalid_status(self, vibe_root_and_tools):
        """Test that invalid status raises an error."""
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]
        update_task_status = tools["tool_update_task_status"]

        create_task(
            project="test_project",
            title="Test Task",
            objective="Test objective",
        )

        with pytest.raises(ValueError, match="Invalid status"):
            update_task_status("test_project", "001-test-task.md", "invalid-status")

    def test_update_task_status_nonexistent_task(self, vibe_root_and_tools):
        """Test that updating a non-existent task raises an error."""
        vibe_root, tools = vibe_root_and_tools
        update_task_status = tools["tool_update_task_status"]

        with pytest.raises(ValueError, match="not found"):
            update_task_status("test_project", "999-nonexistent.md", "done")

    def test_update_task_status_from_hyphenated_status(self, vibe_root_and_tools):
        """Test updating from a status with hyphen (e.g., in-progress).

        Regression test: the original regex r'^Status:\\s*\\w+' didn't match
        statuses containing hyphens, causing duplicate Status lines.
        """
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]
        update_task_status = tools["tool_update_task_status"]

        create_task(
            project="test_project",
            title="Hyphen Status Test",
            objective="Test hyphenated status replacement",
        )

        # Set to in-progress first
        update_task_status("test_project", "001-hyphen-status-test.md", "in-progress")

        # Now update from in-progress to blocked (both have hyphens or not)
        update_task_status("test_project", "001-hyphen-status-test.md", "blocked")

        file_path = vibe_root / "test_project" / "tasks" / "001-hyphen-status-test.md"
        content = file_path.read_text()

        # Should have exactly one Status line with the new value
        assert "Status: blocked" in content
        assert "Status: in-progress" not in content
        assert content.count("Status:") == 1, "Should have exactly one Status line"


class TestCreatePlan:
    """Tests for tool_create_plan function."""

    def test_create_plan(self, vibe_root_and_tools):
        """Test creating an execution plan."""
        vibe_root, tools = vibe_root_and_tools
        create_plan = tools["tool_create_plan"]

        content = """# Execution Plan

## Phase 1
- Task A
- Task B

## Phase 2
- Task C
"""

        result = create_plan(project="test_project", content=content)

        assert result["status"] == "created"
        assert result["path"] == "test_project/plans/execution-plan.md"

        file_path = vibe_root / "test_project" / "plans" / "execution-plan.md"
        assert file_path.exists()
        assert file_path.read_text() == content

    def test_update_plan(self, vibe_root_and_tools):
        """Test updating an existing plan."""
        vibe_root, tools = vibe_root_and_tools
        create_plan = tools["tool_create_plan"]

        # Create initial plan
        create_plan(project="test_project", content="# Original Plan")

        # Update plan
        result = create_plan(project="test_project", content="# Updated Plan")

        assert result["status"] == "updated"

        file_path = vibe_root / "test_project" / "plans" / "execution-plan.md"
        assert file_path.read_text() == "# Updated Plan"


class TestLogSession:
    """Tests for tool_log_session function."""

    def test_create_session_log(self, vibe_root_and_tools):
        """Test creating a new session log."""
        vibe_root, tools = vibe_root_and_tools
        log_session = tools["tool_log_session"]

        result = log_session(
            project="test_project",
            content="Started working on feature X",
        )

        assert result["status"] == "created"
        assert "date" in result
        assert result["path"].startswith("test_project/sessions/")

        # Check file exists and has correct format
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = vibe_root / "test_project" / "sessions" / f"{today}.md"
        assert file_path.exists()

        content = file_path.read_text()
        assert f"# Session Log - {today}" in content
        assert "Started working on feature X" in content

    def test_append_session_log(self, vibe_root_and_tools):
        """Test appending to an existing session log."""
        vibe_root, tools = vibe_root_and_tools
        log_session = tools["tool_log_session"]

        # Create initial log
        log_session(project="test_project", content="First entry")

        # Append to log
        result = log_session(project="test_project", content="Second entry")

        assert result["status"] == "appended"

        # Check both entries are present
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = vibe_root / "test_project" / "sessions" / f"{today}.md"
        content = file_path.read_text()

        assert "First entry" in content
        assert "Second entry" in content
        assert "---" in content  # Separator
        # Check for timestamp pattern (HH:MM:SS)
        assert re.search(r"\*\*\d{2}:\d{2}:\d{2}\*\*", content)


class TestReindex:
    """Tests for tool_reindex function."""

    def test_reindex(self, vibe_root_and_tools):
        """Test full reindex."""
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]
        create_plan = tools["tool_create_plan"]
        reindex = tools["tool_reindex"]

        # Create some documents
        create_task(project="test_project", title="Task 1", objective="Test 1")
        create_task(project="test_project", title="Task 2", objective="Test 2")
        create_plan(project="test_project", content="# Plan")

        # Reindex
        result = reindex()

        assert result["status"] == "reindexed"
        assert result["document_count"] >= 3  # At least our 3 documents


class TestInitProject:
    """Tests for tool_init_project function."""

    def test_init_project_creates_structure(self, vibe_root_and_tools):
        """Test that init_project creates the standard folder structure."""
        vibe_root, tools = vibe_root_and_tools
        init_project = tools["tool_init_project"]

        result = init_project(project="newproject")

        assert result["status"] == "initialized"
        assert result["project"] == "newproject"
        assert result["path"] == "newproject"

        project_path = vibe_root / "newproject"
        assert project_path.is_dir()

        # Check all standard folders are created
        expected_folders = [
            "tasks",
            "plans",
            "sessions",
            "reports",
            "changelog",
            "references",
            "scratch",
            "assets",
        ]
        for folder in expected_folders:
            assert (project_path / folder).is_dir(), f"Folder '{folder}' should exist"

        assert result["folders"] == expected_folders

        # Check status.md was created
        status_path = project_path / "status.md"
        assert status_path.exists()
        content = status_path.read_text()
        assert "# newproject" in content
        assert "Status: setup" in content

    def test_init_project_fails_if_exists(self, vibe_root_and_tools):
        """Test that init_project fails if project already exists."""
        vibe_root, tools = vibe_root_and_tools
        init_project = tools["tool_init_project"]

        # Create a project directory first
        (vibe_root / "existing").mkdir()

        with pytest.raises(ValueError, match="already exists"):
            init_project(project="existing")

    def test_init_project_prevents_traversal(self, vibe_root_and_tools):
        """Test that directory traversal is prevented."""
        vibe_root, tools = vibe_root_and_tools
        init_project = tools["tool_init_project"]

        with pytest.raises(ValueError, match="Invalid project name"):
            init_project(project="../evil")

        with pytest.raises(ValueError, match="Invalid project name"):
            init_project(project="foo/bar")

        with pytest.raises(ValueError, match="Invalid project name"):
            init_project(project="foo\\bar")

    def test_init_project_returns_absolute_path(self, vibe_root_and_tools):
        """Test that absolute_path is included in result."""
        vibe_root, tools = vibe_root_and_tools
        init_project = tools["tool_init_project"]

        result = init_project(project="myproject")

        assert "absolute_path" in result
        assert result["absolute_path"] == str(vibe_root / "myproject")


class TestFeatureSupport:
    """Tests for feature-based task and plan organization."""

    def test_create_task_with_feature(self, vibe_root_and_tools):
        """Test creating a task with a feature tag."""
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]

        result = create_task(
            project="test_project",
            title="Auth bearer token",
            objective="Implement bearer token auth",
            feature="auth",
        )

        assert result["status"] == "created"
        assert result["feature"] == "auth"

        file_path = vibe_root / "test_project" / "tasks" / "001-auth-bearer-token.md"
        content = file_path.read_text()

        # Check frontmatter with feature
        assert "---" in content
        assert "type: task" in content
        assert "status: pending" in content
        assert "feature: auth" in content

    def test_create_task_without_feature_no_frontmatter(self, vibe_root_and_tools):
        """Test that tasks without feature don't have frontmatter."""
        vibe_root, tools = vibe_root_and_tools
        create_task = tools["tool_create_task"]

        create_task(
            project="test_project",
            title="Simple task",
            objective="Do something",
        )

        file_path = vibe_root / "test_project" / "tasks" / "001-simple-task.md"
        content = file_path.read_text()

        # Without feature, no frontmatter (starts with #)
        assert content.startswith("# Task:")
        assert "---" not in content.split("\n")[0]

    def test_create_plan_with_filename(self, vibe_root_and_tools):
        """Test creating a plan with custom filename."""
        vibe_root, tools = vibe_root_and_tools
        create_plan = tools["tool_create_plan"]

        content = "# Feature: Auth\n\nAuth feature plan."
        result = create_plan(
            project="test_project",
            content=content,
            filename="feature-auth.md",
        )

        assert result["status"] == "created"
        assert result["filename"] == "feature-auth.md"
        assert result["path"] == "test_project/plans/feature-auth.md"

        file_path = vibe_root / "test_project" / "plans" / "feature-auth.md"
        assert file_path.exists()
        assert file_path.read_text() == content

    def test_create_plan_adds_md_extension(self, vibe_root_and_tools):
        """Test that .md extension is added to plan filename if missing."""
        vibe_root, tools = vibe_root_and_tools
        create_plan = tools["tool_create_plan"]

        result = create_plan(
            project="test_project",
            content="# Plan",
            filename="feature-deploy",
        )

        assert result["filename"] == "feature-deploy.md"
        file_path = vibe_root / "test_project" / "plans" / "feature-deploy.md"
        assert file_path.exists()

    def test_create_plan_prevents_path_traversal(self, vibe_root_and_tools):
        """Test that directory traversal in filename is prevented."""
        vibe_root, tools = vibe_root_and_tools
        create_plan = tools["tool_create_plan"]

        with pytest.raises(ValueError, match="cannot contain path separators"):
            create_plan(
                project="test_project",
                content="# Evil",
                filename="../evil.md",
            )

        with pytest.raises(ValueError, match="cannot contain path separators"):
            create_plan(
                project="test_project",
                content="# Evil",
                filename="foo/bar.md",
            )
