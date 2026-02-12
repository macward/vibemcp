"""Tests for config module."""

from pathlib import Path

import pytest

from vibe_mcp.config import Config


def test_config_defaults():
    """Test config loads with defaults when no env vars set."""
    config = Config.from_env()
    assert config.vibe_root == Path.home() / ".vibe"
    assert config.vibe_port == 8080
    assert config.vibe_db == Path.home() / ".vibe" / "index.db"


def test_config_from_env(monkeypatch):
    """Test config loads from environment variables."""
    monkeypatch.setenv("VIBE_ROOT", "/custom/vibe")
    monkeypatch.setenv("VIBE_PORT", "9000")
    monkeypatch.setenv("VIBE_DB", "/custom/db.sqlite")

    config = Config.from_env()
    assert config.vibe_root == Path("/custom/vibe")
    assert config.vibe_port == 9000
    assert config.vibe_db == Path("/custom/db.sqlite")


def test_config_from_env_creates_new_instances():
    """Test Config.from_env() creates new instances each time."""
    config1 = Config.from_env()
    config2 = Config.from_env()
    assert config1 is not config2


def test_config_tilde_expansion(monkeypatch):
    """Test config expands tilde in paths."""
    monkeypatch.setenv("VIBE_ROOT", "~/custom/vibe")
    config = Config.from_env()
    assert "~" not in str(config.vibe_root)
    assert config.vibe_root.is_absolute()


def test_config_invalid_port_non_numeric(monkeypatch):
    """Test config raises error for non-numeric port."""
    monkeypatch.setenv("VIBE_PORT", "not_a_number")
    with pytest.raises(ValueError, match="Invalid VIBE_PORT"):
        Config.from_env()


def test_config_invalid_port_out_of_range(monkeypatch):
    """Test config raises error for port out of valid range."""
    monkeypatch.setenv("VIBE_PORT", "70000")
    with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
        Config.from_env()
