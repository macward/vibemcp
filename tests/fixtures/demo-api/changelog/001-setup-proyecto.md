# Changelog: 001 - Setup proyecto

**Date:** 2025-02-07
**Status:** Completed

## Summary

Configuración inicial del proyecto FastAPI con estructura de carpetas, dependencias, y tooling.

## Changes

### Added
- `src/main.py` — FastAPI app con health endpoint
- `pyproject.toml` — Configuración de proyecto con uv
- `tests/` — Estructura de tests con pytest
- `.pre-commit-config.yaml` — Hooks para ruff y mypy

### Configuration
- Python 3.12
- FastAPI 0.109+
- pytest con pytest-asyncio
- ruff para linting
- mypy para type checking

## Files Changed
- `src/main.py` (created)
- `pyproject.toml` (created)
- `tests/conftest.py` (created)
- `tests/test_health.py` (created)
