---
name: disable-openclaw
description: Temporarily disable openclaw — stops the gateway process, unloads all 5 openclaw-related launchctl entries (the main GUI app + token-enforcer + auth-rotation + autocommit-workspaces + screenshot-watcher), comments out the gateway-watchdog cron line so it stops auto-restarting every 2 minutes, and backs up everything needed for /enable-openclaw to reverse it in one command. Idempotent — safe to run when already disabled. Use when you need to stop Gemini billing from openclaw, debug gateway state, or pause the whole BIGMAC agent mesh without deleting anything.
user-invocable: true
---

# /disable-openclaw

Cleanly shut down openclaw and everything that keeps it running, so the gateway stays down until `/enable-openclaw` brings it back. Used when you need to stop the BIGMAC agent mesh for cost reasons (Gemini API billing), debugging, or clean-state testing.

## Hard rules (NEVER violate)

1. **Back up BEFORE you break.** Crontab state + launchctl inventory + running-process list get captured to `~/.openclaw/disable-state/` before any change. `/enable-openclaw` reads these to reverse everything.
2. **Idempotent.** If already disabled (no gateway process, no port 1492 listener, cron already commented, launchctl already booted out), print a message and exit 0 without re-backing-up — do NOT clobber the existing backup with an empty one.
3. **Comment cron BEFORE killing the gateway.** Otherwise the watchdog can fire mid-operation and fight the shutdown.
4. **Graceful SIGTERM first, SIGKILL only if SIGTERM fails.** Any in-flight DB writes or Turso syncs should be allowed to complete. SIGKILL severs them mid-operation.
5. **Do not delete `/Applications/OpenClawGateway.app`.** Disabling = processes down, bundle untouched. `/enable-openclaw` re-opens the .app to restart.
6. **Do not touch the BIGMAC_OPENCLAW Google API key.** This skill stops the gateway that calls Gemini; it does not revoke credentials. That's a separate concern (and more destructive to reverse).
7. **Verify with a 130-second wait** before declaring success. The gateway-watchdog runs every 2 min, so a 130-second wait guarantees at least one cron tick passed and nothing restarted.

## State directory layout

```
~/.openclaw/disable-state/
  crontab.backup            ← original crontab (6 lines typically)
  launchctl-before.txt      ← launchctl output for openclaw entries pre-disable
  processes-before.txt      ← pgrep output pre-disable
  disabled-at.txt           ← ISO timestamp of when disable was run
  history/
    <YYYY-MM-DDTHH-MM-SSZ>/ ← any prior disable state gets archived here
```

If a prior disable state exists when this skill runs (e.g. Ben ran disable, then re-enabled, then ran disable again), the old state moves to `history/<timestamp>/` before the new state is captured. That way `/enable-openclaw` always reads "the most recent disable" from the top-level path.

## Step 0 — Idempotency check

```bash
GATEWAY_PID=$(pgrep -f "openclaw-gateway" 2>/dev/null | head -1)
PORT_LISTENER=$(lsof -iTCP:1492 -sTCP:LISTEN 2>/dev/null | grep -v COMMAND | head -1)
CRON_ACTIVE=$(crontab -l 2>/dev/null | grep -E "^\*/2 \* \* \* \* .*gateway-watchdog" | head -1)

if [ -z "$GATEWAY_PID" ] && [ -z "$PORT_LISTENER" ] && [ -z "$CRON_ACTIVE" ]; then
  echo "openclaw is already disabled:"
  echo "  gateway process: none"
  echo "  port 1492: empty"
  echo "  watchdog cron: commented out"
  if [ -f ~/.openclaw/disable-state/disabled-at.txt ]; then
    echo "  previously disabled at: $(cat ~/.openclaw/disable-state/disabled-at.txt)"
  fi
  echo "nothing to do. exit 0"
  exit 0
fi
```

## Step 1 — Backup current state

```bash
STATE=~/.openclaw/disable-state
mkdir -p "$STATE/history"

# If a prior backup exists, archive it
if [ -f "$STATE/disabled-at.txt" ]; then
  TS=$(cat "$STATE/disabled-at.txt" | tr ':' '-' | tr -d ' ')
  ARCHIVE="$STATE/history/$TS"
  mkdir -p "$ARCHIVE"
  mv "$STATE"/*.txt "$STATE"/crontab.backup "$ARCHIVE/" 2>/dev/null || true
  echo "archived prior disable state to $ARCHIVE"
fi

# Capture current state
crontab -l > "$STATE/crontab.backup" 2>&1
launchctl list 2>/dev/null | grep -i openclaw > "$STATE/launchctl-before.txt"
pgrep -fl "openclaw" 2>/dev/null > "$STATE/processes-before.txt"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$STATE/disabled-at.txt"

echo "backed up:"
wc -l "$STATE/crontab.backup" "$STATE/launchctl-before.txt" "$STATE/processes-before.txt"
```

## Step 2 — Comment out the gateway-watchdog cron line

```bash
# The line looks like: */2 * * * * /Users/benfife/clawd/scripts/gateway-watchdog.sh
# Replace with: # DISABLED <timestamp> (openclaw temporarily disabled): <original>
TS=$(date -u +"%Y-%m-%d")
crontab -l 2>/dev/null \
  | sed "s|^\(\*/2 \* \* \* \* .*gateway-watchdog\.sh\)\$|# DISABLED $TS (openclaw temporarily disabled) — /enable-openclaw: \1|" \
  | crontab -

# Verify
if crontab -l | grep -q "^# DISABLED.*gateway-watchdog"; then
  echo "✓ cron watchdog commented out"
else
  echo "✗ FAIL: crontab edit didn't catch the watchdog line"
  echo "  current openclaw-related cron entries:"
  crontab -l | grep -i "openclaw\|gateway-watchdog"
  exit 1
fi
```

**Why cron first:** if the gateway-watchdog fires mid-shutdown while the gateway is down, it will try to `open -a OpenClawGateway` and fight us. Commenting cron first closes that race.

## Step 3 — Unload all openclaw launchctl entries

Five known entries (the main GUI app + four supporting services). The main GUI app has a label with a random suffix that changes between installs, so we extract it dynamically:

```bash
UID_NUM=$(id -u)

# Main GUI app — label has a random suffix, look up dynamically
GUI_LABEL=$(launchctl list 2>/dev/null | awk '/application\.ai\.openclaw\.gateway\./ {print $3}')
if [ -n "$GUI_LABEL" ]; then
  echo "  $GUI_LABEL"
  launchctl bootout gui/$UID_NUM/$GUI_LABEL 2>&1 | head -2 || echo "    bootout non-zero (may already be gone)"
fi

# Supporting services — fixed labels
for label in \
  com.bigmac.openclaw-token-enforcer \
  com.openclaw.auth-rotation \
  com.openclaw.autocommit-workspaces \
  com.openclaw.screenshot-watcher
do
  echo "  $label"
  launchctl bootout gui/$UID_NUM/$label 2>&1 | head -2 || echo "    bootout non-zero"
done
```

**Why `bootout` not `stop`:** `launchctl stop` just sends SIGTERM — KeepAlive will restart the process. `bootout` unregisters the service entirely, so it stays dead until explicitly loaded again (which happens when `open -a OpenClawGateway` runs in `/enable-openclaw`).

## Step 4 — SIGTERM any lingering gateway processes

```bash
pkill -TERM -f "openclaw-gateway" 2>/dev/null && echo "  SIGTERM sent" || echo "  no gateway processes found (expected after bootout)"
sleep 3
# Escalate to SIGKILL only if something is still alive
if pgrep -f "openclaw-gateway" >/dev/null 2>&1; then
  echo "  gateway still alive 3s after SIGTERM — escalating to SIGKILL"
  pkill -KILL -f "openclaw-gateway" 2>/dev/null
fi
```

## Step 5 — Verification (quick)

**Note:** naive `cmd | head && echo A || echo B` is unreliable when `head` receives empty stdin — the exit code propagates from `head`, not from the originating command, and the pipeline always succeeds with empty output, making the `|| echo B` branch unreachable. Use explicit variable capture + `-z` tests instead.

```bash
echo "immediate verification:"

PROCS=$(pgrep -fl openclaw-gateway 2>/dev/null)
if [ -z "$PROCS" ]; then
  echo "  ✓ no gateway processes"
else
  echo "  ✗ processes still running:"
  echo "$PROCS" | sed 's/^/    /'
fi

PORT=$(lsof -iTCP:1492 -sTCP:LISTEN 2>/dev/null | grep -v '^COMMAND')
if [ -z "$PORT" ]; then
  echo "  ✓ port 1492 empty"
else
  echo "  ✗ port 1492 still bound:"
  echo "$PORT" | sed 's/^/    /'
fi

LCTL=$(launchctl list 2>&1 | grep -i openclaw)
if [ -z "$LCTL" ]; then
  echo "  ✓ no launchctl openclaw entries"
else
  echo "  ✗ launchctl entries remaining:"
  echo "$LCTL" | sed 's/^/    /'
fi
```

## Step 6 — 130-second stability verification

The gateway-watchdog cron runs every 2 minutes. Waiting 130 seconds guarantees at least one cron tick passed. If the cron comment didn't take effect (e.g. crontab edit failed silently, or cron is caching old state), the gateway will come back up within this window.

```bash
echo "waiting 130s for cron cycle..."
sleep 130

# Re-verify
if pgrep -fl openclaw-gateway >/dev/null || lsof -iTCP:1492 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "✗ FAIL: gateway came back up during wait — crontab edit likely didn't work"
  crontab -l | grep -i "gateway-watchdog"
  exit 1
fi
echo "✓ stable — openclaw still disabled 130s after shutdown"
```

## Step 7 — Log to Turso (optional but recommended)

Use the real HTTP pipeline, not the bogus `facts add` CLI:

```bash
python3 - <<'PY'
import json, urllib.request, subprocess, glob, os
URL = subprocess.check_output(['bash','-c',
    'source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_DATABASE_URL" | sed "s|libsql://|https://|"'
]).decode() + "/v2/pipeline"
TOKEN = subprocess.check_output(['bash','-c',
    'source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_AUTH_TOKEN"'
]).decode()
sids = sorted(glob.glob('/Users/benfife/.claude/projects/-Users-benfife/*.jsonl'),
              key=os.path.getmtime, reverse=True)
sid = os.path.basename(sids[0]).replace('.jsonl','') if sids else 'unknown'

content = ("openclaw temporarily disabled via /disable-openclaw. Gateway process killed (SIGTERM clean exit), "
           "5 launchctl entries booted out (main GUI + 4 supporting services), gateway-watchdog cron commented out. "
           "State backup at ~/.openclaw/disable-state/. Reverse via /enable-openclaw.")

body = {"requests":[{"type":"execute","stmt":{
  "sql":"INSERT INTO memory (agent_id, date, content, tags, created_by, created_by_session, created_by_platform) VALUES (?, ?, ?, ?, ?, ?, ?)",
  "args":[
    {"type":"text","value":"Claude"},
    {"type":"text","value":"NOW"},
    {"type":"text","value":content},
    {"type":"text","value":"openclaw,disabled,gateway,cost-savings"},
    {"type":"text","value":"Claude"},
    {"type":"text","value":sid},
    {"type":"text","value":"darwin"},
  ]}}]}
req = urllib.request.Request(URL, data=json.dumps(body).encode(),
    headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
res = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())['results'][0]
if res.get('type')=='ok':
    print(f"logged to turso memory row {res['response']['result'].get('last_insert_rowid')}")
PY
```

## Step 8 — Report

Output a concise summary:
- Backup state path
- Disabled timestamp
- All 5 launchctl entries that were booted out
- Cron line that was commented out (exact text)
- Verification results (processes, port, launchctl)
- **Exact one-line restore command**: `/enable-openclaw`

## What this skill does NOT touch

- `/Applications/OpenClawGateway.app` bundle (still on disk)
- openclaw source tree at `~/github/ammonfife/BIGMAC/openclaw/`
- BIGMAC_OPENCLAW Google API key (separate concern)
- `~/clawd/agents/*` agent workspaces
- Turso (the database stays online — only the gateway that reads it is down)
- Claude Code itself (Claude Code is not part of openclaw)

## What WILL break while openclaw is disabled

- Inter-agent messaging via `bigmac-msg` / `sessions_send` / `openclaw agent --agent <id> --message`
- `.inbox` files keep accumulating but nobody reads them until the gateway comes back
- Gateway-routed Turso triggers don't fire
- Any BIGMAC skill that calls Gemini via openclaw's provider stack — errors out immediately

## What STILL works

- Claude Code (this session) — independent of openclaw
- `bigmac-sync push` — direct Turso HTTP, no gateway
- Claude Code's native Agent tool — spawns subagents directly, not via gateway
- File-based `.inbox` drops — content is written to files regardless; just nothing consumes them
- macOS apps like Mail.app, Safari — unaffected
