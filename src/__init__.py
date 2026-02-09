"""
vibemcp - MCP server para centralizar contexto de proyectos.

Un MCP server que centraliza el contexto de todos tus proyectos en un solo lugar,
accesible por cualquier AI agent (Claude Code, Claude.ai, Cursor) desde cualquier máquina.

Stack:
- Python + FastMCP (SDK oficial)
- SQLite FTS5 (índice de búsqueda)
- SSE (transporte HTTP remoto)
- Markdown (source of truth)
"""

__version__ = "0.1.0"
__author__ = "macward"
