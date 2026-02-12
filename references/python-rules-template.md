# Python Project Rules & Best Practices Template

> Use this document as a reference to generate project-specific rules in CLAUDE.md.
> Adapt and prioritize rules based on the project's stack and needs.

---

## Architecture & Dependencies

- **Dependency Injection over Singletons**: Always inject dependencies via constructor (`__init__`). Never use singletons, module-level global state, or the Singleton pattern.
- **No global state modules**: Do not create `config.py`, `state.py`, or similar files with mutable module-level variables. Use configuration classes injected where needed.
- **Composition over inheritance**: Prefer composing objects over deep class hierarchies. If a class needs behavior from another, inject it — don't inherit from it.
- **Protocols for abstractions**: Use `typing.Protocol` for defining interfaces and contracts. Avoid `ABC` unless you need shared implementation in the base class.
- **No premature abstraction**: Do not create abstract layers, base classes, or interfaces until there are at least two concrete implementations that justify it.
- **No god classes**: A class should have one clear responsibility. If it has more than 5-7 public methods, it's likely doing too much.
- **Functions over single-method classes**: If a class only has one public method (besides `__init__`), it should be a plain function instead.

## Project Structure & Modularity

- **One file, one responsibility**: Each module should have a clear, singular purpose. Avoid catch-all files.
- **No `utils.py` or `helpers.py` dumping grounds**: If utility functions are needed, group them in domain-specific modules (e.g., `string_formatting.py`, `date_helpers.py`).
- **Separate domain from infrastructure**: Business logic must never directly depend on database clients, HTTP libraries, or filesystem operations. Use an abstraction layer.
- **`__init__.py` is only for exports**: Never put logic, classes, or functions in `__init__.py`. Only use it for re-exports and `__all__` definitions.
- **No circular imports**: Circular dependencies between modules indicate poor architecture. Refactor by extracting shared types or inverting dependencies.
- **Prefer pure functions**: Functions that take inputs and return outputs without side effects are easier to test, compose, and reason about. Use them wherever possible.

## Error Handling

- **Custom exceptions per domain**: Define specific exception classes for each domain/module (e.g., `UserNotFoundError`, `PaymentDeclinedError`). Never raise bare `Exception` or `ValueError` for business logic errors.
- **No generic except clauses**: Never write `except Exception as e` unless re-raising. Catch specific exceptions only.
- **Never silently swallow errors**: No `except: pass` or `except Exception: log_and_continue`. If you catch it, handle it properly.
- **Fail fast**: Validate inputs at the boundary (function entry, API endpoint). Don't bury validation deep in call chains.
- **Use result patterns when appropriate**: For operations that can fail in expected ways, consider returning `Result` types or `Optional` over raising exceptions for control flow.

## Async

- **Consistent async stack**: If the project uses an async framework (FastAPI, aiohttp), the entire call chain should be async. Do not mix sync and async without explicit justification.
- **No `asyncio.run()` inside async code**: Never call `asyncio.run()` from within an already-running event loop.
- **No blocking calls in async functions**: Never use `time.sleep()`, synchronous I/O, or CPU-heavy operations directly in async functions. Use `asyncio.sleep()`, async libraries, or `run_in_executor()`.
- **Async context managers**: Use `async with` for resources that need cleanup in async contexts (DB connections, HTTP sessions).

## Type Hints & Data Validation

- **Type hints everywhere**: All function parameters, return types, and class attributes must have type annotations. No exceptions.
- **No `Any` escape hatch**: Do not use `typing.Any` unless the type is genuinely unknown and dynamic. If you're tempted to use `Any`, define a `Protocol` or `TypeVar` instead.
- **Pydantic for external data**: Use Pydantic models for API request/response schemas, configuration, and any data coming from outside the system (user input, DB records, API responses).
- **Dataclasses for internal data**: Use `@dataclass` for internal value objects and data containers that don't need validation.
- **Use modern typing syntax**: Prefer `str | None` over `Optional[str]`, `list[int]` over `List[int]` (Python 3.10+).
- **Use `TypeAlias` and `TypeVar`**: Define type aliases for complex types. Use generics (`TypeVar`, `Generic`) when building reusable components.

## Testing

- **Dependency injection enables testability**: All external dependencies (DB, HTTP, filesystem) must be injectable so tests can provide fakes/mocks.
- **No monkeypatching globals**: If you need to mock something, it should be injected — not patched at the module level with `unittest.mock.patch`.
- **pytest over unittest**: Use pytest fixtures, parametrize, and conftest.py. Avoid `unittest.TestCase`, `setUp`, and `tearDown`.
- **Tests are isolated**: No test should depend on filesystem, network, database, or another test's state. Use in-memory fakes.
- **Test behavior, not implementation**: Tests should verify what a function does, not how it does it. Avoid asserting on internal method calls.
- **Arrange-Act-Assert structure**: Every test should clearly separate setup, execution, and verification.

## Naming & Style

- **No abbreviations**: Use descriptive, full names. `user_manager` not `usr_mgr`, `configuration` not `cfg`.
- **Google-style docstrings**: All public functions and classes must have docstrings with Args, Returns, and Raises sections.
- **Self-documenting code over comments**: If code needs a comment to explain what it does, refactor it to be clearer. Comments should explain *why*, not *what*.
- **Private with single underscore**: Use `_prefix` for private members. Never use `__name_mangling` unless there's a concrete inheritance conflict.
- **Constants in UPPER_SNAKE_CASE**: Module-level constants only. No mutable "constants".
- **Boolean parameters need keyword-only syntax**: Functions with boolean flags should use `*` to force keyword arguments: `def process(data, *, verbose: bool = False)`.

## Common Anti-Patterns to Avoid

- **No `@staticmethod` abuse**: If a method doesn't use `self` or `cls`, it should be a module-level function, not a staticmethod.
- **No logic in `__init__.py`**: Only `__all__` and re-exports.
- **No mutable default arguments**: Never use `def f(items=[])` or `def f(config={})`. Use `None` and create inside the function.
- **No wildcard imports**: Never use `from module import *`. Always import explicitly.
- **No nested functions for reusable logic**: If a nested function is complex or used in multiple places, extract it to module level.
- **No print() for logging**: Use the `logging` module or structured logging (e.g., `structlog`). Never use `print()` for operational output.
- **No hardcoded values**: Magic numbers, URLs, file paths, etc. must be configuration or constants. Never inline them.

## FastAPI-Specific Rules (if applicable)

- **Router organization**: One router per domain/resource. Never put all endpoints in a single file.
- **Service layer**: Endpoints should be thin — validate input, call a service, return response. Business logic lives in service classes/functions, not in route handlers.
- **Dependency injection via `Depends()`**: Use FastAPI's DI system for services, DB sessions, auth, etc.
- **Response models always defined**: Every endpoint must declare `response_model`. Never return raw dicts.
- **No business logic in middleware**: Middleware is for cross-cutting concerns only (logging, CORS, auth token extraction). Not for business rules.
- **Background tasks for side effects**: Use `BackgroundTasks` for non-critical operations (sending emails, analytics). Don't block the response.

## Logging & Observability (if applicable)

- **Structured logging from day one**: Use `structlog` or equivalent. Every log entry should be a structured dict, not a formatted string.
- **Trace every external call**: Log every HTTP request, DB query, and external service call with latency, status, and context.
- **Correlation IDs**: Pass a request/trace ID through the entire call chain for debugging.
- **No sensitive data in logs**: Never log passwords, tokens, PII, or full request bodies containing sensitive fields.

---

## How to Use This Template

Tell Claude Code:

```
Read the rules template at <path-to-this-file> and generate a CLAUDE.md 
for this project. Adapt the rules to the specific stack and structure 
of this project. Remove rules that don't apply and add project-specific 
conventions based on the existing codebase.
```
