# Task: Implementar autenticación JWT

Status: in-progress

## Objective
Agregar endpoints de login/register y middleware de autenticación JWT.

## Context
- Related files: `src/auth/`, `src/middleware/`
- Dependencies: 002-modelo-usuario

## Steps
1. [x] Crear servicio de generación/validación de JWT
2. [x] Implementar endpoint POST /auth/register
3. [x] Implementar endpoint POST /auth/login
4. [ ] Agregar middleware de validación de token
5. [ ] Implementar refresh token rotation
6. [ ] Escribir tests de integración

## Acceptance Criteria
- [x] Usuario puede registrarse con email/password
- [x] Usuario puede hacer login y recibir access token
- [ ] Rutas protegidas requieren token válido
- [ ] Refresh tokens rotan correctamente

## Notes
Usando PyJWT. Access token expira en 15min, refresh en 7 días. Almacenar refresh tokens en Redis cuando esté disponible.
