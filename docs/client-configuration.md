# Client Configuration

Guide for connecting MCP clients to vibeMCP.

## Overview

vibeMCP supports any MCP-compatible client. This guide covers configuration for the most common clients:

1. **Claude Code CLI** - Most stable, connect first
2. **Claude.ai** - Web/mobile access
3. **Cursor/Windsurf** - IDE integration (more fragile with MCP)

---

## Connection URL

### Local Development

```
http://localhost:8080
```

### Remote Server

```
https://vibe.yourdomain.com
```

---

## Claude Code CLI

Claude Code is the most stable MCP client. Configure it first.

### Configuration File

Edit `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "vibeMCP": {
      "url": "https://vibe.yourdomain.com",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
  }
}
```

### Local Development

```json
{
  "mcpServers": {
    "vibeMCP": {
      "url": "http://localhost:8080",
      "transport": "sse"
    }
  }
}
```

### Verify Connection

```bash
# List available tools
claude mcp list-tools vibeMCP

# Test search
claude mcp call vibeMCP search '{"query": "test"}'
```

---

## Claude.ai

Configure MCP servers in Claude.ai settings.

### Steps

1. Open Claude.ai
2. Go to **Settings** > **MCP Servers**
3. Click **Add Server**
4. Enter configuration:

| Field | Value |
|-------|-------|
| Name | vibeMCP |
| URL | https://vibe.yourdomain.com |
| Transport | SSE |
| Auth Token | your-token-here |

### Using in Chat

Once connected, you can use natural language:

```
"Search my projects for authentication implementation"
"Show me the status of vibeMCP project"
"Create a new task in demo-api: Implement rate limiting"
```

---

## Cursor

Cursor has more fragile MCP support. Connect this last after verifying with Claude Code.

### Configuration

Edit `.cursor/mcp.json` in your project or `~/.cursor/mcp.json` globally:

```json
{
  "servers": {
    "vibeMCP": {
      "url": "https://vibe.yourdomain.com",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
  }
}
```

### Troubleshooting Cursor

If connection fails:

1. Restart Cursor
2. Check Developer Tools (Help > Toggle Developer Tools) for errors
3. Verify URL is accessible: `curl https://vibe.yourdomain.com`
4. Try without auth first (if server allows)

---

## Windsurf

Similar to Cursor configuration.

### Configuration

Edit `~/.windsurf/mcp.json`:

```json
{
  "servers": {
    "vibeMCP": {
      "url": "https://vibe.yourdomain.com",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
  }
}
```

---

## Authentication

### Token Format

Include the Bearer token in headers:

```
Authorization: Bearer your-32-character-minimum-token
```

### Generating Tokens

```bash
# Generate a secure token
openssl rand -hex 32
```

### Rotating Tokens

1. Generate new token
2. Update `VIBE_AUTH_TOKEN` on server
3. Restart vibeMCP service
4. Update all client configurations
5. Old token immediately becomes invalid

### No Authentication (Development Only)

For local development, you can run without auth:

```bash
# Start server without VIBE_AUTH_TOKEN
VIBE_ROOT=~/.vibe uv run vibe-mcp
```

Client config without auth:

```json
{
  "mcpServers": {
    "vibeMCP": {
      "url": "http://localhost:8080",
      "transport": "sse"
    }
  }
}
```

---

## Using with CLAUDE.md

Integrate vibeMCP with your project's `CLAUDE.md`:

```markdown
# My Project

vibe: my-project

## MCP Server

This project uses vibeMCP for centralized context.
The workspace is at `~/.vibe/my-project/`.

## Common Tasks

Before starting work:
1. Use `session_start` prompt to load context
2. Check active tasks with `list_tasks`

When creating tasks:
1. Use `tool_create_task` instead of manual file creation
2. Update status with `tool_update_task_status`

End of session:
1. Log progress with `tool_log_session`
```

---

## Example Workflows

### Starting a Work Session

```
User: "Start a session on vibeMCP"

Agent uses:
1. session_start prompt → loads full context
2. list_tasks → shows current work
3. read_doc → gets relevant task details
```

### Creating Tasks

```
User: "Break down implementing rate limiting into tasks"

Agent uses:
1. tool_create_task for each subtask
2. Tasks auto-numbered: 010, 011, 012...
3. Each task has standard format
```

### Searching Across Projects

```
User: "Find all authentication-related code"

Agent uses:
1. search query="authentication"
2. Returns results from all projects
3. Ranked by relevance, recency, importance
```

### Logging Progress

```
User: "Log today's progress"

Agent uses:
1. tool_log_session with summary
2. Creates/appends to today's session file
```

---

## Adapting Existing Commands

If you have commands like `/task-decomposer`, adapt them to use MCP tools:

### Before (direct filesystem)

```python
# Old approach
with open(f"~/.vibe/{project}/tasks/{filename}", "w") as f:
    f.write(task_content)
```

### After (MCP tools)

```python
# New approach - use tool_create_task
result = mcp.call_tool("tool_create_task", {
    "project": project,
    "title": title,
    "objective": objective,
    "steps": steps
})
```

Benefits:
- Automatic numbering
- Consistent format
- Auto-reindexing
- Works from any machine

---

## Troubleshooting

### Connection Refused

```bash
# Check if server is running
curl https://vibe.yourdomain.com/health

# Check firewall
sudo ufw status

# Check Caddy
sudo systemctl status caddy
```

### Authentication Failed

```bash
# Verify token format
echo "Token length: $(echo -n 'your-token' | wc -c)"
# Must be >= 32 characters

# Test with curl
curl -H "Authorization: Bearer your-token" \
  https://vibe.yourdomain.com/tools
```

### SSE Connection Drops

- Check client reconnection settings
- Verify Caddy proxy buffering is disabled
- Look for timeout settings

### Tools Not Appearing

```bash
# List available tools
curl -H "Authorization: Bearer your-token" \
  https://vibe.yourdomain.com/tools

# Force reindex
curl -X POST -H "Authorization: Bearer your-token" \
  https://vibe.yourdomain.com/reindex
```

### Slow Search Results

- Check database size: `ls -la ~/.vibe/index.db`
- Consider reindexing: `vibe-mcp --reindex`
- Check for very large documents

---

## Client Comparison

| Feature | Claude Code | Claude.ai | Cursor |
|---------|-------------|-----------|--------|
| Stability | Excellent | Good | Variable |
| Setup | Config file | UI | Config file |
| Auth | Headers | UI field | Headers |
| Reconnection | Auto | Auto | Manual |
| Debugging | Verbose logs | Limited | Dev tools |

**Recommendation:** Start with Claude Code CLI to verify your setup works, then configure other clients.
