# Vibe Init Command

Inicializa un proyecto vibe creando el workspace en el servidor MCP.

## PROHIBICIONES ESTRICTAS

**NO DEBES usar ninguna de estas tools:**
- ❌ Write — no crear archivos
- ❌ Edit — no modificar archivos
- ❌ Read — no leer archivos locales
- ❌ Bash — no ejecutar comandos
- ❌ Otras tools MCP — solo `tool_init_project`

**NO DEBES:**
- ❌ Escribir a memoria (MEMORY.md)
- ❌ Crear o modificar CLAUDE.md
- ❌ Crear ningún archivo local

## ÚNICA TOOL PERMITIDA

```
mcp__vibeMCP__tool_init_project(project="<nombre>")
```

## Proceso

### 1. Preguntar nombre del proyecto
- Usar AskUserQuestion para obtener el nombre
- Validar que no contenga caracteres especiales (solo letras, números, guiones)

### 2. Crear workspace
- Llamar `mcp__vibeMCP__tool_init_project(project="<nombre>")`
- Esta tool crea TODAS las carpetas: tasks, plans, sessions, reports, changelog, references, scratch, assets

### 3. Informar al usuario
- Confirmar que el workspace fue creado
- Indicar al usuario que añada manualmente `vibe: <nombre>` a su CLAUDE.md si desea vincular el repo

**FIN. No hacer nada más.**
