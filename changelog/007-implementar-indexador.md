# Task 007: Implementar indexador (core del sistema)

**Completed**: 2026-02-09
**Branch**: task/007-implementar-indexador
**Status**: Done

## Summary

Implemented the core indexer module that syncs the .vibe filesystem with SQLite FTS5. This is the heart of the vibeMCP system - a robust indexer that discovers, parses, chunks, and indexes markdown documents for full-text search with sophisticated ranking.

## Changes

### Added
- `src/vibe_mcp/indexer/__init__.py` - Module exports
- `src/vibe_mcp/indexer/models.py` - Data models (Project, Document, Chunk, SearchResult)
- `src/vibe_mcp/indexer/walker.py` - File discovery in VIBE_ROOT with SHA-256 hashing
- `src/vibe_mcp/indexer/parser.py` - YAML frontmatter parsing with path-based inference fallback
- `src/vibe_mcp/indexer/chunker.py` - Document chunking by headings with paragraph/line fallbacks
- `src/vibe_mcp/indexer/database.py` - SQLite database with FTS5, triggers, and thread-safe operations
- `src/vibe_mcp/indexer/indexer.py` - Main Indexer class coordinating full reindex and incremental sync
- `tests/test_indexer/` - Comprehensive test suite (104 tests)

### Modified
- `pyproject.toml` - Added ruff lint ignore for E501 in SQL strings and tests

## Features Implemented

1. **File Walker** - Discovers all .md files in VIBE_ROOT, computes content hashes
2. **Change Detection** - mtime fast-path + content hash for edge cases
3. **Frontmatter Parser** - YAML frontmatter with fallback to path inference (folder -> type)
4. **Document Chunking** - Splits by headings (#/##), respects 6000 char limit, falls back to paragraphs/lines
5. **SQLite FTS5 Index** - Full-text search with triggers to keep FTS synchronized
6. **Search Ranking** - Multi-factor: BM25 * type_boost * recency_boost * heading_boost * status_boost
7. **Thread Safety** - Thread-local connections + write lock for concurrent read/write
8. **Reindex Command** - Full rebuild of index from filesystem

## Search Ranking Boosts

- **Type boost**: status.md (3.0) > tasks (2.0) > plans (1.8) > sessions (1.5) > ...
- **Recency boost**: 1 day (2.0) > 7 days (1.5) > 30 days (1.2) > 90 days (1.0) > older (0.8)
- **Heading boost**: Priority headings like "Blockers", "Next Steps" (2.5)
- **Status boost**: in-progress (2.0) > blocked (1.8) > pending (1.2) > done (0.6)

## Files Changed
- `src/vibe_mcp/indexer/__init__.py` (created)
- `src/vibe_mcp/indexer/models.py` (created)
- `src/vibe_mcp/indexer/walker.py` (created)
- `src/vibe_mcp/indexer/parser.py` (created)
- `src/vibe_mcp/indexer/chunker.py` (created)
- `src/vibe_mcp/indexer/database.py` (created)
- `src/vibe_mcp/indexer/indexer.py` (created)
- `tests/test_indexer/__init__.py` (created)
- `tests/test_indexer/test_walker.py` (created)
- `tests/test_indexer/test_parser.py` (created)
- `tests/test_indexer/test_chunker.py` (created)
- `tests/test_indexer/test_database.py` (created)
- `tests/test_indexer/test_indexer.py` (created)
- `pyproject.toml` (modified)

## Security Improvements

- Path traversal validation to prevent symlink attacks outside vibe_root
- UTF-8 encoding error handling to prevent crashes on malformed files
- Removed `check_same_thread=False` for safer thread handling

## Notes

- The indexer is designed to be "disposable" - if the SQLite database is corrupted or deleted, it can be fully regenerated from the filesystem
- Incremental sync uses mtime as a fast-path; only checks content hash when mtime differs
- Test coverage includes concurrent access testing to verify thread safety
