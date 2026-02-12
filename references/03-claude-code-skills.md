# Claude Code Skills para vibeMCP

Skills (slash commands) disponibles para trabajar con proyectos vibe desde Claude Code.

## Resumen de Skills

| Skill | Descripción |
|-------|-------------|
| `/vibe-init` | Inicializa un nuevo proyecto vibe |
| `/status` | Muestra el estado actual del proyecto |
| `/session-start` | Retoma contexto al iniciar sesión de trabajo |
| `/next-task` | Selecciona la siguiente tarea disponible |
| `/task-breakdown` | Descompone un objetivo en tareas |
| `/solve-task` | Ejecuta una tarea completa (branch → PR → merge) |
| `/run-plan` | Orquesta la ejecución de todas las tareas pendientes |

---

## `/solve-task`

Ejecuta el ciclo completo de una tarea: crear branch, implementar, testear, crear PR y mergear.

### Sintaxis

```
/solve-task           # siguiente tarea in-progress o pending
/solve-task 003       # tarea específica por número
```

### Flujo de Ejecución

```
1. Selección
   └── Busca tarea in-progress, si no hay → primera pending

2. Preparación
   ├── Marca como in-progress
   ├── git checkout <base-branch> && git pull
   └── git checkout -b task/NNN-nombre

3. Implementación
   ├── Lee la tarea completa
   └── Sigue los steps definidos

4. Validación
   └── Ejecuta tests (npm test, pytest, etc.)

5. Commit + Push
   └── git add . && git commit && git push -u origin

6. PR + Merge
   ├── gh pr create --base <base-branch>
   └── gh pr merge --auto --squash

7. Cleanup
   ├── Marca tarea como done
   ├── Log de sesión
   └── git checkout <base-branch> && git pull
```

### Configuración

Lee del `CLAUDE.md` del proyecto:
- `vibe: <project>` — workspace vibe a usar
- `branch: <branch>` — rama base (default: `main`)

### Ejemplo de Uso

```
> /solve-task 003

/solve-task 003 started

[1/7] Reading task... done
      003-auth-service: Implement authentication

[2/7] Creating branch... done
      Branch: task/003-auth-service

[3/7] Implementing...
      └── Creating auth/service.py
      └── Adding middleware
      └── Writing tests

[4/7] Running tests... done
      ✓ 12 tests passed

[5/7] Committing... done
[6/7] Creating PR... done (#15)
[7/7] Merging... done

Task 003-auth-service completed ✓
```

### Manejo de Errores

| Error | Comportamiento |
|-------|----------------|
| Tests fallan | Muestra output, detiene ejecución |
| Merge conflict | Muestra archivos en conflicto, da instrucciones |
| PR checks fallan | Muestra estado, sugiere fix |
| Push rejected | Pull y rebase, reintenta |

---

## `/run-plan`

Orquesta la ejecución de todas las tareas pendientes en secuencia.

### Sintaxis

```
/run-plan              # modo autónomo (default)
/run-plan --confirm    # pausa entre tareas para confirmación
/run-plan --dry-run    # muestra plan sin ejecutar nada
```

### Modos

#### Autónomo (default)
Ejecuta todas las tareas sin pausa. Ideal para lotes de tareas pequeñas o cuando ya revisaste el plan.

```
> /run-plan

/run-plan started (3 pending tasks)
Mode: autonomous

[1/3] 003-auth ━━━━━━━━━━ done ✓ (#15)
[2/3] 004-tests ━━━━━━━━ done ✓ (#16)
[3/3] 005-docs ━━━━━━━━━ done ✓ (#17)

/run-plan completed: 3/3 tasks done
```

#### Semi-autónomo (`--confirm`)
Pausa antes de cada tarea para confirmación.

```
> /run-plan --confirm

[1/3] 003-auth completed ✓

Next: 004-tests
Objective: Add unit tests for auth

Continue? [Y/n/skip/abort]
```

Opciones en cada pausa:
- `Y` — continuar con la tarea
- `n` / `skip` — saltar esta tarea
- `abort` — detener run-plan

#### Dry Run (`--dry-run`)
Muestra el plan sin ejecutar nada.

```
> /run-plan --dry-run

Execution Plan for vibeMCP:

Order | Task             | Status  | Depends On
------|------------------|---------|------------
1     | 003-auth-service | pending | 002 (done)
2     | 004-auth-tests   | pending | 003
3     | 005-integration  | pending | 004

3 tasks will be executed in order.

Run /run-plan to execute.
```

### Flags Adicionales

| Flag | Descripción |
|------|-------------|
| `--continue` | Retoma desde la última tarea fallida |
| `--skip NNN` | Salta una tarea específica |

### Recuperación de Errores

Si una tarea falla, run-plan se detiene y ofrece opciones:

```
[2/5] 004-tests ━━━━━━━━ FAILED ✗
      └── Tests failed: 2 assertions

Options:
1. Fix issues and run: /run-plan --continue
2. Retry this task: /solve-task 004
3. Skip and continue: /run-plan --skip 004
4. Abort remaining tasks
```

### Resumen Final

Al completar todas las tareas:

```
/run-plan completed

Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ 003-auth-service    PR #15
✓ 004-auth-tests      PR #16
✓ 005-integration     PR #17
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3/3 tasks completed

Merged PRs:
- #15 task/003-auth-service
- #16 task/004-auth-tests
- #17 task/005-integration
```

---

## Workflow Típico

### 1. Inicio de proyecto

```
/vibe-init              # crear workspace
/task-breakdown         # crear tareas desde un objetivo
```

### 2. Sesión de trabajo

```
/session-start          # retomar contexto
/status                 # ver estado actual
/next-task              # seleccionar siguiente tarea
```

### 3. Ejecución

```
# Una tarea a la vez
/solve-task 003

# O todas las pendientes
/run-plan --confirm     # con supervisión
/run-plan               # autónomo
```

### 4. Revisión

```
/status                 # verificar progreso
```

---

## Requisitos

- **CLAUDE.md** con `vibe: <project>` y opcionalmente `branch: <branch>`
- **gh CLI** autenticado (`gh auth login`)
- **Git** configurado con permisos de push al repo

---

## Configuración del Proyecto

En el `CLAUDE.md` del repositorio:

```markdown
# Mi Proyecto

vibe: mi-proyecto        # nombre del workspace en ~/.vibe/
branch: develop          # rama base para PRs (default: main)
```

El skill lee estas variables para:
1. Saber qué workspace vibe usar
2. Crear branches desde la rama correcta
3. Hacer PRs hacia la rama correcta
