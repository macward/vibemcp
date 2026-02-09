# Task 017: Auth con Bearer Token

**Completed**: 2026-02-09
**Branch**: task/017-auth-bearer-token
**Status**: Done

## Summary
Implemented Bearer token authentication for the MCP server (Phase 2). The auth system integrates with FastMCP's TokenVerifier pattern to properly enforce authentication on all requests when `VIBE_AUTH_TOKEN` is configured.

## Changes

### Added
- `src/vibe_mcp/auth.py` - Authentication module with:
  - `BearerTokenVerifier` class extending FastMCP's `TokenVerifier`
  - `get_auth_provider()` function to get auth provider based on config
  - `check_write_permission()` for read-only mode enforcement
  - `AuthError` exception class
- `tests/test_auth.py` - Comprehensive test suite (14 tests) covering:
  - Token verification (valid, invalid, empty, no auth configured)
  - Auth provider creation
  - Write permission checks
  - Config token validation

### Modified
- `src/vibe_mcp/config.py`:
  - Added `auth_token: str | None` field
  - Added `read_only: bool` field
  - Added `set_read_only_override()` function for CLI integration
  - Token must be >= 32 characters for security
- `src/vibe_mcp/main.py`:
  - Added `--read-only` CLI flag
  - Integrated auth provider with FastMCP server
  - Updated startup banner to show auth and read-only status
- `src/vibe_mcp/tools_write.py`:
  - Added `check_write_permission()` calls to all write functions
- `README.md`:
  - Added Configuration section with environment variables table
  - Added Authentication section with usage examples
  - Added Read-Only Mode section

## Files Changed
- `src/vibe_mcp/auth.py` (created)
- `src/vibe_mcp/config.py` (modified)
- `src/vibe_mcp/main.py` (modified)
- `src/vibe_mcp/tools_write.py` (modified)
- `tests/test_auth.py` (created)
- `README.md` (modified)

## Security Features
- Constant-time token comparison using `hmac.compare_digest()` to prevent timing attacks
- Minimum 32-character token requirement
- Proper integration with FastMCP's auth system via `TokenVerifier`
- Read-only mode to disable write operations

## Configuration
```bash
# Enable authentication (required: >= 32 characters)
export VIBE_AUTH_TOKEN=$(openssl rand -hex 32)

# Enable read-only mode
export VIBE_READ_ONLY=true
# or
python -m vibe_mcp.main --read-only
```

## Notes
- When `VIBE_AUTH_TOKEN` is not set, the server allows anonymous access
- Read-only mode prevents all write operations even for authenticated users
- CLI flag takes precedence over environment variable for read-only mode
