---
name: import-cloud-sessions
description: Extract and register cloud (server-side) Claude sessions from Claude Desktop localStorage into Turso and sessions-index.json. Use when you need to find a teleport session, audit active cloud sessions, or ensure cloud sessions appear in the BigMac session index alongside local JSONL sessions.
type: reference
---

> [!IMPORTANT]
> **Cross-Platform Skill**: This skill is shared across Claude Code, OpenClaw, Gemini, and Codex.
> Before executing, check the "Platform Blocks" below. If your current platform is missing, or if a command fails, **UPDATE THIS SKILL** with a platform-specific block.

# import-cloud-sessions

Imports cloud sessions (`session_01XXX` format) from the Claude Desktop app's localStorage into the BigMac session tracking system (Turso + `~/clawd/data/sessions-index.json`).

## Background

Cloud sessions are server-side conversations that live on Anthropic's servers. Unlike local Cowork sessions (`local_UUID`) or CLI sessions (JSONL files), cloud sessions have **no local transcript**. Claude Desktop stores only metadata about them in its Electron localStorage (LevelDB):

- **Repo/branch context**: `_<sessionId>:<owner>/<repo>:<branch>:<ref>` key
- **Model preference**: `sticky-model-selector-session_<id>` key
- **Group assignment**: sidebar state JSON with `customGroupAssignments`
- **Tool acknowledgments**: tool use IDs that have been acknowledged in the UI

The `--teleport` CLI flag reconnects to a cloud session by its ID:
```bash
claude --teleport session_01XhgiDvcynud3MQ6hoeRVmB
```

## When to invoke

- User mentions `--teleport` or a `session_01XXX` ID they can't find locally
- You need to audit which cloud sessions are active on the Desktop
- After a long Desktop session to register it in Turso before it becomes stale
- As part of `/exit-protocol` when the session used the Desktop app

## localStorage path

```
~/Library/Application Support/Claude/Local Storage/leveldb/
```

Files of interest: `*.ldb` (stable data) and `*.log` (active writes).

## Step 1 — Extract all cloud session IDs

### If you are Claude Code / CLI
```bash
strings "/Users/benfife/Library/Application Support/Claude/Local Storage/leveldb/"*.ldb \
        "/Users/benfife/Library/Application Support/Claude/Local Storage/leveldb/"*.log \
  2>/dev/null \
  | grep -oE 'session_01[A-Za-z0-9]+' \
  | sort -u
```

### If you are OpenClaw / Gemini / Codex (no macOS `strings`)
```bash
cat "/Users/benfife/Library/Application Support/Claude/Local Storage/leveldb/"*.log \
    "/Users/benfife/Library/Application Support/Claude/Local Storage/leveldb/"*.ldb \
  2>/dev/null \
  | tr -cs '[:print:]' '\n' \
  | grep -oE 'session_01[A-Za-z0-9]+' \
  | sort -u
```

## Step 2 — Extract metadata for each session

```bash
# Repo context (format: _<id>:<owner>/<repo>:<branch>:<ref>)
strings "/Users/benfife/Library/Application Support/Claude/Local Storage/leveldb/"*.ldb \
        "/Users/benfife/Library/Application Support/Claude/Local Storage/leveldb/"*.log \
  2>/dev/null | grep -oE '_[A-Za-z0-9]+:[a-zA-Z0-9._/-]+:[a-zA-Z0-9._/-]+:[a-zA-Z0-9._/-]+'

# Group assignments (JSON blob containing customGroupAssignments)
strings "/Users/benfife/Library/Application Support/Claude/Local Storage/leveldb/"*.log \
  2>/dev/null | grep -o '"customGroupAssignments":{[^}]*}'
```

## Step 3 — Run the automated sync script

The canonical implementation lives at:
```
~/clawd/scripts/sync-cloud-sessions.mjs
```

Run it directly:
```bash
~/.nvm/versions/node/v22.20.0/bin/node ~/clawd/scripts/sync-cloud-sessions.mjs
```

Or trigger it as part of the full session sync (already wired into the Stop hook):
```bash
~/.nvm/versions/node/v22.20.0/bin/node ~/clawd/scripts/sync-external-sessions.mjs
```

The script:
1. Parses all `.ldb` and `.log` files in localStorage
2. Extracts unique `session_01XXX` IDs
3. Correlates metadata (repo context, group name)
4. Registers new sessions in Turso under platform `claude-cloud`
5. Updates `~/clawd/data/sessions-index.json` (auto-committed to git by `auto-sync-and-commit.sh`)

## Step 4 — Verify registration

```bash
# Check Turso for newly registered cloud sessions
TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
curl -s -X POST "https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"requests":[{"type":"execute","stmt":{"sql":"SELECT session_key, agent_id, conversation_log_path FROM sessions WHERE platform = '\''claude-cloud'\'' ORDER BY created_at DESC LIMIT 20","args":[]}}]}' \
  | python3 -c "import json,sys; rows=json.load(sys.stdin)['results'][0]['response']['result']['rows']; [print(r[0]['value'][:50], '|', r[1]['value'], '|', r[2]['value'][:40]) for r in rows]"
```

## Key facts

| Field | Value |
|---|---|
| Platform name in Turso | `claude-cloud` |
| Session ID format | `session_01[A-Za-z0-9]+` |
| localStorage path | `~/Library/Application Support/Claude/Local Storage/leveldb/` |
| No local transcript | Cloud sessions have no JSONL — conversation is on Anthropic servers |
| Repo context format | `_<id>:<owner>/<repo>:<branch>:<ref>` |
| `--teleport` reconnects | `claude --teleport <session_id>` |
| Sync script | `~/clawd/scripts/sync-cloud-sessions.mjs` (also inside `sync-external-sessions.mjs`) |
| sessions-index.json | `~/clawd/data/sessions-index.json` (git-tracked, auto-committed) |

## Fallback path for agents without Turso access

If Turso or MCP is unavailable, read `~/clawd/data/sessions-index.json` directly — it is updated every Stop hook and auto-committed to the `clawd` git repo. Filter for `"platform":"claude-cloud"` entries.

## Pulling conversation content via BigMac scraper extension

Cloud sessions have no local transcript, but the BigMac GTM extension (`~/bigmac-state/gtm-hackathon/chrome-extension/`) can intercept the SSE stream from claude.ai using a `window.fetch` patch in a content script.

### How it works

The extension has `<all_urls>` host permissions and a `content.js` that runs on any page. Adding a `claude-capture.js` content script at `document_start` on `*://claude.ai/*` lets you:

1. Patch `window.fetch` before the page's own code runs
2. Intercept calls to `api2.anthropic.com/v1/messages` (the SSE stream)
3. `tee()` the ReadableStream so the app is unaffected
4. Decode SSE chunks (`data: {...}`) and accumulate the full message
5. Post the completed turn to Turso via the MCP integration layer (`localhost:3000`) or directly via the Turso HTTP pipeline

### Content script to add: `claude-capture.js`

```javascript
// Runs at document_start on claude.ai — patches fetch before app loads
(function() {
  const _fetch = window.fetch;
  window.fetch = async function(input, init) {
    const url = typeof input === 'string' ? input : input?.url ?? '';
    const isStream = url.includes('anthropic.com') && url.includes('messages');
    
    const response = await _fetch.apply(this, arguments);
    if (!isStream) return response;

    // Tee the SSE stream — app gets [0], we read [1]
    const [appStream, captureStream] = response.body.tee();
    captureSSE(captureStream, url);
    return new Response(appStream, {
      status: response.status,
      headers: response.headers,
    });
  };

  async function captureSSE(stream, url) {
    const reader = stream.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let sessionId = window.location.pathname.split('/').pop() || 'unknown';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // Parse SSE lines
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (data === '[DONE]') continue;
          try {
            const parsed = JSON.parse(data);
            // Only forward content_block_delta events (actual text)
            if (parsed.type === 'content_block_delta' && parsed.delta?.text) {
              chrome.runtime.sendMessage({
                action: 'captureClaudeChunk',
                sessionId,
                text: parsed.delta.text,
                timestamp: Date.now(),
              });
            }
          } catch {}
        }
      }
      // Signal turn complete
      chrome.runtime.sendMessage({ action: 'captureClaudeTurnDone', sessionId });
    } catch (e) {
      console.debug('[BigMac capture] stream error', e);
    }
  }
})();
```

### manifest.json additions

```json
{
  "content_scripts": [
    {
      "matches": ["*://claude.ai/*"],
      "js": ["claude-capture.js"],
      "run_at": "document_start",
      "world": "MAIN"
    }
  ]
}
```

**`"world": "MAIN"` is required** — without it, content scripts run in an isolated world and cannot patch `window.fetch` on the page.

### background.js additions

```javascript
// Accumulate chunks per session, flush to Turso on turn done
const sessionBuffers = new Map();

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.action === 'captureClaudeChunk') {
    const buf = sessionBuffers.get(msg.sessionId) ?? '';
    sessionBuffers.set(msg.sessionId, buf + msg.text);
  }
  if (msg.action === 'captureClaudeTurnDone') {
    const text = sessionBuffers.get(msg.sessionId) ?? '';
    sessionBuffers.delete(msg.sessionId);
    if (text) flushToTurso(msg.sessionId, text);
  }
});

async function flushToTurso(sessionId, text) {
  const TOKEN = await getStoredToken(); // from chrome.storage
  await fetch('https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline', {
    method: 'POST',
    headers: { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ requests: [{ type: 'execute', stmt: {
      sql: 'INSERT INTO sessions (agent_id, platform, session_key, created_at, active, created_by, created_by_platform, created_by_machine, created_by_combined, as_of_date, conversation_log_path) VALUES (?,?,?,?,0,?,?,?,?,date(\'now\'),?)',
      args: [
        {type:'text',value:'claude'},
        {type:'text',value:'claude-cloud-capture'},
        {type:'text',value:`cloud_${sessionId}`},
        {type:'integer',value:Date.now()},
        {type:'text',value:'extension'},
        {type:'text',value:'extension'},
        {type:'text',value:'extension'},
        {type:'text',value:`captured:${text.slice(0,200)}`},
      ]
    }}]}),
  });
}
```

### Implementation location

The capture script belongs in both extension copies:
- `~/bigmac-state/gtm-hackathon/chrome-extension/claude-capture.js`
- `~/bigmac-state/easy-event-planner/chrome-extension/claude-capture.js`

Load unpacked from either path in Chrome → the extension will then intercept all claude.ai SSE streams and register them in Turso under platform `claude-cloud-capture`.

## Last updated

2026-05-08 — added after discovering `session_01XhgiDvcynud3MQ6hoeRVmB` (lkup.info PR #39 work) in Desktop localStorage. Repo context key format reverse-engineered from live LevelDB inspection.
