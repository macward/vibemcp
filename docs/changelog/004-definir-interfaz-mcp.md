# Changelog: 004 - Definir interfaz MCP

**Date:** 2025-02-09
**Status:** Completed

## Summary

Documentación completa de la interfaz MCP del servidor vibeMCP: resources, tools, y prompts.

## Changes

### Added

- `docs/mcp-interface.md` — Especificación completa de la interfaz MCP

### Documentation

**Resources definidos:**
- `vibe://projects` — lista de proyectos con stats
- `vibe://projects/{name}` — detalle de proyecto
- `vibe://projects/{name}/{folder}/{file}` — archivo específico

**Tools de lectura:**
- `search` — búsqueda full-text con ranking ⭐
- `read_doc` — leer documento completo ⭐
- `list_tasks` — listar tareas con filtros
- `get_plan` — leer execution plan

**Tools de escritura:**
- `create_doc` — crear archivo en cualquier carpeta
- `update_doc` — actualizar archivo existente
- `create_task` — crear tarea con formato estándar ⭐
- `update_task_status` — cambiar status de tarea
- `create_plan` — crear/actualizar execution plan
- `log_session` — registrar nota de sesión ⭐
- `reindex` — forzar re-indexación

**Prompts:**
- `project_briefing` — resumen del estado del proyecto
- `session_start` — cargar contexto antes de trabajar

## Key Decisions

1. **Happy path identificado** — 4 tools (search, read_doc, create_task, log_session) cubren el 80% del uso
2. **Re-indexación automática** — toda escritura dispara re-index del archivo afectado
3. **Validación de paths** — prevención de directory traversal en todas las tools
4. **Error handling unificado** — formato estándar de errores con códigos

## Related Files

- `docs/sqlite-schema.md` — Schema SQLite (task 003)
- `docs/vibe-structure.md` — Estructura del workspace (task 001)
- `references/01-vibe-mcp-project-v2.md` — Contexto del proyecto
