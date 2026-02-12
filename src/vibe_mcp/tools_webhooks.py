"""Webhook MCP tools for vibeMCP - register, unregister, and list webhooks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from vibe_mcp.auth import check_write_permission
from vibe_mcp.config import Config
from vibe_mcp.webhooks import WebhookManager

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_tools_webhooks(
    mcp: "FastMCP",
    webhook_mgr: WebhookManager | None,
    config: Config,
) -> None:
    """Register webhook tools with the FastMCP server.

    Args:
        mcp: FastMCP server instance
        webhook_mgr: WebhookManager instance (None if webhooks disabled)
        config: Config instance for permission checks
    """
    _config = config

    @mcp.tool()
    def tool_register_webhook(
        url: str,
        secret: str,
        event_types: list[str],
        project: str | None = None,
        description: str | None = None,
    ) -> dict:
        """Register a new webhook subscription.

        Subscribe to events and receive POST notifications at the specified URL.
        Each notification includes an HMAC-SHA256 signature for verification.

        Supported event types:
        - task.created, task.updated
        - doc.created, doc.updated
        - session.logged
        - plan.created, plan.updated
        - project.initialized
        - index.reindexed
        - * (wildcard - all events)

        Args:
            url: URL to POST to when events occur (must be http:// or https://)
            secret: Secret for HMAC-SHA256 signature (min 32 chars)
            event_types: List of event types to subscribe to
            project: Optional project filter (None = all projects)
            description: Optional description for this webhook

        Returns:
            Dict with subscription_id and other info
        """
        if webhook_mgr is None:
            raise ValueError("Webhooks are disabled on this server")

        check_write_permission(_config)
        return webhook_mgr.register(
            url=url,
            secret=secret,
            event_types=event_types,
            project=project,
            description=description,
        )

    @mcp.tool()
    def tool_unregister_webhook(subscription_id: int) -> dict:
        """Unregister a webhook subscription.

        Args:
            subscription_id: ID of the subscription to remove

        Returns:
            Dict with status
        """
        if webhook_mgr is None:
            raise ValueError("Webhooks are disabled on this server")

        check_write_permission(_config)
        return webhook_mgr.unregister(subscription_id)

    @mcp.tool()
    def tool_list_webhooks(project: str | None = None) -> list[dict]:
        """List webhook subscriptions.

        Args:
            project: Optional project filter to show only subscriptions
                     that would match events from this project

        Returns:
            List of subscription dicts (secrets are not included)
        """
        if webhook_mgr is None:
            return []  # No webhooks when disabled

        return webhook_mgr.list_subscriptions(project=project)
