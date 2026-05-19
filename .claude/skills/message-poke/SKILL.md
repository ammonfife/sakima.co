---
name: message-poke
description: Send messages to Poke, Mog, or M — each agent has a distinct phone number. Use for cross-agent communication, task handoffs, urgent alerts, and status updates to Ben.
---

# /message-poke — Send a Message to Poke, Mog, or M

Three agents each have a distinct iMessage/SMS number. Route messages to the right one.

## Target agents and phone numbers

| Target | Number | Role | When to use |
|--------|--------|------|-------------|
| **poke** | +16504336288 | Primary BIGMAC iMessage bridge — GM of lkup.info + coin business | Task completion, urgent alerts to Ben, coin business ops, most general BIGMAC updates |
| **mog** | +16502488932 | lkup.info + BIGMAC field executor (cloud agent, gptagency.ai) | lkup.info work handoffs, enrichment pipeline updates, cloud task results |
| **M** | +16502835397 | Main orchestrator (same persona as BIGMAC M / the "big mac") | High-level coordination, cross-project orchestration, BIGMAC-wide status |

---

## Path 1: poke-send CLI (preferred on local Mac)
```bash
poke-send "your message here" --agent=<your-name> --to=poke   # default
poke-send "your message here" --agent=<your-name> --to=mog
poke-send "your message here" --agent=<your-name> --to=M
```
Reads POKE_API_KEY / MOG_API_KEY / M_API_KEY from Turso secrets automatically.

## Path 2: BIGMAC MCP tool (any surface with MCP access)
```
POST https://ammonfife-bigmac-mcp-server.hf.space/mcp
Authorization: Bearer <your-scoped-token>
{
  "jsonrpc": "2.0", "id": 1, "method": "tools/call",
  "params": {
    "name": "send_poke_message",
    "arguments": { "message": "your message", "target": "poke" }
  }
}
```
`target` values: `"poke"` (default), `"mog"`, `"M"`

## Path 3: Direct Poke API (any surface with curl/fetch)
```bash
# Routing map
POKE_NUMBER="+16504336288"
MOG_NUMBER="+16502488932"
M_NUMBER="+16502835397"

# Get API key from Turso
POKE_KEY=$(bigmac-secrets get POKE_API_KEY)

# Send to poke (default)
curl -s -X POST "https://poke.com/api/v1/inbound/api-message" \
  -H "Authorization: Bearer $POKE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "🤖 [BIGMAC] your message here"}'
```

## Path 4: From .poke repo (bin/msg)
```bash
# Sends to poke by default
bash ~/github/ammonfife/.poke/bin/msg poke "your message"
```

---

## When to message which agent

**→ poke** (most common):
- Task Ben delegated via poke that BIGMAC agents just completed
- Urgent alerts Ben needs to see on his phone
- Coin business pipeline failures (PCGS, enrichment, Whatnot)
- P0 todos filed, domain/webhook failures

**→ mog**:
- lkup.info branch work handoffs
- Enrichment pipeline results or blockers
- When Ben is actively in a mog session and needs an update

**→ M**:
- High-level cross-project coordination
- BIGMAC-wide status that Main needs to see
- When orchestration decisions need to route through the M persona

---

## Message format guidelines
- Always include agent tag: `🤖 [BIGMAC/<your-agent>]:`
- SMS-length is fine — Poke/Mog relay to Ben's phone
- Don't repeat yourself — all API messages are logged
- For urgent: prefix with `⚠️` or `🔴`

## Tokens (stored in Turso secrets)
- `POKE_API_KEY` — direct Poke API access
- `MCP_TOKEN_BOB`, `MCP_TOKEN_CHLOE`, `MCP_TOKEN_CLAUDE_CODE`, etc. — scoped MCP tokens
- `bigmac-secrets get <key>` to retrieve any value

## Audit log
Every message is logged to BigMac Supabase `poke_messages`:
```sql
SELECT * FROM poke_messages ORDER BY sent_at DESC LIMIT 20
```
