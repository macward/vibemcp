"""SQLite database management for the index."""

import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from vibe_mcp.indexer.models import Chunk, Document, Project, SearchResult

SCHEMA_VERSION = "1.0"

SCHEMA_SQL = """
-- vibeMCP Index Schema v1.0
-- This index is disposable: it regenerates from VIBE_ROOT/

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    path        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL,
    path         TEXT NOT NULL UNIQUE,
    folder       TEXT NOT NULL,
    filename     TEXT NOT NULL,
    type         TEXT,
    status       TEXT,
    owner        TEXT,
    tags         TEXT,
    content_hash TEXT NOT NULL,
    mtime        REAL NOT NULL,
    updated      TEXT,
    indexed_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_mtime ON documents(mtime DESC);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_project_folder ON documents(project_id, folder);

-- Chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id         INTEGER NOT NULL,
    heading             TEXT,
    heading_level       INTEGER DEFAULT 0,
    content             TEXT NOT NULL,
    chunk_order         INTEGER NOT NULL,
    char_offset         INTEGER NOT NULL,
    is_priority_heading INTEGER DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_order ON chunks(document_id, chunk_order);
CREATE INDEX IF NOT EXISTS idx_chunks_heading ON chunks(heading);
CREATE INDEX IF NOT EXISTS idx_chunks_priority ON chunks(is_priority_heading) WHERE is_priority_heading = 1;

-- FTS5 virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content,
    heading,
    content='chunks',
    content_rowid='id'
);

-- Triggers to keep FTS5 synchronized
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content, heading)
    VALUES (NEW.id, NEW.content, NEW.heading);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, heading)
    VALUES ('delete', OLD.id, OLD.content, OLD.heading);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, heading)
    VALUES ('delete', OLD.id, OLD.content, OLD.heading);
    INSERT INTO chunks_fts(rowid, content, heading)
    VALUES (NEW.id, NEW.content, NEW.heading);
END;

-- Metadata table for index versioning
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', '1.0');
INSERT OR REPLACE INTO meta (key, value) VALUES ('created_at', datetime('now'));
"""


class Database:
    """SQLite database for the vibe index."""

    # Snippet configuration for FTS5 search results
    SNIPPET_COLUMN_INDEX = 0  # content is the first column in chunks_fts
    SNIPPET_HIGHLIGHT_START = ">>>"
    SNIPPET_HIGHLIGHT_END = "<<<"
    SNIPPET_ELLIPSIS = "..."
    SNIPPET_MAX_TOKENS = 64

    def __init__(self, db_path: Path):
        """Initialize database connection."""
        self.db_path = db_path
        self._local = threading.local()
        self._write_lock = threading.Lock()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def _read_cursor(self) -> Iterator[sqlite3.Cursor]:
        """Get a cursor for read operations."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    @contextmanager
    def _write_cursor(self) -> Iterator[sqlite3.Cursor]:
        """Get a cursor for write operations with locking."""
        with self._write_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def initialize(self) -> None:
        """Initialize the database schema."""
        with self._write_cursor() as cursor:
            cursor.executescript(SCHEMA_SQL)

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def clear(self) -> None:
        """Clear all data from the database (for reindexing)."""
        with self._write_cursor() as cursor:
            cursor.execute("DELETE FROM chunks")
            cursor.execute("DELETE FROM documents")
            cursor.execute("DELETE FROM projects")
            # Rebuild FTS index
            cursor.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")

    # Project operations

    def get_or_create_project(self, name: str, path: str) -> int:
        """Get or create a project, returning its ID."""
        with self._write_cursor() as cursor:
            cursor.execute(
                "SELECT id FROM projects WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            if row:
                # Update path and timestamp
                cursor.execute(
                    """UPDATE projects
                    SET path = ?, updated_at = datetime('now')
                    WHERE id = ?""",
                    (path, row["id"]),
                )
                return row["id"]
            else:
                cursor.execute(
                    "INSERT INTO projects (name, path) VALUES (?, ?)",
                    (name, path),
                )
                return cursor.lastrowid  # type: ignore

    def get_project(self, name: str) -> Project | None:
        """Get a project by name."""
        with self._read_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM projects WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            if row:
                return Project(
                    id=row["id"],
                    name=row["name"],
                    path=row["path"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
            return None

    def list_projects(self) -> list[Project]:
        """List all projects."""
        with self._read_cursor() as cursor:
            cursor.execute("SELECT * FROM projects ORDER BY name")
            return [
                Project(
                    id=row["id"],
                    name=row["name"],
                    path=row["path"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in cursor.fetchall()
            ]

    # Document operations

    def get_document_by_path(self, path: str) -> Document | None:
        """Get a document by its relative path."""
        with self._read_cursor() as cursor:
            cursor.execute(
                "SELECT * FROM documents WHERE path = ?",
                (path,),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_document(row)
            return None

    def get_document_hash(self, path: str) -> str | None:
        """Get the content hash of a document for change detection."""
        with self._read_cursor() as cursor:
            cursor.execute(
                "SELECT content_hash FROM documents WHERE path = ?",
                (path,),
            )
            row = cursor.fetchone()
            return row["content_hash"] if row else None

    def get_document_mtime(self, path: str) -> float | None:
        """Get the mtime of a document for fast-path change detection."""
        with self._read_cursor() as cursor:
            cursor.execute(
                "SELECT mtime FROM documents WHERE path = ?",
                (path,),
            )
            row = cursor.fetchone()
            return row["mtime"] if row else None

    def upsert_document(self, doc: Document) -> int:
        """Insert or update a document, returning its ID."""
        tags_json = json.dumps(doc.tags) if doc.tags else None

        with self._write_cursor() as cursor:
            cursor.execute(
                """INSERT INTO documents
                (project_id, path, folder, filename, type, status, owner, tags, content_hash, mtime, updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    project_id = excluded.project_id,
                    folder = excluded.folder,
                    filename = excluded.filename,
                    type = excluded.type,
                    status = excluded.status,
                    owner = excluded.owner,
                    tags = excluded.tags,
                    content_hash = excluded.content_hash,
                    mtime = excluded.mtime,
                    updated = excluded.updated,
                    indexed_at = datetime('now')
                """,
                (
                    doc.project_id,
                    doc.path,
                    doc.folder,
                    doc.filename,
                    doc.type,
                    doc.status,
                    doc.owner,
                    tags_json,
                    doc.content_hash,
                    doc.mtime,
                    doc.updated,
                ),
            )
            # Get the document ID
            cursor.execute("SELECT id FROM documents WHERE path = ?", (doc.path,))
            return cursor.fetchone()["id"]

    def delete_document(self, path: str) -> None:
        """Delete a document by path."""
        with self._write_cursor() as cursor:
            cursor.execute("DELETE FROM documents WHERE path = ?", (path,))

    def delete_documents_for_project(self, project_id: int) -> None:
        """Delete all documents for a project."""
        with self._write_cursor() as cursor:
            cursor.execute("DELETE FROM documents WHERE project_id = ?", (project_id,))

    def list_documents(
        self,
        project_name: str | None = None,
        folder: str | None = None,
    ) -> list[Document]:
        """List documents, optionally filtered by project and/or folder."""
        query = """
            SELECT d.* FROM documents d
            JOIN projects p ON d.project_id = p.id
            WHERE 1=1
        """
        params: list = []

        if project_name:
            query += " AND p.name = ?"
            params.append(project_name)
        if folder:
            query += " AND d.folder = ?"
            params.append(folder)

        query += " ORDER BY d.path"

        with self._read_cursor() as cursor:
            cursor.execute(query, params)
            return [self._row_to_document(row) for row in cursor.fetchall()]

    def get_indexed_paths(self, project_name: str) -> set[str]:
        """Get all indexed paths for a project."""
        with self._read_cursor() as cursor:
            cursor.execute(
                """SELECT d.path FROM documents d
                JOIN projects p ON d.project_id = p.id
                WHERE p.name = ?""",
                (project_name,),
            )
            return {row["path"] for row in cursor.fetchall()}

    def _row_to_document(self, row: sqlite3.Row) -> Document:
        """Convert a database row to a Document."""
        tags = json.loads(row["tags"]) if row["tags"] else []
        return Document(
            id=row["id"],
            project_id=row["project_id"],
            path=row["path"],
            folder=row["folder"],
            filename=row["filename"],
            type=row["type"],
            status=row["status"],
            owner=row["owner"],
            tags=tags,
            content_hash=row["content_hash"],
            mtime=row["mtime"],
            updated=row["updated"],
            indexed_at=datetime.fromisoformat(row["indexed_at"]),
        )

    # Chunk operations

    def delete_chunks_for_document(self, document_id: int) -> None:
        """Delete all chunks for a document."""
        with self._write_cursor() as cursor:
            cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))

    def insert_chunks(self, document_id: int, chunks: list[Chunk]) -> None:
        """Insert chunks for a document."""
        with self._write_cursor() as cursor:
            cursor.executemany(
                """INSERT INTO chunks
                (document_id, heading, heading_level, content, chunk_order, char_offset, is_priority_heading)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        document_id,
                        chunk.heading,
                        chunk.heading_level,
                        chunk.content,
                        chunk.chunk_order,
                        chunk.char_offset,
                        1 if chunk.is_priority_heading else 0,
                    )
                    for chunk in chunks
                ],
            )

    def get_chunks(self, document_id: int) -> list[Chunk]:
        """Get all chunks for a document."""
        with self._read_cursor() as cursor:
            cursor.execute(
                """SELECT * FROM chunks
                WHERE document_id = ?
                ORDER BY chunk_order""",
                (document_id,),
            )
            return [
                Chunk(
                    id=row["id"],
                    document_id=row["document_id"],
                    heading=row["heading"],
                    heading_level=row["heading_level"],
                    content=row["content"],
                    chunk_order=row["chunk_order"],
                    char_offset=row["char_offset"],
                    is_priority_heading=bool(row["is_priority_heading"]),
                )
                for row in cursor.fetchall()
            ]

    # Search operations

    def search(
        self,
        query: str,
        project_name: str | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """
        Search for chunks matching the query with ranking.

        Returns contextual snippets using FTS5 snippet() function instead
        of full chunk content.

        Ranking combines:
        - BM25 score from FTS5
        - Type boost (tasks > plans > sessions > ...)
        - Recency boost (recent documents score higher)
        - Heading boost (priority headings score higher)
        - Status boost (in-progress > blocked > pending > done)
        """
        # Build snippet function with configured parameters
        snippet_func = (
            f"snippet(chunks_fts, {self.SNIPPET_COLUMN_INDEX}, "
            f"'{self.SNIPPET_HIGHLIGHT_START}', '{self.SNIPPET_HIGHLIGHT_END}', "
            f"'{self.SNIPPET_ELLIPSIS}', {self.SNIPPET_MAX_TOKENS})"
        )
        search_query = f"""
            SELECT
                c.id as chunk_id,
                c.document_id,
                p.name as project_name,
                d.path as document_path,
                d.folder,
                c.heading,
                c.content,
                {snippet_func} as snippet,
                bm25(chunks_fts) as bm25_score,
                CASE
                    WHEN d.path LIKE '%/status.md' OR d.path LIKE '%status.md' THEN 3.0
                    WHEN d.folder = 'tasks' THEN 2.0
                    WHEN d.folder = 'plans' THEN 1.8
                    WHEN d.folder = 'sessions' THEN 1.5
                    WHEN d.folder = 'changelog' THEN 1.2
                    WHEN d.folder = 'reports' THEN 1.0
                    WHEN d.folder = 'references' THEN 0.8
                    WHEN d.folder = 'scratch' THEN 0.5
                    ELSE 0.3
                END as type_boost,
                CASE
                    WHEN julianday('now') - julianday(COALESCE(d.updated, datetime(d.mtime, 'unixepoch'))) <= 1 THEN 2.0
                    WHEN julianday('now') - julianday(COALESCE(d.updated, datetime(d.mtime, 'unixepoch'))) <= 7 THEN 1.5
                    WHEN julianday('now') - julianday(COALESCE(d.updated, datetime(d.mtime, 'unixepoch'))) <= 30 THEN 1.2
                    WHEN julianday('now') - julianday(COALESCE(d.updated, datetime(d.mtime, 'unixepoch'))) <= 90 THEN 1.0
                    ELSE 0.8
                END as recency_boost,
                CASE
                    WHEN c.is_priority_heading = 1 THEN 2.5
                    WHEN c.heading LIKE '%Objective%' THEN 1.5
                    WHEN c.heading LIKE '%Acceptance%' THEN 1.5
                    ELSE 1.0
                END as heading_boost,
                CASE
                    WHEN d.status = 'in-progress' THEN 2.0
                    WHEN d.status = 'blocked' THEN 1.8
                    WHEN d.status = 'pending' THEN 1.2
                    WHEN d.status = 'done' THEN 0.6
                    ELSE 1.0
                END as status_boost
            FROM chunks_fts
            JOIN chunks c ON chunks_fts.rowid = c.id
            JOIN documents d ON c.document_id = d.id
            JOIN projects p ON d.project_id = p.id
            WHERE chunks_fts MATCH ?
        """
        params: list = [query]

        if project_name:
            search_query += " AND p.name = ?"
            params.append(project_name)

        search_query += """
            ORDER BY (
                bm25(chunks_fts) * type_boost * recency_boost * heading_boost * status_boost
            ) DESC
            LIMIT ?
        """
        params.append(limit)

        with self._read_cursor() as cursor:
            cursor.execute(search_query, params)
            results = []
            for row in cursor.fetchall():
                final_score = (
                    row["bm25_score"]
                    * row["type_boost"]
                    * row["recency_boost"]
                    * row["heading_boost"]
                    * row["status_boost"]
                )
                results.append(
                    SearchResult(
                        chunk_id=row["chunk_id"],
                        document_id=row["document_id"],
                        project_name=row["project_name"],
                        document_path=row["document_path"],
                        folder=row["folder"],
                        heading=row["heading"],
                        content=row["content"],
                        snippet=row["snippet"],
                        bm25_score=row["bm25_score"],
                        type_boost=row["type_boost"],
                        recency_boost=row["recency_boost"],
                        heading_boost=row["heading_boost"],
                        status_boost=row["status_boost"],
                        final_score=final_score,
                    )
                )
            return results

    def rebuild_fts(self) -> None:
        """Rebuild the FTS5 index."""
        with self._write_cursor() as cursor:
            cursor.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
