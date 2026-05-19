---
name: message-poke
description: Send messages to Poke from any agent surface using the local CLI, BigMac MCP, or the direct Poke API.
---

# /message-poke — Send a Message to Poke

Send any message to Poke (Ben's AI assistant at +16504336288) from any agent or surface.
Messages are prefixed with 🤖 [BIGMAC] so Poke can distinguish API messages from Ben's SMS.
All sends are logged to BigMac Supabase `poke_messages` table.

## Two paths — use whichever works on your surface

### Path 1: poke-send CLI (preferred on local Mac)
```bash
poke-send "your message here" --agent=<your-agent-name>
```
Reads POKE_API_KEY from Turso secrets automatically.

### Path 2: BIGMAC MCP tool (any surface with MCP access)
Call the `send_poke_message` tool on the BIGMAC MCP server:
```
POST https://ammonfife-bigmac-mcp-server.hf.space/mcp
Authorization: Bearer <your-scoped-token>
{
  "jsonrpc": "2.0", "id": 1, "method": "tools/call",
  "params": { "name": "send_poke_message", "arguments": { "message": "your message" } }
}
```

### Path 3: Direct Poke API (any surface with curl/fetch)
```bash
POKE_KEY=$(bigmac-secrets get POKE_API_KEY)
curl -s -X POST "https://poke.com/api/v1/inbound/api-message" \
  -H "Authorization: Bearer $POKE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "🤖 [BIGMAC] your message here"}'
```

## When to use
- Completing a task Ben asked Poke to delegate to BIGMAC agents
- Reporting back results of long-running autonomous work
- Alerting Ben to something urgent discovered during a session
- Responding to a `message_agent` call from Poke → BIGMAC direction
- Any time an agent needs to reach Ben when he may not be in a Claude session

## Message format guidelines
- Always include `🤖 [BIGMAC]` prefix (poke-send and MCP tool add this automatically)
- Keep it short — Poke relays to Ben's phone, SMS-length is fine
- Include agent name if relevant: "🤖 [BIGMAC/bob]: ..."
- Don't repeat yourself — Poke logs all API messages, Ben can review history

## Tokens (stored in Turso secrets)
- `POKE_API_KEY` — direct Poke API access
- `MCP_TOKEN_BOB`, `MCP_TOKEN_CHLOE`, `MCP_TOKEN_CLAUDE_CODE`, etc. — scoped MCP tokens
- `bigmac-secrets get <key>` to retrieve any value

## Audit log
Every message is logged to BigMac Supabase `poke_messages`:
`SELECT * FROM poke_messages ORDER BY sent_at DESC LIMIT 20`
View live in the BIGMAC dashboard: `~/clawd/data/bigmac-dashboard.html`
