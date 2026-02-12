"""Webhook manager for vibeMCP - handles outgoing webhook notifications."""

import hashlib
import hmac
import ipaddress
import json
import logging
import socket
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

import warnings

from vibe_mcp.config import Config, get_config
from vibe_mcp.indexer import Database

logger = logging.getLogger(__name__)

# Supported event types
EVENT_TYPES = {
    "task.created",
    "task.updated",
    "doc.created",
    "doc.updated",
    "session.logged",
    "plan.created",
    "plan.updated",
    "project.initialized",
    "index.reindexed",
    "*",  # Wildcard
}

# Timeout for webhook delivery
DELIVERY_TIMEOUT = 10.0  # seconds

# Rate limiting: max concurrent deliveries
MAX_CONCURRENT_DELIVERIES = 10

# Subscription limits (anti-spam/DoS protection)
MAX_SUBSCRIPTIONS_PER_PROJECT = 50
MAX_SUBSCRIPTIONS_GLOBAL = 200

# Blocked IP ranges for SSRF protection
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 private
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]


def _is_safe_url(url: str) -> tuple[bool, str]:
    """Check if a URL is safe (not pointing to internal/private networks).

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_safe, error_message)
    """
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False, "URL must use http or https scheme"

        hostname = parsed.hostname
        if not hostname:
            return False, "URL must have a valid hostname"

        # Block common internal hostnames
        blocked_hostnames = {
            "localhost",
            "127.0.0.1",
            "::1",
            "0.0.0.0",
            "metadata.google.internal",
            "metadata.goog",
        }
        if hostname.lower() in blocked_hostnames:
            return False, f"Blocked hostname: {hostname}"

        # Resolve hostname to IP and check against blocked ranges
        try:
            # Get all IPs for the hostname
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
            for info in addr_info:
                ip_str = info[4][0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                    for blocked_range in BLOCKED_IP_RANGES:
                        if ip in blocked_range:
                            return False, f"URL resolves to blocked IP range: {ip}"
                except ValueError:
                    continue
        except socket.gaierror:
            # Can't resolve - allow it (might be valid but unreachable now)
            pass

        return True, ""

    except Exception as e:
        return False, f"Invalid URL: {e}"


class WebhookManager:
    """Manages webhook subscriptions and event delivery.

    Payload format sent to webhook endpoints:
    {
        "event_id": "550e8400-e29b-41d4-a716-446655440000",
        "event_type": "task.created",
        "project": "my-project",
        "timestamp": "2024-02-10T12:34:56.789000+00:00",
        "data": {
            "task_number": 1,
            "title": "New Task",
            ...
        }
    }
    """

    def __init__(self, db: Database, config: Config):
        """Initialize the webhook manager.

        Args:
            db: Database instance for subscription storage
            config: Config instance for checking webhooks_enabled
        """
        self.db = db
        self._config = config
        self._executor = ThreadPoolExecutor(
            max_workers=MAX_CONCURRENT_DELIVERIES,
            thread_name_prefix="webhook-delivery",
        )
        self._shutdown_event = threading.Event()

    def shutdown(self, timeout: float = 5.0) -> None:
        """Shutdown the webhook manager gracefully.

        Args:
            timeout: Maximum time to wait for pending deliveries
        """
        self._shutdown_event.set()
        self._executor.shutdown(wait=True, cancel_futures=False)
        logger.info("Webhook manager shutdown complete")

    def register(
        self,
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
        """
        # Validate URL scheme
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        # SSRF protection: validate URL doesn't point to internal networks
        is_safe, error_msg = _is_safe_url(url)
        if not is_safe:
            raise ValueError(f"Unsafe webhook URL: {error_msg}")

        # Validate secret
        if len(secret) < 32:
            raise ValueError("Secret must be at least 32 characters")

        # Validate event types
        invalid_types = set(event_types) - EVENT_TYPES
        if invalid_types:
            raise ValueError(f"Invalid event types: {', '.join(invalid_types)}")

        if not event_types:
            raise ValueError("At least one event type is required")

        # Check subscription limits
        existing_subs = self.db.list_webhook_subscriptions(project=project, active_only=True)
        if project:
            project_count = len([s for s in existing_subs if s.get("project") == project])
            if project_count >= MAX_SUBSCRIPTIONS_PER_PROJECT:
                raise ValueError(
                    f"Maximum subscriptions ({MAX_SUBSCRIPTIONS_PER_PROJECT}) "
                    f"reached for project: {project}"
                )
        else:
            global_count = len([s for s in existing_subs if s.get("project") is None])
            if global_count >= MAX_SUBSCRIPTIONS_GLOBAL:
                raise ValueError(
                    f"Maximum global subscriptions ({MAX_SUBSCRIPTIONS_GLOBAL}) reached"
                )

        # Create subscription
        subscription_id = self.db.create_webhook_subscription(
            url=url,
            secret=secret,
            event_types=event_types,
            project=project,
            description=description,
        )

        # Log with partial secret for debugging
        secret_hint = f"{secret[:4]}...{secret[-4:]}"
        logger.info(
            "Registered webhook subscription %d for %s (secret: %s)",
            subscription_id,
            url,
            secret_hint,
        )

        return {
            "status": "registered",
            "subscription_id": subscription_id,
            "url": url,
            "event_types": event_types,
            "project": project,
        }

    def unregister(self, subscription_id: int) -> dict:
        """Unregister a webhook subscription.

        Args:
            subscription_id: ID of the subscription to remove

        Returns:
            Dict with status

        Raises:
            ValueError: If subscription not found
        """
        deleted = self.db.delete_webhook_subscription(subscription_id)
        if not deleted:
            raise ValueError(f"Subscription not found: {subscription_id}")

        logger.info("Unregistered webhook subscription %d", subscription_id)

        return {
            "status": "unregistered",
            "subscription_id": subscription_id,
        }

    def list_subscriptions(self, project: str | None = None) -> list[dict]:
        """List webhook subscriptions.

        Args:
            project: Optional project filter

        Returns:
            List of subscription dicts (without secrets)
        """
        subscriptions = self.db.list_webhook_subscriptions(project=project)

        # Remove secrets from response
        for sub in subscriptions:
            del sub["secret"]

        return subscriptions

    def fire_event(
        self,
        event_type: str,
        project: str | None,
        data: dict[str, Any],
    ) -> None:
        """Fire a webhook event asynchronously.

        This method is non-blocking and returns immediately.
        Event delivery happens in a background thread pool.

        Args:
            event_type: Event type (e.g., "task.created")
            project: Project name (None for global events)
            data: Event data
        """
        # Check if webhooks are enabled
        if not self._config.webhooks_enabled:
            logger.debug("Webhooks disabled, skipping event %s", event_type)
            return

        # Check if shutdown is in progress
        if self._shutdown_event.is_set():
            logger.warning("Webhook manager is shutting down, skipping event %s", event_type)
            return

        # Get matching subscriptions
        subscriptions = self.db.get_active_subscriptions_for_event(
            event_type, project or ""
        )

        if not subscriptions:
            logger.debug("No subscriptions for event %s in project %s", event_type, project)
            return

        # Generate event ID and timestamp
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        # Build payload
        payload = {
            "event_id": event_id,
            "event_type": event_type,
            "project": project,
            "timestamp": timestamp,
            "data": data,
        }

        # Schedule deliveries using thread pool
        for subscription in subscriptions:
            self._executor.submit(
                self._deliver_sync,
                event_id,
                event_type,
                payload,
                subscription,
            )

    def _deliver_sync(
        self,
        event_id: str,
        event_type: str,
        payload: dict,
        subscription: dict,
    ) -> None:
        """Deliver a webhook synchronously.

        Args:
            event_id: Unique event ID
            event_type: Event type
            payload: Event payload
            subscription: Subscription dict
        """
        url = subscription["url"]
        secret = subscription["secret"]
        subscription_id = subscription["id"]

        # Serialize payload
        payload_json = json.dumps(payload)
        payload_bytes = payload_json.encode("utf-8")

        # Generate HMAC signature
        signature = self._generate_signature(payload_bytes, secret)

        # Build headers
        headers = {
            "Content-Type": "application/json",
            "X-Vibe-Signature": f"sha256={signature}",
            "X-Vibe-Event": event_type,
            "X-Vibe-Event-ID": event_id,
        }

        status_code = None
        success = False
        error_message = None

        try:
            with httpx.Client(timeout=DELIVERY_TIMEOUT) as client:
                response = client.post(url, content=payload_bytes, headers=headers)
                status_code = response.status_code
                success = 200 <= status_code < 300

                if not success:
                    error_message = f"HTTP {status_code}: {response.text[:200]}"
                    logger.warning(
                        "Webhook delivery failed for subscription %d: %s",
                        subscription_id,
                        error_message,
                    )
                else:
                    logger.info(
                        "Webhook delivered: event=%s subscription=%d url=%s",
                        event_id,
                        subscription_id,
                        url,
                    )

        except httpx.TimeoutException:
            error_message = "Request timed out"
            logger.warning(
                "Webhook delivery timed out for subscription %d: %s",
                subscription_id,
                url,
            )
        except httpx.RequestError as e:
            error_message = str(e)
            logger.warning(
                "Webhook delivery error for subscription %d: %s",
                subscription_id,
                error_message,
            )
        except Exception:
            error_message = "Unexpected error during delivery"
            logger.exception(
                "Unexpected error delivering webhook %s to subscription %d",
                event_id,
                subscription_id,
            )

        # Log delivery attempt
        try:
            self.db.log_webhook_delivery(
                subscription_id=subscription_id,
                event_type=event_type,
                event_id=event_id,
                payload=payload_json,
                status_code=status_code,
                success=success,
                error_message=error_message,
            )
        except Exception:
            logger.exception("Failed to log webhook delivery for event %s", event_id)

    @staticmethod
    def _generate_signature(payload: bytes, secret: str) -> str:
        """Generate HMAC-SHA256 signature for a payload.

        Args:
            payload: Raw payload bytes
            secret: Secret key

        Returns:
            Hex-encoded signature
        """
        return hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()


# =============================================================================
# DEPRECATED: Global singleton pattern - will be removed after DI migration
# =============================================================================
_webhook_manager: WebhookManager | None = None
_webhook_manager_lock = threading.Lock()


def get_webhook_manager() -> WebhookManager:
    """DEPRECATED: Get or create the global webhook manager instance.

    Use WebhookManager(db, config) with dependency injection instead.
    """
    warnings.warn(
        "get_webhook_manager() is deprecated. Use WebhookManager(db, config) "
        "and dependency injection instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _webhook_manager
    if _webhook_manager is None:
        with _webhook_manager_lock:
            # Double-check after acquiring lock
            if _webhook_manager is None:
                config = get_config()
                db = Database(config.vibe_db)
                db.initialize()
                _webhook_manager = WebhookManager(db, config)
    return _webhook_manager


def reset_webhook_manager() -> None:
    """DEPRECATED: Reset the global webhook manager (for testing).

    Create fresh WebhookManager instances directly instead.
    """
    warnings.warn(
        "reset_webhook_manager() is deprecated. Create fresh WebhookManager instances instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _webhook_manager
    with _webhook_manager_lock:
        if _webhook_manager is not None:
            _webhook_manager.shutdown(timeout=2.0)
        _webhook_manager = None
