"""Tests for MCP prompts."""

import tempfile
from pathlib import Path

import pytest

from vibe_mcp.config import Config
from vibe_mcp.indexer.database import Database
from vibe_mcp.indexer.indexer import Indexer


@pytest.fixture
def indexed_project(monkeypatch):
    """Create a temporary vibe root with an indexed demo-api project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vibe_path = Path(tmpdir)
        db_path = vibe_path / "index.db"

        # Create demo-api project structure
        project_path = vibe_path / "demo-api"
        project_path.mkdir()

        # Create folders
        (project_path / "tasks").mkdir()
        (project_path / "plans").mkdir()
        (project_path / "sessions").mkdir()
        (project_path / "reports").mkdir()

        # Create status.md
        status_file = project_path / "status.md"
        status_file.write_text(
            """# demo-api — Project Status

## Current Status

Backend API for user management and authentication.

**Sprint:** 3 of 6
**Progress:** 65%

## Blockers

- Waiting for Redis instance

## Next Steps

1. Complete OAuth2 callback handler
2. Write integration tests
"""
        )

        # Create tasks
        task1 = project_path / "tasks" / "003-auth-jwt.md"
        task1.write_text(
            """# Task: Implementar autenticación JWT

Status: in-progress

## Objective
Agregar endpoints de login/register y middleware de autenticación JWT.

## Steps
1. [x] Crear servicio de generación/validación de JWT
2. [ ] Agregar middleware de validación de token
"""
        )

        task2 = project_path / "tasks" / "004-oauth-google.md"
        task2.write_text(
            """# Task: Agregar OAuth2 con Google

Status: blocked

## Objective
Permitir a usuarios autenticarse con su cuenta de Google.

## Notes
Bloqueado: necesitamos credentials de Google en staging.
"""
        )

        task3 = project_path / "tasks" / "005-rate-limiting.md"
        task3.write_text(
            """# Task: Implementar rate limiting

Status: pending

## Objective
Agregar rate limiting para proteger la API.
"""
        )

        # Create sessions
        session1 = project_path / "sessions" / "2025-02-09.md"
        session1.write_text(
            """# Session 2025-02-09

## Lo que hice

- Implementé servicio JWT con PyJWT
- Creé endpoints /auth/register y /auth/login

## Bloqueado por

- Redis no disponible aún para refresh tokens

## Próximo

1. Esperar a que Bob configure Redis
2. Completar middleware de auth
"""
        )

        session2 = project_path / "sessions" / "2025-02-08.md"
        session2.write_text(
            """# Session 2025-02-08

## Lo que hice

- Implementé modelo User con SQLAlchemy
- Escribí tests unitarios
"""
        )

        # Create execution plan
        (project_path / "plans").mkdir(exist_ok=True)
        plan_file = project_path / "plans" / "execution-plan.md"
        plan_file.write_text(
            """# Execution Plan — demo-api

## Overview
Backend API for authentication system.

## Current Status
- In Progress: Auth implementation
- Blocked: OAuth needs credentials
"""
        )

        # Set environment variables for Config.from_env() in tests
        monkeypatch.setenv("VIBE_ROOT", str(vibe_path))
        monkeypatch.setenv("VIBE_DB", str(db_path))

        # Initialize database and index the project
        indexer = Indexer(vibe_path, db_path)
        indexer.initialize()
        indexer.reindex()
        indexer.close()

        yield vibe_path


@pytest.fixture
def empty_project(monkeypatch):
    """Create a temporary vibe root with an empty project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        vibe_path = Path(tmpdir)
        db_path = vibe_path / "index.db"

        # Create empty project structure
        project_path = vibe_path / "empty-project"
        project_path.mkdir()

        # Create empty folders
        (project_path / "tasks").mkdir()
        (project_path / "sessions").mkdir()

        # Create a minimal task file so the project gets indexed
        empty_task = project_path / "tasks" / "001-placeholder.md"
        empty_task.write_text(
            """# Task: Placeholder

Status: pending

## Objective
Placeholder task for empty project.
"""
        )

        # Set environment variables for Config.from_env() in tests
        monkeypatch.setenv("VIBE_ROOT", str(vibe_path))
        monkeypatch.setenv("VIBE_DB", str(db_path))

        # Initialize database and index
        indexer = Indexer(vibe_path, db_path)
        indexer.initialize()
        indexer.reindex()
        indexer.close()

        yield vibe_path


class TestProjectBriefing:
    def test_project_not_found(self, indexed_project):
        """Test briefing for non-existent project."""
        from fastmcp import FastMCP

        from vibe_mcp.prompts import register_prompts

        mcp = FastMCP("test")
        register_prompts(mcp)

        # Get the prompt function
        config = Config.from_env()
        db = Database(config.vibe_db)

        # Manually call the function logic (since we can't easily invoke prompts)
        project_obj = db.get_project("nonexistent")
        db.close()

        assert project_obj is None

    def test_project_briefing_with_content(self, indexed_project):
        """Test briefing for project with content."""
        from fastmcp import FastMCP

        from vibe_mcp.prompts import register_prompts

        mcp = FastMCP("test")
        register_prompts(mcp)

        config = Config.from_env()
        db = Database(config.vibe_db)

        # Verify project exists and has data
        project = db.get_project("demo-api")
        assert project is not None

        # Verify tasks were indexed
        tasks = db.list_documents(project_name="demo-api", folder="tasks")
        assert len(tasks) == 3

        # Verify status counts
        in_progress = [t for t in tasks if t.status == "in-progress"]
        blocked = [t for t in tasks if t.status == "blocked"]
        pending = [t for t in tasks if t.status == "pending"]

        assert len(in_progress) == 1
        assert len(blocked) == 1
        assert len(pending) == 1

        # Verify sessions exist
        sessions = db.list_documents(project_name="demo-api", folder="sessions")
        assert len(sessions) == 2

        db.close()

    def test_empty_project_briefing(self, empty_project):
        """Test briefing for project with no content."""
        from fastmcp import FastMCP

        from vibe_mcp.prompts import register_prompts

        mcp = FastMCP("test")
        register_prompts(mcp)

        config = Config.from_env()
        db = Database(config.vibe_db)

        # Verify project exists
        project = db.get_project("empty-project")
        assert project is not None

        # Verify minimal content (just the placeholder task)
        tasks = db.list_documents(project_name="empty-project", folder="tasks")
        sessions = db.list_documents(project_name="empty-project", folder="sessions")

        assert len(tasks) == 1  # Just the placeholder
        assert len(sessions) == 0

        db.close()


class TestSessionStart:
    def test_session_start_with_content(self, indexed_project):
        """Test session start for project with content."""
        from fastmcp import FastMCP

        from vibe_mcp.prompts import register_prompts

        mcp = FastMCP("test")
        register_prompts(mcp)

        config = Config.from_env()
        db = Database(config.vibe_db)

        # Verify project exists
        project = db.get_project("demo-api")
        assert project is not None

        # Verify execution plan exists
        project_path = Path(config.vibe_root) / "demo-api"
        plan_file = project_path / "plans" / "execution-plan.md"
        assert plan_file.exists()

        # Verify tasks are properly organized
        tasks = db.list_documents(project_name="demo-api", folder="tasks")
        in_progress = [t for t in tasks if t.status == "in-progress"]
        blocked = [t for t in tasks if t.status == "blocked"]
        pending = [t for t in tasks if t.status == "pending"]

        assert len(in_progress) >= 1
        assert len(blocked) >= 1
        assert len(pending) >= 1

        db.close()

    def test_session_start_empty_project(self, empty_project):
        """Test session start for empty project."""
        from fastmcp import FastMCP

        from vibe_mcp.prompts import register_prompts

        mcp = FastMCP("test")
        register_prompts(mcp)

        config = Config.from_env()
        db = Database(config.vibe_db)

        # Verify project exists but has no content
        project = db.get_project("empty-project")
        assert project is not None

        project_path = Path(config.vibe_root) / "empty-project"
        status_file = project_path / "status.md"
        assert not status_file.exists()

        db.close()


class TestExtractSection:
    def test_extract_objective(self):
        """Test extracting a section from markdown content."""
        from vibe_mcp.prompts import _extract_section

        content = """# Task Title

Status: pending

## Objective
This is the objective text.

## Steps
1. Step one
2. Step two
"""
        objective = _extract_section(content, "## Objective")
        assert "This is the objective text" in objective
        assert "Steps" not in objective

    def test_extract_missing_section(self):
        """Test extracting a section that doesn't exist."""
        from vibe_mcp.prompts import _extract_section

        content = """# Task Title

Status: pending

## Objective
This is the objective text.
"""
        result = _extract_section(content, "## Notes")
        assert result == ""

    def test_extract_with_multiple_newlines(self):
        """Test that multiple newlines are collapsed."""
        from vibe_mcp.prompts import _extract_section

        content = """# Task Title

## Section
Line 1


Line 2



Line 3

## Next Section
"""
        result = _extract_section(content, "## Section")
        assert "\n\n\n" not in result
        assert "Line 1" in result
        assert "Line 3" in result
