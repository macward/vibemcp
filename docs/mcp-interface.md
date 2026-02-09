# MCP Interface Specification

Definición completa de la interfaz MCP del servidor vibeMCP: resources para lectura de contexto, tools para operaciones, y prompts para templates.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        vibeMCP Server                            │
├─────────────────────────────────────────────────────────────────┤
│  RESOURCES (lectura de contexto)                                 │
│  └── vibe://projects                                            │
│  └── vibe://projects/{name}                                     │
│  └── vibe://projects/{name}/{folder}/{file}                     │
├─────────────────────────────────────────────────────────────────┤
│  TOOLS                                                          │
│  ├── Lectura: search, read_doc, list_tasks, get_plan            │
│  └── Escritura: create_doc, update_doc, create_task,            │
│                 update_task_status, create_plan, log_session,    │
│                 reindex                                          │
├─────────────────────────────────────────────────────────────────┤
│  PROMPTS (templates)                                            │
│  └── project_briefing, session_start                            │
└─────────────────────────────────────────────────────────────────┘
```

### Happy Path

El 80% del uso diario se cubre con 4 operaciones:

| Tool | Uso |
|------|-----|
| **search** | Buscar información en cualquier proyecto |
| **read_doc** | Leer un documento específico |
| **create_task** | Crear una tarea nueva |
| **log_session** | Registrar notas de sesión |

---

## Resources

Los resources exponen el contenido de `.vibe/` como URIs navegables.

### `vibe://projects`

Lista todos los proyectos con resumen estadístico.

**Response:**

```json
{
  "projects": [
    {
      "name": "vibeMCP",
      "path": "/Users/x/.vibe/vibeMCP",
      "last_updated": "2025-02-09T14:30:00Z",
      "stats": {
        "total_docs": 42,
        "open_tasks": 5,
        "pending_tasks": 3,
        "in_progress_tasks": 2,
        "done_tasks": 12,
        "last_session_date": "2025-02-09"
      },
      "folders": {
        "tasks": 17,
        "plans": 2,
        "sessions": 8,
        "reports": 3,
        "changelog": 5,
        "references": 4,
        "scratch": 2,
        "assets": 1
      }
    }
  ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `name` | string | Nombre del workspace |
| `path` | string | Path absoluto |
| `last_updated` | ISO 8601 | Fecha del archivo más reciente |
| `stats.total_docs` | int | Total de documentos `.md` |
| `stats.open_tasks` | int | Tareas pending + in-progress |
| `stats.pending_tasks` | int | Tareas con status pending |
| `stats.in_progress_tasks` | int | Tareas con status in-progress |
| `stats.done_tasks` | int | Tareas con status done |
| `stats.last_session_date` | date | Fecha de última nota en sessions/ |
| `folders.*` | int | Cantidad de archivos por carpeta |

---

### `vibe://projects/{name}`

Detalle de un proyecto específico: estructura y archivos.

**Parameters:**

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `name` | string | sí | Nombre del proyecto |

**Response:**

```json
{
  "name": "vibeMCP",
  "path": "/Users/x/.vibe/vibeMCP",
  "last_updated": "2025-02-09T14:30:00Z",
  "folders": {
    "tasks": [
      {
        "filename": "001-documentar-estructura.md",
        "status": "done",
        "updated": "2025-02-07"
      },
      {
        "filename": "002-definir-yaml-frontmatter.md",
        "status": "done",
        "updated": "2025-02-08"
      },
      {
        "filename": "003-disenar-schema-sqlite.md",
        "status": "done",
        "updated": "2025-02-09"
      },
      {
        "filename": "004-definir-interfaz-mcp.md",
        "status": "pending",
        "updated": "2025-02-09"
      }
    ],
    "plans": [
      {
        "filename": "execution-plan.md",
        "updated": "2025-02-09"
      }
    ],
    "sessions": [
      {
        "filename": "2025-02-09.md",
        "updated": "2025-02-09"
      }
    ]
  }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `folders.tasks[]` | array | Lista de tareas con status |
| `folders.*[]` | array | Lista de archivos en cada carpeta |
| `*.filename` | string | Nombre del archivo |
| `*.status` | string | Status (solo para tasks) |
| `*.updated` | date | Fecha de actualización |

---

### `vibe://projects/{name}/{folder}/{file}`

Contenido de un archivo específico.

**Parameters:**

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `name` | string | sí | Nombre del proyecto |
| `folder` | string | sí | Carpeta: tasks, plans, sessions, etc. |
| `file` | string | sí | Nombre del archivo |

**Response:**

```json
{
  "project": "vibeMCP",
  "folder": "tasks",
  "filename": "004-definir-interfaz-mcp.md",
  "path": "vibeMCP/tasks/004-definir-interfaz-mcp.md",
  "metadata": {
    "type": "task",
    "status": "pending",
    "updated": "2025-02-09",
    "tags": ["mcp", "design"],
    "owner": null
  },
  "content": "# Task: Definir interfaz MCP...\n\nStatus: pending\n\n## Objective\n..."
}
```

---

## Tools

### Clasificación

| Categoría | Tools | Descripción |
|-----------|-------|-------------|
| **Lectura** | search, read_doc, list_tasks, get_plan | Solo consultan datos, no modifican filesystem |
| **Escritura** | create_doc, update_doc, create_task, update_task_status, create_plan, log_session | Crean o modifican archivos |
| **Admin** | reindex | Operaciones de mantenimiento |

---

## Tools de Lectura

### `search` ⭐ Happy Path

Búsqueda full-text cross-project vía FTS5 con ranking inteligente.

**Parameters:**

| Param | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `query` | string | sí | - | Texto a buscar |
| `project` | string | no | null | Filtrar por proyecto |
| `folder` | string | no | null | Filtrar por carpeta |
| `limit` | int | no | 20 | Máximo de resultados |

**Request:**

```json
{
  "query": "indexador sqlite",
  "project": "vibeMCP",
  "limit": 10
}
```

**Response:**

```json
{
  "query": "indexador sqlite",
  "total_matches": 15,
  "results": [
    {
      "project": "vibeMCP",
      "folder": "tasks",
      "filename": "003-disenar-schema-sqlite.md",
      "path": "vibeMCP/tasks/003-disenar-schema-sqlite.md",
      "heading": "## Objective",
      "snippet": "...diseñar el **schema SQLite** para el **indexador** del MCP server...",
      "score": 7.65,
      "metadata": {
        "type": "task",
        "status": "done",
        "updated": "2025-02-09"
      }
    }
  ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `results[].heading` | string | Heading del chunk donde se encontró |
| `results[].snippet` | string | Fragmento con términos resaltados |
| `results[].score` | float | Score combinado (BM25 × boosts) |

**Filesystem operation:** Consulta SQLite FTS5 (chunks_fts), no toca filesystem.

---

### `read_doc` ⭐ Happy Path

Lee un documento completo de cualquier carpeta.

**Parameters:**

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `project` | string | sí | Nombre del proyecto |
| `folder` | string | sí | Carpeta contenedora |
| `filename` | string | sí | Nombre del archivo |

**Request:**

```json
{
  "project": "vibeMCP",
  "folder": "tasks",
  "filename": "004-definir-interfaz-mcp.md"
}
```

**Response:**

```json
{
  "project": "vibeMCP",
  "folder": "tasks",
  "filename": "004-definir-interfaz-mcp.md",
  "path": "vibeMCP/tasks/004-definir-interfaz-mcp.md",
  "metadata": {
    "type": "task",
    "status": "pending",
    "updated": "2025-02-09",
    "tags": [],
    "owner": null
  },
  "content": "# Task: Definir interfaz MCP (resources, tools, prompts)\n\nStatus: pending\n\n## Objective\nDocumentar la API completa del MCP server...\n\n## Steps\n1. [ ] Definir resources...\n"
}
```

**Filesystem operation:** `read(~/.vibe/{project}/{folder}/{filename})`

---

### `list_tasks`

Lista tareas de un proyecto o cross-project, con filtro opcional por status.

**Parameters:**

| Param | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `project` | string | no | null | Filtrar por proyecto (null = todos) |
| `status` | string | no | null | Filtrar por status: pending, in-progress, done, blocked |
| `include_content` | bool | no | false | Incluir contenido completo de cada tarea |

**Request:**

```json
{
  "project": "vibeMCP",
  "status": "pending"
}
```

**Response:**

```json
{
  "project": "vibeMCP",
  "filter": {
    "status": "pending"
  },
  "total": 2,
  "tasks": [
    {
      "filename": "004-definir-interfaz-mcp.md",
      "title": "Definir interfaz MCP (resources, tools, prompts)",
      "status": "pending",
      "updated": "2025-02-09",
      "objective": "Documentar la API completa del MCP server: resources para lectura, tools para operaciones, y prompts para templates."
    },
    {
      "filename": "005-crear-workspace-ejemplo.md",
      "title": "Crear un workspace de ejemplo",
      "status": "pending",
      "updated": "2025-02-09",
      "objective": "Armar 2-3 proyectos con contenido realista para validación."
    }
  ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tasks[].title` | string | Título extraído del `# Task:` header |
| `tasks[].objective` | string | Contenido de la sección `## Objective` |

**Filesystem operation:** Consulta SQLite (tabla documents), no toca filesystem.

---

### `get_plan`

Lee el execution plan de un proyecto.

**Parameters:**

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `project` | string | sí | Nombre del proyecto |
| `filename` | string | no | Nombre del plan (default: `execution-plan.md`) |

**Request:**

```json
{
  "project": "vibeMCP"
}
```

**Response:**

```json
{
  "project": "vibeMCP",
  "filename": "execution-plan.md",
  "path": "vibeMCP/plans/execution-plan.md",
  "exists": true,
  "metadata": {
    "type": "plan",
    "updated": "2025-02-09"
  },
  "content": "# Execution Plan — vibeMCP\n\n## Overview\n...",
  "parsed": {
    "overview": "Exponer el sistema de workspaces .vibe existente como un MCP server...",
    "task_count": 12,
    "pending": 5,
    "in_progress": 1,
    "done": 6
  }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `exists` | bool | Si el plan existe |
| `parsed.overview` | string | Contenido de `## Overview` |
| `parsed.*_count` | int | Conteos parseados de `## Current Status` |

**Filesystem operation:** `read(~/.vibe/{project}/plans/{filename})`

---

## Tools de Escritura

Todas las tools de escritura disparan re-indexación automática del archivo afectado (no reindex global).

### `create_doc`

Crea un archivo en cualquier carpeta de un proyecto.

**Parameters:**

| Param | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `project` | string | sí | - | Nombre del proyecto |
| `folder` | string | sí | - | Carpeta: tasks, plans, sessions, etc. |
| `filename` | string | sí | - | Nombre del archivo |
| `content` | string | sí | - | Contenido del archivo |
| `frontmatter` | object | no | null | YAML frontmatter opcional |

**Request:**

```json
{
  "project": "vibeMCP",
  "folder": "references",
  "filename": "mcp-protocol-notes.md",
  "content": "# MCP Protocol Notes\n\n## Overview\n...",
  "frontmatter": {
    "tags": ["mcp", "protocol", "reference"]
  }
}
```

**Response:**

```json
{
  "success": true,
  "path": "vibeMCP/references/mcp-protocol-notes.md",
  "absolute_path": "/Users/x/.vibe/vibeMCP/references/mcp-protocol-notes.md",
  "indexed": true
}
```

**Errors:**

| Code | Descripción |
|------|-------------|
| `FILE_EXISTS` | El archivo ya existe (usar update_doc) |
| `INVALID_FOLDER` | Carpeta no válida |
| `PROJECT_NOT_FOUND` | Proyecto no existe |

**Filesystem operation:** `write(~/.vibe/{project}/{folder}/{filename})`

---

### `update_doc`

Actualiza el contenido de un archivo existente.

**Parameters:**

| Param | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `project` | string | sí | - | Nombre del proyecto |
| `folder` | string | sí | - | Carpeta contenedora |
| `filename` | string | sí | - | Nombre del archivo |
| `content` | string | sí | - | Nuevo contenido completo |
| `frontmatter` | object | no | null | Actualizar frontmatter (merge) |

**Request:**

```json
{
  "project": "vibeMCP",
  "folder": "tasks",
  "filename": "004-definir-interfaz-mcp.md",
  "content": "# Task: Definir interfaz MCP...\n\nStatus: in-progress\n\n..."
}
```

**Response:**

```json
{
  "success": true,
  "path": "vibeMCP/tasks/004-definir-interfaz-mcp.md",
  "previous_hash": "abc123...",
  "new_hash": "def456...",
  "indexed": true
}
```

**Errors:**

| Code | Descripción |
|------|-------------|
| `FILE_NOT_FOUND` | El archivo no existe (usar create_doc) |

**Filesystem operation:** `write(~/.vibe/{project}/{folder}/{filename})`

---

### `create_task` ⭐ Happy Path

Crea un archivo de tarea con el formato estándar.

**Parameters:**

| Param | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `project` | string | sí | - | Nombre del proyecto |
| `title` | string | sí | - | Título de la tarea |
| `objective` | string | sí | - | Objetivo (1 párrafo) |
| `steps` | array[string] | sí | - | Lista de pasos |
| `acceptance_criteria` | array[string] | sí | - | Criterios de aceptación |
| `context` | object | no | null | Archivos relacionados, dependencias |
| `notes` | string | no | null | Notas adicionales |
| `status` | string | no | "pending" | Status inicial |
| `tags` | array[string] | no | [] | Tags para frontmatter |

**Request:**

```json
{
  "project": "vibeMCP",
  "title": "Implementar tool search",
  "objective": "Implementar la tool search con FTS5 y ranking inteligente.",
  "steps": [
    "Crear función de búsqueda en SQLite",
    "Implementar cálculo de ranking con boosts",
    "Formatear respuesta según spec MCP",
    "Agregar tests"
  ],
  "acceptance_criteria": [
    "Búsqueda devuelve resultados relevantes",
    "Ranking ordena por relevancia combinada",
    "Snippets muestran contexto del match"
  ],
  "context": {
    "related_files": ["src/tools/search.py", "src/db/fts.py"],
    "dependencies": ["003-disenar-schema-sqlite"]
  },
  "notes": "Usar BM25 nativo de FTS5. Los boosts están documentados en sqlite-schema.md",
  "tags": ["backend", "fts5", "search"]
}
```

**Response:**

```json
{
  "success": true,
  "task": {
    "number": "006",
    "filename": "006-implementar-tool-search.md",
    "path": "vibeMCP/tasks/006-implementar-tool-search.md",
    "status": "pending"
  },
  "indexed": true
}
```

**Comportamiento:**
1. Detecta el siguiente número de tarea disponible (NNN)
2. Genera slug del título en kebab-case
3. Crea archivo con formato estándar de task
4. Agrega frontmatter si hay tags

**Archivo generado:**

```markdown
---
tags: [backend, fts5, search]
---
# Task: Implementar tool search

Status: pending

## Objective
Implementar la tool search con FTS5 y ranking inteligente.

## Context
- Related files: `src/tools/search.py`, `src/db/fts.py`
- Dependencies: 003-disenar-schema-sqlite

## Steps
1. [ ] Crear función de búsqueda en SQLite
2. [ ] Implementar cálculo de ranking con boosts
3. [ ] Formatear respuesta según spec MCP
4. [ ] Agregar tests

## Acceptance Criteria
- [ ] Búsqueda devuelve resultados relevantes
- [ ] Ranking ordena por relevancia combinada
- [ ] Snippets muestran contexto del match

## Notes
Usar BM25 nativo de FTS5. Los boosts están documentados en sqlite-schema.md
```

**Filesystem operation:** `write(~/.vibe/{project}/tasks/{NNN}-{slug}.md)`

---

### `update_task_status`

Cambia el status de una tarea.

**Parameters:**

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `project` | string | sí | Nombre del proyecto |
| `task` | string | sí | Filename o número de tarea (ej: "004" o "004-definir-interfaz-mcp.md") |
| `status` | string | sí | Nuevo status: pending, in-progress, done, blocked |

**Request:**

```json
{
  "project": "vibeMCP",
  "task": "004",
  "status": "in-progress"
}
```

**Response:**

```json
{
  "success": true,
  "task": {
    "filename": "004-definir-interfaz-mcp.md",
    "path": "vibeMCP/tasks/004-definir-interfaz-mcp.md",
    "previous_status": "pending",
    "new_status": "in-progress"
  },
  "indexed": true
}
```

**Comportamiento:**
1. Busca el archivo de tarea por número o filename
2. Parsea el contenido
3. Reemplaza la línea `Status: X` con el nuevo status
4. Escribe el archivo modificado

**Filesystem operation:** `read + write(~/.vibe/{project}/tasks/{task}.md)`

---

### `create_plan`

Crea o actualiza un execution plan.

**Parameters:**

| Param | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `project` | string | sí | - | Nombre del proyecto |
| `filename` | string | no | "execution-plan.md" | Nombre del archivo |
| `content` | string | sí | - | Contenido completo del plan |

**Request:**

```json
{
  "project": "vibeMCP",
  "content": "# Execution Plan — vibeMCP\n\n## Overview\n..."
}
```

**Response:**

```json
{
  "success": true,
  "path": "vibeMCP/plans/execution-plan.md",
  "action": "created",
  "indexed": true
}
```

| `action` | Descripción |
|----------|-------------|
| `created` | Archivo nuevo |
| `updated` | Archivo existente sobrescrito |

**Filesystem operation:** `write(~/.vibe/{project}/plans/{filename})`

---

### `log_session` ⭐ Happy Path

Registra una nota de sesión con fecha automática.

**Parameters:**

| Param | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `project` | string | sí | - | Nombre del proyecto |
| `content` | string | sí | - | Contenido de la nota |
| `suffix` | string | no | null | Sufijo opcional para el filename (ej: "debugging-auth") |
| `append` | bool | no | false | Agregar al archivo existente del día |

**Request (crear nueva):**

```json
{
  "project": "vibeMCP",
  "content": "## Lo que hice\n\n- Diseñé la interfaz MCP\n- Documenté todos los tools\n\n## Next steps\n\n- Implementar indexador\n- Escribir tests"
}
```

**Request (append a sesión existente):**

```json
{
  "project": "vibeMCP",
  "content": "## Afternoon update\n\n- Terminé el diseño\n- El PR está listo para review",
  "append": true
}
```

**Response:**

```json
{
  "success": true,
  "session": {
    "filename": "2025-02-09.md",
    "path": "vibeMCP/sessions/2025-02-09.md",
    "action": "created"
  },
  "indexed": true
}
```

| `action` | Descripción |
|----------|-------------|
| `created` | Archivo nuevo del día |
| `appended` | Agregado a archivo existente |

**Comportamiento:**
1. Genera filename con fecha actual: `YYYY-MM-DD.md` (o `YYYY-MM-DD-{suffix}.md`)
2. Si `append=true` y el archivo existe, agrega contenido con separador `---`
3. Si el archivo no existe, crea uno nuevo

**Filesystem operation:** `write/append(~/.vibe/{project}/sessions/{date}.md)`

---

## Tool Administrativa

### `reindex`

Fuerza re-indexación del workspace completo o de un proyecto específico.

**Parameters:**

| Param | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `project` | string | no | null | Proyecto específico (null = todos) |
| `full` | bool | no | false | Forzar rebuild completo (ignorar mtime) |

**Request:**

```json
{
  "project": "vibeMCP",
  "full": false
}
```

**Response:**

```json
{
  "success": true,
  "project": "vibeMCP",
  "stats": {
    "scanned": 42,
    "updated": 3,
    "added": 1,
    "deleted": 0,
    "unchanged": 38,
    "duration_ms": 156
  }
}
```

| Campo | Descripción |
|-------|-------------|
| `scanned` | Total de archivos procesados |
| `updated` | Archivos re-indexados por cambio de contenido |
| `added` | Archivos nuevos indexados |
| `deleted` | Archivos eliminados del índice |
| `unchanged` | Archivos sin cambios (skip) |

**Filesystem operation:** `walk(~/.vibe/{project}/)` + SQLite sync

---

## Prompts

Los prompts son templates que el cliente puede invocar para obtener contexto estructurado.

### `project_briefing`

"Poneme al día con {proyecto}" — resume el estado actual del proyecto.

**Parameters:**

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `project` | string | sí | Nombre del proyecto |

**Invocación:**

```
project_briefing(project="vibeMCP")
```

**Genera prompt que incluye:**

1. **Overview del proyecto** — stats generales
2. **Tareas activas** — in-progress y blocked
3. **Tareas pendientes** — próximas a ejecutar
4. **Últimas sesiones** — notas de las últimas 3 sesiones
5. **Decisiones recientes** — de plans/ o changelog/

**Ejemplo de prompt generado:**

```
# Project Briefing: vibeMCP

## Current Status
- **Total documents:** 42
- **Open tasks:** 5 (2 in-progress, 3 pending)
- **Last updated:** 2025-02-09

## Active Tasks (in-progress)

### 004 - Definir interfaz MCP
**Objective:** Documentar la API completa del MCP server...
**Progress:** 3/7 steps completed

## Blocked Tasks

(none)

## Pending Tasks (next up)

1. 005 - Crear workspace de ejemplo
2. 006 - Implementar indexador

## Recent Sessions

### 2025-02-09
- Diseñé el schema SQLite
- Documenté reglas de ranking
- Próximo: interfaz MCP

### 2025-02-08
- Definí formato de frontmatter YAML
- Actualicé vibe-structure.md

## Recent Decisions

- **Database choice:** SQLite con FTS5 (no necesitamos escala)
- **Chunking strategy:** Por headings nivel 1-2
```

---

### `session_start`

Carga contexto completo del proyecto antes de empezar a trabajar.

**Parameters:**

| Param | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `project` | string | sí | Nombre del proyecto |
| `focus` | string | no | Área de enfoque (task number, feature name) |

**Invocación:**

```
session_start(project="vibeMCP", focus="004")
```

**Genera prompt que incluye:**

1. **Briefing del proyecto** (similar a project_briefing)
2. **Contexto específico del focus** (si se provee)
3. **Archivos relacionados**
4. **Última sesión** (para retomar donde quedó)
5. **Suggested actions**

**Ejemplo de prompt generado:**

```
# Session Start: vibeMCP
Focus: Task 004 - Definir interfaz MCP

## Task Details
**Status:** pending
**Objective:** Documentar la API completa del MCP server...

### Steps
1. [ ] Definir resources
2. [ ] Definir tools de lectura
3. [ ] Definir tools de escritura
4. [ ] Definir prompts
5. [ ] Documentar parámetros y respuestas
6. [ ] Marcar happy path
7. [ ] Mapear tools a filesystem ops

## Related Files
- `docs/sqlite-schema.md` — Schema SQLite (task 003, done)
- `docs/vibe-structure.md` — Estructura del workspace

## Last Session (2025-02-09)
- Completé el schema SQLite
- Documenté reglas de ranking
- Próximo paso: empezar con interfaz MCP

## Suggested Actions
1. Read related files for context
2. Start with resources definition
3. Document happy path tools first
```

---

## Error Handling

Todas las respuestas de error siguen el mismo formato:

```json
{
  "success": false,
  "error": {
    "code": "FILE_NOT_FOUND",
    "message": "File 'tasks/999-nonexistent.md' not found in project 'vibeMCP'",
    "details": {
      "project": "vibeMCP",
      "path": "tasks/999-nonexistent.md"
    }
  }
}
```

### Códigos de Error Comunes

| Code | HTTP | Descripción |
|------|------|-------------|
| `PROJECT_NOT_FOUND` | 404 | El proyecto no existe |
| `FILE_NOT_FOUND` | 404 | El archivo no existe |
| `FILE_EXISTS` | 409 | El archivo ya existe (en create) |
| `INVALID_FOLDER` | 400 | Carpeta no válida |
| `INVALID_STATUS` | 400 | Status no válido |
| `INVALID_QUERY` | 400 | Query de búsqueda inválida |
| `INDEX_ERROR` | 500 | Error al indexar |
| `FILESYSTEM_ERROR` | 500 | Error de lectura/escritura |

---

## Mapeo Tool → Filesystem

Referencia rápida de qué operación de filesystem ejecuta cada tool:

| Tool | Tipo | Filesystem Operation |
|------|------|---------------------|
| `search` | read | SQLite query (no filesystem) |
| `read_doc` | read | `read(~/.vibe/{project}/{folder}/{file})` |
| `list_tasks` | read | SQLite query (no filesystem) |
| `get_plan` | read | `read(~/.vibe/{project}/plans/{file})` |
| `create_doc` | write | `write(~/.vibe/{project}/{folder}/{file})` |
| `update_doc` | write | `write(~/.vibe/{project}/{folder}/{file})` |
| `create_task` | write | `write(~/.vibe/{project}/tasks/{NNN}-{slug}.md)` |
| `update_task_status` | write | `read+write(~/.vibe/{project}/tasks/{task}.md)` |
| `create_plan` | write | `write(~/.vibe/{project}/plans/{file})` |
| `log_session` | write | `write/append(~/.vibe/{project}/sessions/{date}.md)` |
| `reindex` | admin | `walk(~/.vibe/)` + SQLite sync |

---

## Integración con Comandos Existentes

### `/task-breakdown` → MCP Tools

El comando `/task-breakdown` actualmente escribe directamente al filesystem. Con MCP, usaría:

1. `list_tasks(project)` — obtener tareas existentes
2. `create_task(...)` × N — crear cada tarea
3. `create_plan(...)` — crear execution plan

### `/solve-task` → MCP Tools

1. `read_doc(project, "tasks", task_file)` — leer tarea
2. `update_task_status(project, task, "in-progress")` — marcar inicio
3. (trabajo del agente)
4. `update_task_status(project, task, "done")` — marcar fin
5. `log_session(project, summary)` — registrar sesión

---

## Notas de Implementación

### Re-indexación Automática

Toda tool de escritura dispara re-indexación del archivo afectado:

```python
async def create_doc(...):
    # 1. Escribir archivo
    write_file(path, content)

    # 2. Re-indexar solo este archivo
    await index_file(path)

    return {"success": True, "indexed": True}
```

### Validación de Paths

Todas las tools validan que el path final esté dentro de `VIBE_ROOT`:

```python
def validate_path(project: str, folder: str, filename: str) -> Path:
    path = VIBE_ROOT / project / folder / filename

    # Prevenir directory traversal
    if not path.resolve().is_relative_to(VIBE_ROOT):
        raise InvalidPathError("Path outside VIBE_ROOT")

    return path
```

### Concurrencia

- Lecturas son concurrentes (WAL mode de SQLite)
- Escrituras usan lock por proyecto
- Re-indexación global usa lock global
