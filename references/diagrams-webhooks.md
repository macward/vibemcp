# Diagramas del Sistema de Webhooks

Diagramas en formato Mermaid para visualización en GitHub/GitLab.

## Arquitectura General

```mermaid
flowchart TB
    subgraph Clients["MCP Clients"]
        CC[Claude Code]
        CA[Claude.ai]
        CU[Cursor]
    end

    subgraph Server["vibeMCP Server"]
        subgraph Tools["MCP Tools"]
            TW[tools_write.py]
            TWH[tools_webhooks.py]
        end

        subgraph Core["Core"]
            WM[WebhookManager]
            TP[ThreadPoolExecutor<br/>max_workers=10]
        end

        subgraph Storage["SQLite Database"]
            WS[(webhook_subscriptions)]
            WL[(webhook_logs)]
            DOCS[(documents/chunks)]
        end
    end

    subgraph External["External Endpoints"]
        SL[Slack]
        JI[Jira]
        GH[GitHub Actions]
        CUS[Custom APIs]
    end

    CC --> TW
    CA --> TW
    CU --> TW

    CC --> TWH

    TW -->|fire_event| WM
    TWH -->|register/unregister| WM

    WM --> TP
    WM --> WS

    TP -->|POST + HMAC| SL
    TP -->|POST + HMAC| JI
    TP -->|POST + HMAC| GH
    TP -->|POST + HMAC| CUS

    TP -->|log result| WL

    TW --> DOCS
```

## Flujo de Registro de Webhook

```mermaid
sequenceDiagram
    participant C as MCP Client
    participant T as tools_webhooks
    participant W as WebhookManager
    participant V as _is_safe_url
    participant D as Database

    C->>T: register_webhook(url, secret, events)
    T->>W: register()

    W->>W: Validate URL scheme
    W->>V: _is_safe_url(url)
    V->>V: Check blocked hostnames
    V->>V: Resolve DNS → IP
    V->>V: Check blocked IP ranges
    V-->>W: (is_safe, error_msg)

    alt URL is unsafe
        W-->>T: ValueError("Unsafe URL")
        T-->>C: Error response
    else URL is safe
        W->>W: Validate secret ≥ 32 chars
        W->>W: Validate event_types
        W->>D: list_webhook_subscriptions()
        D-->>W: existing subscriptions
        W->>W: Check limits

        alt Limit exceeded
            W-->>T: ValueError("Maximum reached")
            T-->>C: Error response
        else Within limits
            W->>D: create_webhook_subscription()
            D-->>W: subscription_id
            W-->>T: {status: registered, id: N}
            T-->>C: Success response
        end
    end
```

## Flujo de Disparo de Evento

```mermaid
sequenceDiagram
    participant T as tools_write
    participant F as _fire_webhook
    participant W as WebhookManager
    participant E as ThreadPoolExecutor
    participant D as Database
    participant X as External URL

    T->>T: create_task() / update_task() / etc
    T->>T: Write file to disk
    T->>T: Reindex file

    T->>F: _fire_webhook(event_type, project, data)
    F->>W: fire_event()

    Note over T: Returns immediately<br/>(non-blocking)

    W->>W: Check webhooks_enabled
    W->>W: Check shutdown_event
    W->>D: get_active_subscriptions_for_event()
    D-->>W: matching subscriptions

    loop For each subscription
        W->>E: submit(_deliver_sync)
    end

    Note over E: Async execution<br/>in thread pool

    par Parallel Deliveries
        E->>E: Build payload JSON
        E->>E: Generate HMAC signature
        E->>X: POST with headers
        X-->>E: HTTP response
        E->>D: log_webhook_delivery()
    end
```

## Estructura de Base de Datos

```mermaid
erDiagram
    webhook_subscriptions {
        int id PK
        text url
        text secret
        text event_types "JSON array"
        text project "nullable"
        int active "default 1"
        text description "nullable"
        text created_at
    }

    webhook_logs {
        int id PK
        int subscription_id FK
        text event_type
        text event_id "UUID"
        text payload "JSON"
        int status_code "nullable"
        int success "0 or 1"
        text error_message "nullable"
        text created_at
    }

    webhook_subscriptions ||--o{ webhook_logs : "has many"
```

## Validación SSRF

```mermaid
flowchart TD
    URL[URL Input] --> S{Scheme?}

    S -->|http/https| H{Hostname<br/>blocked?}
    S -->|other| R1[❌ Reject:<br/>Invalid scheme]

    H -->|localhost<br/>127.0.0.1<br/>0.0.0.0<br/>metadata.*| R2[❌ Reject:<br/>Blocked hostname]
    H -->|other| DNS[Resolve DNS]

    DNS --> IP{IP in blocked<br/>range?}

    IP -->|10.0.0.0/8<br/>172.16.0.0/12<br/>192.168.0.0/16<br/>169.254.0.0/16<br/>fc00::/7<br/>fe80::/10| R3[❌ Reject:<br/>Private IP]

    IP -->|public IP| OK[✅ Accept]
```

## Proceso de Firma HMAC

```mermaid
flowchart LR
    subgraph Input
        P[Payload JSON]
        S[Secret]
    end

    subgraph Encoding
        P --> PE[UTF-8 bytes]
        S --> SE[UTF-8 bytes]
    end

    subgraph Signing
        PE --> HMAC[HMAC-SHA256]
        SE --> HMAC
        HMAC --> HEX[Hex digest]
    end

    subgraph Output
        HEX --> SIG["sha256=abc123..."]
        SIG --> HDR[X-Vibe-Signature<br/>header]
    end
```

## Modelo de Concurrencia

```mermaid
flowchart TB
    subgraph Main["Main Thread"]
        FE[fire_event]
    end

    subgraph Pool["ThreadPoolExecutor (max=10)"]
        W0[Worker 0]
        W1[Worker 1]
        W2[Worker 2]
        WN[Worker N]
    end

    subgraph Endpoints["External"]
        E1[URL 1]
        E2[URL 2]
        E3[URL 3]
        EN[URL N]
    end

    FE -->|submit| W0
    FE -->|submit| W1
    FE -->|submit| W2
    FE -->|submit| WN

    W0 -->|POST| E1
    W1 -->|POST| E2
    W2 -->|POST| E3
    WN -->|POST| EN

    FE -.->|returns immediately| RET[Response to client]
```

## Estados del Ciclo de Vida

```mermaid
stateDiagram-v2
    [*] --> Registered: register_webhook()

    Registered --> Active: Default state
    Active --> Delivering: Event fired
    Delivering --> Active: Delivery complete
    Delivering --> Active: Delivery failed

    Active --> Unregistered: unregister_webhook()
    Unregistered --> [*]

    note right of Delivering
        Logs written to
        webhook_logs table
    end note
```

## Payload de Evento

```mermaid
classDiagram
    class WebhookPayload {
        +string event_id
        +string event_type
        +string|null project
        +string timestamp
        +object data
    }

    class TaskCreatedData {
        +int task_number
        +string title
        +string filename
        +string path
        +string status
    }

    class TaskUpdatedData {
        +string filename
        +string path
        +string new_status
    }

    class DocCreatedData {
        +string folder
        +string filename
        +string path
    }

    WebhookPayload --> TaskCreatedData : task.created
    WebhookPayload --> TaskUpdatedData : task.updated
    WebhookPayload --> DocCreatedData : doc.created
```

## Headers HTTP

```mermaid
flowchart LR
    subgraph Request["HTTP POST Request"]
        H1["Content-Type:<br/>application/json"]
        H2["X-Vibe-Event:<br/>task.created"]
        H3["X-Vibe-Event-ID:<br/>uuid"]
        H4["X-Vibe-Signature:<br/>sha256=..."]
        BODY["JSON Payload"]
    end

    Request --> EP[External Endpoint]

    EP --> V{Verify<br/>Signature}
    V -->|Valid| PROC[Process Event]
    V -->|Invalid| REJ[401 Unauthorized]
```
