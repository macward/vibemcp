# Task: Crear store de autenticación

Status: pending

## Objective
Implementar store Zustand para manejar estado de autenticación, tokens, y usuario actual.

## Context
- Related files: `src/stores/auth.ts`
- Dependencies: 002-login-form

## Steps
1. [ ] Crear auth store con Zustand
2. [ ] Implementar persistencia de tokens en localStorage
3. [ ] Agregar refresh token automático
4. [ ] Crear hook useAuth para acceso fácil
5. [ ] Tests para el store

## Acceptance Criteria
- [ ] Store mantiene usuario y tokens
- [ ] Tokens persisten en refresh de página
- [ ] Refresh automático antes de expiración
- [ ] Logout limpia todo el estado

## Notes
Sin frontmatter a propósito para testear inferencia por path.
Usar zustand/middleware para persistencia.
