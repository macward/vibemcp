# Vibe Init Command

Inicializa un proyecto vibe vinculando el repo actual con un workspace en el servidor MCP.

## IMPORTANTE

**DEBES usar la tool `mcp__vibeMCP__tool_init_project` para crear el proyecto.**

NO uses `create_plan`, `create_doc`, ni ninguna otra tool. Solo `tool_init_project` crea la estructura completa de carpetas.

## Proceso

### 1. Obtener nombre del proyecto
- Preguntar al usuario el nombre del proyecto
- Validar que no contenga caracteres especiales (solo letras, números, guiones)

### 2. Crear estructura en servidor
```
OBLIGATORIO: mcp__vibeMCP__tool_init_project(project="<nombre>")
```
- Esta tool crea TODAS las carpetas: tasks, plans, sessions, reports, changelog, references, scratch, assets
- Si el proyecto ya existe, informar y preguntar si continuar (solo vincular)

### 3. Vincular repo local
- Leer el `CLAUDE.md` del directorio actual (o crearlo si no existe)
- Añadir línea `vibe: <nombre>` si no existe
- Si ya tiene `vibe:`, preguntar si reemplazar

### 4. Confirmar
- Mostrar resumen de lo creado

## Reglas
1. **SIEMPRE usar `tool_init_project`** - nunca crear carpetas manualmente ni usar otras tools
2. No sobrescribir configuración existente sin confirmar
3. Si MCP no está disponible, informar al usuario
4. El nombre del proyecto debe ser válido (sin /, \, ..)
