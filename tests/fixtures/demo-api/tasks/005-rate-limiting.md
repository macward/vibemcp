# Task: Implementar rate limiting

Status: pending

## Objective
Agregar rate limiting por usuario y por API key para prevenir abuso.

## Context
- Related files: `src/middleware/rate_limit.py`
- Dependencies: 003-auth-jwt

## Steps
1. [ ] Elegir librería de rate limiting (slowapi o custom con Redis)
2. [ ] Implementar middleware de rate limiting
3. [ ] Configurar límites: 100 req/min por usuario, 1000 req/min por API key
4. [ ] Agregar headers X-RateLimit-* en responses
5. [ ] Tests de rate limiting

## Acceptance Criteria
- [ ] Requests excediendo límite reciben 429 Too Many Requests
- [ ] Headers muestran límite y remaining
- [ ] Diferentes límites para usuarios vs API keys
- [ ] Redis almacena contadores (fallback a memoria si no hay Redis)

## Notes
Decidido usar slowapi que es compatible con FastAPI. Necesita Redis para funcionar en múltiples instancias.
