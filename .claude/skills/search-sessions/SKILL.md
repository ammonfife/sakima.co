---
name: search-sessions
description: Locate and search session logs across BigMac platforms, including local files and Turso-backed session records.
---

# search-sessions — Find Session Logs Across All BigMac Platforms

Search and locate session logs for any agent, platform, or project in the BigMac system.
Covers all local file paths and Turso database queries.

---

## Local Session File Paths

### Claude Code CLI
```
~/.claude/projects/<project-slug>/<session-id>.jsonl
~/.claude/sessions/<session-id>.json
```
Project slugs mirror the filesystem path with `/` → `-`:
- `/Users/benfife` → `-Users-benfife`
- `/Users/benfife/clawd` → `-Users-benfife-clawd`

List all CLI sessions:
```bash
ls -lt ~/.claude/projects/*/*.jsonl | head -20
ls -lt ~/.claude/sessions/*.json | head -20
```

Search session content:
```bash
grep -r "keyword" ~/.claude/projects/ --include="*.jsonl" -l
```

### Claude Desktop (App)
```
~/Library/Application Support/Claude/claude-code-sessions/<account-uuid>/<session>.jsonl
```
```bash
ls -lt ~/Library/Application\ Support/Claude/claude-code-sessions/5345be5b-9c46-453f-b927-1ae32b30699e/
```

### Cowork / Local Agent Mode Sessions
```
~/Library/Application Support/Claude/local-agent-mode-sessions/<account-uuid>/<org-uuid>/
├── local_<session-uuid>/        # per-chat sessions (ephemeral)
│   ├── audit.jsonl
│   └── .claude/sessions/*.json
├── local_ditto_<org-uuid>/      # persistent Cowork agent
│   └── .claude/sessions/*.json
└── agent/                       # ditto agent workspace
```
```bash
ls ~/Library/Application\ Support/Claude/local-agent-mode-sessions/5345be5b-9c46-453f-b927-1ae32b30699e/490d42cb-5811-4685-bad6-03d9e74d651f/
```

### OpenClaw Agents
```
~/.openclaw/agents/<agent-name>/sessions/
~/.openclaw/state/agents/<agent-name>/
```
Agent names: main, 007, bob, chloe, computer, drj, garcia, lance, moneypenny, q, vandam, watchdog
```bash
ls ~/.openclaw/agents/*/sessions/ 2>/dev/null
```

### Gemini
```
~/.gemini/tmp/<session-dir>/chats/session-*.json
```
```bash
ls -lt ~/.gemini/tmp/*/chats/session-*.json 2>/dev/null | head -20
```

### Grok
```
~/.grok/sessions/ or ~/.grok_assistant/
```
```bash
find ~/.grok ~/.grok_assistant -name "*.json" 2>/dev/null | head -20
```

### Codex
```
~/CodexSessions/
~/.codex/
```
```bash
ls -lt ~/CodexSessions/ 2>/dev/null | head -20
find ~/.codex -name "*.json" 2>/dev/null | head -20
```

### Clawd / BigMac Agent Workspaces
```
~/clawd/agents/<agent>/          # agent workspace root
~/clawd-<agent>/                 # alt workspace pattern
~/clawd-Claude/                  # Claude's consolidated workspace
```
```bash
ls ~/clawd/agents/
ls ~/clawd-*/
```

---

## Turso Database Queries

### Connection
```bash
# Token from keychain
TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
DB="https://bigmac-ammonfife.aws-us-west-2.turso.io"
HEADER="Authorization: Bearer $TOKEN"
```

Or use the bigmac CLI:
```bash
bigmac-sessions list --agent <name>
bigmac-sessions list --platform claude-code
```

### Sessions Table — All Columns
```
agent_id | platform | session_key | created_at | active
conversation_log_path | created_by | created_by_machine
```

### Common Turso Queries (use via node or curl/Hrana)

```javascript
// ── Via node (fastest) ────────────────────────────────────────────────
import { execSync } from 'child_process';
const TOKEN = execSync('security find-generic-password -a bigmac -s turso-bigmac-token -w').toString().trim();
const DB = 'https://bigmac-ammonfife.aws-us-west-2.turso.io';

async function q(sql, args=[]) {
  const r = await fetch(`${DB}/v2/pipeline`, {
    method:'POST',
    headers:{'Authorization':`Bearer ${TOKEN}`,'Content-Type':'application/json'},
    body: JSON.stringify({requests:[{type:'execute',stmt:{sql,args:args.map(v=>({type:'text',value:String(v)}))}},{type:'close'}]})
  });
  const d = await r.json();
  const {cols,rows} = d.results[0].response.result;
  return rows.map(row=>{const o={};cols.forEach((c,i)=>o[c.name]=row[i].value);return o;});
}

// Recent sessions by platform
await q(`SELECT agent_id,platform,session_key,datetime(created_at/1000,'unixepoch') as dt
         FROM sessions ORDER BY created_at DESC LIMIT 20`);

// Sessions for a specific agent
await q(`SELECT * FROM sessions WHERE agent_id=? ORDER BY created_at DESC LIMIT 10`, ['garcia']);

// Sessions for a specific platform
await q(`SELECT * FROM sessions WHERE platform=? ORDER BY created_at DESC LIMIT 20`, ['gemini']);

// Search memory by keyword
await q(`SELECT agent_id,date,substr(content,1,200) as preview
         FROM memory WHERE content LIKE ? AND inactive_date IS NULL
         ORDER BY date DESC LIMIT 10`, ['%keyword%']);

// Get full memory for agent + date
await q(`SELECT content FROM memory WHERE agent_id=? AND date=? AND inactive_date IS NULL`,
        ['main','2026-04-11']);

// Recent memory across all agents
await q(`SELECT agent_id,date,length(content) as bytes
         FROM memory WHERE inactive_date IS NULL
         ORDER BY date DESC LIMIT 20`);

// Search soul (workspace docs) by key
await q(`SELECT agent_id,key,substr(content,1,100) as preview
         FROM soul WHERE valid_until IS NULL AND key LIKE ?`, ['%AGENTS%']);

// All skills in Turso
await q(`SELECT DISTINCT skill_name FROM skills_current ORDER BY skill_name`);
```

### bigmac-sessions CLI Reference
```bash
bigmac-sessions list                          # all sessions
bigmac-sessions list --agent main             # by agent
bigmac-sessions list --platform claude-code   # by platform
bigmac-sessions list --since 2026-04-01       # by date
bigmac-sessions get <session-key>             # specific session
```

---

## Quick Search Recipes

### "Find all Claude Code sessions from today"
```bash
find ~/.claude/projects -name "$(date +%Y-%m-%d)*.jsonl" 2>/dev/null
ls -lt ~/.claude/projects/*/*.jsonl | awk '{print $6,$7,$8,$9}' | head -20
```

### "Find what session talked about X"
```bash
grep -r "X" ~/.claude/projects/ --include="*.jsonl" -l 2>/dev/null
grep -r "X" ~/.gemini/tmp/ --include="*.json" -l 2>/dev/null
```

### "Find OpenClaw session logs for agent garcia"
```bash
ls ~/.openclaw/agents/garcia/sessions/ 2>/dev/null
cat ~/.openclaw/agents/garcia/sessions/*.json 2>/dev/null | jq '.messages[-3:]'
```

### "Which session has the most recent memory for agent bob?"
```bash
# Turso query — run inline with node
node -e "
const {execSync}=require('child_process');
const t=execSync('security find-generic-password -a bigmac -s turso-bigmac-token -w').toString().trim();
fetch('https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline',{method:'POST',headers:{'Authorization':'Bearer '+t,'Content-Type':'application/json'},body:JSON.stringify({requests:[{type:'execute',stmt:{sql:'SELECT date,length(content) bytes FROM memory WHERE agent_id=\"bob\" AND inactive_date IS NULL ORDER BY date DESC LIMIT 5',args:[]}},{type:'close'}]})}).then(r=>r.json()).then(d=>console.log(JSON.stringify(d.results[0].response.result.rows,null,2)));
"
```

---

## Platform → Turso agent_id Mapping

| Platform | agent_id in Turso |
|---|---|
| Claude Code CLI (main project) | `claude` |
| Claude Code CLI (per-agent workspace) | `main`, `bob`, `garcia`, etc. |
| Claude Desktop | `claude` |
| Cowork / local agent | `claude` |
| OpenClaw main | `main` |
| OpenClaw agents | `007`, `bob`, `chloe`, `computer`, `drj`, `garcia`, `lance`, `moneypenny`, `q`, `vandam`, `watchdog` |
| Gemini (named agent dir) | agent name if matches BigMac roster, else `gemini` |
| Grok | `grok` |
| Codex | `codex` |
