# Task 015: Implement FTS5 Snippets in Search

**Completed**: 2026-02-09
**Branch**: task/015-search-snippets-fts5
**Status**: Done

## Summary

Improved search results by using FTS5 `snippet()` function to return contextual snippets with highlighted matches instead of returning full chunk content. This reduces response payload size and provides more relevant context to users.

## Changes

### Added
- `snippet` field in `SearchResult` dataclass for contextual search result snippets
- New tests for snippet functionality: `test_search_returns_snippet`, `test_snippet_shows_context`
- Configuration constants for snippet generation: `SNIPPET_COLUMN_INDEX`, `SNIPPET_HIGHLIGHT_START`, `SNIPPET_HIGHLIGHT_END`, `SNIPPET_ELLIPSIS`, `SNIPPET_MAX_TOKENS`

### Modified
- `Database.search()` method now uses FTS5 `snippet()` function to generate contextual snippets
- Search tool returns `snippet` instead of `content` in API responses
- Updated tool docstring to document new snippet format with `>>>match<<<` highlighting

## Files Changed
- `src/vibe_mcp/indexer/models.py` (modified) - Added snippet field to SearchResult
- `src/vibe_mcp/indexer/database.py` (modified) - Added snippet generation using FTS5
- `src/vibe_mcp/tools.py` (modified) - Updated search tool to return snippets
- `tests/test_indexer/test_database.py` (modified) - Added snippet tests

## Technical Details

- FTS5 snippet() parameters:
  - Column index 0 (content column)
  - `>>>` and `<<<` as highlight markers
  - `...` as ellipsis for truncated content
  - 64 max tokens for reasonable snippet length

## Notes

- `SearchResult` still includes full `content` field for backward compatibility, but MCP clients receive only `snippet`
- Snippet configuration is now centralized as class constants for easy modification
