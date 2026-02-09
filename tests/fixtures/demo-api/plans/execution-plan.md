# Execution Plan — demo-api

## Overview

API REST de autenticación con soporte para email/password y OAuth2 (Google).

## Task Graph

```
001-setup-proyecto
 └─► 002-modelo-usuario
      └─► 003-auth-jwt
           ├─► 004-oauth-google
           └─► 005-rate-limiting
```

## Execution Order

| Order | Task | Status | Blocked By | Blocks |
|-------|------|--------|------------|--------|
| 1 | 001-setup-proyecto | done | - | 002 |
| 2 | 002-modelo-usuario | done | 001 | 003 |
| 3 | 003-auth-jwt | in-progress | 002 | 004, 005 |
| 4 | 004-oauth-google | blocked | 003 | - |
| 5 | 005-rate-limiting | pending | 003 | - |

## Parallel Execution Opportunities

- **004 + 005** pueden ejecutarse en paralelo después de completar 003

## Current Status

- **Done**: 001, 002
- **In Progress**: 003
- **Blocked**: 004 (esperando Google credentials)
- **Pending**: 005

## Notes

- Sprint actual: 3 de 6
- Blocker principal: Redis + Google OAuth credentials
- Milestone: Auth completa para fin de Sprint 4
