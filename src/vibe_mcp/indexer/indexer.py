"""Main indexer that coordinates syncing filesystem to SQLite."""

import logging
import threading
from pathlib import Path

from vibe_mcp.indexer.chunker import chunk_document
from vibe_mcp.indexer.database import Database
from vibe_mcp.indexer.models import Chunk, Document, Project, SearchResult
from vibe_mcp.indexer.parser import parse_frontmatter
from vibe_mcp.indexer.walker import FileInfo, walk_vibe_root

logger = logging.getLogger(__name__)


class Indexer:
    """
    Indexer that syncs the .vibe filesystem with SQLite FTS5.

    The filesystem is always the source of truth. SQLite is a derived index
    that can be regenerated at any time.

    Thread Safety:
        Write operations (reindex, sync, index_project, index_file) are protected
        by a lock to prevent concurrent modifications. Read operations are safe
        to call from multiple threads as the Database uses thread-local connections.
    """

    def __init__(self, vibe_root: Path, db_path: Path):
        """
        Initialize the indexer.

        Args:
            vibe_root: Path to the .vibe directory
            db_path: Path to the SQLite database file
        """
        self.vibe_root = vibe_root
        self.db = Database(db_path)
        self._initialized = False
        self._write_lock = threading.Lock()

    def initialize(self) -> None:
        """Initialize the database schema."""
        self.db.initialize()
        self._initialized = True

    def close(self) -> None:
        """Close database connections."""
        self.db.close()

    def _ensure_initialized(self) -> None:
        """Ensure the database is initialized."""
        if not self._initialized:
            self.initialize()

    def reindex(self) -> int:
        """
        Perform a full reindex of all projects.

        Returns the number of documents indexed.
        """
        self._ensure_initialized()
        with self._write_lock:
            logger.info("Starting full reindex of %s", self.vibe_root)

            # Clear all data
            self.db.clear()

            count = 0
            for file_info in walk_vibe_root(self.vibe_root):
                self._index_file(file_info)
                count += 1

            logger.info("Reindex complete: %d documents indexed", count)
            return count

    def sync(self) -> tuple[int, int, int]:
        """
        Sync the index with filesystem changes.

        Uses mtime as fast-path and content hash for edge cases.

        Returns:
            Tuple of (added, updated, deleted) counts.
        """
        self._ensure_initialized()
        with self._write_lock:
            logger.debug("Syncing index with filesystem")

            added = 0
            updated = 0
            deleted = 0

            # Track all paths we see in the filesystem
            seen_paths: set[str] = set()

            # Process all files
            for file_info in walk_vibe_root(self.vibe_root):
                seen_paths.add(file_info.relative_path)

                # Check if document exists and if it has changed
                existing_mtime = self.db.get_document_mtime(file_info.relative_path)

                if existing_mtime is None:
                    # New file
                    self._index_file(file_info)
                    added += 1
                elif abs(file_info.mtime - existing_mtime) > 0.001:  # mtime changed
                    # Check content hash for actual change
                    existing_hash = self.db.get_document_hash(file_info.relative_path)
                    if existing_hash != file_info.content_hash:
                        # Content actually changed
                        self._index_file(file_info)
                        updated += 1
                    else:
                        # Only mtime changed, update it
                        doc = self.db.get_document_by_path(file_info.relative_path)
                        if doc:
                            doc.mtime = file_info.mtime
                            self.db.upsert_document(doc)

            # Find deleted files
            all_projects = self.db.list_projects()
            for project in all_projects:
                indexed_paths = self.db.get_indexed_paths(project.name)
                for path in indexed_paths:
                    if path not in seen_paths:
                        self.db.delete_document(path)
                        deleted += 1

            logger.debug(
                "Sync complete: %d added, %d updated, %d deleted",
                added,
                updated,
                deleted,
            )
            return added, updated, deleted

    def index_project(self, project_path: Path) -> int:
        """
        Index a single project.

        Args:
            project_path: Path to the project directory

        Returns:
            Number of documents indexed.
        """
        self._ensure_initialized()
        with self._write_lock:
            project_name = project_path.name
            logger.info("Indexing project: %s", project_name)

            count = 0
            for file_info in walk_vibe_root(project_path.parent):
                if file_info.project_name == project_name:
                    self._index_file(file_info)
                    count += 1

            logger.info("Project %s: %d documents indexed", project_name, count)
            return count

    def index_file(self, file_info: FileInfo) -> None:
        """
        Index a single file (thread-safe).

        Args:
            file_info: FileInfo object with file metadata.
        """
        with self._write_lock:
            self._index_file(file_info)

    def _index_file(self, file_info: FileInfo) -> None:
        """Index a single file."""
        # Validate path is within vibe_root (prevent symlink attacks)
        try:
            resolved_path = file_info.path.resolve()
            resolved_root = self.vibe_root.resolve()
            if not str(resolved_path).startswith(str(resolved_root) + "/"):
                logger.warning(
                    "Skipping file outside vibe root: %s", file_info.relative_path
                )
                return
        except OSError as e:
            logger.warning("Cannot resolve path %s: %s", file_info.relative_path, e)
            return

        # Get or create project
        project_path = str(self.vibe_root / file_info.project_name)
        project_id = self.db.get_or_create_project(file_info.project_name, project_path)

        # Read content with error handling for encoding issues
        try:
            content = file_info.path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            logger.warning(
                "Skipping file with invalid UTF-8 encoding: %s (%s)",
                file_info.relative_path,
                e,
            )
            return

        # Parse frontmatter
        metadata, body = parse_frontmatter(content, file_info.relative_path)

        # Format updated date if present
        updated_str = None
        if metadata.updated:
            if isinstance(metadata.updated, str):
                updated_str = metadata.updated
            else:
                updated_str = str(metadata.updated)

        # Create document
        doc = Document(
            project_id=project_id,
            path=file_info.relative_path,
            folder=file_info.folder,
            filename=file_info.filename,
            type=metadata.type,
            status=metadata.status,
            owner=metadata.owner,
            tags=metadata.tags or [],
            feature=metadata.feature,
            content_hash=file_info.content_hash,
            mtime=file_info.mtime,
            updated=updated_str,
        )

        # Upsert document
        document_id = self.db.upsert_document(doc)

        # Delete existing chunks and create new ones
        self.db.delete_chunks_for_document(document_id)

        # Chunk the content
        chunker_chunks = chunk_document(content)

        # Convert chunker chunks to model chunks
        model_chunks: list[Chunk] = []
        for c in chunker_chunks:
            model_chunk = Chunk(
                document_id=document_id,
                heading=c.heading,
                heading_level=c.heading_level,
                content=c.content,
                chunk_order=c.chunk_order,
                char_offset=c.char_offset,
                is_priority_heading=c.is_priority_heading,
            )
            model_chunks.append(model_chunk)

        # Insert chunks
        self.db.insert_chunks(document_id, model_chunks)

    # Query methods

    def search(
        self,
        query: str,
        project: str | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """
        Search for documents matching the query.

        Args:
            query: Search query (FTS5 syntax)
            project: Optional project name filter
            limit: Maximum number of results

        Returns:
            List of SearchResult objects with ranking information.
        """
        self._ensure_initialized()
        return self.db.search(query, project_name=project, limit=limit)

    def list_projects(self) -> list[Project]:
        """List all indexed projects."""
        self._ensure_initialized()
        return self.db.list_projects()

    def list_documents(
        self,
        project: str | None = None,
        folder: str | None = None,
    ) -> list[Document]:
        """List documents, optionally filtered."""
        self._ensure_initialized()
        return self.db.list_documents(project_name=project, folder=folder)

    def get_document(self, path: str) -> Document | None:
        """Get a document by path."""
        self._ensure_initialized()
        return self.db.get_document_by_path(path)

    def get_chunks(self, document_id: int) -> list[Chunk]:
        """Get all chunks for a document."""
        self._ensure_initialized()
        return self.db.get_chunks(document_id)
