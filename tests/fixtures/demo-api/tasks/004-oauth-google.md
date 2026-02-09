# Task: Agregar OAuth2 con Google

Status: blocked

## Objective
Permitir a usuarios autenticarse con su cuenta de Google.

## Context
- Related files: `src/auth/oauth.py`, `src/auth/providers/google.py`
- Dependencies: 003-auth-jwt

## Steps
1. [ ] Configurar Google OAuth2 credentials
2. [ ] Implementar endpoint GET /auth/google
3. [ ] Implementar callback GET /auth/google/callback
4. [ ] Vincular cuenta Google con usuario existente o crear nuevo
5. [ ] Tests con mocks de Google API

## Acceptance Criteria
- [ ] Botón "Sign in with Google" inicia flujo OAuth
- [ ] Callback maneja código de autorización
- [ ] Usuario se crea o vincula correctamente
- [ ] Token JWT se emite después de auth exitosa

## Notes
Bloqueado: necesitamos credentials de Google en staging. Bob está en eso.

Usar authlib para OAuth2 flow. El callback debe manejar:
- Usuario nuevo → crear cuenta
- Usuario existente con mismo email → vincular
- Usuario ya vinculado → login directo
