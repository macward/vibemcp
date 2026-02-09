# Deployment Guide

Guide for deploying vibeMCP to a production environment.

## Overview

vibeMCP is designed to run on a VPS with HTTPS access, allowing AI agents from any location to connect to your workspace context.

```
Client (Claude Code, Claude.ai, Cursor)
    ↓ HTTPS
Caddy (reverse proxy + TLS)
    ↓ HTTP
vibeMCP (FastMCP + SSE)
    ↓ read/write
~/.vibe/ (filesystem)
```

---

## Docker Deployment

The fastest way to deploy vibeMCP is using Docker.

### Prerequisites

- Docker and Docker Compose installed
- Your `~/.vibe` workspace directory

### Quick Start

1. **Clone the repository:**

```bash
git clone https://github.com/your-username/vibeMCP.git
cd vibeMCP
```

2. **Configure environment:**

```bash
# Copy example env file
cp .env.example .env

# Generate a secure auth token
echo "VIBE_AUTH_TOKEN=$(openssl rand -hex 32)" >> .env
```

3. **Build and run:**

```bash
# Build the image
docker compose build

# Start the container
docker compose up -d

# Check logs
docker compose logs -f
```

4. **Verify:**

```bash
# Check health
curl http://localhost:8288/

# Test with auth (if configured)
curl http://localhost:8288/ -H "Authorization: Bearer YOUR_TOKEN"
```

### Docker Configuration

The `docker-compose.yml` mounts your local `~/.vibe` directory to `/data` in the container:

```yaml
services:
  vibemcp:
    build: .
    ports:
      - "127.0.0.1:8288:8288"
    volumes:
      - ~/.vibe:/data
    environment:
      - VIBE_ROOT=/data
      - VIBE_DB=/data/index.db
      - VIBE_AUTH_TOKEN=${VIBE_AUTH_TOKEN}
      - VIBE_READ_ONLY=${VIBE_READ_ONLY:-false}
    restart: unless-stopped
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VIBE_ROOT` | Workspace directory inside container | `/data` |
| `VIBE_DB` | SQLite database path | `/data/index.db` |
| `VIBE_PORT` | Server port | `8288` |
| `VIBE_AUTH_TOKEN` | Bearer token for authentication | (none) |
| `VIBE_READ_ONLY` | Disable write operations | `false` |

### Building Manually

```bash
# Build the image
docker build -t vibemcp .

# Run with custom options
docker run -d \
  --name vibemcp \
  -p 127.0.0.1:8288:8288 \
  -v ~/.vibe:/data \
  -e VIBE_AUTH_TOKEN="your-token-here" \
  vibemcp
```

### Docker with Caddy

For HTTPS with automatic certificates, use Caddy as reverse proxy:

```yaml
# docker-compose.prod.yml
services:
  vibemcp:
    build: .
    expose:
      - "8288"
    volumes:
      - ~/.vibe:/data
    environment:
      - VIBE_ROOT=/data
      - VIBE_AUTH_TOKEN=${VIBE_AUTH_TOKEN}
    restart: unless-stopped

  caddy:
    image: caddy:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - vibemcp
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

### Updating

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose build
docker compose up -d
```

---

## Manual Server Setup

For more control, deploy vibeMCP directly on a VPS.

### Prerequisites

- VPS with Ubuntu 22.04+ (DigitalOcean, Fly.io, Linode, etc.)
- Domain name pointed to your VPS IP
- SSH access to the server

---

## Server Setup

### 1. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Caddy (reverse proxy)
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy -y

# Install Git
sudo apt install git -y
```

### 2. Create Service User

```bash
# Create dedicated user for vibeMCP
sudo useradd -r -m -s /bin/bash vibemcp

# Switch to vibemcp user
sudo -u vibemcp -i
```

### 3. Clone and Install vibeMCP

```bash
# As vibemcp user
cd ~

# Clone repository
git clone https://github.com/your-username/vibeMCP.git
cd vibeMCP

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install package
pip install -e .
```

### 4. Set Up Workspace

```bash
# Create .vibe directory
mkdir -p ~/.vibe

# If you have existing workspaces, clone them
# git clone git@github.com:your-username/vibe-workspaces.git ~/.vibe
```

---

## Configuration

### 1. Environment File

Create `/home/vibemcp/.env`:

```bash
# vibeMCP Configuration
VIBE_ROOT=/home/vibemcp/.vibe
VIBE_PORT=8288
VIBE_DB=/home/vibemcp/.vibe/index.db

# Authentication (generate a secure token)
# Use: openssl rand -hex 32
VIBE_AUTH_TOKEN=your-32-character-minimum-secure-token-here

# Read-only mode (optional, recommended for public deployments)
# VIBE_READ_ONLY=true
```

Generate a secure token:

```bash
# Generate and display a secure token
openssl rand -hex 32
```

### 2. Systemd Service

Create `/etc/systemd/system/vibemcp.service`:

```ini
[Unit]
Description=vibeMCP MCP Server
After=network.target

[Service]
Type=simple
User=vibemcp
Group=vibemcp
WorkingDirectory=/home/vibemcp/vibeMCP
EnvironmentFile=/home/vibemcp/.env
ExecStart=/home/vibemcp/vibeMCP/.venv/bin/python -m vibe_mcp.main
Restart=always
RestartSec=5

# Security hardening
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/vibemcp/.vibe
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vibemcp
sudo systemctl start vibemcp

# Check status
sudo systemctl status vibemcp

# View logs
sudo journalctl -u vibemcp -f
```

### 3. Caddy Configuration

Create `/etc/caddy/Caddyfile`:

```caddy
vibe.yourdomain.com {
    # Reverse proxy to vibeMCP
    reverse_proxy localhost:8288

    # Enable compression
    encode gzip

    # Logging
    log {
        output file /var/log/caddy/vibemcp.log
        format json
    }

    # Security headers
    header {
        # Prevent clickjacking
        X-Frame-Options DENY
        # XSS protection
        X-Content-Type-Options nosniff
        # Remove server header
        -Server
    }
}
```

Restart Caddy:

```bash
sudo systemctl restart caddy

# Caddy automatically handles HTTPS via Let's Encrypt
```

---

## Sync Workspaces with Git

### Initial Setup

```bash
# As vibemcp user
cd ~/.vibe

# Initialize Git repo (if not cloned)
git init
git remote add origin git@github.com:your-username/vibe-workspaces.git
```

### Manual Sync Script

Create `/home/vibemcp/sync-vibe.sh`:

```bash
#!/bin/bash
set -e

cd /home/vibemcp/.vibe

# Pull latest changes
git pull origin main

# Trigger reindex
curl -X POST http://localhost:8288/reindex \
  -H "Authorization: Bearer $VIBE_AUTH_TOKEN" \
  -H "Content-Type: application/json"

echo "Sync complete"
```

Make executable:

```bash
chmod +x /home/vibemcp/sync-vibe.sh
```

### Cron Job (Optional)

For automatic sync every 15 minutes:

```bash
# Edit crontab
crontab -e

# Add line:
*/15 * * * * /home/vibemcp/sync-vibe.sh >> /home/vibemcp/sync.log 2>&1
```

**Note:** The server never auto-commits. All writes are local until you manually push.

---

## Security Considerations

### 1. Authentication

Always enable authentication in production:

```bash
# Minimum 32 characters
VIBE_AUTH_TOKEN=$(openssl rand -hex 32)
```

### 2. Read-Only Mode

For public-facing deployments where you don't need write access:

```bash
VIBE_READ_ONLY=true
```

### 3. Firewall

```bash
# Only allow SSH and HTTPS
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# Block direct access to vibeMCP port
# (only accessible via Caddy reverse proxy)
```

### 4. Path Validation

vibeMCP validates all file paths to prevent:
- Directory traversal (`../`)
- Access outside `VIBE_ROOT`
- Symlink attacks

### 5. Rate Limiting

Add rate limiting in Caddy:

```caddy
vibe.yourdomain.com {
    # Rate limit: 100 requests per minute per IP
    @ratelimit {
        path *
    }
    rate_limit @ratelimit {
        zone vibe_zone {
            key {remote_host}
            events 100
            window 1m
        }
    }

    reverse_proxy localhost:8288
}
```

---

## Monitoring

### Health Check

Create a simple health check endpoint test:

```bash
# Check if server responds
curl -s https://vibe.yourdomain.com/health \
  -H "Authorization: Bearer $VIBE_AUTH_TOKEN" \
  | jq .
```

### Logs

```bash
# vibeMCP logs
sudo journalctl -u vibemcp -f

# Caddy logs
sudo tail -f /var/log/caddy/vibemcp.log
```

### Metrics (Optional)

For production monitoring, consider adding:
- Prometheus metrics endpoint
- Grafana dashboards
- Alerting on errors

---

## SSE Reconnection

MCP uses Server-Sent Events (SSE) for real-time communication. For reliable connections:

### Client Configuration

Most MCP clients handle reconnection automatically. Configure:
- Reconnection timeout: 30 seconds
- Max retries: 5
- Exponential backoff

### Server-Side

Caddy handles SSE connections automatically. For long-running connections, ensure:

```caddy
vibe.yourdomain.com {
    reverse_proxy localhost:8288 {
        # Disable buffering for SSE
        flush_interval -1
    }
}
```

---

## Backup

### Database

The SQLite database is disposable (regenerated from filesystem), but for faster recovery:

```bash
# Backup script
sqlite3 /home/vibemcp/.vibe/index.db ".backup /home/vibemcp/backups/index-$(date +%Y%m%d).db"
```

### Workspaces

```bash
# Push to Git regularly
cd ~/.vibe
git add -A
git commit -m "Backup: $(date +%Y-%m-%d)"
git push origin main
```

---

## Upgrading

```bash
# Stop service
sudo systemctl stop vibemcp

# As vibemcp user
sudo -u vibemcp -i
cd ~/vibeMCP

# Pull latest
git pull origin main

# Update dependencies
source .venv/bin/activate
pip install -e .

# Exit back to root
exit

# Restart service
sudo systemctl start vibemcp

# Force reindex if schema changed
curl -X POST https://vibe.yourdomain.com/reindex \
  -H "Authorization: Bearer $VIBE_AUTH_TOKEN"
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u vibemcp -n 50

# Common issues:
# - Missing .env file
# - Invalid VIBE_AUTH_TOKEN (< 32 chars)
# - Port already in use
# - Permission denied on VIBE_ROOT
```

### SSL Certificate Issues

```bash
# Caddy auto-renews certificates
# Force renewal:
sudo caddy reload --config /etc/caddy/Caddyfile

# Check certificate status
curl -vI https://vibe.yourdomain.com 2>&1 | grep -i "SSL\|certificate"
```

### Index Corruption

```bash
# Delete and rebuild index
rm /home/vibemcp/.vibe/index.db
sudo systemctl restart vibemcp
# Index rebuilds automatically on startup
```

### Connection Refused

```bash
# Check if vibeMCP is running
sudo systemctl status vibemcp

# Check if port is open
ss -tlnp | grep 8288

# Check Caddy
sudo systemctl status caddy
```
