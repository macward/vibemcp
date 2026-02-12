"""Tests for main module."""

import logging

from vibe_mcp.config import Config
from vibe_mcp.main import create_server


def test_create_server(tmp_path, monkeypatch, caplog):
    """Test create_server initializes all components."""
    # Set up temporary vibe root
    vibe_root = tmp_path / "vibe"
    vibe_root.mkdir()

    # Create a test project
    project_dir = vibe_root / "test-project"
    project_dir.mkdir()
    tasks_dir = project_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "001-test.md").write_text("# Test Task\n\nStatus: pending\n")

    # Set environment variables
    monkeypatch.setenv("VIBE_ROOT", str(vibe_root))
    monkeypatch.setenv("VIBE_DB", str(tmp_path / "test.db"))

    # Create config from environment
    config = Config.from_env()

    # Capture logs
    with caplog.at_level(logging.INFO):
        mcp = create_server(config)

    # Verify server was created
    assert mcp is not None
    assert mcp.name == "vibeMCP"

    # Verify components were registered (check logs)
    log_messages = [record.message for record in caplog.records]
    assert any("Registering resources" in msg for msg in log_messages)
    assert any("Registering read tools" in msg for msg in log_messages)
    assert any("Registering write tools" in msg for msg in log_messages)
    assert any("Registering prompts" in msg for msg in log_messages)
    assert any("Server configured successfully" in msg for msg in log_messages)


def test_create_server_reindexes_empty_db(tmp_path, monkeypatch, caplog):
    """Test that create_server performs initial index when DB is empty."""
    # Set up temporary vibe root
    vibe_root = tmp_path / "vibe"
    vibe_root.mkdir()

    # Create a test project with some content
    project_dir = vibe_root / "test-project"
    project_dir.mkdir()
    tasks_dir = project_dir / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "001-task.md").write_text("# Task 1\n\nStatus: pending\n")
    (tasks_dir / "002-task.md").write_text("# Task 2\n\nStatus: done\n")

    # Set environment variables
    monkeypatch.setenv("VIBE_ROOT", str(vibe_root))
    monkeypatch.setenv("VIBE_DB", str(tmp_path / "fresh.db"))

    # Create config from environment
    config = Config.from_env()

    # Capture logs
    with caplog.at_level(logging.INFO):
        mcp = create_server(config)

    # Verify initial index was performed
    log_messages = [record.message for record in caplog.records]
    assert any("Database is empty, performing initial index" in msg for msg in log_messages)
    assert any("Initial index complete" in msg for msg in log_messages)
