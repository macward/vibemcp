# Task: Setup proyecto FastAPI

Status: done

## Objective
Configurar el proyecto base con FastAPI, estructura de carpetas, y dependencias iniciales.

## Context
- Related files: `src/main.py`, `pyproject.toml`
- Dependencies: ninguna

## Steps
1. [x] Crear estructura de carpetas (src/, tests/, config/)
2. [x] Configurar pyproject.toml con dependencias
3. [x] Crear main.py con health endpoint
4. [x] Configurar pytest y primer test
5. [x] Agregar pre-commit hooks

## Acceptance Criteria
- [x] `uv run pytest` pasa
- [x] `uv run uvicorn src.main:app` inicia el server
- [x] `/health` endpoint responde 200 OK

## Notes
Usando uv como package manager. Mínima configuración inicial, iterar después.
