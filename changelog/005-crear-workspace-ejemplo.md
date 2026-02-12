# Changelog: 005 - Crear workspace de ejemplo

**Date:** 2025-02-09
**Status:** Completed

## Summary

Creados dos proyectos de ejemplo realistas para testing del indexador: demo-api y demo-frontend.

## Changes

### Added

**tests/fixtures/demo-api/**
- `status.md` — Estado del proyecto con Blockers, Next Steps, Decisions
- `tasks/001-005` — 5 tareas en distintos estados (done, in-progress, blocked, pending)
- `plans/execution-plan.md` — Plan de ejecución con dependencias
- `sessions/2025-02-{07,08,09}.md` — 3 días de notas de sesión
- `references/jwt-spec.md` — Especificación técnica
- `changelog/001-setup-proyecto.md` — Ejemplo de changelog

**tests/fixtures/demo-frontend/**
- `status.md` — Con YAML frontmatter completo
- `tasks/001-004` — 4 tareas, algunas con frontmatter, otras sin
- `plans/execution-plan.md` — Con frontmatter
- `sessions/2025-02-09.md` — Sesión con código embebido
- `references/design-tokens.md` — Design system
- `scratch/component-ideas.md` — Borrador de ideas
- `assets/README.md` — Documentación de assets

**tests/fixtures/README.md**
- Documentación completa de uso en tests
- Ejemplos de código Python/pytest
- Tabla de cobertura de casos

## Key Decisions

1. **Contenido realista** — No lorem ipsum, simula proyectos de desarrollo reales
2. **Mix de frontmatter** — demo-api sin frontmatter (inferencia), demo-frontend con mix
3. **Todos los estados** — Tareas en done, in-progress, blocked, pending
4. **Headings clave** — status.md incluye "Blockers", "Next", "Decisions" para testing de boost

## Test Coverage

| Caso | Cubierto |
|------|----------|
| Indexar sin frontmatter | demo-api |
| Indexar con frontmatter | demo-frontend |
| Inferencia de metadata | demo-api, demo-frontend/tasks/003-004 |
| Búsqueda cross-project | Ambos proyectos |
| Ranking por heading clave | demo-api/status.md |
| Ranking por recencia | sessions/ con fechas |
| Ranking por status | Tareas in-progress vs done |

## Files Changed

- `tests/fixtures/` — Nuevo directorio con 23 archivos
- `tests/fixtures/README.md` — Documentación de uso
