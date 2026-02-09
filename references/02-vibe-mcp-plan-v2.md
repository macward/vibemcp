# .vibe MCP — Plan de Desarrollo

## Resumen

Exponer el sistema de workspaces `.vibe` existente como un MCP server accesible remotamente, manteniendo compatibilidad total con la estructura de carpetas y los comandos de agentes actuales.

**Stack:** Python + FastMCP, SSE, Filesystem `.vibe/` + SQLite FTS5, Bearer token
**Deploy:** VPS (DigitalOcean/Fly) con HTTPS vía Caddy
**Clientes:** Claude Code CLI, Claude.ai, Cursor/Windsurf

**Orden de implementación recomendado:** empezar por el indexador (1.2). Si eso funciona bien, todo lo demás encaja solo.

---

## Fase 0 — Diseño

### 0.1 — Documentar la estructura existente

- Mapear las 8 carpetas estándar (`tasks`, `plans`, `sessions`, `reports`, `changelog`, `references`, `scratch`, `assets`) y su propósito
- Documentar las convenciones de nombres de archivos por carpeta (ej: `001-nombre.md` en tasks, fechas en sessions)
- Documentar el formato de archivos de tareas (status, objective, steps, acceptance criteria)
- Documentar el formato de execution plans (task graph, tabla de dependencias, current status)

### 0.2 — Definir YAML frontmatter opcional

- Campos estándar: `project`, `type`, `updated`, `tags`, `status`, `owner`
- Todos opcionales — si no existe frontmatter, inferir por path (carpeta = tipo, directorio padre = proyecto)
- Documentar cómo el indexador usa el frontmatter cuando está presente y cómo infiere cuando no

### 0.3 — Diseñar el schema SQLite

- Tabla `projects` — nombre, path, metadata
- Tabla `documents` — proyecto, carpeta, path, frontmatter parseado, content_hash, mtime, timestamps
- Tabla `chunks` — document_id, heading, contenido del chunk, orden
- Tabla FTS5 `chunks_fts` — índice full-text sobre chunks
- Definir max chunk size (~1-2k tokens). Si una sección excede el límite, subdividir por párrafos como fallback
- Documentar reglas de ranking con pesos numéricos explícitos:
  - Boost por tipo de archivo: `status.md` > `tasks/` > `plans/` > resto
  - Boost por recencia (`updated` del frontmatter o mtime)
  - Boost por heading clave: "Next", "Blockers", "Decisions", "Current Status"

### 0.4 — Definir la interfaz MCP

- Listar resources, tools y prompts con sus parámetros y respuestas esperadas
- Documentar el happy path: `search`, `read_doc`, `create_task`, `log_session` cubren el 80% del uso
- Mapear cada tool a la operación de filesystem que ejecuta
- Definir qué tools son de lectura y cuáles de escritura
- Documentar cómo `/task-decomposer` y otros comandos usarían las tools del MCP en vez de escribir directo

### 0.5 — Crear un workspace de ejemplo

- Armar 2-3 proyectos con contenido realista
- Incluir tareas en distintos estados, un execution plan, notas de sesión
- Incluir archivos con y sin frontmatter para validar ambos paths
- Validar que un LLM puede entender el contexto leyendo los archivos

---

## Fase 1 — MCP Server core

### 1.1 — Setup del proyecto

- Estructura del repo (`src/`, `tests/`, `config/`)
- `pyproject.toml` con dependencias (mcp, sqlite)
- Configuración vía env vars: `VIBE_ROOT`, `VIBE_PORT`, `VIBE_DB`

### 1.2 — Indexador ⭐ (implementar primero)

Este es el corazón del sistema. Si funciona bien, todo lo demás encaja.

- File walker: descubrir todos los archivos en `VIBE_ROOT`, respetando la estructura de carpetas
- Detección de cambios: mtime como fast-path, content hash para edge cases (git checkout, rsync)
- Parser de frontmatter: extraer YAML si existe, inferir metadata por path si no
- Chunking por headings: partir cada archivo en secciones por `#` / `##`
  - Max chunk size ~1-2k tokens
  - Fallback: subdividir por párrafos si una sección es muy grande
- Sync a SQLite: insertar/actualizar/borrar según cambios detectados
- FTS5: poblar el índice sobre chunks
- Ranking: implementar boost por tipo de archivo, recencia, y headings clave con pesos documentados
- Concurrencia: lock simple (por proyecto o global corto) para write + search
- Comando `reindex`: rebuild completo desde el filesystem
- Dejar documentado "incremental reindex" como mejora futura (no implementar aún)

### 1.3 — Resources

- `vibe://projects` — listar todos los proyectos con resumen:
  - `last_updated` (fecha del archivo más reciente)
  - `open_tasks_count` (tareas pending + in-progress)
  - `last_session_date` (última nota de sesión)
  - Cantidad de archivos por carpeta
- `vibe://projects/{name}` — detalle de un proyecto: carpetas, archivos disponibles, estado de tareas
- `vibe://projects/{name}/{folder}/{file}` — leer un archivo específico

### 1.4 — Tools de lectura

- `search` — búsqueda full-text vía FTS5 con ranking, devuelve chunks con contexto (proyecto, carpeta, archivo, heading)
- `read_doc` — leer un documento completo
- `list_tasks` — listar tareas de un proyecto o cross-project, filtrar por status (pending, in-progress, done)
- `get_plan` — leer el execution plan de un proyecto

### 1.5 — Tools de escritura

- `create_doc` — crear un archivo en cualquier carpeta de un proyecto
- `update_doc` — actualizar contenido de un archivo existente
- `create_task` — crear un archivo de tarea con el formato estándar (status, objective, steps, acceptance criteria)
- `update_task_status` — cambiar el status de una tarea (pending → in-progress → done)
- `create_plan` — crear o actualizar un execution plan
- `log_session` — crear una nota de sesión con fecha automática en `sessions/`
- `reindex` — forzar re-indexación del workspace
- Toda escritura dispara re-indexación del archivo afectado (no reindex global)

### 1.6 — Prompts

- `project_briefing` — "poneme al día con {proyecto}": lee context, status, tareas pendientes, últimas sesiones
- `session_start` — cargar contexto completo del proyecto antes de arrancar a trabajar

### 1.7 — Tests

- Tests del indexador: sync correcto, chunking por headings, max chunk size, FTS5 devuelve resultados, ranking funciona, detección de cambios por mtime y hash
- Tests de cada resource: responde con la estructura esperada, incluye métricas (task count, last updated)
- Tests de cada tool de lectura: devuelve contenido correcto
- Tests de cada tool de escritura: crea/modifica archivos correctamente, dispara re-indexación
- Test de integración: crear task vía tool → buscar → encontrar
- Tests de borde: workspace vacío, proyecto sin tareas, archivo sin frontmatter, sección enorme que requiere fallback de chunking
- Test de concurrencia: write + search simultáneo no corrompe

---

## Fase 2 — Auth + seguridad

- Middleware de bearer token (`Authorization: Bearer <token>`)
- Token >= 32 bytes
- Rotación de token sin downtime (reload de env var)
- Validación de paths (evitar directory traversal, restringir a `VIBE_ROOT`)
- Rate limiting básico
- Tests de auth y path safety

---

## Fase 3 — Deploy

- Provisionar VPS (DigitalOcean droplet o Fly.io)
- Configurar HTTPS con Caddy reverse proxy
- Manejar reconexiones SSE: documentar e implementar `Last-Event-ID`
- Systemd service para el MCP server
- Repo Git para `~/.vibe/` — sync manual: `git pull` + `reindex`. Nunca auto-commit desde el server
- Smoke tests en producción

---

## Fase 4 — Conectar clientes

- Configurar Claude Code CLI → endpoint SSE remoto (conectar primero, es el más estable)
- Configurar Claude.ai → MCP server en settings
- Configurar Cursor/Windsurf → MCP config (conectar último, más frágiles con MCP)
- Adaptar `/task-decomposer` y otros comandos para usar tools del MCP
- Documentar la configuración de cada cliente

---

## Fase 5 — Uso real + iteración

- Migrar los workspaces existentes al repo Git
- Usar el flujo diario por una semana
- Ajustar pesos de ranking según uso real
- Identificar qué tools sobran y qué prompts faltan
- Evaluar si alguna tool genera confusión en el LLM y simplificar
