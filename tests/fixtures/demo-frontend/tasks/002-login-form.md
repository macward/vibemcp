---
project: demo-frontend
type: task
status: in-progress
updated: 2025-02-09
tags: [auth, forms, ui]
owner: diana
---
# Task: Implementar formulario de login

Status: in-progress

## Objective
Crear el formulario de login con validación client-side y conexión al backend.

## Context
- Related files: `src/pages/Login.tsx`, `src/components/auth/`
- Dependencies: 001-setup-vite

## Steps
1. [x] Crear componente LoginForm con React Hook Form
2. [x] Agregar validación con Zod (email, password min 8 chars)
3. [x] Diseñar UI con Tailwind
4. [ ] Conectar con endpoint /auth/login del backend
5. [ ] Manejar errores de autenticación
6. [ ] Agregar "Remember me" checkbox

## Acceptance Criteria
- [x] Formulario valida campos antes de submit
- [x] Muestra errores inline por campo
- [ ] Login exitoso redirige a /dashboard
- [ ] Login fallido muestra mensaje de error
- [ ] Loading state durante submit

## Notes
El backend (demo-api) aún está completando el endpoint de login. Por ahora usar mock para desarrollo UI.
