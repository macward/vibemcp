# .vibe — Project Context Server

## Qué es

Un MCP server que centraliza el contexto de todos tus proyectos en un solo lugar, accesible por cualquier AI agent (Claude Code, Claude.ai, Cursor) desde cualquier máquina.

## Problema que resuelve

Cuando trabajás con AI agents en múltiples proyectos, cada sesión arranca de cero. El agent no sabe qué estás construyendo, qué decisiones tomaste, qué queda pendiente, ni cómo se relacionan tus proyectos entre sí. Si encima estás en otra máquina, perdés todo el contexto local.

**.vibe** es la memoria compartida entre vos y tus agents.

## Cómo funciona

Cada proyecto tiene un directorio con documentos markdown que describen el proyecto: qué es, decisiones de arquitectura, estado actual, notas de sesión. El MCP server expone esa información para que cualquier AI agent la consuma vía el protocolo MCP, sin importar desde dónde te conectes.

Un índice SQLite se mantiene sincronizado con los archivos markdown, permitiendo búsqueda rápida y queries cross-project sin parsear archivos en cada request.

```
~/.vibe/                          ← directorio raíz (source of truth)
├── rumi/
│   ├── context.md                ← qué es, stack, decisiones clave
│   ├── architecture.md           ← diseño técnico
│   ├── status.md                 ← estado actual, qué sigue
│   └── sessions/
│       └── 2025-02-08.md         ← notas de sesión de trabajo
├── personality-lab/
│   ├── context.md
│   └── status.md
└── ...

~/.vibe/.index.db                 ← SQLite (índice, autogenerado)
```

## Stack

| Componente | Tecnología | Razón |
|---|---|---|
| **MCP Server** | Python + FastMCP | SDK oficial, decoradores simples, SSE built-in |
| **Transporte** | SSE (HTTP) | Accesible remotamente desde cualquier cliente MCP |
| **Source of truth** | Archivos Markdown | Legibles, versionables con Git, editables a mano |
| **Índice** | SQLite | Búsqueda full-text (FTS5), queries rápidas, zero config |
| **Auth** | Bearer token | Simple, suficiente para un solo usuario |
| **Deploy** | VPS (DigitalOcean/Fly) | Siempre disponible, HTTPS con Caddy |
| **Sync** | Git repo | Backup, historial, sync entre máquinas |

## Capacidades del MCP Server

### Resources (lectura de contexto)
- Listar todos los proyectos con resumen de estado
- Leer el contexto completo de un proyecto
- Ver el estado actual de un proyecto

### Tools (acciones)
- Búsqueda full-text cross-project (vía SQLite FTS5)
- Leer/crear/actualizar documentos
- Registrar notas de sesión
- Re-indexar el contenido

### Prompts (templates)
- Briefing de proyecto: "poneme al día con X"
- Standup diario: resumen cruzado de todos los proyectos

## Flujo de indexación

```
Markdown files ──(file watcher/on-demand)──→ SQLite FTS5 index
                                               ↓
                                          MCP Tools usan el índice
                                          para búsqueda rápida
```

El markdown siempre manda. El SQLite es derivado y se puede regenerar en cualquier momento con un re-index.

## Clientes target

- **Claude Code CLI** — para sesiones de desarrollo local y remoto
- **Claude.ai** — para planning, revisión, brainstorming desde web/mobile
- **Cursor / Windsurf** — para contexto dentro del IDE

Todos se conectan al mismo endpoint SSE. Mismo contexto, sin importar la herramienta.

## Principios de diseño

1. **Markdown first** — Si el server se cae, los archivos siguen siendo útiles solos
2. **Zero friction** — Agregar contexto = crear/editar un .md
3. **Agent-friendly** — La estructura está pensada para que un LLM entienda rápido qué hay
4. **Un solo endpoint** — Todos los clientes, misma fuente de verdad
5. **Liviano** — No es un framework, es un server mínimo con un propósito claro
