# Vibe Init Command

Inicializa un proyecto vibe vinculando el repo actual con un workspace en el servidor MCP.

## Proceso

### 1. Obtener nombre del proyecto
- Preguntar al usuario el nombre del proyecto
- Validar que no contenga caracteres especiales (solo letras, números, guiones)

### 2. Crear estructura en servidor
- Llamar `mcp__vibeMCP__tool_init_project` con el nombre del proyecto
- Si el proyecto ya existe, informar y preguntar si continuar (solo vincular)

### 3. Vincular repo local
- Leer el `CLAUDE.md` del directorio actual (o crearlo si no existe)
- Añadir línea `vibe: <nombre>` si no existe
- Si ya tiene `vibe:`, preguntar si reemplazar

### 4. Confirmar
- Mostrar resumen:
  - Proyecto creado/vinculado en servidor
  - CLAUDE.md actualizado
  - Próximos pasos (usar MCP tools)

## Reglas
1. No sobrescribir configuración existente sin confirmar
2. Si MCP no está disponible, informar al usuario
3. El nombre del proyecto debe ser válido (sin /, \, ..)
