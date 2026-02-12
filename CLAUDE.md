# vibeMCP

vibe: vibe-mcp
branch: develop

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

---

## Python Rules & Best Practices

### Architecture & Dependencies

- **Dependency Injection over Singletons**: Inject dependencies via constructor (`__init__`). No singletons, no mutable module-level state.
- **Composition over inheritance**: Prefer composing objects. If a class needs behavior from another, inject it.
- **Protocols for abstractions**: Use `typing.Protocol` for interfaces. Avoid `ABC` unless you need shared implementation.
- **No premature abstraction**: No abstract layers until at least two concrete implementations justify it.
- **No god classes**: One clear responsibility per class. If >5-7 public methods, split it.
- **Functions over single-method classes**: A class with only one public method should be a plain function.

### Project Structure

```
src/vibe_mcp/
├── main.py           ← FastMCP server entry point
├── config.py         ← pydantic-settings configuration
├── auth.py           ← authentication logic
├── tools.py          ← MCP tools (read operations)
├── tools_write.py    ← MCP tools (write operations)
├── tools_webhooks.py ← webhook-related tools
├── resources.py      ← MCP resources
├── prompts.py        ← MCP prompts
├── webhooks.py       ← webhook system
└── indexer/          ← SQLite FTS5 indexing subsystem
    ├── database.py   ← DB connection & queries
    ├── indexer.py    ← orchestrates indexing
    ├── parser.py     ← markdown parsing
    ├── chunker.py    ← heading-based chunking
    ├── walker.py     ← filesystem traversal
    └── models.py     ← data models
```

- **One file, one responsibility**: Each module has a clear, singular purpose.
- **No `utils.py` dumping grounds**: Group utilities in domain-specific modules.
- **`__init__.py` is only for exports**: No logic, only re-exports and `__all__`.
- **No circular imports**: Refactor by extracting shared types or inverting dependencies.

### Type Hints & Data Validation

- **Type hints everywhere**: All parameters, return types, and class attributes must have annotations.
- **No `Any` escape hatch**: Use `Protocol` or `TypeVar` instead.
- **Pydantic for external data**: Use Pydantic models for configuration, API schemas, and data from outside the system.
- **Dataclasses for internal data**: Use `@dataclass` for internal value objects that don't need validation.
- **Modern typing syntax**: Prefer `str | None` over `Optional[str]`, `list[int]` over `List[int]`.

### Error Handling

- **Custom exceptions per domain**: Define specific exception classes (e.g., `DocumentNotFoundError`, `IndexError`). Never raise bare `Exception`.
- **No generic except clauses**: Never `except Exception as e` unless re-raising. Catch specific exceptions.
- **Never silently swallow errors**: No `except: pass`.
- **Fail fast**: Validate inputs at boundaries (tool entry, config load).

### Async

- **Consistent async stack**: The MCP server is async; keep the entire call chain async.
- **No `asyncio.run()` inside async code**: Never call from within an already-running event loop.
- **No blocking calls in async functions**: Use `asyncio.sleep()`, async libraries, or `run_in_executor()` for blocking operations.
- **Async context managers**: Use `async with` for resources (DB connections).

### Testing (pytest)

- **Dependencies are injectable**: All external dependencies (filesystem, SQLite) must be injectable for testing.
- **No monkeypatching globals**: Mock via injection, not `unittest.mock.patch` at module level.
- **pytest over unittest**: Use fixtures, parametrize, and conftest.py.
- **Tests are isolated**: No test depends on filesystem, network, or another test's state. Use in-memory fakes.
- **Arrange-Act-Assert structure**: Every test clearly separates setup, execution, and verification.

### Naming & Style

- **No abbreviations**: `configuration` not `cfg`, `document` not `doc` (except in established terms like "docstring").
- **Google-style docstrings**: All public functions and classes have docstrings with Args, Returns, Raises.
- **Self-documenting code over comments**: Comments explain *why*, not *what*.
- **Private with single underscore**: `_prefix` for private members.
- **Constants in UPPER_SNAKE_CASE**: Module-level only. No mutable "constants".
- **Boolean parameters need keyword-only syntax**: `def process(data, *, verbose: bool = False)`

### Anti-Patterns to Avoid

- **No `@staticmethod` abuse**: Non-instance methods should be module-level functions.
- **No logic in `__init__.py`**: Only `__all__` and re-exports.
- **No mutable default arguments**: Use `None` and create inside the function.
- **No wildcard imports**: Always import explicitly.
- **No `print()` for logging**: Use `logging` module.
- **No hardcoded values**: Magic numbers, paths, etc. must be configuration or constants.

### MCP-Specific Rules

- **Tools are thin**: Validate input, call service functions, return response. Business logic lives in service modules.
- **TODO: Response models always defined**: MCP tools should return typed responses, not raw dicts. (Currently returning `dict`.)
- **Index is disposable**: SQLite can be regenerated from filesystem. Never treat it as source of truth.
- **Filesystem first**: Operations should work even if the index is unavailable.
