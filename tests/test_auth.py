"""Tests for auth module."""

import pytest

from vibe_mcp.auth import (
    AuthError,
    BearerTokenVerifier,
    check_write_permission,
    get_auth_provider,
)
from vibe_mcp.config import Config


class TestBearerTokenVerifier:
    """Tests for BearerTokenVerifier class."""

    @pytest.mark.asyncio
    async def test_no_auth_configured_allows_any_request(self, monkeypatch):
        """When VIBE_AUTH_TOKEN is not set, all requests should pass."""
        monkeypatch.delenv("VIBE_AUTH_TOKEN", raising=False)
        config = Config.from_env()

        verifier = BearerTokenVerifier(config)

        # Should return valid AccessToken for any token
        result = await verifier.verify_token("any-token")
        assert result is not None
        assert result.client_id == "anonymous"

        result = await verifier.verify_token("")
        assert result is not None

    @pytest.mark.asyncio
    async def test_empty_token_rejected(self, monkeypatch):
        """When auth is configured, empty token should be rejected."""
        monkeypatch.setenv("VIBE_AUTH_TOKEN", "a" * 32)
        config = Config.from_env()

        verifier = BearerTokenVerifier(config)
        result = await verifier.verify_token("")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, monkeypatch):
        """When auth is configured, wrong token should be rejected."""
        monkeypatch.setenv("VIBE_AUTH_TOKEN", "correct-token-with-32-characters!")
        config = Config.from_env()

        verifier = BearerTokenVerifier(config)
        result = await verifier.verify_token("wrong-token")
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_accepted(self, monkeypatch):
        """When auth is configured, correct token should be accepted."""
        token = "my-super-secret-token-32-chars!!"
        monkeypatch.setenv("VIBE_AUTH_TOKEN", token)
        config = Config.from_env()

        verifier = BearerTokenVerifier(config)
        result = await verifier.verify_token(token)
        assert result is not None
        assert result.client_id == "authenticated"
        assert result.token == token


class TestGetAuthProvider:
    """Tests for get_auth_provider function."""

    def test_returns_verifier_when_token_configured(self, monkeypatch):
        """When VIBE_AUTH_TOKEN is set, should return BearerTokenVerifier."""
        monkeypatch.setenv("VIBE_AUTH_TOKEN", "a" * 32)
        config = Config.from_env()

        provider = get_auth_provider(config)
        assert provider is not None
        assert isinstance(provider, BearerTokenVerifier)

    def test_returns_none_when_no_token(self, monkeypatch):
        """When VIBE_AUTH_TOKEN is not set, should return None."""
        monkeypatch.delenv("VIBE_AUTH_TOKEN", raising=False)
        config = Config.from_env()

        provider = get_auth_provider(config)
        assert provider is None


class TestCheckWritePermission:
    """Tests for check_write_permission function."""

    def test_write_allowed_by_default(self, monkeypatch):
        """By default, write operations should be allowed."""
        monkeypatch.delenv("VIBE_READ_ONLY", raising=False)
        config = Config.from_env()

        # Should not raise
        check_write_permission(config)

    def test_write_rejected_in_read_only_mode_env(self, monkeypatch):
        """When VIBE_READ_ONLY is set, write should be rejected."""
        monkeypatch.setenv("VIBE_READ_ONLY", "true")
        config = Config.from_env()

        with pytest.raises(AuthError, match="read-only mode"):
            check_write_permission(config)

    def test_write_rejected_in_read_only_mode_cli(self, monkeypatch):
        """When CLI read-only flag is set, write should be rejected."""
        monkeypatch.delenv("VIBE_READ_ONLY", raising=False)
        config = Config.from_env(read_only_override=True)

        with pytest.raises(AuthError, match="read-only mode"):
            check_write_permission(config)

    def test_read_only_env_values(self, monkeypatch):
        """Test various truthy values for VIBE_READ_ONLY."""
        for value in ("1", "true", "TRUE", "yes", "YES", "True"):
            monkeypatch.setenv("VIBE_READ_ONLY", value)
            config = Config.from_env()

            with pytest.raises(AuthError, match="read-only mode"):
                check_write_permission(config)

    def test_read_only_false_values(self, monkeypatch):
        """Test that other values don't enable read-only mode."""
        for value in ("0", "false", "no", ""):
            monkeypatch.setenv("VIBE_READ_ONLY", value)
            config = Config.from_env()

            # Should not raise
            check_write_permission(config)


class TestConfigAuthToken:
    """Tests for auth token configuration."""

    def test_token_too_short_rejected(self, monkeypatch):
        """Token shorter than 32 characters should be rejected."""
        monkeypatch.setenv("VIBE_AUTH_TOKEN", "short")

        with pytest.raises(ValueError, match="at least 32 characters"):
            Config.from_env()

    def test_token_exactly_32_chars_accepted(self, monkeypatch):
        """Token with exactly 32 characters should be accepted."""
        token = "a" * 32
        monkeypatch.setenv("VIBE_AUTH_TOKEN", token)

        config = Config.from_env()
        assert config.auth_token == token

    def test_token_longer_than_32_chars_accepted(self, monkeypatch):
        """Token longer than 32 characters should be accepted."""
        token = "a" * 64
        monkeypatch.setenv("VIBE_AUTH_TOKEN", token)

        config = Config.from_env()
        assert config.auth_token == token
