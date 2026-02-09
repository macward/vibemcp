---
project: demo-frontend
type: task
status: done
updated: 2025-02-06
tags: [setup, vite, react]
owner: diana
---
# Task: Setup proyecto con Vite

Status: done

## Objective
Crear el proyecto React con Vite, TypeScript, y configuración inicial de desarrollo.

## Context
- Related files: `vite.config.ts`, `package.json`
- Dependencies: ninguna

## Steps
1. [x] Crear proyecto con Vite template react-ts
2. [x] Configurar ESLint y Prettier
3. [x] Agregar Tailwind CSS
4. [x] Configurar path aliases (@/)
5. [x] Crear estructura de carpetas

## Acceptance Criteria
- [x] `npm run dev` inicia el servidor de desarrollo
- [x] TypeScript strict mode habilitado
- [x] Tailwind funciona correctamente
- [x] Import aliases configurados

## Notes
Usando Vite 5.x. La estructura de carpetas sigue:
```
src/
├── components/
├── pages/
├── hooks/
├── lib/
├── stores/
└── types/
```
