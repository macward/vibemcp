# .vibe Workspace Structure

Documentación formal del sistema de workspaces `.vibe` para AI agents.

## Overview

Cada proyecto puede tener un workspace `.vibe` asociado en `~/.vibe/<project-name>/`. El nombre del workspace se define en el `CLAUDE.md` del proyecto con la directiva `vibe: <nombre>`.

```
# En CLAUDE.md del proyecto
vibe: mi-proyecto
```

## Estructura de Carpetas

Un workspace `.vibe` tiene 8 carpetas estándar:

```
~/.vibe/<proyecto>/
├── tasks/       ← Tareas individuales del proyecto
├── plans/       ← Planes de ejecución y diseños
├── sessions/    ← Notas de sesiones de trabajo
├── reports/     ← Reportes generados
├── changelog/   ← Historial de cambios
├── references/  ← Material de referencia externo
├── scratch/     ← Borradores y exploración
└── assets/      ← Recursos del proyecto
```

### 1. tasks/

**Propósito**: Almacenar tareas individuales del proyecto, creadas manualmente o por comandos como `/task-breakdown`.

**Naming convention**: `NNN-nombre-descriptivo.md`
- `NNN`: número secuencial de 3 dígitos (001, 002, 003...)
- `nombre-descriptivo`: slug en kebab-case

**Ejemplos**:
```
tasks/
├── 001-setup-proyecto.md
├── 002-implementar-auth.md
├── 003-agregar-tests.md
└── 004-deploy-staging.md
```

### 2. plans/

**Propósito**: Planes de ejecución, diseños arquitectónicos, y documentos de decisiones.

**Naming convention**: Libre, pero típicamente:
- `execution-plan.md` — plan principal del proyecto
- `design-<feature>.md` — diseños específicos
- `decision-<topic>.md` — ADRs (Architecture Decision Records)

**Ejemplos**:
```
plans/
├── execution-plan.md
├── design-auth-system.md
└── decision-database-choice.md
```

### 3. sessions/

**Propósito**: Notas de sesiones de trabajo, para retomar contexto entre sesiones.

**Naming convention**: `YYYY-MM-DD.md` o `YYYY-MM-DD-tema.md`

**Ejemplos**:
```
sessions/
├── 2025-02-07.md
├── 2025-02-08.md
└── 2025-02-09-debugging-auth.md
```

### 4. reports/

**Propósito**: Reportes generados por agents o manualmente (análisis, auditorías, métricas).

**Naming convention**: Libre, descriptivo

**Ejemplos**:
```
reports/
├── security-audit-2025-02.md
├── performance-analysis.md
└── code-review-summary.md
```

### 5. changelog/

**Propósito**: Historial de cambios del proyecto, típicamente por tarea completada.

**Naming convention**: `NNN-nombre-tarea.md` (match con task) o `YYYY-MM-DD-cambio.md`

**Ejemplos**:
```
changelog/
├── 001-setup-proyecto.md
├── 002-implementar-auth.md
└── 2025-02-09-hotfix-login.md
```

### 6. references/

**Propósito**: Material de referencia externo: specs, docs de APIs, snippets, artículos.

**Naming convention**: Libre, descriptivo

**Ejemplos**:
```
references/
├── api-spec-v2.md
├── design-patterns.md
└── competitor-analysis.md
```

### 7. scratch/

**Propósito**: Borradores, exploración, ideas sueltas, experimentos. Contenido temporal o no estructurado.

**Naming convention**: Libre

**Ejemplos**:
```
scratch/
├── idea-nueva-feature.md
├── prueba-algoritmo.py
└── notes.md
```

### 8. assets/

**Propósito**: Recursos del proyecto: diagramas, imágenes, configs, mockups.

**Naming convention**: Libre, organizado por tipo si es necesario

**Ejemplos**:
```
assets/
├── architecture-diagram.png
├── mockup-login.png
├── config-template.json
└── diagrams/
    └── flow-auth.mermaid
```

---

## Formato de Task Files

Los archivos de tareas siguen un formato estándar:

```markdown
# Task: [Título claro de la tarea]

Status: pending | in-progress | done | blocked

## Objective
[Un párrafo máximo describiendo qué logra esta tarea]

## Context
- Related files: [lista de archivos afectados]
- Dependencies: [tareas previas requeridas, si aplica]

## Steps
1. [ ] Paso uno (específico, accionable)
2. [ ] Paso dos
3. [ ] Paso tres
...

## Acceptance Criteria
- [ ] Criterio 1
- [ ] Criterio 2
- [ ] Criterio 3

## Notes
[Opcional: edge cases, gotchas, hints de implementación]
```

### Campos

| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| `# Task:` | Sí | Título de la tarea |
| `Status:` | Sí | Estado actual: `pending`, `in-progress`, `done`, `blocked` |
| `## Objective` | Sí | Descripción breve del objetivo |
| `## Context` | No | Archivos relacionados, dependencias |
| `## Steps` | Sí | Lista de pasos con checkboxes `[ ]` |
| `## Acceptance Criteria` | Sí | Criterios de aceptación con checkboxes |
| `## Notes` | No | Información adicional |

### Estados de tarea

| Status | Significado |
|--------|-------------|
| `pending` | Tarea creada, no iniciada |
| `in-progress` | Tarea en desarrollo activo |
| `done` | Tarea completada, todos los criterios cumplidos |
| `blocked` | Tarea bloqueada por dependencia o impedimento |

---

## Formato de Execution Plan

El execution plan documenta las dependencias entre tareas y el orden de ejecución:

```markdown
# Execution Plan — [Nombre del proyecto]

## Overview
[Una oración describiendo el objetivo general]

## Task Graph

```
001-primera-tarea
 └─► 002-depende-de-001
      └─► 004-depende-de-002
 └─► 003-depende-de-001

005-tarea-independiente
```

## Execution Order

| Order | Task | Blocked By | Blocks |
|-------|------|------------|--------|
| 1 | 001-primera-tarea | - | 002, 003 |
| 2 | 002-segunda-tarea | 001 | 004 |
| 3 | 003-tercera-tarea | 001 | - |
| 4 | 004-cuarta-tarea | 002 | - |
| 5 | 005-independiente | - | - |

## Parallel Execution Opportunities

- **001 + 005** pueden ejecutarse en paralelo (sin dependencias mutuas)
- **002 + 003** pueden ejecutarse en paralelo después de 001

## Current Status

- **Pending**: 001, 002, 003, 004, 005
- **In Progress**: -
- **Done**: -

## Notes
[Observaciones adicionales, componentes críticos, estrategia]
```

### Secciones del Execution Plan

| Sección | Requerido | Descripción |
|---------|-----------|-------------|
| `## Overview` | Sí | Objetivo general del plan |
| `## Task Graph` | Sí | Visualización ASCII de dependencias |
| `## Execution Order` | Sí | Tabla con orden, bloqueos y dependencias |
| `## Parallel Execution Opportunities` | No | Oportunidades de paralelismo |
| `## Current Status` | Sí | Estado actual de todas las tareas |
| `## Notes` | No | Observaciones adicionales |

---

## Convenciones Generales

### Encoding
- Todos los archivos en UTF-8
- Line endings: LF (Unix-style)

### Markdown
- Usar headers jerárquicos (`#`, `##`, `###`)
- Checkboxes con `[ ]` (pendiente) y `[x]` (completado)
- Código inline con backticks, bloques con triple backtick

### Nombres de archivo
- Preferir kebab-case: `nombre-descriptivo.md`
- Sin espacios ni caracteres especiales
- Extensión `.md` para documentos de texto

### Frontmatter YAML (opcional)

Cualquier archivo `.md` puede incluir un bloque YAML frontmatter opcional al inicio del archivo. El frontmatter está delimitado por `---` y debe ser lo primero en el archivo (sin líneas en blanco antes).

**Todos los campos son opcionales.** El sistema funciona igual de bien con o sin frontmatter — el indexador infiere metadata por path cuando no existe.

#### Schema de Campos

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `project` | `string` | Nombre del proyecto | `"vibeMCP"` |
| `type` | `enum` | Tipo de documento | `"task"`, `"plan"`, `"session"`, `"report"`, `"changelog"`, `"reference"`, `"scratch"`, `"asset"` |
| `updated` | `date` | Fecha de última actualización | `2025-02-09` |
| `tags` | `list[string]` | Etiquetas para búsqueda y clasificación | `[backend, api, auth]` |
| `status` | `enum` | Estado del documento (principalmente para tasks) | `"pending"`, `"in-progress"`, `"done"`, `"blocked"` |
| `owner` | `string` | Persona o agente responsable | `"max"`, `"claude"` |

#### Tipos de Datos

- **string**: Texto libre. Si contiene caracteres especiales, usar comillas: `"mi: valor"`
- **date**: Formato ISO 8601: `YYYY-MM-DD` (ej. `2025-02-09`)
- **enum**: Valor de un conjunto predefinido (ver tabla arriba)
- **list[string]**: Lista de strings en formato YAML inline `[tag1, tag2]` o multilinea:
  ```yaml
  tags:
    - backend
    - api
    - auth
  ```

#### Reglas de Inferencia por Path

Cuando un archivo **no tiene frontmatter** (o le faltan campos), el indexador infiere metadata automáticamente basándose en la ubicación del archivo:

| Campo | Regla de Inferencia |
|-------|---------------------|
| `project` | Nombre del directorio inmediatamente después de `~/.vibe/`. Ej: `~/.vibe/vibeMCP/tasks/001.md` → `project: vibeMCP` |
| `type` | Nombre de la carpeta contenedora (singularizado). Ej: `tasks/` → `task`, `plans/` → `plan`, `sessions/` → `session` |
| `updated` | Fecha de modificación del archivo (mtime del filesystem) |
| `tags` | Lista vacía `[]` |
| `status` | Para archivos en `tasks/`: se busca patrón `Status: <valor>` en línea 3 del cuerpo (case-insensitive). Para otras carpetas: `null` |
| `owner` | `null` (no se infiere) |

**Mapeo de carpetas a tipos:**

| Carpeta | Tipo Inferido |
|---------|---------------|
| `tasks/` | `task` |
| `plans/` | `plan` |
| `sessions/` | `session` |
| `reports/` | `report` |
| `changelog/` | `changelog` |
| `references/` | `reference` |
| `scratch/` | `scratch` |
| `assets/` | `asset` |

> **Nota**: Solo archivos `.md` son indexados. Archivos binarios en `assets/` (imágenes, diagramas, configs) no se procesan.

#### Precedencia: Frontmatter vs Inferencia

El indexador usa la siguiente precedencia:

1. **Frontmatter explícito** — si el campo existe en frontmatter, usa ese valor
2. **Inferencia por path** — si no existe en frontmatter, infiere por ubicación
3. **Valor por defecto** — si no se puede inferir, usa `null` o valor vacío

```
┌─────────────────────────────┐
│ Archivo tiene frontmatter?  │
└─────────────┬───────────────┘
              │
     ┌────────┴────────┐
     │                 │
    Sí                No
     │                 │
     ▼                 ▼
┌─────────────┐  ┌─────────────────┐
│ Campo X     │  │ Inferir todos   │
│ en YAML?    │  │ los campos por  │
└──────┬──────┘  │ path            │
       │         └─────────────────┘
  ┌────┴────┐
  │         │
 Sí        No
  │         │
  ▼         ▼
┌──────┐  ┌──────────┐
│ Usar │  │ Inferir  │
│ YAML │  │ por path │
└──────┘  └──────────┘
```

#### Ejemplos

**Archivo CON frontmatter completo:**

```yaml
---
project: vibeMCP
type: task
updated: 2025-02-09
tags: [indexer, sqlite, fts5]
status: in-progress
owner: claude
---
# Task: Implementar indexador SQLite

...contenido...
```

**Archivo CON frontmatter parcial:**

```yaml
---
tags: [urgente, hotfix]
owner: max
---
# Fix crítico en autenticación

...contenido...
```

En este caso:
- `project` → inferido de path (`vibeMCP`)
- `type` → inferido de carpeta (`scratch`)
- `updated` → inferido de mtime
- `tags` → del frontmatter: `[urgente, hotfix]`
- `status` → `null`
- `owner` → del frontmatter: `max`

**Archivo SIN frontmatter:**

```markdown
# Session 2025-02-09

## Lo que hice hoy

- Avancé con el indexador
- Debuggeé problema de encoding
```

Ubicado en `~/.vibe/vibeMCP/sessions/2025-02-09.md`:
- `project` → `vibeMCP`
- `type` → `session`
- `updated` → mtime del archivo
- `tags` → `[]`
- `status` → `null`
- `owner` → `null`

#### Uso por el Indexador

El indexador procesa archivos así:

1. Lee el archivo completo
2. Detecta si empieza con `---` (frontmatter presente)
3. Si hay frontmatter, parsea YAML y extrae campos
4. Para campos faltantes, aplica inferencia por path
5. Almacena metadata en SQLite junto con el contenido indexado
6. El contenido se indexa para FTS5 **sin** el frontmatter

**Ejemplo de registro en SQLite:**

```sql
-- Tabla: documents
INSERT INTO documents (path, project, type, updated, tags, status, owner, content)
VALUES (
  'vibeMCP/tasks/001-setup.md',
  'vibeMCP',           -- de frontmatter o inferido
  'task',              -- de frontmatter o inferido
  '2025-02-09',        -- de frontmatter o mtime
  '["setup", "init"]', -- de frontmatter o []
  'done',              -- de frontmatter o null
  'max',               -- de frontmatter o null
  '# Task: Setup...'   -- contenido sin frontmatter
);
```

#### Notas de Implementación

- El parser YAML debe ser tolerante a errores. Si el frontmatter está malformado, tratar como si no existiera y loguear warning.
- Las fechas en formato incorrecto deben caer back a mtime.
- Los tags se normalizan a lowercase.
- El campo `status` en frontmatter tiene precedencia sobre `Status:` en el cuerpo del documento (para tasks).

---

## Ejemplos Reales

### Task file completo

```markdown
# Task: Implementar autenticación JWT

Status: pending

## Objective
Agregar autenticación basada en JWT al API, incluyendo login, registro, y middleware de validación.

## Context
- Related files: `src/auth/`, `src/middleware/`
- Dependencies: 001-setup-proyecto (debe estar done)

## Steps
1. [ ] Crear modelos User y Token
2. [ ] Implementar servicio de generación de JWT
3. [ ] Crear endpoints /login y /register
4. [ ] Agregar middleware de validación de token
5. [ ] Escribir tests

## Acceptance Criteria
- [ ] Usuario puede registrarse con email/password
- [ ] Usuario puede hacer login y recibir JWT
- [ ] Rutas protegidas rechazan requests sin token válido
- [ ] Tests cubren happy path y edge cases

## Notes
Usar PyJWT. Token expira en 24h. Refresh tokens fuera de scope por ahora.
```

### Execution plan compacto

```markdown
# Execution Plan — mi-api

## Overview
API REST con autenticación y CRUD de recursos.

## Task Graph

001-setup
 └─► 002-auth
      └─► 003-crud
           └─► 004-tests

## Execution Order

| Order | Task | Blocked By | Blocks |
|-------|------|------------|--------|
| 1 | 001-setup | - | 002 |
| 2 | 002-auth | 001 | 003 |
| 3 | 003-crud | 002 | 004 |
| 4 | 004-tests | 003 | - |

## Current Status

- **Pending**: 002, 003, 004
- **In Progress**: -
- **Done**: 001
```
