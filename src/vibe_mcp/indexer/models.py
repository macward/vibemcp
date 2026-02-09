"""Data models for the indexer."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Project:
    """Represents a project (workspace) in the vibe system."""

    id: int | None = None
    name: str = ""
    path: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Document:
    """Represents a document in the index."""

    id: int | None = None
    project_id: int = 0
    path: str = ""  # Relative from VIBE_ROOT
    folder: str = ""  # e.g., "tasks", "plans", "sessions"
    filename: str = ""
    type: str | None = None  # task, plan, session, etc.
    status: str | None = None  # pending, in-progress, done, blocked
    owner: str | None = None
    tags: list[str] = field(default_factory=list)
    content_hash: str = ""
    mtime: float = 0.0
    updated: str | None = None  # From frontmatter
    indexed_at: datetime | None = None


@dataclass
class Chunk:
    """Represents a chunk of content from a document."""

    id: int | None = None
    document_id: int = 0
    heading: str | None = None
    heading_level: int = 0
    content: str = ""
    chunk_order: int = 0
    char_offset: int = 0
    is_priority_heading: bool = False


@dataclass
class SearchResult:
    """Represents a search result with ranking information."""

    chunk_id: int
    document_id: int
    project_name: str
    document_path: str
    folder: str
    heading: str | None
    content: str
    bm25_score: float
    type_boost: float
    recency_boost: float
    heading_boost: float
    status_boost: float
    final_score: float
