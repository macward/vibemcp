"""Main entry point for vibemcp MCP server."""

from vibe_mcp.config import get_config


def main() -> None:
    """Main function - starts the MCP server."""
    config = get_config()
    print("vibemcp starting...")
    print(f"  VIBE_ROOT: {config.vibe_root}")
    print(f"  VIBE_PORT: {config.vibe_port}")
    print(f"  VIBE_DB:   {config.vibe_db}")


if __name__ == "__main__":
    main()
