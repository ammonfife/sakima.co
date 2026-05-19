---
name: use-bigmac-mcp
description: Use the BigMac MCP server for shared knowledge, todos, coordination, messaging, and violation logging across agents.
---

# BIGMAC MCP — Cross-Agent Knowledge & Coordination

**What this is:** Access to the BIGMAC MCP server via `mcp__bigmac__*` tools — the central nervous system for all BIGMAC agents. 22 tools for reading/writing shared knowledge (facts, policies, assumptions, opinions), managing todos, messaging other agents or Ben, searching the knowledge base, and autonomous task execution.

**Server:** `https://ammonfife-bigmac-mcp-server.hf.space/mcp`
**Auth:** Claude Code token (retrieved from `bigmac-secrets` vault)
**Database:** `libsql://bigmac-ammonfife.aws-us-west-2.turso.io`
**Bridge:** HTTP-to-stdio via `~/bin/bigmac-mcp-wrapper.sh` + `~/clawd/scripts/mcp-http-bridge.mjs`

## When to Use

Use BIGMAC MCP tools when you need to:

- **Search knowledge** — before claiming you don't know something, search the BIGMAC knowledge base
- **Log important decisions** — facts, policies, assumptions that other agents need to know
- **Coordinate work** — check open todos, claim tasks, mark tasks complete
- **Message other agents** — bob, lance, q, computer, main, chloe, gemini
- **Message Ben** — async notifications, alerts, results (fire-and-forget)
- **Track violations** — log Garcia violations or policy breaches
- **Captain's log** — cross-agent conversational index for major milestones

## Available Tools (22)

All BIGMAC MCP tools are prefixed with `mcp__bigmac__` in Claude Code.

### Read Tools (7)

#### `mcp__bigmac__search_knowledge`
Search BIGMAC knowledge — facts, policies, memory, opinions, todos.

#### `mcp__bigmac__get_todos`
Get open todos from BIGMAC. Filter by tag or assignee.

#### `mcp__bigmac__semantic_search`
Semantic search across all BIGMAC knowledge using knowledge-search CLI.

#### `mcp__bigmac__get_system_status`
Get BIGMAC system status — open todos, recent sessions, violations in last 24h.

#### `mcp__bigmac__get_bigmac_status` (ADMIN)
Full BIGMAC status snapshot — admin tokens only.

#### `mcp__bigmac__refresh_agent_context`
Refresh and return AGENT_CONTEXT.md for a BIGMAC agent.

#### `mcp__bigmac__list_registered_agents` (ADMIN)
List all registered MCP agents.

### Write Tools (8)

#### `mcp__bigmac__add_todo`, `mcp__bigmac__update_todo`, `mcp__bigmac__complete_todo`
Todo management integrated with TaskCreate/TaskCompleted hooks.

#### `mcp__bigmac__add_fact`, `mcp__bigmac__add_assumption`, `mcp__bigmac__add_opinion`, `mcp__bigmac__add_policy`
Knowledge base writes with confidence scoring and tagging.

#### `mcp__bigmac__add_captains_log`
Cross-agent conversational index for milestones.

#### `mcp__bigmac__log_violation`
Behavior violation tracking.

### Action Tools (7)

#### `mcp__bigmac__message_agent`, `mcp__bigmac__message_ben`, `mcp__bigmac__send_poke_message`
Cross-agent messaging and notifications.

## Hook Integration

**TaskCreated hook** → `mcp__bigmac__add_todo` (automatic)
**TaskCompleted hook** → `mcp__bigmac__complete_todo` (automatic)

## Related

- **Full docs:** `~/.gemini/BIGMAC_MCP.md`
- **Architecture:** `~/clawd/AGENTS.md`
- **MCP Protocol:** https://modelcontextprotocol.io/
