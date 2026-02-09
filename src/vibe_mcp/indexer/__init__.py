"""
Indexer module for vibeMCP.

This module handles synchronization between the .vibe filesystem and SQLite FTS5 index.
It is the core component of the system - if it works well, everything else fits.
"""

from vibe_mcp.indexer.chunker import chunk_document
from vibe_mcp.indexer.database import Database
from vibe_mcp.indexer.indexer import Indexer
from vibe_mcp.indexer.models import Chunk, Document, Project, SearchResult
from vibe_mcp.indexer.parser import parse_frontmatter
from vibe_mcp.indexer.walker import FileInfo, walk_vibe_root

__all__ = [
    "Chunk",
    "Database",
    "Document",
    "FileInfo",
    "Indexer",
    "Project",
    "SearchResult",
    "chunk_document",
    "parse_frontmatter",
    "walk_vibe_root",
]
