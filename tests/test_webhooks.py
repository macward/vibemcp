"""Tests for webhook functionality."""

import hashlib
import hmac
import json
import time
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vibe_mcp.config import Config, reset_config
from vibe_mcp.indexer import Database
from vibe_mcp.webhooks import (
    EVENT_TYPES,
    MAX_SUBSCRIPTIONS_PER_PROJECT,
    WebhookManager,
    _is_safe_url,
    get_webhook_manager,
    reset_webhook_manager,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.initialize()
    return db


@pytest.fixture
def test_config(tmp_path):
    """Create a test config with webhooks enabled."""
    vibe_root = tmp_path / ".vibe"
    vibe_root.mkdir(exist_ok=True)
    return Config(
        vibe_root=vibe_root,
        vibe_db=tmp_path / "test.db",
        vibe_port=8765,
        auth_token=None,
        read_only=False,
        webhooks_enabled=True,
    )


@pytest.fixture
def webhook_manager(test_db, test_config):
    """Create a webhook manager with test database and config."""
    return WebhookManager(test_db, test_config)


def _reset_singletons_silent():
    """Reset config and webhook manager singletons without triggering deprecation warnings.

    This is needed for tests that rely on the singleton pattern still used in some modules.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        reset_config()
        reset_webhook_manager()


@pytest.fixture
def test_vibe_env(tmp_path, monkeypatch):
    """Set up test environment variables."""
    vibe_root = tmp_path / ".vibe"
    vibe_root.mkdir()
    db_path = tmp_path / "test.db"

    monkeypatch.setenv("VIBE_ROOT", str(vibe_root))
    monkeypatch.setenv("VIBE_DB", str(db_path))
    monkeypatch.setenv("VIBE_WEBHOOKS_ENABLED", "true")

    # Reset global state (needed for integration tests with tools_write)
    _reset_singletons_silent()

    yield vibe_root

    # Cleanup
    _reset_singletons_silent()


class TestWebhookRegistration:
    """Tests for webhook subscription management."""

    def test_register_webhook(self, webhook_manager):
        """Test registering a webhook subscription."""
        result = webhook_manager.register(
            url="https://example.com/webhook",
            secret="a" * 32,
            event_types=["task.created", "task.updated"],
            project="test-project",
            description="Test webhook",
        )

        assert result["status"] == "registered"
        assert result["subscription_id"] > 0
        assert result["url"] == "https://example.com/webhook"
        assert result["event_types"] == ["task.created", "task.updated"]
        assert result["project"] == "test-project"

    def test_register_webhook_all_projects(self, webhook_manager):
        """Test registering a webhook for all projects."""
        result = webhook_manager.register(
            url="https://example.com/webhook",
            secret="a" * 32,
            event_types=["*"],
        )

        assert result["status"] == "registered"
        assert result["project"] is None

    def test_register_webhook_invalid_url(self, webhook_manager):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValueError, match="URL must start with"):
            webhook_manager.register(
                url="ftp://example.com/webhook",
                secret="a" * 32,
                event_types=["task.created"],
            )

    def test_register_webhook_short_secret(self, webhook_manager):
        """Test that short secrets are rejected."""
        with pytest.raises(ValueError, match="at least 32 characters"):
            webhook_manager.register(
                url="https://example.com/webhook",
                secret="tooshort",
                event_types=["task.created"],
            )

    def test_register_webhook_invalid_event_type(self, webhook_manager):
        """Test that invalid event types are rejected."""
        with pytest.raises(ValueError, match="Invalid event types"):
            webhook_manager.register(
                url="https://example.com/webhook",
                secret="a" * 32,
                event_types=["invalid.event"],
            )

    def test_register_webhook_empty_event_types(self, webhook_manager):
        """Test that empty event types are rejected."""
        with pytest.raises(ValueError, match="At least one event type"):
            webhook_manager.register(
                url="https://example.com/webhook",
                secret="a" * 32,
                event_types=[],
            )

    def test_unregister_webhook(self, webhook_manager):
        """Test unregistering a webhook."""
        # Register first
        register_result = webhook_manager.register(
            url="https://example.com/webhook",
            secret="a" * 32,
            event_types=["task.created"],
        )
        subscription_id = register_result["subscription_id"]

        # Unregister
        result = webhook_manager.unregister(subscription_id)
        assert result["status"] == "unregistered"
        assert result["subscription_id"] == subscription_id

        # Should not appear in listings
        subscriptions = webhook_manager.list_subscriptions()
        assert len(subscriptions) == 0

    def test_unregister_nonexistent(self, webhook_manager):
        """Test unregistering a non-existent subscription."""
        with pytest.raises(ValueError, match="not found"):
            webhook_manager.unregister(999)

    def test_list_subscriptions(self, webhook_manager):
        """Test listing subscriptions."""
        # Register multiple webhooks
        webhook_manager.register(
            url="https://example.com/webhook1",
            secret="a" * 32,
            event_types=["task.created"],
            project="project1",
        )
        webhook_manager.register(
            url="https://example.com/webhook2",
            secret="b" * 32,
            event_types=["task.updated"],
            project="project2",
        )
        webhook_manager.register(
            url="https://example.com/webhook3",
            secret="c" * 32,
            event_types=["*"],
        )

        # List all
        subscriptions = webhook_manager.list_subscriptions()
        assert len(subscriptions) == 3

        # Secrets should not be included
        for sub in subscriptions:
            assert "secret" not in sub

    def test_list_subscriptions_by_project(self, webhook_manager):
        """Test listing subscriptions filtered by project."""
        webhook_manager.register(
            url="https://example.com/webhook1",
            secret="a" * 32,
            event_types=["task.created"],
            project="project1",
        )
        webhook_manager.register(
            url="https://example.com/webhook2",
            secret="b" * 32,
            event_types=["task.updated"],
            project="project2",
        )
        webhook_manager.register(
            url="https://example.com/webhook3",
            secret="c" * 32,
            event_types=["*"],  # Global
        )

        # Filter by project1
        subscriptions = webhook_manager.list_subscriptions(project="project1")
        assert len(subscriptions) == 2  # project1 + global


class TestWebhookDelivery:
    """Tests for webhook event firing and delivery."""

    def test_fire_event_no_subscriptions(self, webhook_manager):
        """Test firing event with no matching subscriptions."""
        # Should not raise
        webhook_manager.fire_event(
            event_type="task.created",
            project="test-project",
            data={"title": "Test Task"},
        )

    @patch("vibe_mcp.webhooks.httpx.Client")
    def test_fire_event_with_subscription(self, mock_client_class, webhook_manager):
        """Test firing event with a matching subscription."""
        # Register webhook
        webhook_manager.register(
            url="https://example.com/webhook",
            secret="a" * 32,
            event_types=["task.created"],
            project="test-project",
        )

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Fire event
        webhook_manager.fire_event(
            event_type="task.created",
            project="test-project",
            data={"title": "Test Task"},
        )

        # Wait for background thread
        time.sleep(0.5)

        # Verify HTTP call was made
        assert mock_client.post.called
        call_args = mock_client.post.call_args
        assert call_args[1]["headers"]["X-Vibe-Event"] == "task.created"
        assert "X-Vibe-Signature" in call_args[1]["headers"]

    @patch("vibe_mcp.webhooks.httpx.Client")
    def test_fire_event_wildcard_subscription(self, mock_client_class, webhook_manager):
        """Test that wildcard subscriptions receive all events."""
        # Register wildcard webhook
        webhook_manager.register(
            url="https://example.com/webhook",
            secret="a" * 32,
            event_types=["*"],
        )

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Fire event
        webhook_manager.fire_event(
            event_type="doc.created",
            project="any-project",
            data={"filename": "test.md"},
        )

        # Wait for background thread
        time.sleep(0.5)

        # Verify HTTP call was made
        assert mock_client.post.called

    def test_hmac_signature(self, webhook_manager):
        """Test HMAC signature generation."""
        payload = b'{"event":"test"}'
        secret = "a" * 32

        signature = webhook_manager._generate_signature(payload, secret)

        # Verify signature
        expected = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert signature == expected

    @patch("vibe_mcp.webhooks.httpx.Client")
    def test_delivery_logs_success(self, mock_client_class, webhook_manager):
        """Test that successful deliveries are logged."""
        # Register webhook
        result = webhook_manager.register(
            url="https://example.com/webhook",
            secret="a" * 32,
            event_types=["task.created"],
            project="test-project",
        )
        subscription_id = result["subscription_id"]

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Fire event
        webhook_manager.fire_event(
            event_type="task.created",
            project="test-project",
            data={"title": "Test Task"},
        )

        # Wait for background thread
        time.sleep(0.5)

        # Check logs
        logs = webhook_manager.db.get_webhook_logs(subscription_id=subscription_id)
        assert len(logs) == 1
        assert logs[0]["success"] is True
        assert logs[0]["status_code"] == 200

    @patch("vibe_mcp.webhooks.httpx.Client")
    def test_delivery_logs_failure(self, mock_client_class, webhook_manager):
        """Test that failed deliveries are logged."""
        # Register webhook
        result = webhook_manager.register(
            url="https://example.com/webhook",
            secret="a" * 32,
            event_types=["task.created"],
            project="test-project",
        )
        subscription_id = result["subscription_id"]

        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Fire event
        webhook_manager.fire_event(
            event_type="task.created",
            project="test-project",
            data={"title": "Test Task"},
        )

        # Wait for background thread
        time.sleep(0.5)

        # Check logs
        logs = webhook_manager.db.get_webhook_logs(subscription_id=subscription_id)
        assert len(logs) == 1
        assert logs[0]["success"] is False
        assert logs[0]["status_code"] == 500
        assert "500" in logs[0]["error_message"]


class TestWebhookIntegration:
    """Integration tests for webhooks with write tools."""

    def test_create_task_fires_webhook(self, test_vibe_env):
        """Test that creating a task fires a webhook."""
        from fastmcp import FastMCP

        from vibe_mcp.indexer import Indexer
        from vibe_mcp.tools_write import register_tools_write

        # Create test project
        test_project = test_vibe_env / "test_project"
        test_project.mkdir()

        # Create fresh config, indexer, and webhook manager
        config = Config.from_env()
        db = Database(config.vibe_db)
        db.initialize()
        indexer = Indexer(config.vibe_root, config.vibe_db)
        indexer.initialize()
        manager = WebhookManager(db, config)

        # Register webhook
        manager.register(
            url="https://example.com/webhook",
            secret="a" * 32,
            event_types=["task.created"],
            project="test_project",
        )

        # Mock the _deliver_sync method to capture calls
        delivery_calls = []
        original_deliver = manager._deliver_sync

        def mock_deliver(event_id, event_type, payload, subscription):
            delivery_calls.append({
                "event_id": event_id,
                "event_type": event_type,
                "payload": payload,
                "subscription": subscription,
            })

        manager._deliver_sync = mock_deliver

        # Register tools with the webhook manager
        mcp = FastMCP()
        register_tools_write(mcp, config, indexer, webhook_mgr=manager)

        # Get create_task tool
        create_task = None
        for tool in mcp._tool_manager._tools.values():
            if tool.fn.__name__ == "tool_create_task":
                create_task = tool.fn
                break

        try:
            # Create task
            create_task(
                project="test_project",
                title="Test Task",
                objective="Test objective",
            )

            # Wait for background thread
            time.sleep(0.5)

            # Verify webhook was called
            assert len(delivery_calls) == 1
            call = delivery_calls[0]
            assert call["event_type"] == "task.created"
            assert call["payload"]["project"] == "test_project"
            assert call["payload"]["data"]["title"] == "Test Task"
        finally:
            manager._deliver_sync = original_deliver
            manager.shutdown(timeout=1.0)
            indexer.close()
            db.close()

    def test_webhooks_disabled(self, test_vibe_env, monkeypatch):
        """Test that webhooks are not fired when no webhook manager is provided."""
        from fastmcp import FastMCP

        from vibe_mcp.indexer import Indexer
        from vibe_mcp.tools_write import register_tools_write

        # Create test project
        test_project = test_vibe_env / "test_project"
        test_project.mkdir()

        # Create fresh config and indexer, but no webhook manager
        config = Config.from_env()
        indexer = Indexer(config.vibe_root, config.vibe_db)
        indexer.initialize()

        # Register tools without webhook manager
        mcp = FastMCP()
        register_tools_write(mcp, config, indexer, webhook_mgr=None)

        # Get create_task tool
        create_task = None
        for tool in mcp._tool_manager._tools.values():
            if tool.fn.__name__ == "tool_create_task":
                create_task = tool.fn
                break

        try:
            # Create task - should not raise even without webhook manager
            result = create_task(
                project="test_project",
                title="Test Task",
                objective="Test objective",
            )

            assert result["status"] == "created"
        finally:
            indexer.close()


class TestSSRFProtection:
    """Tests for SSRF (Server-Side Request Forgery) protection."""

    def test_reject_localhost_url(self, webhook_manager):
        """Test that localhost URLs are rejected."""
        with pytest.raises(ValueError, match="Blocked hostname"):
            webhook_manager.register(
                url="http://localhost:8080/webhook",
                secret="a" * 32,
                event_types=["task.created"],
            )

    def test_reject_127_0_0_1_url(self, webhook_manager):
        """Test that 127.0.0.1 URLs are rejected."""
        with pytest.raises(ValueError, match="Blocked hostname"):
            webhook_manager.register(
                url="http://127.0.0.1:8080/webhook",
                secret="a" * 32,
                event_types=["task.created"],
            )

    def test_reject_0_0_0_0_url(self, webhook_manager):
        """Test that 0.0.0.0 URLs are rejected."""
        with pytest.raises(ValueError, match="Blocked hostname"):
            webhook_manager.register(
                url="http://0.0.0.0:8080/webhook",
                secret="a" * 32,
                event_types=["task.created"],
            )

    def test_reject_metadata_google_url(self, webhook_manager):
        """Test that cloud metadata URLs are rejected."""
        with pytest.raises(ValueError, match="Blocked hostname"):
            webhook_manager.register(
                url="http://metadata.google.internal/computeMetadata/v1/",
                secret="a" * 32,
                event_types=["task.created"],
            )

    def test_is_safe_url_function(self):
        """Test the _is_safe_url helper function directly."""
        # Safe URLs
        is_safe, _ = _is_safe_url("https://example.com/webhook")
        assert is_safe is True

        is_safe, _ = _is_safe_url("https://api.github.com/webhook")
        assert is_safe is True

        # Blocked hostnames
        is_safe, msg = _is_safe_url("http://localhost/webhook")
        assert is_safe is False
        assert "Blocked hostname" in msg

        is_safe, msg = _is_safe_url("http://127.0.0.1/webhook")
        assert is_safe is False
        assert "Blocked hostname" in msg

        # Invalid schemes
        is_safe, msg = _is_safe_url("ftp://example.com/file")
        assert is_safe is False
        assert "scheme" in msg.lower()

    def test_accept_valid_external_url(self, webhook_manager):
        """Test that valid external URLs are accepted."""
        # This should not raise
        result = webhook_manager.register(
            url="https://example.com/webhook",
            secret="a" * 32,
            event_types=["task.created"],
        )
        assert result["status"] == "registered"


class TestShutdown:
    """Tests for graceful shutdown."""

    def test_shutdown_prevents_new_events(self, webhook_manager):
        """Test that shutdown prevents new events from being processed."""
        # Register a webhook
        webhook_manager.register(
            url="https://example.com/webhook",
            secret="a" * 32,
            event_types=["task.created"],
        )

        # Shutdown the manager
        webhook_manager.shutdown(timeout=1.0)

        # Fire event after shutdown - should not raise but should be skipped
        webhook_manager.fire_event(
            event_type="task.created",
            project="test",
            data={"title": "Test"},
        )

        # No deliveries should have been scheduled
        time.sleep(0.2)
        logs = webhook_manager.db.get_webhook_logs()
        assert len(logs) == 0


class TestSubscriptionLimits:
    """Tests for subscription limits (anti-spam/DoS)."""

    def test_project_subscription_limit(self, webhook_manager):
        """Test that project subscription limits are enforced."""
        from vibe_mcp.webhooks import MAX_SUBSCRIPTIONS_PER_PROJECT

        # Register up to the limit
        for i in range(MAX_SUBSCRIPTIONS_PER_PROJECT):
            webhook_manager.register(
                url=f"https://example{i}.com/webhook",
                secret="a" * 32,
                event_types=["task.created"],
                project="test-project",
            )

        # Next one should fail
        with pytest.raises(ValueError, match="Maximum subscriptions"):
            webhook_manager.register(
                url="https://overflow.com/webhook",
                secret="a" * 32,
                event_types=["task.created"],
                project="test-project",
            )

    def test_different_projects_have_separate_limits(self, webhook_manager):
        """Test that different projects have independent limits."""
        # Register for project1
        webhook_manager.register(
            url="https://example1.com/webhook",
            secret="a" * 32,
            event_types=["task.created"],
            project="project1",
        )

        # Should still be able to register for project2
        result = webhook_manager.register(
            url="https://example2.com/webhook",
            secret="a" * 32,
            event_types=["task.created"],
            project="project2",
        )
        assert result["status"] == "registered"


class TestEventTypes:
    """Tests for event type validation."""

    def test_all_event_types_valid(self):
        """Verify all documented event types are in the set."""
        expected = {
            "task.created",
            "task.updated",
            "doc.created",
            "doc.updated",
            "session.logged",
            "plan.created",
            "plan.updated",
            "project.initialized",
            "index.reindexed",
            "*",
        }
        assert EVENT_TYPES == expected


class TestDatabaseWebhooks:
    """Tests for database webhook operations."""

    def test_create_and_get_subscription(self, test_db):
        """Test creating and retrieving a subscription."""
        sub_id = test_db.create_webhook_subscription(
            url="https://example.com/webhook",
            secret="test-secret",
            event_types=["task.created"],
            project="test-project",
            description="Test subscription",
        )

        sub = test_db.get_webhook_subscription(sub_id)
        assert sub is not None
        assert sub["url"] == "https://example.com/webhook"
        assert sub["secret"] == "test-secret"
        assert sub["event_types"] == ["task.created"]
        assert sub["project"] == "test-project"
        assert sub["description"] == "Test subscription"
        assert sub["active"] is True

    def test_delete_subscription(self, test_db):
        """Test deleting a subscription."""
        sub_id = test_db.create_webhook_subscription(
            url="https://example.com/webhook",
            secret="test-secret",
            event_types=["task.created"],
        )

        assert test_db.delete_webhook_subscription(sub_id) is True
        assert test_db.get_webhook_subscription(sub_id) is None

    def test_delete_nonexistent_subscription(self, test_db):
        """Test deleting a non-existent subscription."""
        assert test_db.delete_webhook_subscription(999) is False

    def test_list_subscriptions_by_project(self, test_db):
        """Test listing subscriptions filtered by project."""
        test_db.create_webhook_subscription(
            url="https://example.com/webhook1",
            secret="test-secret",
            event_types=["task.created"],
            project="project1",
        )
        test_db.create_webhook_subscription(
            url="https://example.com/webhook2",
            secret="test-secret",
            event_types=["task.updated"],
            project="project2",
        )
        test_db.create_webhook_subscription(
            url="https://example.com/webhook3",
            secret="test-secret",
            event_types=["*"],
            project=None,  # Global
        )

        # Get subscriptions for project1 (should include project1 + global)
        subs = test_db.list_webhook_subscriptions(project="project1")
        assert len(subs) == 2

    def test_get_active_subscriptions_for_event(self, test_db):
        """Test getting active subscriptions matching an event."""
        test_db.create_webhook_subscription(
            url="https://example.com/webhook1",
            secret="test-secret",
            event_types=["task.created"],
            project="test-project",
        )
        test_db.create_webhook_subscription(
            url="https://example.com/webhook2",
            secret="test-secret",
            event_types=["task.updated"],
            project="test-project",
        )
        test_db.create_webhook_subscription(
            url="https://example.com/webhook3",
            secret="test-secret",
            event_types=["*"],
        )

        # Get subscriptions for task.created
        subs = test_db.get_active_subscriptions_for_event("task.created", "test-project")
        assert len(subs) == 2  # task.created + wildcard

        # Get subscriptions for task.updated
        subs = test_db.get_active_subscriptions_for_event("task.updated", "test-project")
        assert len(subs) == 2  # task.updated + wildcard

    def test_log_webhook_delivery(self, test_db):
        """Test logging webhook delivery."""
        sub_id = test_db.create_webhook_subscription(
            url="https://example.com/webhook",
            secret="test-secret",
            event_types=["task.created"],
        )

        log_id = test_db.log_webhook_delivery(
            subscription_id=sub_id,
            event_type="task.created",
            event_id="test-event-id",
            payload='{"test": true}',
            status_code=200,
            success=True,
        )

        logs = test_db.get_webhook_logs(subscription_id=sub_id)
        assert len(logs) == 1
        assert logs[0]["id"] == log_id
        assert logs[0]["event_type"] == "task.created"
        assert logs[0]["success"] is True
        assert logs[0]["status_code"] == 200

    def test_webhook_logs_cascade_delete(self, test_db):
        """Test that deleting subscription cascades to logs."""
        sub_id = test_db.create_webhook_subscription(
            url="https://example.com/webhook",
            secret="test-secret",
            event_types=["task.created"],
        )

        test_db.log_webhook_delivery(
            subscription_id=sub_id,
            event_type="task.created",
            event_id="test-event-id",
            payload='{"test": true}',
            status_code=200,
            success=True,
        )

        # Delete subscription
        test_db.delete_webhook_subscription(sub_id)

        # Logs should be deleted too
        logs = test_db.get_webhook_logs(subscription_id=sub_id)
        assert len(logs) == 0
