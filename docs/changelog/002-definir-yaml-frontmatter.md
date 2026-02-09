# Task 002: Definir spec de YAML frontmatter

**Completed**: 2026-02-09
**Branch**: task/002-definir-yaml-frontmatter
**Status**: Done

## Summary

Defined the complete YAML frontmatter specification for `.md` files in the vibe workspace system, including field schema, data types, inference rules, and usage examples.

## Changes

### Modified
- `docs/vibe-structure.md` — Expanded "Frontmatter YAML (opcional)" section from ~20 lines to a comprehensive specification (~150 lines)

## Details

The specification now includes:

1. **Schema de Campos** — Table with all 6 standard fields (`project`, `type`, `updated`, `tags`, `status`, `owner`) with their types and examples

2. **Tipos de Datos** — Description of each data type (string, date, enum, list) with YAML syntax examples

3. **Reglas de Inferencia por Path** — How the indexer infers metadata when frontmatter is missing:
   - `project` from parent directory name
   - `type` from containing folder (singularized)
   - `updated` from file mtime
   - `status` from `Status:` line in task files

4. **Mapeo de carpetas a tipos** — Complete folder-to-type mapping

5. **Precedencia: Frontmatter vs Inferencia** — ASCII flowchart showing resolution logic

6. **Ejemplos** — Three concrete examples:
   - File with full frontmatter
   - File with partial frontmatter
   - File without frontmatter

7. **Uso por el Indexador** — How the indexer processes and stores metadata, including SQLite example

8. **Notas de Implementación** — Error handling, normalization, and precedence rules

## Files Changed
- `docs/vibe-structure.md` (modified)

## Notes

Key design decisions:
- All fields are optional (zero-friction)
- Frontmatter takes precedence over inference
- Status can be extracted from task body (`Status: pending` on line 3)
- Only `.md` files are indexed (binaries in assets/ are excluded)
- Malformed frontmatter is treated as absent (with warning)
