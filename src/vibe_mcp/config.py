"""Configuration module for vibemcp.

Loads configuration from environment variables with sensible defaults.
"""

import os
import warnings
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Application configuration."""

    vibe_root: Path
    vibe_port: int
    vibe_db: Path
    auth_token: str | None
    read_only: bool
    webhooks_enabled: bool
    sync_interval: int

    @classmethod
    def from_env(cls, read_only_override: bool | None = None) -> "Config":
        """Load configuration from environment variables.

        Args:
            read_only_override: If provided, overrides the VIBE_READ_ONLY env var.
        """
        default_root = str(Path.home() / ".vibe")
        vibe_root = Path(os.getenv("VIBE_ROOT", default_root)).expanduser()

        port_str = os.getenv("VIBE_PORT", "8080")
        try:
            vibe_port = int(port_str)
            if not 1 <= vibe_port <= 65535:
                raise ValueError(f"Port must be between 1 and 65535, got {vibe_port}")
        except ValueError as e:
            raise ValueError(f"Invalid VIBE_PORT value '{port_str}': {e}") from e

        default_db = str(vibe_root / "index.db")
        vibe_db = Path(os.getenv("VIBE_DB", default_db)).expanduser()

        # Auth token - must be at least 32 bytes if set
        auth_token = os.getenv("VIBE_AUTH_TOKEN")
        if auth_token is not None:
            if len(auth_token) < 32:
                raise ValueError(
                    "VIBE_AUTH_TOKEN must be at least 32 characters for security"
                )

        # Read-only mode - CLI flag takes precedence over env var
        if read_only_override is not None:
            read_only = read_only_override
        else:
            read_only = os.getenv("VIBE_READ_ONLY", "").lower() in ("1", "true", "yes")

        # Webhooks enabled by default
        webhooks_enabled = os.getenv("VIBE_WEBHOOKS_ENABLED", "true").lower() not in (
            "0",
            "false",
            "no",
        )

        # Sync interval in seconds (0 to disable)
        sync_interval_str = os.getenv("VIBE_SYNC_INTERVAL", "30")
        try:
            sync_interval = int(sync_interval_str)
            if sync_interval < 0:
                raise ValueError(f"Sync interval must be >= 0, got {sync_interval}")
        except ValueError as e:
            raise ValueError(f"Invalid VIBE_SYNC_INTERVAL value '{sync_interval_str}': {e}") from e

        return cls(
            vibe_root=vibe_root,
            vibe_port=vibe_port,
            vibe_db=vibe_db,
            auth_token=auth_token,
            read_only=read_only,
            webhooks_enabled=webhooks_enabled,
            sync_interval=sync_interval,
        )


# =============================================================================
# DEPRECATED: Global singleton pattern - will be removed after DI migration
# =============================================================================
_config: Config | None = None
_read_only_override: bool | None = None


def set_read_only_override(read_only: bool | None) -> None:
    """DEPRECATED: Set the read-only override from CLI.

    Use Config.from_env(read_only_override=...) instead.
    """
    warnings.warn(
        "set_read_only_override() is deprecated. Use Config.from_env(read_only_override=...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _read_only_override
    _read_only_override = read_only


def get_config() -> Config:
    """DEPRECATED: Get the global configuration instance.

    Use Config.from_env() instead and pass config as a parameter.
    """
    warnings.warn(
        "get_config() is deprecated. Use Config.from_env() and dependency injection instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _config
    if _config is None:
        _config = Config.from_env(read_only_override=_read_only_override)
    return _config


def reset_config() -> None:
    """DEPRECATED: Reset the global configuration (for testing).

    Create fresh Config instances directly instead.
    """
    warnings.warn(
        "reset_config() is deprecated. Create fresh Config instances instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _config, _read_only_override
    _config = None
    _read_only_override = None
