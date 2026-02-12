"""Authentication module for vibeMCP.

Provides Bearer token validation for the MCP server using FastMCP's auth system.
"""

import hmac
import logging
import warnings

from fastmcp.server.auth import AccessToken, TokenVerifier

from vibe_mcp.config import Config, get_config

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Raised when authentication fails."""

    pass


class BearerTokenVerifier(TokenVerifier):
    """
    FastMCP TokenVerifier that validates bearer tokens against VIBE_AUTH_TOKEN.

    This integrates with FastMCP's auth system to enforce authentication
    on all MCP requests when VIBE_AUTH_TOKEN is configured.
    """

    def __init__(self, config: Config):
        """Initialize verifier with config.

        Args:
            config: Config instance with auth_token
        """
        self._config = config

    async def verify_token(self, token: str) -> AccessToken | None:
        """
        Verify a bearer token and return access info if valid.

        Args:
            token: The bearer token (without "Bearer " prefix)

        Returns:
            AccessToken if valid, None if invalid
        """
        # If no auth token is configured, allow all requests
        if self._config.auth_token is None:
            return AccessToken(
                token=token or "anonymous",
                client_id="anonymous",
                scopes=["read", "write"],
            )

        # Empty token is invalid
        if not token:
            logger.warning("Empty authentication token")
            return None

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(token, self._config.auth_token):
            logger.warning("Invalid authentication token")
            return None

        # Valid token
        return AccessToken(
            token=token,
            client_id="authenticated",
            scopes=["read", "write"],
        )


def get_auth_provider(config: Config | None = None) -> BearerTokenVerifier | None:
    """
    Get the auth provider for FastMCP based on configuration.

    Args:
        config: Config instance (if None, uses deprecated get_config())

    Returns:
        BearerTokenVerifier if VIBE_AUTH_TOKEN is set, None otherwise
    """
    if config is None:
        warnings.warn(
            "get_auth_provider() without config is deprecated. Pass config explicitly.",
            DeprecationWarning,
            stacklevel=2,
        )
        config = get_config()

    if config.auth_token is not None:
        return BearerTokenVerifier(config)

    return None


def check_write_permission(config: Config) -> None:
    """
    Check if write operations are allowed.

    Args:
        config: Config instance

    Raises:
        AuthError: If the server is in read-only mode
    """
    if config.read_only:
        logger.warning("Write operation rejected: server is in read-only mode")
        raise AuthError("Server is in read-only mode")
