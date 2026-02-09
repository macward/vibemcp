# .vibe MCP — Project Context Server

## Qué es

Un MCP server que expone el sistema de workspaces `.vibe` existente para que cualquier AI agent (Claude Code, Claude.ai, Cursor) pueda acceder al contexto de todos los proyectos desde cualquier máquina.

No es un task manager. Es un **context fabric** para agentes: una capa de acceso al conocimiento de tus proyectos, independiente del vendor o la herramienta.

## Problema que resuelve

`.vibe` ya funciona como sistema local: cada proyecto tiene su workspace con tareas, planes, sesiones, reportes y referencias. Los agents ya interactúan con él vía `CLAUDE.md` y comandos como `/task-decomposer`. El problema es que todo vive en una sola máquina. Si trabajás remotamente, por SSH, desde otro dispositivo o un codespace, perdés el acceso a ese contexto centralizado.

El MCP server no redefine `.vibe` — lo expone tal cual sobre el protocolo MCP, haciéndolo accesible desde cualquier cliente compatible.

## Cómo funciona hoy (local)

```
Proyecto (repo)
├── CLAUDE.md          ← incluye "vibe: mi-proyecto"
└── src/...

~/.vibe/
├── mi-proyecto/
│   ├── tasks/         ← tareas creadas por /task-decomposer
│   ├── plans/         ← execution plans con dependencias
│   ├── sessions/      ← notas de sesión de trabajo
│   ├── reports/       ← reportes generados
│   ├── changelog/     ← historial de cambios
│   ├── references/    ← material de referencia
│   ├── scratch/       ← borradores, exploración
│   └── assets/        ← recursos del proyecto
├── otro-proyecto/
│   └── ...
└── ...
```

El agent lee `CLAUDE.md`, encuentra el nombre del workspace `.vibe`, y opera sobre esa carpeta. Comandos como `/task-decomposer` crean archivos de tareas y execution plans directamente en el workspace.

## Qué cambia con el MCP server

```
~/.vibe/ (source of truth)
    ↕ read/write
.vibe MCP Server (FastMCP + SSE)
    ↕ MCP protocol
Cualquier cliente: Claude Code, Claude.ai, Cursor
(local o remoto, misma interfaz)
```

El server lee y escribe el filesystem `.vibe/` y lo expone vía MCP. Un índice SQLite con FTS5 permite búsqueda rápida cross-project sin parsear archivos en cada request. El índice se construye partiendo cada documento en chunks por headings, lo que le permite a los agents recibir respuestas precisas y con poco ruido.

Los agents que hoy operan localmente (como `/task-decomposer`) se adaptan para usar las tools del MCP en vez de escribir directamente al filesystem. El resultado es el mismo: archivos en `.vibe/`, pero accesibles desde cualquier lado.

## Stack

| Componente | Tecnología | Razón |
|---|---|---|
| **MCP Server** | Python + FastMCP | SDK oficial, decoradores simples, SSE built-in |
| **Transporte** | SSE (HTTP) | Accesible remotamente. Manejar reconexiones y `Last-Event-ID` desde el inicio |
| **Source of truth** | Filesystem `.vibe/` | Ya existe, legible, versionable con Git, editable a mano |
| **Índice** | SQLite FTS5 | Búsqueda full-text por chunks, ranking con boost, zero config. Si muere, se regenera |
| **Auth** | Bearer token (>= 32 bytes) | Simple, con rotación sin downtime vía env reload |
| **Deploy** | VPS (DigitalOcean/Fly) | Siempre disponible, HTTPS con Caddy |
| **Sync** | Git repo | Backup, historial. Pull manual + reindex. Nunca auto-commit desde el server |

## Estructura del workspace .vibe

Creada por el script `vibe-init`:

```
~/.vibe/<proyecto>/
├── tasks/          ← archivos de tareas individuales (001-nombre.md, 002-nombre.md)
├── plans/          ← execution plans con grafos de dependencia
├── sessions/       ← notas de sesión por fecha
├── reports/        ← reportes generados por agents o manualmente
├── changelog/      ← historial de cambios del proyecto
├── references/     ← docs externos, specs, material de consulta
├── scratch/        ← borradores, exploración, ideas sueltas
└── assets/         ← recursos (diagramas, imágenes, configs)
```

El MCP server no impone estructura adicional. Descubre lo que hay y lo expone.

## YAML frontmatter (opcional)

Cualquier archivo `.md` puede incluir frontmatter YAML al inicio. Si no existe, el indexador infiere la metadata por path (carpeta = tipo, directorio padre = proyecto).

```yaml
---
project: rumi
type: status
updated: 2026-02-09
tags: [backend, mcp]
status: in-progress
owner: max
---
```

Campos estándar: `project`, `type`, `updated`, `tags`, `status`, `owner`. Todos opcionales.

## Capacidades del MCP Server

### Resources (lectura de contexto)

- Listar todos los proyectos con resumen (`last_updated`, `open_tasks_count`, `last_session_date`)
- Leer el contenido de un proyecto (carpetas, archivos disponibles)
- Leer archivos específicos de cualquier carpeta

### Tools

**Happy path (80% del uso diario):**
- `search` — búsqueda full-text cross-project
- `read_doc` — leer un documento completo
- `create_task` — crear una tarea con formato estándar
- `log_session` — registrar nota de sesión con fecha automática

**Resto de tools:**
- `list_tasks` — listar tareas por proyecto o cross-project, filtrar por status
- `get_plan` — leer el execution plan de un proyecto
- `create_doc` — crear un archivo en cualquier carpeta
- `update_doc` — actualizar contenido de un archivo existente
- `update_task_status` — cambiar status de una tarea
- `create_plan` — crear o actualizar un execution plan
- `reindex` — forzar re-indexación del workspace

### Prompts (templates)

- `project_briefing` — "poneme al día con {proyecto}"
- `session_start` — cargar contexto del proyecto antes de trabajar

## Indexación

```
.vibe/ filesystem ──(on-demand/reindex)──→ SQLite FTS5
                                            │
                                            ├── chunking por headings (# / ##)
                                            │   └── max ~1-2k tokens por chunk
                                            │       └── fallback: subdividir por párrafos
                                            ├── detección de cambios: mtime (fast-path) + hash (edge cases)
                                            ├── metadata: proyecto, carpeta, archivo, frontmatter
                                            ├── ranking: FTS5 rank + boost por tipo + recencia + heading
                                            └── lock simple para write + search concurrente
```

El filesystem siempre manda. El SQLite es derivado y se regenera con `reindex`. Si la DB muere, el sistema sigue vivo.

### Ranking de búsqueda

Además del score de FTS5, se aplican boosts pragmáticos (no ML):

- Boost si el match está en `status.md` o `tasks/`
- Boost si el documento es más reciente (`updated` o mtime)
- Boost si el heading contiene "Next", "Blockers", "Decisions", "Current Status"

Los pesos se documentan explícitamente y se ajustan con el uso real.

## Clientes target

- **Claude Code CLI** — sesiones de desarrollo local y remoto (conectar primero)
- **Claude.ai** — planning, revisión, brainstorming desde web/mobile
- **Cursor / Windsurf** — contexto dentro del IDE (más frágiles con MCP, conectar último)

Todos se conectan al mismo endpoint SSE.

## Principios de diseño

1. **No reinventar** — `.vibe` ya existe y funciona. El MCP lo expone, no lo redefine
2. **Filesystem first** — Si el server se cae, los archivos siguen siendo útiles solos
3. **Index is disposable** — Si SQLite muere, se regenera. Nunca es fuente de verdad
4. **Zero friction** — Agregar contexto = crear/editar un archivo en la carpeta correcta
5. **Agent-friendly** — Estructura predecible, happy path claro, menos tools = menos confusión
6. **Un solo endpoint** — Todos los clientes, misma fuente de verdad
7. **Escritura habilitada** — Los agents necesitan crear tareas, planes y sesiones como parte del flujo normal
8. **Scope acotado** — Es un context server, no un task manager 2.0
