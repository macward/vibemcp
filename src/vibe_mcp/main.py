"""Main entry point for vibemcp MCP server."""

import argparse
import logging
import sys

from fastmcp import FastMCP

from vibe_mcp.auth import get_auth_provider
from vibe_mcp.config import get_config, reset_config, set_read_only_override
from vibe_mcp.indexer import Database, Indexer
from vibe_mcp.prompts import register_prompts
from vibe_mcp.resources import register_resources
from vibe_mcp.tools import register_tools
from vibe_mcp.tools_write import register_tools_write

logger = logging.getLogger(__name__)


def create_server(read_only: bool | None = None) -> FastMCP:
    """Create and configure the MCP server with all components.

    Args:
        read_only: If provided, forces read-only mode regardless of env var.
    """
    # Set and apply CLI override if provided
    if read_only is not None:
        set_read_only_override(read_only)
        reset_config()

    config = get_config()

    # Get auth provider if configured
    auth_provider = get_auth_provider()

    # Create FastMCP server instance
    mcp = FastMCP(
        name="vibeMCP",
        instructions=(
            "vibeMCP provides access to a workspace of project documentation, tasks, "
            "plans, and session logs. Use the search tool to find relevant content "
            "across all projects, or use resources to browse specific projects and files."
        ),
        auth=auth_provider,
    )

    # Initialize database and indexer
    logger.info("Initializing database at %s", config.vibe_db)
    db = Database(config.vibe_db)
    db.initialize()

    indexer = Indexer(config.vibe_root, config.vibe_db)
    indexer.initialize()

    # Check if reindex is needed (empty database)
    project_count = len(db.list_projects())
    if project_count == 0:
        logger.info("Database is empty, performing initial index...")
        doc_count = indexer.reindex()
        logger.info("Initial index complete: %d documents indexed", doc_count)

    # Register all components
    logger.info("Registering resources...")
    register_resources(mcp)

    logger.info("Registering read tools...")
    register_tools(mcp, db)

    logger.info("Registering write tools...")
    register_tools_write(mcp)

    logger.info("Registering prompts...")
    register_prompts(mcp)

    logger.info("Server configured successfully")
    return mcp


def main() -> None:
    """Main function - starts the MCP server."""
    # Configure logging here to avoid side effects on import
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(description="vibeMCP - MCP server for vibe workspaces")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Force reindex of all projects before starting",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Run in read-only mode (disable write tools)",
    )
    args = parser.parse_args()

    # Set CLI override for read-only mode
    if args.read_only:
        set_read_only_override(True)

    config = get_config()

    # Print startup banner
    logger.info("=" * 50)
    logger.info("vibeMCP starting...")
    logger.info("  VIBE_ROOT: %s", config.vibe_root)
    logger.info("  VIBE_PORT: %s", config.vibe_port)
    logger.info("  VIBE_DB:   %s", config.vibe_db)
    logger.info("  AUTH:      %s", "enabled" if config.auth_token else "disabled")
    logger.info("  READ_ONLY: %s", config.read_only)
    logger.info("=" * 50)

    # Force reindex if requested
    if args.reindex:
        logger.info("Force reindex requested...")
        indexer = Indexer(config.vibe_root, config.vibe_db)
        indexer.initialize()
        doc_count = indexer.reindex()
        logger.info("Reindex complete: %d documents indexed", doc_count)

    # Create and run server
    try:
        mcp = create_server()
        logger.info("Starting MCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception:
        logger.exception("Server error")
        sys.exit(1)


if __name__ == "__main__":
    main()
