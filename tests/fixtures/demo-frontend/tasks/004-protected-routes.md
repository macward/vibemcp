# Task: Implementar rutas protegidas

Status: pending

## Objective
Crear componente wrapper que protege rutas y redirige a login si no hay sesión.

## Context
- Related files: `src/components/ProtectedRoute.tsx`, `src/lib/router.tsx`
- Dependencies: 003-auth-store

## Steps
1. [ ] Crear componente ProtectedRoute
2. [ ] Verificar token en store antes de renderizar
3. [ ] Redirigir a /login si no autenticado
4. [ ] Guardar URL original para redirect post-login
5. [ ] Agregar loading state mientras verifica

## Acceptance Criteria
- [ ] Rutas protegidas requieren autenticación
- [ ] Redirect a login si no hay token
- [ ] Redirect back después de login exitoso
- [ ] Loading indicator mientras verifica

## Notes
Archivo sin frontmatter para testing de inferencia.
