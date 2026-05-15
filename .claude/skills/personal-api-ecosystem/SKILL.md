---
name: personal-api-ecosystem
description: Access personal data (messages, memory, projects, relationships) via REST API or MCP servers with FTS5 full-text search. Use when you need to query iMessage history, search conversations, check project status, analyze relationship health, or access personal memory/notes. Supports both direct API calls and Model Context Protocol integration.
---

# Personal API Ecosystem

Access unified personal data through REST API endpoints or MCP servers. All data is stored in Turso with FTS5 full-text search for fast queries.

## Quick Start

**API Gateway**: `http://localhost:3000/api/v1`  
**Status**: Check if running with `curl http://localhost:3000/health`

If not running, start it:

```bash
cd /Users/benfife/clawd/agents/garcia/projects/personal-api-ecosystem/api-gateway
npm run dev
```

## What's Available

### 1. Messages (iMessage History)

- **142,589 messages** indexed with FTS5 full-text search
- Search conversations, analyze patterns, get contact stats
- **Performance**: 1-3x faster than LIKE queries

### 2. Memory (Personal Notes)

- Daily memory files (`memory/YYYY-MM-DD.md`)
- Long-term curated memory (`MEMORY.md`)
- Session history and logs

### 3. Projects (Git Repositories)

- 30+ repositories tracked
- Status, health, commits, branches
- Identifies stale repos and uncommitted changes

### 4. Relationships (Contact Analysis)

- 50+ contacts with message statistics
- Relationship health scoring
- Outreach suggestions based on patterns

## API Endpoints

### Messages

**Recent messages:**

```bash
GET /api/v1/messages/recent?limit=10&hours=24
```

**Search with FTS5 (fast!):**

```bash
GET /api/v1/messages/search?query=hello&limit=20
```

**Conversation with contact:**

```bash
GET /api/v1/messages/conversation?contact=John&limit=50
```

**Contact statistics:**

```bash
GET /api/v1/messages/stats
```

### Memory

**Search memory:**

```bash
GET /api/v1/memory/search?query=database
```

**Recent entries:**

```bash
GET /api/v1/memory/recent?days=7
```

### Projects

**List all projects:**

```bash
GET /api/v1/projects
```

**Project health check:**

```bash
GET /api/v1/projects/health
```

**Specific project status:**

```bash
GET /api/v1/projects/:name
```

### Relationships

**List contacts:**

```bash
GET /api/v1/relationships
```

**Relationship health overview:**

```bash
GET /api/v1/relationships/health
```

**Outreach suggestions:**

```bash
GET /api/v1/relationships/outreach
```

**Specific contact:**

```bash
GET /api/v1/relationships/:contact
```

## MCP Servers

Four MCP servers provide tool-based access for AI agents:

**Location**: `/Users/benfife/clawd-garcia/projects/personal-api-ecosystem/mcp-servers/`

### 1. Messages MCP

- `search_messages` - FTS5 full-text search
- `get_conversation` - Full conversation history
- `analyze_relationship` - Message frequency patterns

### 2. Memory MCP

- `search_memory` - Semantic search across all memory
- `add_memory` - Add new entry
- `update_memory` - Update existing entry

### 3. Projects MCP

- `get_project_status` - Git status, branches, uncommitted changes
- `get_project_commits` - Recent commit history
- `check_project_health` - Health check for all projects

### 4. Relationships MCP

- `get_contact_context` - Full context for specific contact
- `suggest_outreach` - Outreach suggestions based on patterns
- `check_relationship_health` - Identify relationships needing attention

### MCP Configuration

Add to `~/Library/Application Support/Codex/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "personal-messages": {
      "command": "node",
      "args": [
        "/Users/benfife/clawd/agents/garcia/projects/personal-api-ecosystem/mcp-servers/messages/dist/index.js"
      ],
      "env": { "API_BASE": "http://localhost:3000/api/v1" }
    },
    "personal-memory": {
      "command": "node",
      "args": [
        "/Users/benfife/clawd/agents/garcia/projects/personal-api-ecosystem/mcp-servers/memory/dist/index.js"
      ],
      "env": { "API_BASE": "http://localhost:3000/api/v1" }
    },
    "personal-projects": {
      "command": "node",
      "args": [
        "/Users/benfife/clawd/agents/garcia/projects/personal-api-ecosystem/mcp-servers/projects/dist/index.js"
      ],
      "env": { "API_BASE": "http://localhost:3000/api/v1" }
    },
    "personal-relationships": {
      "command": "node",
      "args": [
        "/Users/benfife/clawd/agents/garcia/projects/personal-api-ecosystem/mcp-servers/relationships/dist/index.js"
      ],
      "env": { "API_BASE": "http://localhost:3000/api/v1" }
    }
  }
}
```

## FTS5 Full-Text Search

Messages are indexed with SQLite FTS5 for fast search:

**Status**: 142,589 messages fully indexed with auto-sync triggers

**Search syntax:**

- Simple: `hello` - matches messages containing "hello"
- Multiple terms: `hello meeting` - matches messages with both terms
- OR operator: `hello OR hi` - matches either term
- Phrase: `"exact phrase"` - matches exact phrase
- Wildcard: `hel*` - matches "hello", "help", etc.

**Performance**: 1-3x faster than LIKE queries depending on query selectivity.

**Auto-sync**: Triggers automatically maintain FTS index on INSERT/UPDATE/DELETE.

## Common Use Cases

### Find a conversation

```bash
curl "http://localhost:3000/api/v1/messages/search?query=meeting+tomorrow&limit=10"
```

### Check who needs outreach

```bash
curl "http://localhost:3000/api/v1/relationships/outreach"
```

### Find stale projects

```bash
curl "http://localhost:3000/api/v1/projects/health" | jq '.[] | select(.status == "stale")'
```

### Search your memory

```bash
curl "http://localhost:3000/api/v1/memory/search?query=database+migration"
```

## Technical Details

**Database**: Turso (libSQL)  
**Location**: `libsql://personaldatastore-efifneb.aws-us-west-2.turso.io`  
**Credentials**: Stored in `projects/personal-api-ecosystem/.env`

**Project location**: `/Users/benfife/clawd/agents/garcia/projects/personal-api-ecosystem/`

**Documentation**: See `references/endpoints.md` for complete API reference.

## Troubleshooting

**API not responding?**

```bash
# Check if running
curl http://localhost:3000/health

# Restart if needed
cd /Users/benfife/clawd-garcia/projects/personal-api-ecosystem/api-gateway
npm run dev
```

**Search not working?**

- Verify FTS5 table populated: Check task status in `/Users/benfife/clawd-q/agi-tasks.json`
- Should show "fts5_implementation_complete" in completed items

**MCP servers not working?**

- Verify API gateway is running first
- Check MCP config path and rebuild if needed: `cd mcp-servers/messages && npm run build`
