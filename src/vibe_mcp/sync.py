"""Background sync manager for automatic index updates.

Runs a daemon thread that periodically calls indexer.sync() to keep
the SQLite index in sync with filesystem changes made outside of MCP tools.
"""

import logging
import threading
import time

from vibe_mcp.indexer import Indexer

logger = logging.getLogger(__name__)


class SyncManager:
    """Manages periodic background sync of the index with the filesystem.

    The sync thread is a daemon, so it automatically terminates when the
    main process exits.
    """

    def __init__(self, indexer: Indexer, interval: int):
        """Initialize the sync manager.

        Args:
            indexer: The indexer instance to sync.
            interval: Sync interval in seconds. Must be > 0.
        """
        if interval <= 0:
            raise ValueError(f"Sync interval must be positive, got {interval}")

        self._indexer = indexer
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background sync thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Sync thread already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._sync_loop,
            name="vibe-sync",
            daemon=True,
        )
        self._thread.start()
        logger.info("Sync manager started (interval: %ds)", self._interval)

    def stop(self) -> None:
        """Stop the background sync thread.

        Blocks until the thread terminates (up to one interval).
        """
        if self._thread is None or not self._thread.is_alive():
            return

        self._stop_event.set()
        self._thread.join(timeout=self._interval + 1)
        if self._thread.is_alive():
            logger.warning("Sync thread did not stop cleanly")
        else:
            logger.info("Sync manager stopped")
        self._thread = None

    def _sync_loop(self) -> None:
        """Main sync loop - runs in background thread."""
        logger.debug("Sync loop started")

        while not self._stop_event.is_set():
            # Sleep first, then sync (allows immediate shutdown on start)
            if self._stop_event.wait(timeout=self._interval):
                break  # Stop event was set

            try:
                added, updated, deleted = self._indexer.sync()
                if added or updated or deleted:
                    logger.info(
                        "Auto-sync: %d added, %d updated, %d deleted",
                        added,
                        updated,
                        deleted,
                    )
                else:
                    logger.debug("Auto-sync: no changes detected")
            except Exception:
                logger.exception("Error during auto-sync")

        logger.debug("Sync loop stopped")
