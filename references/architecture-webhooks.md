# Arquitectura del Sistema de Webhooks

## Diagrama General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              vibeMCP Server                                  │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │   MCP Client    │    │   tools_write   │    │    tools_webhooks       │  │
│  │  (Claude, etc)  │───▶│                 │    │                         │  │
│  └─────────────────┘    │  create_task()  │    │  register_webhook()     │  │
│                         │  update_task()  │    │  unregister_webhook()   │  │
│                         │  create_doc()   │    │  list_webhooks()        │  │
│                         │  log_session()  │    └───────────┬─────────────┘  │
│                         │  init_project() │                │               │
│                         │  reindex()      │                │               │
│                         └────────┬────────┘                │               │
│                                  │                         │               │
│                                  │ _fire_webhook()         │               │
│                                  ▼                         ▼               │
│                         ┌─────────────────────────────────────┐            │
│                         │          WebhookManager             │            │
│                         │                                     │            │
│                         │  ┌─────────────────────────────┐   │            │
│                         │  │     ThreadPoolExecutor      │   │            │
│                         │  │      (max_workers=10)       │   │            │
│                         │  └─────────────┬───────────────┘   │            │
│                         │                │                    │            │
│                         │  ┌─────────────▼───────────────┐   │            │
│                         │  │      _deliver_sync()        │   │            │
│                         │  │  - HMAC-SHA256 signature    │   │            │
│                         │  │  - HTTP POST with headers   │   │            │
│                         │  │  - Log delivery result      │   │            │
│                         │  └─────────────────────────────┘   │            │
│                         └──────────────┬──────────────────────┘            │
│                                        │                                   │
│  ┌─────────────────────────────────────┼───────────────────────────────┐   │
│  │                        SQLite Database                              │   │
│  │                                     │                               │   │
│  │  ┌──────────────────┐    ┌──────────▼─────────┐    ┌─────────────┐  │   │
│  │  │ webhook_         │    │ webhook_logs       │    │ documents   │  │   │
│  │  │ subscriptions    │    │                    │    │ chunks      │  │   │
│  │  │                  │    │ - subscription_id  │    │ projects    │  │   │
│  │  │ - url            │◀───│ - event_type       │    │ ...         │  │   │
│  │  │ - secret         │    │ - event_id         │    └─────────────┘  │   │
│  │  │ - event_types    │    │ - payload          │                     │   │
│  │  │ - project        │    │ - status_code      │                     │   │
│  │  │ - active         │    │ - success          │                     │   │
│  │  └──────────────────┘    │ - error_message    │                     │   │
│  │                          └────────────────────┘                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                        │                                   │
└────────────────────────────────────────┼───────────────────────────────────┘
                                         │
                                         │ HTTPS POST
                                         │ + X-Vibe-Signature
                                         │ + X-Vibe-Event
                                         │ + X-Vibe-Event-ID
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │         External Endpoints               │
                    │                                         │
                    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
                    │  │  Slack  │  │  Jira   │  │ CI/CD   │  │
                    │  └─────────┘  └─────────┘  └─────────┘  │
                    │                                         │
                    └─────────────────────────────────────────┘
```

## Flujo de Eventos

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Flujo: Crear Tarea                                │
└──────────────────────────────────────────────────────────────────────────┘

    MCP Client              tools_write           WebhookManager         External
        │                        │                      │                   │
        │  create_task()         │                      │                   │
        │───────────────────────▶│                      │                   │
        │                        │                      │                   │
        │                        │  1. Validate input   │                   │
        │                        │  2. Write file       │                   │
        │                        │  3. Reindex          │                   │
        │                        │                      │                   │
        │                        │  fire_event()        │                   │
        │                        │─────────────────────▶│                   │
        │                        │                      │                   │
        │  { status: created }   │                      │  (async)          │
        │◀───────────────────────│                      │                   │
        │                        │                      │                   │
        │                        │                      │  Get subscriptions│
        │                        │                      │  matching event   │
        │                        │                      │                   │
        │                        │                      │  For each:        │
        │                        │                      │  ┌───────────────┐│
        │                        │                      │  │ Build payload ││
        │                        │                      │  │ Sign HMAC     ││
        │                        │                      │  │ POST request  │├─────────▶│
        │                        │                      │  │ Log result    ││          │
        │                        │                      │  └───────────────┘│◀─────────│
        │                        │                      │                   │  200 OK  │
        │                        │                      │                   │          │
```

## Componentes

### 1. WebhookManager (`webhooks.py`)

Clase central que gestiona todo el ciclo de vida de webhooks.

```
┌─────────────────────────────────────────────────────────────────┐
│                      WebhookManager                              │
├─────────────────────────────────────────────────────────────────┤
│ Atributos:                                                      │
│   - db: Database              # Conexión a SQLite              │
│   - _executor: ThreadPoolExecutor  # Pool de threads           │
│   - _shutdown_event: Event    # Señal de shutdown              │
├─────────────────────────────────────────────────────────────────┤
│ Métodos Públicos:                                               │
│   + register(url, secret, event_types, project, description)   │
│   + unregister(subscription_id)                                 │
│   + list_subscriptions(project)                                 │
│   + fire_event(event_type, project, data)                      │
│   + shutdown(timeout)                                           │
├─────────────────────────────────────────────────────────────────┤
│ Métodos Privados:                                               │
│   - _deliver_sync(event_id, event_type, payload, subscription) │
│   - _generate_signature(payload, secret)                        │
├─────────────────────────────────────────────────────────────────┤
│ Validaciones:                                                   │
│   - _is_safe_url(url) → SSRF protection                        │
│   - Secret ≥ 32 chars                                           │
│   - Event types válidos                                         │
│   - Límites de subscripciones                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Database Layer (`database.py`)

Extensión del schema SQLite para webhooks.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Webhook Tables (v1.1)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  webhook_subscriptions          webhook_logs                    │
│  ┌─────────────────────┐       ┌─────────────────────┐         │
│  │ id (PK)             │       │ id (PK)             │         │
│  │ url                 │       │ subscription_id (FK)│─────┐   │
│  │ secret              │       │ event_type          │     │   │
│  │ event_types (JSON)  │       │ event_id            │     │   │
│  │ project             │◀──────│ payload             │     │   │
│  │ active              │  1:N  │ status_code         │     │   │
│  │ description         │       │ success             │     │   │
│  │ created_at          │       │ error_message       │     │   │
│  └─────────────────────┘       │ created_at          │     │   │
│                                └─────────────────────┘     │   │
│                                         │                  │   │
│                                         │ ON DELETE CASCADE│   │
│                                         └──────────────────┘   │
│                                                                 │
│  Índices:                                                       │
│  - idx_webhook_subscriptions_active                            │
│  - idx_webhook_subscriptions_project                           │
│  - idx_webhook_subscriptions_active_project (compuesto)        │
│  - idx_webhook_logs_subscription                               │
│  - idx_webhook_logs_event_id                                   │
│  - idx_webhook_logs_created                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Integración con Write Tools

```
┌─────────────────────────────────────────────────────────────────┐
│                    tools_write.py                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Función              Evento Disparado         Datos            │
│  ─────────────────────────────────────────────────────────────  │
│  create_task()    →   task.created         task_number, title   │
│  update_task()    →   task.updated         filename, new_status │
│  create_doc()     →   doc.created          folder, filename     │
│  update_doc()     →   doc.updated          filename, path       │
│  log_session()    →   session.logged       date, action         │
│  create_plan()    →   plan.created/updated filename, path       │
│  init_project()   →   project.initialized  project, folders     │
│  reindex()        →   index.reindexed      document_count       │
│                                                                 │
│  Patrón de integración:                                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  def create_task(...):                                    │  │
│  │      # 1. Validar                                         │  │
│  │      # 2. Escribir archivo                                │  │
│  │      # 3. Reindexar                                       │  │
│  │      result = { ... }                                     │  │
│  │                                                           │  │
│  │      # 4. Disparar webhook (no-bloqueante)               │  │
│  │      _fire_webhook("task.created", project, data)        │  │
│  │                                                           │  │
│  │      return result  # Retorna inmediatamente             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Modelo de Concurrencia

```
┌─────────────────────────────────────────────────────────────────┐
│                   ThreadPoolExecutor                             │
│                    (max_workers=10)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Main Thread          Worker Threads (0-9)                      │
│  ───────────          ────────────────────                      │
│                                                                 │
│  fire_event() ──┬──▶ [Thread 0] _deliver_sync() ──▶ POST URL1  │
│                 │                                               │
│                 ├──▶ [Thread 1] _deliver_sync() ──▶ POST URL2  │
│                 │                                               │
│                 └──▶ [Thread 2] _deliver_sync() ──▶ POST URL3  │
│                                                                 │
│  (retorna        (ejecutan en paralelo,                         │
│   inmediatamente)  máximo 10 concurrentes)                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Beneficios:                                                    │
│  ✓ No bloquea operaciones principales                          │
│  ✓ Rate limiting implícito (máx 10 entregas simultáneas)       │
│  ✓ Reutilización de threads (eficiente)                        │
│  ✓ Shutdown graceful con executor.shutdown()                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Seguridad

### Protección SSRF

```
┌─────────────────────────────────────────────────────────────────┐
│                    _is_safe_url(url)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  URL Input                                                      │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────────────────────────────┐                       │
│  │ 1. Validar scheme (http/https)      │                       │
│  └──────────────────┬──────────────────┘                       │
│                     ▼                                           │
│  ┌─────────────────────────────────────┐                       │
│  │ 2. Verificar hostname bloqueado     │                       │
│  │    - localhost                      │                       │
│  │    - 127.0.0.1, ::1, 0.0.0.0       │                       │
│  │    - metadata.google.internal       │                       │
│  └──────────────────┬──────────────────┘                       │
│                     ▼                                           │
│  ┌─────────────────────────────────────┐                       │
│  │ 3. Resolver DNS → IP               │                       │
│  └──────────────────┬──────────────────┘                       │
│                     ▼                                           │
│  ┌─────────────────────────────────────┐                       │
│  │ 4. Verificar IP contra rangos       │                       │
│  │    bloqueados:                      │                       │
│  │    - 127.0.0.0/8    (loopback)     │                       │
│  │    - 10.0.0.0/8     (privado A)    │                       │
│  │    - 172.16.0.0/12  (privado B)    │                       │
│  │    - 192.168.0.0/16 (privado C)    │                       │
│  │    - 169.254.0.0/16 (link-local)   │                       │
│  │    - fc00::/7       (IPv6 privado) │                       │
│  │    - fe80::/10      (IPv6 link)    │                       │
│  └──────────────────┬──────────────────┘                       │
│                     ▼                                           │
│              (True, "") o (False, "reason")                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Firma HMAC-SHA256

```
┌─────────────────────────────────────────────────────────────────┐
│                    Proceso de Firma                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Payload JSON                Secret                             │
│       │                         │                               │
│       ▼                         ▼                               │
│  ┌─────────┐              ┌─────────┐                          │
│  │ encode  │              │ encode  │                          │
│  │ UTF-8   │              │ UTF-8   │                          │
│  └────┬────┘              └────┬────┘                          │
│       │                        │                               │
│       └───────────┬────────────┘                               │
│                   ▼                                             │
│            ┌─────────────┐                                      │
│            │ HMAC-SHA256 │                                      │
│            └──────┬──────┘                                      │
│                   ▼                                             │
│            ┌─────────────┐                                      │
│            │  hexdigest  │                                      │
│            └──────┬──────┘                                      │
│                   ▼                                             │
│         "sha256=" + signature                                   │
│                   │                                             │
│                   ▼                                             │
│         X-Vibe-Signature header                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Singleton Thread-Safe

```
┌─────────────────────────────────────────────────────────────────┐
│              Double-Check Locking Pattern                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  _webhook_manager: WebhookManager | None = None                 │
│  _webhook_manager_lock = threading.Lock()                       │
│                                                                 │
│  def get_webhook_manager():                                     │
│      global _webhook_manager                                    │
│                                                                 │
│      if _webhook_manager is None:        # Check 1 (sin lock)  │
│          with _webhook_manager_lock:     # Acquire lock        │
│              if _webhook_manager is None: # Check 2 (con lock) │
│                  # Crear instancia                              │
│                  db = Database(...)                             │
│                  _webhook_manager = WebhookManager(db)          │
│                                                                 │
│      return _webhook_manager                                    │
│                                                                 │
│  Beneficios:                                                    │
│  ✓ Thread-safe: múltiples threads no crean instancias duplicadas│
│  ✓ Eficiente: solo adquiere lock cuando es necesario           │
│  ✓ Lazy initialization: crea solo cuando se necesita           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Decisiones de Diseño

### 1. ¿Por qué ThreadPoolExecutor en vez de asyncio?

```
┌─────────────────────────────────────────────────────────────────┐
│  Opción           Pros                    Contras               │
├─────────────────────────────────────────────────────────────────┤
│  asyncio         - Más eficiente en I/O   - Requiere async/await│
│                  - Menos overhead          en todo el código    │
│                                           - FastMCP ya tiene    │
│                                             su propio event loop│
│                                                                 │
│  ThreadPool ✓    - Simple de integrar     - Overhead de threads │
│                  - Compatible con código  - Límite de workers   │
│                    síncrono existente                           │
│                  - Aislamiento de errores                       │
│                  - Shutdown graceful fácil                      │
└─────────────────────────────────────────────────────────────────┘

Decisión: ThreadPoolExecutor por simplicidad y compatibilidad con
el código existente. El overhead es aceptable para el volumen
esperado de webhooks.
```

### 2. ¿Por qué secrets en texto plano?

```
┌─────────────────────────────────────────────────────────────────┐
│  Opción           Pros                    Contras               │
├─────────────────────────────────────────────────────────────────┤
│  Encriptado      - Más seguro si DB      - Requiere key mgmt   │
│                    se compromete          - Complejidad añadida │
│                                           - Key storage problem │
│                                                                 │
│  Texto plano ✓   - Simple                 - Riesgo si DB leaks │
│                  - Index es "disposable"  - Mitigado por:       │
│                  - Uso local típico         · Permisos de archivo│
│                                             · No en cloud       │
│                                             · Regenerable       │
└─────────────────────────────────────────────────────────────────┘

Decisión: Texto plano por simplicidad. El índice SQLite es local
y "disposable" (regenerable). Para producción en cloud, considerar
encriptación con Fernet o similar.
```

### 3. ¿Por qué límites de subscripciones?

```
┌─────────────────────────────────────────────────────────────────┐
│  Sin límites:                                                   │
│  - Usuario malicioso registra 10,000 webhooks                  │
│  - Cada evento dispara 10,000 HTTP requests                    │
│  - DoS al servidor y a los endpoints destino                   │
│                                                                 │
│  Con límites (50/proyecto, 200 global):                         │
│  - Suficiente para casos de uso legítimos                      │
│  - Previene abuso                                               │
│  - Configurable en constantes si necesario                      │
└─────────────────────────────────────────────────────────────────┘
```

## Flujo de Datos Completo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  1. REGISTRO                                                                │
│  ───────────                                                                │
│  MCP Client ─▶ tool_register_webhook() ─▶ WebhookManager.register()        │
│                                              │                              │
│                                              ├─ Validar URL (SSRF)         │
│                                              ├─ Validar secret (≥32)       │
│                                              ├─ Validar event_types        │
│                                              ├─ Verificar límites          │
│                                              │                              │
│                                              ▼                              │
│                                         Database.create_webhook_subscription│
│                                              │                              │
│                                              ▼                              │
│                                         webhook_subscriptions (INSERT)      │
│                                                                             │
│  2. DISPARO DE EVENTO                                                       │
│  ────────────────────                                                       │
│  create_task() ─▶ _fire_webhook() ─▶ WebhookManager.fire_event()           │
│                                         │                                   │
│                                         ├─ Check webhooks_enabled          │
│                                         ├─ Check shutdown                   │
│                                         │                                   │
│                                         ▼                                   │
│                                    Database.get_active_subscriptions()      │
│                                         │                                   │
│                                         ▼                                   │
│                                    Para cada subscription:                  │
│                                    executor.submit(_deliver_sync)           │
│                                         │                                   │
│                                         │ (async, en thread pool)           │
│                                         ▼                                   │
│                                                                             │
│  3. ENTREGA                                                                 │
│  ─────────                                                                  │
│  _deliver_sync() ─┬─▶ Build payload JSON                                   │
│                   ├─▶ Generate HMAC signature                               │
│                   ├─▶ HTTP POST with headers                                │
│                   │      │                                                  │
│                   │      ▼                                                  │
│                   │   External Endpoint ─▶ 200 OK / 4xx / 5xx / timeout    │
│                   │      │                                                  │
│                   │      ▼                                                  │
│                   └─▶ Database.log_webhook_delivery()                       │
│                          │                                                  │
│                          ▼                                                  │
│                      webhook_logs (INSERT)                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
