"""Configuration module for vibemcp.

Loads configuration from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Application configuration."""

    vibe_root: Path
    vibe_port: int
    vibe_db: Path

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
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

        return cls(
            vibe_root=vibe_root,
            vibe_port=vibe_port,
            vibe_db=vibe_db,
        )


# Global config instance (lazy loaded)
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config() -> None:
    """Reset the global configuration (useful for testing)."""
    global _config
    _config = None
