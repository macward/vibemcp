"""Main entry point for vibemcp MCP server."""

import argparse
import logging
import sys

from fastmcp import FastMCP

from vibe_mcp.auth import get_auth_provider
from vibe_mcp.config import Config
from vibe_mcp.indexer import Database, Indexer
from vibe_mcp.prompts import register_prompts
from vibe_mcp.resources import register_resources
from vibe_mcp.tools import register_tools
from vibe_mcp.tools_webhooks import register_tools_webhooks
from vibe_mcp.tools_write import register_tools_write
from vibe_mcp.webhooks import WebhookManager

logger = logging.getLogger(__name__)


def create_server(config: Config) -> FastMCP:
    """Create and configure the MCP server with all components.

    Args:
        config: Configuration instance with all settings.
    """
    # Get auth provider if configured (with DI)
    auth_provider = get_auth_provider(config)

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

    # Initialize webhook manager only if webhooks are enabled
    webhook_mgr: WebhookManager | None = None
    if config.webhooks_enabled:
        webhook_mgr = WebhookManager(db, config)
        logger.info("Webhook manager initialized")
    else:
        logger.info("Webhooks disabled, skipping webhook manager")

    # Register all components
    logger.info("Registering resources...")
    register_resources(mcp)

    logger.info("Registering read tools...")
    register_tools(mcp, db)

    logger.info("Registering write tools...")
    register_tools_write(mcp, config, indexer, webhook_mgr)

    logger.info("Registering webhook tools...")
    register_tools_webhooks(mcp, webhook_mgr, config)

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

    # Create config once - CLI flag overrides env var
    config = Config.from_env(read_only_override=args.read_only if args.read_only else None)

    # Print startup banner
    logger.info("=" * 50)
    logger.info("vibeMCP starting...")
    logger.info("  VIBE_ROOT: %s", config.vibe_root)
    logger.info("  VIBE_PORT: %s", config.vibe_port)
    logger.info("  VIBE_DB:   %s", config.vibe_db)
    logger.info("  AUTH:      %s", "enabled" if config.auth_token else "disabled")
    logger.info("  READ_ONLY: %s", config.read_only)
    logger.info("  WEBHOOKS:  %s", "enabled" if config.webhooks_enabled else "disabled")
    logger.info("=" * 50)

    # Force reindex if requested (before server starts)
    if args.reindex:
        logger.info("Force reindex requested...")
        indexer = Indexer(config.vibe_root, config.vibe_db)
        indexer.initialize()
        doc_count = indexer.reindex()
        logger.info("Reindex complete: %d documents indexed", doc_count)

    # Create and run server with the same config instance
    try:
        mcp = create_server(config)
        logger.info("Starting MCP server on port %s...", config.vibe_port)
        mcp.run(transport="sse", host="0.0.0.0", port=config.vibe_port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception:
        logger.exception("Server error")
        sys.exit(1)


if __name__ == "__main__":
    main()
