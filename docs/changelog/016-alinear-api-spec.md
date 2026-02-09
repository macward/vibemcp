# Task 016: Alinear Firmas de API con Spec

**Completed**: 2026-02-09
**Branch**: task/016-alinear-api-spec
**Status**: ✅ Done

## Summary
Aligned read tools API signatures with the spec defined in docs/mcp-interface.md. Updated `read_doc` to accept separate `folder` and `filename` parameters instead of a combined `path`, and enriched both `read_doc` and `get_plan` to return document metadata.

## Changes

### Modified
- `src/vibe_mcp/tools.py` - Updated read tools to match spec:
  - `read_doc(project, path)` → `read_doc(project, folder, filename)` with metadata
  - `get_plan(project)` → `get_plan(project, filename)` with metadata
  - Added security validation (path traversal protection) to `get_plan`

### API Changes

**`read_doc` - Breaking change**

Before:
```python
read_doc(project: str, path: str) -> dict
# Returns: project, path, content, exists, error
```

After:
```python
read_doc(project: str, folder: str, filename: str) -> dict
# Returns: project, folder, filename, path, metadata, content, exists, error
```

**`get_plan` - Non-breaking change (optional parameter)**

Before:
```python
get_plan(project: str) -> dict
# Returns: project, content, exists
```

After:
```python
get_plan(project: str, filename: str = "execution-plan.md") -> dict
# Returns: project, filename, path, exists, metadata, content
```

## Files Changed
- `src/vibe_mcp/tools.py` (modified)

## Commits
- [task/016] Align API signatures with spec - read_doc and get_plan

## Notes
- Metadata includes: type, status, updated, tags, owner (for read_doc) and type, updated (for get_plan)
- Metadata is extracted from YAML frontmatter when present, with fallback to file modification time
- Path traversal security validation added to get_plan to match read_doc's security measures
