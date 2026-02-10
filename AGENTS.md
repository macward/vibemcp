# vibeMCP

vibe: vibeMCP

## Qué es

MCP server que expone el sistema de workspaces `.vibe` existente para que cualquier AI agent (Claude Code, Claude.ai, Cursor) pueda acceder al contexto de todos los proyectos desde cualquier máquina.

**No es un task manager. Es un context fabric para agentes.**

## Stack

| Componente | Tecnología |
|---|---|
| MCP Server | Python + FastMCP |
| Transporte | SSE (HTTP) |
| Source of truth | Filesystem `~/.vibe/` |
| Índice | SQLite FTS5 (chunking por headings) |
| Auth | Bearer token (>= 32 bytes) |
| Deploy | VPS (DigitalOcean/Fly) + Caddy |

## Estructura del workspace

```
~/.vibe/<proyecto>/
├── tasks/       ← 001-nombre.md, 002-nombre.md
├── plans/       ← execution plans con grafos de dependencia
├── sessions/    ← notas por fecha
├── reports/     ← reportes generados
├── changelog/   ← historial de cambios
├── references/  ← docs externos, specs
├── scratch/     ← borradores, exploración
└── assets/      ← recursos del proyecto
```

## Tools MCP (happy path)

- `search` — búsqueda full-text cross-project
- `read_doc` — leer un documento
- `create_task` — crear tarea con formato estándar
- `log_session` — registrar nota de sesión

## Fases de desarrollo

1. **Fase 0** — Diseño (estructura, schema SQLite, interfaz MCP)
2. **Fase 1** — MCP Server core (indexador ⭐, resources, tools, prompts)
3. **Fase 2** — Auth + seguridad
4. **Fase 3** — Deploy (VPS, HTTPS, SSE reconnection)
5. **Fase 4** — Conectar clientes (Claude Code → Claude.ai → Cursor)
6. **Fase 5** — Uso real + iteración

**Orden recomendado:** empezar por el indexador (1.2). Si eso funciona, todo lo demás encaja.

## Principios

1. Filesystem first — si el server se cae, los archivos siguen siendo útiles
2. Index is disposable — SQLite se regenera, nunca es fuente de verdad
3. Un solo endpoint — todos los clientes, misma fuente
4. Scope acotado — context server, no task manager 2.0

## Referencias

Ver `/references/` para documentación completa:
- `01-vibe-mcp-project-v2.md` — contexto y diseño del proyecto
- `02-vibe-mcp-plan-v2.md` — plan de desarrollo detallado
