# Task 003: Disenar Schema SQLite

**Completed**: 2026-02-09
**Branch**: task/003-disenar-schema-sqlite
**Status**: Done

## Summary

Diseño completo del schema SQLite para el índice de vibeMCP, incluyendo tablas core, índice FTS5 para búsqueda full-text, estrategia de chunking, y sistema de ranking con boosts múltiples.

## Changes

### Added
- `docs/sqlite-schema.md` - Documentación completa del schema

### Schema Components
- **projects** - Tabla de workspaces con nombre y path
- **documents** - Archivos indexados con metadata (frontmatter o inferida)
- **chunks** - Fragmentos de contenido divididos por headings
- **chunks_fts** - Índice FTS5 para búsqueda full-text
- **meta** - Versionado del schema

### Chunking Strategy
- Dividir por headings nivel 1 y 2 (`#`, `##`)
- Máximo ~1500 tokens (~6000 chars) por chunk
- Fallback: subdividir por párrafos, luego por líneas

### Ranking System
- **Type boost**: status.md (3.0) > tasks (2.0) > plans (1.8) > sessions (1.5) > ...
- **Recency boost**: 2.0 (hoy) → 1.5 (semana) → 1.2 (mes) → 1.0 (3 meses) → 0.8
- **Heading boost**: Priority headings (2.5) > Objective/Acceptance (1.5) > otros (1.0)
- **Status boost**: in-progress (2.0) > blocked (1.8) > pending (1.2) > done (0.6)

## Files Changed
- `docs/sqlite-schema.md` (created)

## Notes
- Schema reviewed by code-review-expert agent
- Added composite indexes based on review feedback
- Clarified precedence of `updated` vs `mtime` for ranking
- Added query for incremental re-indexing
