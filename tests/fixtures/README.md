# Test Fixtures

Workspaces de ejemplo para desarrollo y testing del indexador vibeMCP.

## Proyectos Disponibles

### demo-api

Backend API de autenticación. Simula un proyecto en desarrollo activo.

| Característica | Detalle |
|----------------|---------|
| **Tareas** | 5 (2 done, 1 in-progress, 1 blocked, 1 pending) |
| **Sessions** | 3 días de notas |
| **Frontmatter** | Sin frontmatter (usa inferencia por path) |
| **Secciones clave** | status.md con "Blockers", "Next Steps", "Decisions" |

### demo-frontend

SPA React para autenticación. Demuestra uso de frontmatter YAML.

| Característica | Detalle |
|----------------|---------|
| **Tareas** | 4 (1 done, 1 in-progress, 2 pending) |
| **Sessions** | 1 día con código |
| **Frontmatter** | Mix: algunos archivos con, otros sin |
| **Extras** | scratch/, assets/, design tokens |

## Uso en Tests

### Python (pytest)

```python
import pytest
from pathlib import Path

@pytest.fixture
def fixtures_root():
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def demo_api_path(fixtures_root):
    return fixtures_root / "demo-api"

@pytest.fixture
def demo_frontend_path(fixtures_root):
    return fixtures_root / "demo-frontend"

def test_index_demo_api(indexer, demo_api_path):
    """Test indexing a project without frontmatter."""
    indexer.index_project(demo_api_path)

    # Verificar que se indexaron los documentos
    docs = indexer.list_documents("demo-api")
    assert len(docs) >= 10

    # Verificar inferencia de metadata
    task = indexer.get_document("demo-api", "tasks", "001-setup-proyecto.md")
    assert task.type == "task"
    assert task.status == "done"

def test_index_demo_frontend(indexer, demo_frontend_path):
    """Test indexing a project with YAML frontmatter."""
    indexer.index_project(demo_frontend_path)

    # Verificar que se parseó el frontmatter
    task = indexer.get_document("demo-frontend", "tasks", "001-setup-vite.md")
    assert task.owner == "diana"
    assert "vite" in task.tags
```

### Búsqueda Full-Text

```python
def test_search_across_projects(indexer, fixtures_root):
    """Test cross-project search."""
    indexer.index_all(fixtures_root)

    results = indexer.search("autenticación")

    # Debe encontrar resultados en ambos proyectos
    projects = {r.project for r in results}
    assert "demo-api" in projects
    assert "demo-frontend" in projects

def test_search_priority_headings(indexer, demo_api_path):
    """Test that priority headings get boosted."""
    indexer.index_project(demo_api_path)

    results = indexer.search("Redis")

    # El resultado de "Blockers" debe tener score alto
    blockers_result = next(r for r in results if "Blockers" in r.heading)
    assert blockers_result.score > results[-1].score * 1.5
```

### Chunking

```python
def test_chunking_by_headings(indexer, demo_api_path):
    """Test that documents are chunked by headings."""
    indexer.index_project(demo_api_path)

    chunks = indexer.get_chunks("demo-api", "tasks", "003-auth-jwt.md")

    # Debe haber chunks para cada sección
    headings = [c.heading for c in chunks]
    assert "# Task: Implementar autenticación JWT" in headings
    assert "## Objective" in headings
    assert "## Steps" in headings
```

## Cobertura de Casos

### Por Status de Tarea

| Status | Proyecto | Archivo |
|--------|----------|---------|
| done | demo-api | 001, 002 |
| in-progress | demo-api | 003 |
| blocked | demo-api | 004 |
| pending | demo-api | 005 |
| done | demo-frontend | 001 |
| in-progress | demo-frontend | 002 |
| pending | demo-frontend | 003, 004 |

### Por Frontmatter

| Tipo | Proyecto | Archivos |
|------|----------|----------|
| Con frontmatter | demo-frontend | status.md, tasks/001, tasks/002, plans/*, sessions/* |
| Sin frontmatter | demo-api | todos |
| Sin frontmatter | demo-frontend | tasks/003, tasks/004 |

### Por Carpeta

| Carpeta | demo-api | demo-frontend |
|---------|----------|---------------|
| tasks/ | 5 | 4 |
| plans/ | 1 | 1 |
| sessions/ | 3 | 1 |
| references/ | 1 | 1 |
| changelog/ | 1 | 0 |
| scratch/ | 0 | 1 |
| assets/ | 0 | 1 |
| status.md | 1 | 1 |

## Actualizar Fixtures

Cuando cambies el formato de archivos o agregues nuevos campos:

1. Actualiza los archivos en `fixtures/`
2. Verifica que los tests sigan pasando
3. Agrega nuevos tests si hay nuevos casos

## Notas

- Los fixtures usan contenido realista, no lorem ipsum
- Las fechas son febrero 2025 (intencionalmente en el pasado para testing de ranking por recencia)
- Los proyectos simulan un escenario de desarrollo típico con dependencias entre proyectos
- Los métodos en los ejemplos de pytest (`get_document()`, `get_chunks()`, etc.) son ilustrativos; la API real del indexador puede diferir

## Limitaciones Conocidas

Estos fixtures NO cubren:
- Archivos binarios (imágenes, PDFs)
- Directorios profundamente anidados
- Archivos extremadamente grandes (>100KB)
- Frontmatter YAML malformado
