"""Tests for read tools."""

import pytest

from vibe_mcp.config import Config
from vibe_mcp.indexer import Database, Indexer
from vibe_mcp.indexer.models import Document


@pytest.fixture
def test_vibe_root(tmp_path, monkeypatch):
    """Create a temporary vibe root for testing."""
    vibe_root = tmp_path / ".vibe"
    vibe_root.mkdir()
    db_path = vibe_root / "test.db"

    # Create a test project with tasks
    test_project = vibe_root / "test_project"
    test_project.mkdir()
    (test_project / "tasks").mkdir()
    (test_project / "plans").mkdir()

    # Create tasks with and without features
    task1 = test_project / "tasks" / "001-auth-bearer.md"
    task1.write_text("""---
type: task
status: pending
feature: auth
---

# Task: Auth Bearer Token

## Objective
Implement bearer token.
""")

    task2 = test_project / "tasks" / "002-auth-refresh.md"
    task2.write_text("""---
type: task
status: pending
feature: auth
---

# Task: Auth Refresh Token

## Objective
Implement refresh token.
""")

    task3 = test_project / "tasks" / "003-deploy-vps.md"
    task3.write_text("""---
type: task
status: pending
feature: deploy
---

# Task: Deploy VPS

## Objective
Deploy to VPS.
""")

    task4 = test_project / "tasks" / "004-no-feature.md"
    task4.write_text("""# Task: No Feature Task

Status: pending

## Objective
Task without feature.
""")

    # Create plans
    master_plan = test_project / "plans" / "execution-plan.md"
    master_plan.write_text("""# Execution Plan

Master plan.
""")

    auth_plan = test_project / "plans" / "feature-auth.md"
    auth_plan.write_text("""# Feature: Auth

Auth feature plan.
""")

    deploy_plan = test_project / "plans" / "feature-deploy.md"
    deploy_plan.write_text("""# Feature: Deploy

Deploy feature plan.
""")

    # Set environment variables
    monkeypatch.setenv("VIBE_ROOT", str(vibe_root))
    monkeypatch.setenv("VIBE_DB", str(db_path))

    # Index the files
    indexer = Indexer(vibe_root, db_path)
    indexer.initialize()
    indexer.reindex()

    return vibe_root


@pytest.fixture
def db(test_vibe_root, tmp_path, monkeypatch):
    """Get database instance."""
    config = Config.from_env()
    db = Database(config.vibe_db)
    db.initialize()
    return db


class TestListTasksWithFeature:
    """Tests for list_tasks with feature filter."""

    def test_list_all_tasks(self, test_vibe_root, db):
        """Test listing all tasks without filters."""
        from vibe_mcp.tools import register_tools
        from fastmcp import FastMCP

        mcp = FastMCP()
        register_tools(mcp, db)

        # Get the list_tasks function
        list_tasks = None
        for tool in mcp._tool_manager._tools.values():
            if tool.fn.__name__ == "list_tasks":
                list_tasks = tool.fn
                break

        assert list_tasks is not None

        tasks = list_tasks(project="test_project")
        assert len(tasks) == 4

    def test_list_tasks_filter_by_feature(self, test_vibe_root, db):
        """Test filtering tasks by feature."""
        from vibe_mcp.tools import register_tools
        from fastmcp import FastMCP

        mcp = FastMCP()
        register_tools(mcp, db)

        list_tasks = None
        for tool in mcp._tool_manager._tools.values():
            if tool.fn.__name__ == "list_tasks":
                list_tasks = tool.fn
                break

        # Filter by auth feature
        auth_tasks = list_tasks(project="test_project", feature="auth")
        assert len(auth_tasks) == 2
        assert all(t["feature"] == "auth" for t in auth_tasks)

        # Filter by deploy feature
        deploy_tasks = list_tasks(project="test_project", feature="deploy")
        assert len(deploy_tasks) == 1
        assert deploy_tasks[0]["feature"] == "deploy"

    def test_list_tasks_returns_feature_field(self, test_vibe_root, db):
        """Test that tasks include the feature field in response."""
        from vibe_mcp.tools import register_tools
        from fastmcp import FastMCP

        mcp = FastMCP()
        register_tools(mcp, db)

        list_tasks = None
        for tool in mcp._tool_manager._tools.values():
            if tool.fn.__name__ == "list_tasks":
                list_tasks = tool.fn
                break

        tasks = list_tasks(project="test_project")

        # All tasks should have a feature field (may be None)
        for task in tasks:
            assert "feature" in task


class TestListPlans:
    """Tests for list_plans tool."""

    def test_list_all_plans(self, test_vibe_root, db):
        """Test listing all plans in a project."""
        from vibe_mcp.tools import register_tools
        from fastmcp import FastMCP

        mcp = FastMCP()
        register_tools(mcp, db)

        list_plans = None
        for tool in mcp._tool_manager._tools.values():
            if tool.fn.__name__ == "list_plans":
                list_plans = tool.fn
                break

        assert list_plans is not None

        plans = list_plans(project="test_project")
        assert len(plans) == 3

        # Check we have all expected plans
        filenames = {p["filename"] for p in plans}
        assert "execution-plan.md" in filenames
        assert "feature-auth.md" in filenames
        assert "feature-deploy.md" in filenames

    def test_list_plans_includes_title(self, test_vibe_root, db):
        """Test that plans include extracted title."""
        from vibe_mcp.tools import register_tools
        from fastmcp import FastMCP

        mcp = FastMCP()
        register_tools(mcp, db)

        list_plans = None
        for tool in mcp._tool_manager._tools.values():
            if tool.fn.__name__ == "list_plans":
                list_plans = tool.fn
                break

        plans = list_plans(project="test_project")

        # Find the auth plan
        auth_plan = next(p for p in plans if p["filename"] == "feature-auth.md")
        assert auth_plan["title"] == "Feature: Auth"

    def test_list_plans_includes_updated(self, test_vibe_root, db):
        """Test that plans include updated date."""
        from vibe_mcp.tools import register_tools
        from fastmcp import FastMCP

        mcp = FastMCP()
        register_tools(mcp, db)

        list_plans = None
        for tool in mcp._tool_manager._tools.values():
            if tool.fn.__name__ == "list_plans":
                list_plans = tool.fn
                break

        plans = list_plans(project="test_project")

        # All plans should have updated field
        for plan in plans:
            assert "updated" in plan
            assert plan["updated"] is not None

    def test_list_plans_nonexistent_project(self, test_vibe_root, db):
        """Test listing plans for non-existent project returns empty."""
        from vibe_mcp.tools import register_tools
        from fastmcp import FastMCP

        mcp = FastMCP()
        register_tools(mcp, db)

        list_plans = None
        for tool in mcp._tool_manager._tools.values():
            if tool.fn.__name__ == "list_plans":
                list_plans = tool.fn
                break

        plans = list_plans(project="nonexistent")
        assert plans == []
