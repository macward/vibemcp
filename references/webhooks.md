# Webhooks en vibeMCP

Sistema de webhooks salientes que notifica a URLs externas cuando ocurren cambios en el workspace.

## Configuración

### Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `VIBE_WEBHOOKS_ENABLED` | `true` | Habilitar/deshabilitar webhooks globalmente |

```bash
# Deshabilitar webhooks
export VIBE_WEBHOOKS_ENABLED=false
```

## MCP Tools

### `tool_register_webhook`

Registra una nueva subscripción de webhook.

**Parámetros:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `url` | string | Sí | URL a la que se enviará el POST (http:// o https://) |
| `secret` | string | Sí | Secret para firma HMAC-SHA256 (mínimo 32 caracteres) |
| `event_types` | list[string] | Sí | Lista de eventos a subscribir |
| `project` | string | No | Filtrar por proyecto (null = todos) |
| `description` | string | No | Descripción del webhook |

**Ejemplo:**

```json
{
  "url": "https://api.example.com/webhooks/vibe",
  "secret": "whsec_abcdefghij1234567890abcdefghij12",
  "event_types": ["task.created", "task.updated"],
  "project": "my-project",
  "description": "Notificar cambios de tareas a Slack"
}
```

**Respuesta:**

```json
{
  "status": "registered",
  "subscription_id": 1,
  "url": "https://api.example.com/webhooks/vibe",
  "event_types": ["task.created", "task.updated"],
  "project": "my-project"
}
```

### `tool_unregister_webhook`

Elimina una subscripción de webhook.

**Parámetros:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `subscription_id` | int | Sí | ID de la subscripción a eliminar |

**Respuesta:**

```json
{
  "status": "unregistered",
  "subscription_id": 1
}
```

### `tool_list_webhooks`

Lista las subscripciones activas.

**Parámetros:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `project` | string | No | Filtrar por proyecto |

**Respuesta:**

```json
[
  {
    "id": 1,
    "url": "https://api.example.com/webhooks/vibe",
    "event_types": ["task.created", "task.updated"],
    "project": "my-project",
    "active": true,
    "description": "Notificar cambios de tareas",
    "created_at": "2024-02-10T12:00:00"
  }
]
```

> **Nota:** Los secrets nunca se incluyen en la respuesta de list.

## Eventos Disponibles

| Evento | Descripción | Datos incluidos |
|--------|-------------|-----------------|
| `task.created` | Nueva tarea creada | task_number, title, filename, path, status |
| `task.updated` | Estado de tarea actualizado | filename, path, new_status |
| `doc.created` | Nuevo documento creado | folder, filename, path |
| `doc.updated` | Documento actualizado | filename, path |
| `session.logged` | Entrada de sesión registrada | date, path, action |
| `plan.created` | Plan de ejecución creado | filename, path |
| `plan.updated` | Plan de ejecución actualizado | filename, path |
| `project.initialized` | Nuevo proyecto inicializado | project, path, folders |
| `index.reindexed` | Índice reconstruido | document_count |
| `*` | Wildcard - todos los eventos | Varía según evento |

## Formato del Payload

Cada notificación incluye:

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "task.created",
  "project": "my-project",
  "timestamp": "2024-02-10T12:34:56.789000+00:00",
  "data": {
    "task_number": 5,
    "title": "Implement feature X",
    "filename": "005-implement-feature-x.md",
    "path": "my-project/tasks/005-implement-feature-x.md",
    "status": "pending"
  }
}
```

### Campos del Payload

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `event_id` | string (UUID) | Identificador único del evento |
| `event_type` | string | Tipo de evento |
| `project` | string \| null | Nombre del proyecto (null para eventos globales) |
| `timestamp` | string (ISO 8601) | Fecha/hora UTC del evento |
| `data` | object | Datos específicos del evento |

## Headers HTTP

Cada POST incluye los siguientes headers:

| Header | Ejemplo | Descripción |
|--------|---------|-------------|
| `Content-Type` | `application/json` | Tipo de contenido |
| `X-Vibe-Event` | `task.created` | Tipo de evento |
| `X-Vibe-Event-ID` | `550e8400-...` | ID único del evento |
| `X-Vibe-Signature` | `sha256=abc123...` | Firma HMAC-SHA256 |

## Verificación de Firma

Para verificar que el webhook proviene de vibeMCP, valida la firma HMAC-SHA256.

### Python

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verificar firma HMAC-SHA256 del webhook."""
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    received = signature.replace('sha256=', '')
    return hmac.compare_digest(expected, received)

# Uso en Flask
from flask import Flask, request, abort

app = Flask(__name__)
WEBHOOK_SECRET = "whsec_abcdefghij1234567890abcdefghij12"

@app.route('/webhooks/vibe', methods=['POST'])
def handle_webhook():
    signature = request.headers.get('X-Vibe-Signature', '')

    if not verify_signature(request.data, signature, WEBHOOK_SECRET):
        abort(401, 'Invalid signature')

    event = request.json
    event_type = event['event_type']

    if event_type == 'task.created':
        print(f"Nueva tarea: {event['data']['title']}")

    return '', 200
```

### Node.js

```javascript
const crypto = require('crypto');
const express = require('express');

const app = express();
const WEBHOOK_SECRET = 'whsec_abcdefghij1234567890abcdefghij12';

function verifySignature(payload, signature, secret) {
    const expected = crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');

    const received = signature.replace('sha256=', '');
    return crypto.timingSafeEqual(
        Buffer.from(expected),
        Buffer.from(received)
    );
}

app.post('/webhooks/vibe', express.raw({type: 'application/json'}), (req, res) => {
    const signature = req.headers['x-vibe-signature'] || '';

    if (!verifySignature(req.body, signature, WEBHOOK_SECRET)) {
        return res.status(401).send('Invalid signature');
    }

    const event = JSON.parse(req.body);
    console.log(`Event: ${event.event_type}`, event.data);

    res.status(200).send('OK');
});
```

### Go

```go
package main

import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "io"
    "net/http"
    "strings"
)

const webhookSecret = "whsec_abcdefghij1234567890abcdefghij12"

func verifySignature(payload []byte, signature, secret string) bool {
    mac := hmac.New(sha256.New, []byte(secret))
    mac.Write(payload)
    expected := hex.EncodeToString(mac.Sum(nil))
    received := strings.TrimPrefix(signature, "sha256=")
    return hmac.Equal([]byte(expected), []byte(received))
}

func webhookHandler(w http.ResponseWriter, r *http.Request) {
    payload, _ := io.ReadAll(r.Body)
    signature := r.Header.Get("X-Vibe-Signature")

    if !verifySignature(payload, signature, webhookSecret) {
        http.Error(w, "Invalid signature", http.StatusUnauthorized)
        return
    }

    var event map[string]interface{}
    json.Unmarshal(payload, &event)

    // Procesar evento...
    w.WriteHeader(http.StatusOK)
}
```

## Límites y Restricciones

### Límites de Subscripciones

| Límite | Valor |
|--------|-------|
| Subscripciones por proyecto | 50 |
| Subscripciones globales | 200 |
| Entregas concurrentes | 10 |
| Timeout por entrega | 10 segundos |

### Protección SSRF

Los siguientes destinos están bloqueados por seguridad:

- `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`
- Rangos IP privados: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
- Link-local: `169.254.0.0/16`, `fe80::/10`
- Cloud metadata: `metadata.google.internal`, `169.254.169.254`

### Requisitos del Secret

- Mínimo 32 caracteres
- Recomendado: usar generador criptográfico

```bash
# Generar secret seguro
openssl rand -hex 32
# o
python -c "import secrets; print('whsec_' + secrets.token_hex(32))"
```

## Logs de Entrega

Cada intento de entrega se registra en la tabla `webhook_logs`:

| Campo | Descripción |
|-------|-------------|
| `subscription_id` | ID de la subscripción |
| `event_type` | Tipo de evento |
| `event_id` | UUID del evento |
| `payload` | JSON enviado |
| `status_code` | Código HTTP de respuesta |
| `success` | true si 2xx |
| `error_message` | Mensaje de error si falló |
| `created_at` | Timestamp del intento |

## Ejemplos de Uso

### Notificar a Slack

```python
# Registrar webhook para Slack
register_webhook(
    url="https://hooks.slack.com/services/T00/B00/xxx",
    secret="a]" * 32,  # Slack no verifica firma, pero es requerido
    event_types=["task.created", "task.updated"],
    project="my-project",
    description="Slack notifications"
)
```

### Sincronizar con Sistema Externo

```python
# Webhook para sincronizar tareas con Jira
register_webhook(
    url="https://api.mycompany.com/integrations/vibe",
    secret="whsec_" + secrets.token_hex(32),
    event_types=["*"],  # Todos los eventos
    description="Sync with internal systems"
)
```

### Trigger CI/CD

```python
# Webhook para GitHub Actions
register_webhook(
    url="https://api.github.com/repos/owner/repo/dispatches",
    secret=os.environ["GITHUB_WEBHOOK_SECRET"],
    event_types=["task.updated"],
    project="my-project",
    description="Trigger CI on task completion"
)
```

## Troubleshooting

### El webhook no se entrega

1. Verificar que `VIBE_WEBHOOKS_ENABLED=true`
2. Verificar que la URL es accesible públicamente (no localhost)
3. Revisar logs de entrega en `webhook_logs`
4. Verificar que el evento está en `event_types` de la subscripción

### Firma inválida

1. Usar el payload raw (bytes), no el JSON parseado
2. Verificar que el secret coincide exactamente
3. No modificar el payload antes de verificar

### Timeout

1. El endpoint debe responder en < 10 segundos
2. Procesar el evento de forma asíncrona si requiere tiempo
3. Responder 200 inmediatamente, procesar después

## Schema de Base de Datos

```sql
-- Subscripciones
CREATE TABLE webhook_subscriptions (
    id          INTEGER PRIMARY KEY,
    url         TEXT NOT NULL,
    secret      TEXT NOT NULL,
    event_types TEXT NOT NULL,  -- JSON array
    project     TEXT,           -- NULL = all
    active      INTEGER DEFAULT 1,
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Logs de entrega
CREATE TABLE webhook_logs (
    id              INTEGER PRIMARY KEY,
    subscription_id INTEGER NOT NULL,
    event_type      TEXT NOT NULL,
    event_id        TEXT NOT NULL,
    payload         TEXT NOT NULL,
    status_code     INTEGER,
    success         INTEGER DEFAULT 0,
    error_message   TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (subscription_id)
        REFERENCES webhook_subscriptions(id) ON DELETE CASCADE
);
```
