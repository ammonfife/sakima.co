---
name: capture-cloud-session
description: Fetch full transcript of a claude.ai Code session by decrypting Desktop app cookies, injecting them into Playwright, navigating to the session URL, and scraping all event pages via the /v1/sessions/{id}/events API. Saves raw JSON + clean transcript to ~/clawd/data/ and registers the session in Turso. Use when user says "pull cloud session", "capture session", "scrape claude session", "get session content", "teleport session", "fetch session transcript", or provides a claude.ai/code/session_* URL.
type: workflow
---

# /capture-cloud-session

Fetch and archive a complete transcript from a `claude.ai/code/session_*` cloud session URL. Works by decrypting the Claude Desktop app's Chromium cookie store, injecting the auth cookie into a Playwright browser session, and scraping all pages of the sessions events API.

## Trigger conditions

Invoke this skill when the user:
- Provides a URL like `https://claude.ai/code/session_01YQDU3WWKQtc46AUu95K8Rp`
- Says "pull cloud session", "capture session", "get session transcript", "teleport session", "fetch this session"
- Mentions a `session_01*` ID they want to read

---

## Prerequisites check

Before starting, verify:
1. `~/clawd/venv/` exists and has `cryptography` installed
2. `~/Library/Application Support/Claude/Cookies` exists (Desktop app must have been run at least once)
3. Playwright MCP is connected (tools starting with `mcp__plugin_playwright_playwright__` are available)

```bash
~/clawd/venv/bin/python3 -c "from cryptography.hazmat.primitives.ciphers import Cipher; print('ok')"
ls "~/Library/Application Support/Claude/Cookies" 2>/dev/null && echo "cookie db ok"
```

If the Desktop app cookie DB is missing: tell the user to open Claude Desktop and log in at least once.

---

## Step 1 — Parse the session ID from the URL

Extract the session ID from the URL or bare ID the user provided:

```python
import re
url_or_id = "<user_input>"
m = re.search(r'(session_[A-Za-z0-9]+)', url_or_id)
if not m:
    raise ValueError("No session_* ID found in input")
session_id = m.group(1)
# e.g. session_01YQDU3WWKQtc46AUu95K8Rp
```

---

## Step 2 — Decrypt Claude Desktop cookies

Run this Python block (use `~/clawd/venv/bin/python3`):

```python
import sqlite3, subprocess, hashlib, os, re, json

# --- Key derivation ---
key_raw = subprocess.run(
    ["security", "find-generic-password", "-s", "Claude Safe Storage", "-w"],
    capture_output=True, text=True
).stdout.strip()

if not key_raw:
    raise RuntimeError(
        "Claude Safe Storage key not found in keychain. "
        "Open Claude Desktop and log in, then retry."
    )

# Chromium standard: PBKDF2-SHA1, salt='saltysalt', 1003 iterations, 16 bytes
key = hashlib.pbkdf2_hmac('sha1', key_raw.encode(), b'saltysalt', 1003, dklen=16)

# --- AES-CBC decryption ---
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

def decrypt_cookie(enc: bytes) -> str:
    """Decrypt a Chromium v10 AES-CBC encrypted cookie value."""
    if not enc or enc[:3] != b'v10':
        return enc.decode('utf-8', errors='replace') if isinstance(enc, bytes) else str(enc)
    iv = b' ' * 16  # Chromium uses 16 spaces as IV
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    d = cipher.decryptor()
    raw = d.update(enc[3:]) + d.finalize()
    pad = raw[-1]  # PKCS7 padding
    raw = raw[:-pad]
    # Extract longest printable ASCII run (cookie values may be surrounded by null bytes)
    runs = re.findall(rb'[ -~]{4,}', raw)
    if runs:
        return max(runs, key=len).decode('ascii', errors='replace')
    return raw.decode('utf-8', errors='replace')

# --- Read cookie DB ---
db_path = os.path.expanduser(
    "~/Library/Application Support/Claude/Cookies"
)
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
rows = conn.execute(
    "SELECT name, encrypted_value, host_key FROM cookies WHERE host_key LIKE '%claude.ai%'"
).fetchall()
conn.close()

cookies = {}
for name, enc_val, host in rows:
    val = decrypt_cookie(enc_val)
    if val:
        cookies[name] = val

print(json.dumps({k: v[:20] + '...' for k, v in cookies.items()}))  # preview only, no secrets in output
```

Key cookies to look for:
- `sessionKey` — the primary auth cookie (`sk-ant-sid02-...`)
- `__cf_bm` — Cloudflare bot management (optional but helps)
- `intercom-session-*` — session context (optional)

**If `sessionKey` is absent or expired:** The Desktop app session has expired. Tell the user to open Claude Desktop, log in, then re-run. The cookie has a TTL.

---

## Step 3 — Inject cookies into Playwright and navigate

Use the Playwright MCP tools. Do NOT use subprocess playwright — use `mcp__plugin_playwright_playwright__*`.

### 3a. Navigate to claude.ai first (establishes the domain context)

```
mcp__plugin_playwright_playwright__browser_navigate(url="https://claude.ai")
```

Wait for the page to load (1-2 seconds).

### 3b. Inject each cookie via evaluate

For each cookie in the dict, run:

```javascript
// For sessionKey (most critical):
document.cookie = `sessionKey=<VALUE>; domain=.claude.ai; path=/; secure; SameSite=None`;

// For optional cookies:
document.cookie = `__cf_bm=<VALUE>; domain=.claude.ai; path=/; secure`;
```

Use `mcp__plugin_playwright_playwright__browser_evaluate` with the JavaScript above (one call per cookie).

### 3c. Navigate to the session URL

```
mcp__plugin_playwright_playwright__browser_navigate(
    url="https://claude.ai/code/session_{session_id}"
)
```

Wait ~3 seconds for the page to fully load and fire API requests.

---

## Step 4 — Capture the events API responses via network capture

### 4a. Check what network requests fired

```
mcp__plugin_playwright_playwright__browser_network_requests()
```

Filter results for requests containing `/events`. The URL pattern is:
```
GET https://claude.ai/api/v1/sessions/{session_id}/events?limit=1000
GET https://claude.ai/api/v1/sessions/{session_id}/events?limit=1000&after_id={uuid}
```

Note the index of each matching request.

### 4b. Get response body for each events request

```
mcp__plugin_playwright_playwright__browser_network_request(index=<N>, part="response-body")
```

This returns the JSON response. Parse it to get the event list and pagination cursor.

### 4c. Paginate if needed

Each response is a JSON array. If the page has exactly 1000 items, there are more pages.

To fetch the next page, use `mcp__plugin_playwright_playwright__browser_navigate` to:
```
https://claude.ai/api/v1/sessions/{session_id}/events?limit=1000&after_id={last_event_uuid}
```

Then capture `browser_network_requests` again and read the new response.

Repeat until a page returns fewer than 1000 events.

**Alternative pagination method** — if direct API navigation doesn't fire network events, use `browser_evaluate` to fetch directly:

```javascript
const resp = await fetch(
  '/api/v1/sessions/{session_id}/events?limit=1000&after_id={after_id}',
  {credentials: 'include'}
);
const data = await resp.json();
return JSON.stringify(data);
```

---

## Step 5 — Extract and clean the transcript

Run this Python block on the collected `all_events` list (concatenation of all pages):

```python
import json
from datetime import datetime

def extract_transcript(all_events: list) -> list:
    """Extract user + assistant turns from raw session events."""
    turns = []
    for e in all_events:
        if not isinstance(e, dict):
            continue
        event_type = e.get('type', '')
        msg = e.get('message', {})
        if not isinstance(msg, dict):
            continue
        
        # Only process user and assistant turns
        if event_type not in ('user', 'assistant'):
            # Also check message.role for some event formats
            role = msg.get('role', '')
            if role not in ('user', 'assistant'):
                continue
            event_type = role
        
        content = msg.get('content', '')
        if not content:
            continue
        
        # Normalize content: may be string or list of content blocks
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get('type') == 'text':
                        text_parts.append(block.get('text', ''))
                    elif block.get('type') == 'tool_use':
                        text_parts.append(f'[tool_use: {block.get("name", "?")}]')
                    elif block.get('type') == 'tool_result':
                        text_parts.append(f'[tool_result]')
            text = ' '.join(t for t in text_parts if t)
        else:
            text = str(content)
        
        if not text.strip():
            continue
        
        created_at = e.get('created_at', '')
        uuid = e.get('uuid', '')
        turns.append({
            'role': event_type,
            'text': text.strip(),
            'created_at': created_at,
            'uuid': uuid,
        })
    
    return turns

# After collecting all events:
turns = extract_transcript(all_events)

# Format as readable transcript
lines = []
for t in turns:
    ts = t['created_at'][:19] if t['created_at'] else ''
    role_label = 'USER' if t['role'] == 'user' else 'ASSISTANT'
    lines.append(f"[{ts}] {role_label}")
    lines.append(t['text'])
    lines.append('')

transcript_text = '\n'.join(lines)
```

---

## Step 6 — Save outputs to ~/clawd/data/

```python
import os, json
from datetime import datetime

data_dir = os.path.expanduser("~/clawd/data")
os.makedirs(data_dir, exist_ok=True)

# Save raw JSON pages
for page_num, page_events in enumerate(pages, 1):
    raw_path = os.path.join(data_dir, f"session-{session_id}-events-page{page_num}.json")
    with open(raw_path, 'w') as f:
        json.dump(page_events, f, indent=2)
    print(f"Saved raw page {page_num}: {raw_path}")

# Save clean transcript
transcript_path = os.path.join(data_dir, f"session-{session_id}-transcript.txt")
with open(transcript_path, 'w') as f:
    f.write(f"# Session: {session_id}\n")
    f.write(f"# Captured: {datetime.now().isoformat()}\n")
    f.write(f"# Total events: {len(all_events)}\n")
    f.write(f"# Total turns: {len(turns)}\n\n")
    f.write(transcript_text)
print(f"Saved transcript: {transcript_path}")
```

Output files:
- `~/clawd/data/session-{id}-events-page{N}.json` — raw API responses (one file per page)
- `~/clawd/data/session-{id}-transcript.txt` — clean human-readable conversation

---

## Step 7 — Register in Turso via bigmac-sessions

Derive a topic from the first user turn (first ~60 chars), then register:

```bash
SESSION_ID="session_01YQDU3WWKQtc46AUu95K8Rp"
TOPIC="<first 60 chars of first user message>"
TOTAL_EVENTS=<N>
TOTAL_TURNS=<M>
FIRST_DATE="<created_at of first event>"
LAST_DATE="<created_at of last event>"

bigmac-sessions add \
  --platform=claude-cloud \
  --agent=claude \
  --session-key="$SESSION_ID" \
  --topic="$TOPIC" \
  --summary="$TOTAL_EVENTS events, $TOTAL_TURNS turns. Date range: $FIRST_DATE to $LAST_DATE. Captured $(date -u +%Y-%m-%dT%H:%M:%SZ)."
```

If `bigmac-sessions add` is not available, fall back to Turso HTTP pipeline:

```bash
TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
curl -s -X POST "https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"requests\": [{\"type\": \"execute\", \"stmt\": {\"sql\": \"INSERT OR IGNORE INTO sessions (platform, agent_id, session_key, topic, summary, created_at) VALUES ('claude-cloud', 'claude', '$SESSION_ID', '$TOPIC', '$TOTAL_EVENTS events, $TOTAL_TURNS turns', datetime('now'))\"}}]}"
```

---

## Error recovery paths

**"Claude Safe Storage" key not found:**
- Open Claude Desktop → log in → wait for the app to fully load → retry.

**`sessionKey` cookie missing or blank after decryption:**
- The Desktop app may not have a fresh session. Open Claude Desktop, navigate to any conversation, then retry.
- Alternatively, check if the cookie value was stored in a different format: look for `intercom-session-*` or `_cf_clearance` which may still let partial auth work.

**Navigation to session URL shows login page:**
- The `sessionKey` TTL expired between decryption and injection. Re-run from Step 2.
- Try injecting `__cf_bm` and `_cf_clearance` cookies in addition to `sessionKey`.

**No `/events` requests appear in `browser_network_requests`:**
- The page may still be loading. Run `browser_evaluate("document.readyState")` — if not "complete", wait and try again.
- Try triggering the API call explicitly via `browser_evaluate` with a `fetch()` call (see Step 4c alternative).
- Navigate directly to `https://claude.ai/api/v1/sessions/{session_id}/events?limit=1000` — the JSON will render in the browser and appear as a network request or can be extracted from `browser_snapshot`.

**Events API returns 401 Unauthorized:**
- Session cookie expired. Re-run from Step 2 after opening Desktop app.

**Events API returns 403 Forbidden:**
- The session_id may belong to a different account. Confirm the URL is a session from Ben's account.

**Fewer events than expected (session seems truncated):**
- Confirm you fetched all pages. The last page should have < 1000 events.
- Some events types (tool_progress, system, control_request) are filtered out of the transcript — this is correct. Check total raw event count vs turn count.

---

## Output summary to report

After completing, report:
- Session ID captured
- Total raw events across all pages (e.g. "3 pages, 2,847 events total")
- Total conversation turns extracted (user + assistant only)
- Date range of the session (first to last event timestamp)
- File paths for raw JSON and transcript
- Whether Turso registration succeeded

Example:
```
Captured session_01YQDU3WWKQtc46AUu95K8Rp
- 2 pages, 1,312 events total
- 47 turns (24 user, 23 assistant)
- Date range: 2026-05-08T14:22:00Z → 2026-05-08T16:45:00Z
- Raw: ~/clawd/data/session-session_01YQDU3WWKQtc46AUu95K8Rp-events-page1.json
- Raw: ~/clawd/data/session-session_01YQDU3WWKQtc46AUu95K8Rp-events-page2.json
- Transcript: ~/clawd/data/session-session_01YQDU3WWKQtc46AUu95K8Rp-transcript.txt
- Turso: registered as claude-cloud/claude
```

---

---

## Step 6 (NEW): Save CLI-compatible JSONL → `claude --resume`

After fetching all event pages, convert the cloud events to CLI JSONL format and save it — so the session can continue in the CLI **without Playwright remote control**.

```python
import json, os, glob, re

SESSION_ID = "<session_id>"  # replace
DATA_DIR = os.path.expanduser("~/clawd/data")
CLI_PATH = os.path.expanduser(f"~/.claude/projects/-Users-benfife/{SESSION_ID}.jsonl")

# Load all captured pages
all_events = []
for p in sorted(glob.glob(f"{DATA_DIR}/session-{SESSION_ID}-events-page*.json")):
    d = json.load(open(p))
    events = d if isinstance(d, list) else d.get('events', [])
    all_events.extend(events)

# Cloud → CLI format conversion
# Cloud:  {"type":"user","message":{"role":"user","content":"..."},"created_at":"...","uuid":"..."}
# CLI:    {"role":"user","message":{"role":"user","content":"..."},"created_at":"...","uuid":"..."}
KEEP_TYPES = {'user', 'assistant', 'control_request', 'control_response', 'system'}
cli_lines = []
for e in all_events:
    if not isinstance(e, dict): continue
    t = e.get('type', '')
    if t not in KEEP_TYPES: continue  # drop rate_limit_event, env_manager_log, tool_progress noise
    msg = e.get('message', {})
    if not isinstance(msg, dict): continue
    cli_line = {
        'role': msg.get('role', t),
        'message': msg,
        'created_at': e.get('created_at', ''),
        'uuid': e.get('uuid', ''),
        'parent_tool_use_id': e.get('parent_tool_use_id'),
        'session_id': SESSION_ID,
    }
    cli_lines.append(json.dumps(cli_line))

with open(CLI_PATH, 'w') as f:
    f.write('\n'.join(cli_lines) + '\n')

print(f"Saved {len(cli_lines)} events → {CLI_PATH}")
print(f"Resume: claude --resume {SESSION_ID}")
```

**Also restore files that cloud wrote** (from `Write` tool blocks):

```python
for e in all_events:
    msg = e.get('message', {})
    for block in (msg.get('content', []) if isinstance(msg.get('content'), list) else []):
        if isinstance(block, dict) and block.get('type') == 'tool_use' and block.get('name') == 'Write':
            inp = block.get('input', {})
            path = inp.get('file_path', '')
            content = inp.get('content', '')
            if path and content and os.path.isabs(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w') as f:
                    f.write(content)
                print(f"Restored: {path}")
```

After this step:
```bash
claude --resume session_01YQDU3WWKQtc46AUu95K8Rp
# Full conversation context loaded. No browser or remote control needed.
```

### Preference order

| Method | When |
|---|---|
| `claude --resume` (this step) | **Default** — moving cloud→CLI. Full context, no browser. |
| Playwright capture (Steps 1–5) | Getting the events in the first place, OR interacting with live cloud session UI. |
| Both | Capture via Playwright, then `--resume` locally. |

---

## Related skills

- `/import-cloud-sessions` — lighter-weight: only extracts session metadata (ID, repo, model) from Desktop localStorage without fetching event content
- `/read-cli-sessions` — reads local JSONL session files for Claude Code CLI sessions (no network needed)
- `/session-archive` — full artifact bundler: git commits, files, scripts, memory, Turso writes, replay.sh
- `/bigmac-sessions` — CLI for browsing registered sessions in Turso
