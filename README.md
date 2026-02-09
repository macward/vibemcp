# vibemcp

MCP server that exposes the `.vibe` workspace system for AI agents.

## Setup

This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management.

### Installation

1. Create and activate a virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install the package with dev dependencies:
```bash
uv pip install -e ".[dev]"
```

## Development

### Running Tests

```bash
uv run pytest
```

### Code Quality

```bash
# Check code style
uv run ruff check .

# Format code
uv run ruff format .
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VIBE_ROOT` | `~/.vibe` | Root directory for vibe workspaces |
| `VIBE_PORT` | `8080` | Server port |
| `VIBE_DB` | `~/.vibe/index.db` | SQLite database path |
| `VIBE_AUTH_TOKEN` | (none) | Bearer token for authentication (min 32 chars) |
| `VIBE_READ_ONLY` | `false` | Enable read-only mode |

### Authentication

To enable authentication, set the `VIBE_AUTH_TOKEN` environment variable:

```bash
# Generate a secure token (32+ characters required)
export VIBE_AUTH_TOKEN=$(openssl rand -hex 32)

# Start the server
uv run python -m vibe_mcp.main
```

Clients must include the token in the `Authorization` header:

```
Authorization: Bearer <token>
```

Requests without a valid token will receive a 401 Unauthorized response.

### Read-Only Mode

To run the server in read-only mode (disables all write tools):

```bash
# Via CLI flag
uv run python -m vibe_mcp.main --read-only

# Or via environment variable
VIBE_READ_ONLY=true uv run python -m vibe_mcp.main
```

In read-only mode, write operations (create_task, log_session, etc.) will be rejected.

## Usage

```bash
# Start the server
uv run python -m vibe_mcp.main

# Force reindex on startup
uv run python -m vibe_mcp.main --reindex

# Start in read-only mode
uv run python -m vibe_mcp.main --read-only
```

## Project Structure

```
vibemcp/
├── src/                  # Source code
│   ├── __init__.py
│   └── main.py
├── tests/                # Tests
│   ├── __init__.py
│   ├── conftest.py
│   └── test_main.py
├── pyproject.toml        # Project configuration
├── .python-version       # Python version specification
├── .gitignore
└── README.md
```

## License

TBD
