# Task: Implementar modelo de usuario

Status: done

## Objective
Crear el modelo SQLAlchemy para usuarios con campos básicos y validación.

## Context
- Related files: `src/models/user.py`, `src/schemas/user.py`
- Dependencies: 001-setup-proyecto

## Steps
1. [x] Crear modelo User con campos: id, email, hashed_password, created_at, updated_at
2. [x] Agregar índice único en email
3. [x] Crear schemas Pydantic: UserCreate, UserRead, UserUpdate
4. [x] Escribir tests unitarios para validación

## Acceptance Criteria
- [x] Modelo User creado con todos los campos
- [x] Email tiene constraint UNIQUE
- [x] Schemas validan email format y password length
- [x] Tests pasan

## Notes
Password se hashea en capa de servicio, no en modelo. El modelo solo almacena hash.
