"""Tests for sync module."""

import threading
import time
from unittest.mock import MagicMock

import pytest

from vibe_mcp.sync import SyncManager


class TestSyncManager:
    """Tests for SyncManager class."""

    def test_init_requires_positive_interval(self):
        """Test SyncManager requires positive interval."""
        indexer = MagicMock()
        with pytest.raises(ValueError, match="Sync interval must be positive"):
            SyncManager(indexer, 0)
        with pytest.raises(ValueError, match="Sync interval must be positive"):
            SyncManager(indexer, -1)

    def test_init_accepts_positive_interval(self):
        """Test SyncManager accepts positive interval."""
        indexer = MagicMock()
        manager = SyncManager(indexer, 30)
        assert manager._interval == 30

    def test_start_creates_daemon_thread(self):
        """Test start() creates a daemon thread."""
        indexer = MagicMock()
        indexer.sync.return_value = (0, 0, 0)
        manager = SyncManager(indexer, 1)

        manager.start()
        try:
            assert manager._thread is not None
            assert manager._thread.is_alive()
            assert manager._thread.daemon is True
            assert manager._thread.name == "vibe-sync"
        finally:
            manager.stop()

    def test_start_idempotent(self):
        """Test calling start() twice doesn't create duplicate threads."""
        indexer = MagicMock()
        indexer.sync.return_value = (0, 0, 0)
        manager = SyncManager(indexer, 1)

        manager.start()
        thread1 = manager._thread
        manager.start()
        thread2 = manager._thread

        try:
            assert thread1 is thread2
        finally:
            manager.stop()

    def test_stop_terminates_thread(self):
        """Test stop() terminates the sync thread."""
        indexer = MagicMock()
        indexer.sync.return_value = (0, 0, 0)
        manager = SyncManager(indexer, 1)

        manager.start()
        assert manager._thread.is_alive()

        manager.stop()
        assert manager._thread is None

    def test_stop_idempotent(self):
        """Test calling stop() when not running is safe."""
        indexer = MagicMock()
        manager = SyncManager(indexer, 1)
        manager.stop()  # Should not raise

    def test_sync_called_after_interval(self):
        """Test sync() is called after the interval elapses."""
        indexer = MagicMock()
        indexer.sync.return_value = (1, 2, 3)
        manager = SyncManager(indexer, 1)

        manager.start()
        # Wait for at least one sync cycle
        time.sleep(1.5)
        manager.stop()

        assert indexer.sync.call_count >= 1

    def test_sync_exception_doesnt_stop_thread(self):
        """Test exceptions in sync() don't stop the thread."""
        indexer = MagicMock()
        call_count = 0

        def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated error")
            return (0, 0, 0)

        indexer.sync.side_effect = side_effect
        manager = SyncManager(indexer, 1)

        manager.start()
        # Wait for multiple sync cycles
        time.sleep(2.5)
        manager.stop()

        # Should have continued after the exception
        assert call_count >= 2
