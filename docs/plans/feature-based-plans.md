# Plan: Planes por Feature en vibeMCP (Opción A - Flat)

## Resumen

Agregar soporte para planes por feature usando múltiples archivos en `plans/` y un campo `feature:` en el frontmatter de tareas.

## Estructura Final

```
~/.vibe/<proyecto>/
├── tasks/
│   ├── 017-auth-bearer.md     # feature: auth
│   ├── 018-deploy-vps.md      # feature: deploy
│   └── ...
├── plans/
│   ├── execution-plan.md      # Plan maestro (sin cambios)
│   ├── feature-auth.md        # Plan del feature auth
│   └── feature-deploy.md      # Plan del feature deploy
```

## Ejemplo: Tarea con Feature

```markdown
---
type: task
status: pending
feature: auth          ← NUEVO CAMPO
---

# 017-auth-bearer-token

## Objective
Implementar autenticación con bearer token...
```

## Ejemplo: Plan de Feature

**`plans/feature-auth.md`:**
```markdown
# Feature: Auth

## Overview
Bearer token authentication para acceso remoto.

## Tasks
| Task | Status | Blocks |
|------|--------|--------|
| 017-auth-bearer-token | pending | deploy:018 |

## Acceptance Criteria
- [ ] VIBE_AUTH_TOKEN validado en endpoints de escritura
- [ ] 401 retornado para token inválido/faltante
```

---

## Implementación

### 1. Agregar columna `feature` al schema (database.py)

```python
# En create_tables()
feature TEXT,

# Agregar índice
CREATE INDEX IF NOT EXISTS idx_documents_feature ON documents(feature);
```

**Archivo:** `src/vibe_mcp/indexer/database.py`

### 2. Extraer `feature` del frontmatter (parser.py)

```python
# En _parse_frontmatter()
feature = fm.get("feature")
return Document(..., feature=feature)
```

**Archivo:** `src/vibe_mcp/indexer/parser.py`

### 3. Agregar `feature` al modelo Document (models.py)

```python
@dataclass
class Document:
    ...
    feature: str | None = None
```

**Archivo:** `src/vibe_mcp/models.py`

### 4. Filtro `feature` en list_tasks (tools.py)

```python
@server.tool()
def list_tasks(
    project: str | None = None,
    status: str | None = None,
    feature: str | None = None,  # NUEVO
) -> list[dict]:
    # Agregar filtro WHERE feature = ?
```

**Archivo:** `src/vibe_mcp/tools.py`

### 5. Nuevo tool list_plans (tools.py)

```python
@server.tool()
def list_plans(project: str) -> list[dict]:
    """List all plan files for a project.

    Returns list of plans with: filename, title, updated
    """
    plans_dir = config.vibe_root / project / "plans"
    return [{"filename": f.name, ...} for f in plans_dir.glob("*.md")]
```

**Archivo:** `src/vibe_mcp/tools.py`

### 6. Parámetro `filename` en create_plan (tools_write.py)

```python
@server.tool()
def create_plan(
    project: str,
    content: str,
    filename: str = "execution-plan.md"  # NUEVO
) -> dict:
```

**Archivo:** `src/vibe_mcp/tools_write.py`

### 7. Parámetro `feature` en create_task (tools_write.py)

```python
@server.tool()
def create_task(
    project: str,
    title: str,
    objective: str,
    steps: list[str] | None = None,
    feature: str | None = None,  # NUEVO - agrega al frontmatter
) -> dict:
```

**Archivo:** `src/vibe_mcp/tools_write.py`

### 8. Actualizar skill /run-plan (SKILL.md)

```markdown
## Parameters
- feature (optional): ejecutar solo tareas de un feature específico

## Process
If feature specified:
    get_plan(project, f"feature-{feature}.md")
    list_tasks(project, feature=feature)
Else:
    get_plan(project)  # plan maestro
    list_tasks(project)
```

**Archivo:** `claude/SKILLS/vibe-run-plan/SKILL.md`

---

## Archivos a Modificar

| Archivo | Cambios |
|---------|---------|
| `src/vibe_mcp/models.py` | Agregar `feature: str \| None` a Document |
| `src/vibe_mcp/indexer/database.py` | Columna `feature`, índice |
| `src/vibe_mcp/indexer/parser.py` | Extraer `feature` del frontmatter |
| `src/vibe_mcp/tools.py` | `feature` en list_tasks, nuevo `list_plans` |
| `src/vibe_mcp/tools_write.py` | `filename` en create_plan, `feature` en create_task |
| `claude/SKILLS/vibe-run-plan/SKILL.md` | Parámetro `feature` opcional |

## Verificación

1. **Test unitarios:**
   - Parser extrae `feature` correctamente
   - `list_tasks(feature="auth")` filtra
   - `list_plans()` devuelve archivos

2. **Test integración MCP:**
   - `create_task(feature="test")` crea con frontmatter correcto
   - `create_plan(filename="feature-test.md")` crea archivo nombrado
   - `get_plan(filename="feature-test.md")` lo lee

3. **Test end-to-end:**
   - Crear feature plan + tareas vinculadas
   - `/run-plan feature=test` ejecuta solo ese feature
