# SQLite Schema Design

Schema de base de datos SQLite para el índice de vibeMCP. Este índice es **disposable** — si se corrompe, se regenera desde el filesystem.

## Overview

```
projects 1───M documents 1───M chunks
                                │
                                ▼
                          chunks_fts (FTS5)
```

## Tables

### 1. projects

Almacena los proyectos (workspaces) descubiertos en `~/.vibe/`.

```sql
CREATE TABLE projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,           -- nombre del workspace (ej: "vibeMCP")
    path        TEXT NOT NULL UNIQUE,           -- path absoluto (ej: "/Users/x/.vibe/vibeMCP")
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_projects_name ON projects(name);
```

### 2. documents

Almacena los archivos `.md` indexados con su metadata (parseada o inferida).

```sql
CREATE TABLE documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Ubicación
    path         TEXT NOT NULL UNIQUE,          -- path relativo desde VIBE_ROOT (ej: "vibeMCP/tasks/001-setup.md")
    folder       TEXT NOT NULL,                 -- carpeta contenedora (ej: "tasks", "plans", "sessions")
    filename     TEXT NOT NULL,                 -- nombre del archivo (ej: "001-setup.md")

    -- Metadata (de frontmatter o inferida)
    type         TEXT,                          -- task, plan, session, report, changelog, reference, scratch, asset
    status       TEXT,                          -- pending, in-progress, done, blocked (solo para tasks)
    owner        TEXT,                          -- responsable del documento
    tags         TEXT,                          -- JSON array: '["tag1", "tag2"]'

    -- Control de cambios
    content_hash TEXT NOT NULL,                 -- SHA-256 del contenido (para detectar cambios)
    mtime        REAL NOT NULL,                 -- timestamp de modificación del archivo
    updated      TEXT,                          -- fecha de frontmatter 'updated' o NULL

    -- Timestamps del índice
    indexed_at   TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE INDEX idx_documents_project ON documents(project_id);
CREATE INDEX idx_documents_folder ON documents(folder);
CREATE INDEX idx_documents_type ON documents(type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_mtime ON documents(mtime DESC);
CREATE INDEX idx_documents_hash ON documents(content_hash);
CREATE INDEX idx_documents_project_folder ON documents(project_id, folder);
```

### 3. chunks

Almacena los fragmentos de contenido, divididos por headings. Esto permite búsquedas más precisas y resultados con mejor contexto.

```sql
CREATE TABLE chunks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Contenido
    heading      TEXT,                          -- heading del chunk (ej: "## Objective", "### Step 1")
    heading_level INTEGER DEFAULT 0,            -- nivel del heading (1 = #, 2 = ##, 0 = sin heading)
    content      TEXT NOT NULL,                 -- contenido del chunk (sin frontmatter)

    -- Orden y posición
    chunk_order  INTEGER NOT NULL,              -- orden dentro del documento (0, 1, 2...)
    char_offset  INTEGER NOT NULL,              -- offset en caracteres desde inicio del documento

    -- Metadata para ranking
    is_priority_heading INTEGER DEFAULT 0,      -- 1 si heading es "Next", "Blockers", "Current Status", "Decisions"

    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_chunks_document_order ON chunks(document_id, chunk_order);
CREATE INDEX idx_chunks_heading ON chunks(heading);
CREATE INDEX idx_chunks_priority ON chunks(is_priority_heading) WHERE is_priority_heading = 1;
```

### 4. chunks_fts (FTS5)

Índice full-text sobre el contenido de chunks para búsqueda rápida.

```sql
CREATE VIRTUAL TABLE chunks_fts USING fts5(
    content,                                    -- contenido del chunk
    heading,                                    -- heading (para búsquedas en títulos)
    content='chunks',                           -- tabla de contenido
    content_rowid='id'                          -- mapeo de rowid
);

-- Triggers para mantener FTS5 sincronizado con chunks
CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content, heading)
    VALUES (NEW.id, NEW.content, NEW.heading);
END;

CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, heading)
    VALUES ('delete', OLD.id, OLD.content, OLD.heading);
END;

CREATE TRIGGER chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, heading)
    VALUES ('delete', OLD.id, OLD.content, OLD.heading);
    INSERT INTO chunks_fts(rowid, content, heading)
    VALUES (NEW.id, NEW.content, NEW.heading);
END;
```

---

## Chunking Strategy

### Reglas de División

1. **Por headings** — Dividir en cada `#` o `##` (niveles 1 y 2)
2. **Máximo ~1500 tokens** (~6000 caracteres) por chunk
3. **Fallback por párrafos** — Si una sección supera el límite, subdividir por párrafos (`\n\n`)
4. **Fallback por líneas** — Si un párrafo supera el límite, dividir por líneas
5. **Mínimo viable** — Si una línea supera el límite, truncar (edge case raro)

### Pseudocode

```python
MAX_CHUNK_CHARS = 6000  # ~1500 tokens

def chunk_document(content: str) -> list[Chunk]:
    # Remover frontmatter primero
    content = strip_frontmatter(content)

    # Dividir por headings nivel 1 y 2
    sections = split_by_headings(content, levels=[1, 2])

    chunks = []
    for section in sections:
        if len(section.content) <= MAX_CHUNK_CHARS:
            chunks.append(section)
        else:
            # Subdividir por párrafos
            sub_chunks = split_by_paragraphs(section, MAX_CHUNK_CHARS)
            chunks.extend(sub_chunks)

    return chunks
```

### Ejemplo

Documento original:
```markdown
# Task: Setup

Status: pending

## Objective
Lorem ipsum...

## Steps
1. Step one
2. Step two
...

## Notes
Additional info...
```

Chunks resultantes:
| Order | Heading | Content |
|-------|---------|---------|
| 0 | `# Task: Setup` | `Status: pending` |
| 1 | `## Objective` | `Lorem ipsum...` |
| 2 | `## Steps` | `1. Step one\n2. Step two...` |
| 3 | `## Notes` | `Additional info...` |

---

## Ranking Rules

El ranking combina la relevancia FTS5 con boosts por tipo, recencia, y contexto.

### Fórmula

```
final_score = bm25_score * type_boost * recency_boost * heading_boost
```

### Boost por Tipo de Documento

Los archivos más importantes para contexto tienen mayor peso:

| Archivo/Carpeta | Boost | Razón |
|-----------------|-------|-------|
| `status.md` (raíz) | 3.0 | Estado actual del proyecto |
| `tasks/` | 2.0 | Tareas activas y pendientes |
| `plans/` | 1.8 | Planes de ejecución y decisiones |
| `sessions/` | 1.5 | Contexto de trabajo reciente |
| `changelog/` | 1.2 | Historial de cambios |
| `reports/` | 1.0 | Sin boost |
| `references/` | 0.8 | Material de referencia (menos urgente) |
| `scratch/` | 0.5 | Borradores (baja prioridad) |
| `assets/` | 0.3 | Normalmente no contiene texto útil |

### Boost por Recencia

Documentos actualizados recientemente son más relevantes:

```python
def recency_boost(updated_at: datetime) -> float:
    days_ago = (now - updated_at).days

    if days_ago <= 1:
        return 2.0    # Actualizado hoy o ayer
    elif days_ago <= 7:
        return 1.5    # Última semana
    elif days_ago <= 30:
        return 1.2    # Último mes
    elif days_ago <= 90:
        return 1.0    # Últimos 3 meses
    else:
        return 0.8    # Más antiguo
```

### Boost por Headings Clave

Ciertos headings contienen información de alto valor:

| Heading (case-insensitive) | Boost | Razón |
|---------------------------|-------|-------|
| `Current Status` | 2.5 | Estado actual |
| `Next` / `Next Steps` | 2.5 | Próximas acciones |
| `Blockers` / `Blocked By` | 2.5 | Impedimentos |
| `Decisions` | 2.0 | Decisiones importantes |
| `Objective` | 1.5 | Objetivo de la tarea |
| `Acceptance Criteria` | 1.5 | Criterios de éxito |
| Otros | 1.0 | Sin boost |

### Boost por Status de Task

Para tareas, el estado actual afecta relevancia:

| Status | Boost | Razón |
|--------|-------|-------|
| `in-progress` | 2.0 | Trabajo activo |
| `blocked` | 1.8 | Requiere atención |
| `pending` | 1.2 | Próximo trabajo |
| `done` | 0.6 | Completado (menos relevante) |

### Ejemplo de Cálculo

Búsqueda: "indexador"
Documento: `tasks/007-implementar-indexador.md`
Chunk: `## Objective` con contenido sobre el indexador

```
bm25_score     = 0.85 (alta relevancia textual)
type_boost     = 2.0  (tasks/)
recency_boost  = 1.5  (actualizado esta semana)
heading_boost  = 1.5  (## Objective)
status_boost   = 2.0  (in-progress)

final_score = 0.85 * 2.0 * 1.5 * 1.5 * 2.0 = 7.65
```

---

## SQL Queries de Referencia

### Búsqueda Full-Text con Ranking

```sql
SELECT
    c.id,
    c.heading,
    c.content,
    d.path,
    d.folder,
    d.type,
    d.status,
    p.name as project,
    -- Ranking base
    bm25(chunks_fts) as bm25_score,
    -- Boosts aplicados
    CASE
        WHEN d.path LIKE '%/status.md' THEN 3.0
        WHEN d.folder = 'tasks' THEN 2.0
        WHEN d.folder = 'plans' THEN 1.8
        WHEN d.folder = 'sessions' THEN 1.5
        WHEN d.folder = 'changelog' THEN 1.2
        WHEN d.folder = 'reports' THEN 1.0
        WHEN d.folder = 'references' THEN 0.8
        WHEN d.folder = 'scratch' THEN 0.5
        ELSE 0.3
    END as type_boost,
    CASE
        WHEN julianday('now') - julianday(COALESCE(d.updated, datetime(d.mtime, 'unixepoch'))) <= 1 THEN 2.0
        WHEN julianday('now') - julianday(COALESCE(d.updated, datetime(d.mtime, 'unixepoch'))) <= 7 THEN 1.5
        WHEN julianday('now') - julianday(COALESCE(d.updated, datetime(d.mtime, 'unixepoch'))) <= 30 THEN 1.2
        WHEN julianday('now') - julianday(COALESCE(d.updated, datetime(d.mtime, 'unixepoch'))) <= 90 THEN 1.0
        ELSE 0.8
    END as recency_boost,
    CASE
        WHEN c.is_priority_heading = 1 THEN 2.5
        WHEN c.heading LIKE '%Objective%' THEN 1.5
        WHEN c.heading LIKE '%Acceptance%' THEN 1.5
        ELSE 1.0
    END as heading_boost,
    CASE
        WHEN d.status = 'in-progress' THEN 2.0
        WHEN d.status = 'blocked' THEN 1.8
        WHEN d.status = 'pending' THEN 1.2
        WHEN d.status = 'done' THEN 0.6
        ELSE 1.0
    END as status_boost
FROM chunks_fts
JOIN chunks c ON chunks_fts.rowid = c.id
JOIN documents d ON c.document_id = d.id
JOIN projects p ON d.project_id = p.id
WHERE chunks_fts MATCH ?
ORDER BY (
    bm25(chunks_fts) * type_boost * recency_boost * heading_boost * status_boost
) DESC
LIMIT 20;
```

### Listar Tareas de un Proyecto

```sql
SELECT
    d.path,
    d.filename,
    d.status,
    d.owner,
    d.updated,
    datetime(d.mtime, 'unixepoch') as modified
FROM documents d
JOIN projects p ON d.project_id = p.id
WHERE p.name = ?
  AND d.folder = 'tasks'
ORDER BY d.filename;
```

### Obtener Resumen de Proyecto

```sql
SELECT
    p.name,
    p.path,
    COUNT(DISTINCT d.id) as total_docs,
    SUM(CASE WHEN d.folder = 'tasks' AND d.status = 'pending' THEN 1 ELSE 0 END) as pending_tasks,
    SUM(CASE WHEN d.folder = 'tasks' AND d.status = 'in-progress' THEN 1 ELSE 0 END) as active_tasks,
    SUM(CASE WHEN d.folder = 'tasks' AND d.status = 'done' THEN 1 ELSE 0 END) as done_tasks,
    MAX(COALESCE(d.updated, datetime(d.mtime, 'unixepoch'))) as last_updated,
    (SELECT MAX(datetime(mtime, 'unixepoch'))
     FROM documents
     WHERE project_id = p.id AND folder = 'sessions') as last_session
FROM projects p
LEFT JOIN documents d ON p.id = d.project_id
GROUP BY p.id;
```

---

## Complete Schema SQL

```sql
-- vibeMCP Index Schema v1.0
-- Este índice es disposable: se regenera desde ~/.vibe/

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    path        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL,
    path         TEXT NOT NULL UNIQUE,
    folder       TEXT NOT NULL,
    filename     TEXT NOT NULL,
    type         TEXT,
    status       TEXT,
    owner        TEXT,
    tags         TEXT,
    content_hash TEXT NOT NULL,
    mtime        REAL NOT NULL,
    updated      TEXT,
    indexed_at   TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_folder ON documents(folder);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(type);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_mtime ON documents(mtime DESC);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_documents_project_folder ON documents(project_id, folder);

-- Chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id         INTEGER NOT NULL,
    heading             TEXT,
    heading_level       INTEGER DEFAULT 0,
    content             TEXT NOT NULL,
    chunk_order         INTEGER NOT NULL,
    char_offset         INTEGER NOT NULL,
    is_priority_heading INTEGER DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_order ON chunks(document_id, chunk_order);
CREATE INDEX IF NOT EXISTS idx_chunks_heading ON chunks(heading);
CREATE INDEX IF NOT EXISTS idx_chunks_priority ON chunks(is_priority_heading) WHERE is_priority_heading = 1;

-- FTS5 virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    content,
    heading,
    content='chunks',
    content_rowid='id'
);

-- Triggers to keep FTS5 synchronized
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, content, heading)
    VALUES (NEW.id, NEW.content, NEW.heading);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, heading)
    VALUES ('delete', OLD.id, OLD.content, OLD.heading);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, content, heading)
    VALUES ('delete', OLD.id, OLD.content, OLD.heading);
    INSERT INTO chunks_fts(rowid, content, heading)
    VALUES (NEW.id, NEW.content, NEW.heading);
END;

-- Metadata table for index versioning
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', '1.0');
INSERT OR REPLACE INTO meta (key, value) VALUES ('created_at', datetime('now'));
```

### Encontrar Documentos para Re-Indexar

```sql
-- Documentos modificados desde el último indexado
SELECT d.id, d.path, d.mtime, d.indexed_at
FROM documents d
WHERE datetime(d.mtime, 'unixepoch') > d.indexed_at;
```

---

## Notes

### Precedencia de Fechas para Ranking

Para el ranking por recencia, se usa:
1. **`updated` (frontmatter)** — si está presente, se considera la fecha "oficial" de actualización
2. **`mtime` (filesystem)** — fallback si no hay frontmatter

**Importante:** Si un archivo tiene `updated: 2024-01-15` pero fue modificado ayer, el ranking usa la fecha del frontmatter. Esto es intencional: el autor puede querer mantener una fecha de referencia aunque haga edits menores.

Para queries que necesitan la fecha más reciente (filesystem), usar `mtime` directamente.

### Notas Generales

- **WAL mode** habilitado para mejor concurrencia (lecturas no bloquean escrituras)
- **Foreign keys** habilitados para integridad referencial
- El índice completo puede recrearse con `DELETE FROM projects` (cascade elimina todo)
- `content_hash` permite detectar cambios sin leer contenido completo
- `mtime` es el fast-path para detectar archivos modificados
- Tags almacenados como JSON array para flexibilidad (validación en capa de aplicación)
