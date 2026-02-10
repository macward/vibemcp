"""Webhook MCP tools for vibeMCP - register, unregister, and list webhooks."""

import logging

from vibe_mcp.auth import check_write_permission
from vibe_mcp.webhooks import get_webhook_manager

logger = logging.getLogger(__name__)


def register_webhook(
    url: str,
    secret: str,
    event_types: list[str],
    project: str | None = None,
    description: str | None = None,
) -> dict:
    """Register a new webhook subscription.

    Args:
        url: URL to POST to when events occur
        secret: Secret for HMAC-SHA256 signature (min 32 chars)
        event_types: List of event types to subscribe to
        project: Optional project filter (None = all projects)
        description: Optional description

    Returns:
        Dict with subscription info

    Raises:
        ValueError: If URL or secret is invalid, or event types are invalid
        AuthError: If server is in read-only mode
    """
    check_write_permission()
    manager = get_webhook_manager()
    return manager.register(
        url=url,
        secret=secret,
        event_types=event_types,
        project=project,
        description=description,
    )


def unregister_webhook(subscription_id: int) -> dict:
    """Unregister a webhook subscription.

    Args:
        subscription_id: ID of the subscription to remove

    Returns:
        Dict with status

    Raises:
        ValueError: If subscription not found
        AuthError: If server is in read-only mode
    """
    check_write_permission()
    manager = get_webhook_manager()
    return manager.unregister(subscription_id)


def list_webhooks(project: str | None = None) -> list[dict]:
    """List webhook subscriptions.

    Args:
        project: Optional project filter

    Returns:
        List of subscription dicts (without secrets)
    """
    manager = get_webhook_manager()
    return manager.list_subscriptions(project=project)


def register_tools_webhooks(mcp) -> None:
    """Register webhook tools with the FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

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
        return register_webhook(
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
        return unregister_webhook(subscription_id)

    @mcp.tool()
    def tool_list_webhooks(project: str | None = None) -> list[dict]:
        """List webhook subscriptions.

        Args:
            project: Optional project filter to show only subscriptions
                     that would match events from this project

        Returns:
            List of subscription dicts (secrets are not included)
        """
        return list_webhooks(project=project)
