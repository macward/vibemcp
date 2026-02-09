# vibemcp

A modern Python project.

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

## Usage

```python
from vibemcp.main import main

main()
```

Or run directly:
```bash
python src/vibemcp/main.py
```

## Project Structure

```
vibemcp/
├── src/vibemcp/          # Source code
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
