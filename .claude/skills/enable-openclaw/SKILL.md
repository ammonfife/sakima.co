---
name: enable-openclaw
description: Re-enable openclaw after /disable-openclaw — restores the original crontab from backup, re-opens OpenClawGateway.app (which re-registers all 5 launchctl entries automatically), waits for the gateway to bind port 1492, verifies reachability via /health with a real body assertion (HTTP 200 ≠ working rule), and logs to Turso. Idempotent — safe to run when already enabled. Reads state from ~/.openclaw/disable-state/ written by /disable-openclaw.
user-invocable: true
---

# /enable-openclaw

Reverse `/disable-openclaw` and bring the full openclaw stack back up. Reads the backup at `~/.openclaw/disable-state/` that disable wrote, restores crontab, relaunches the `.app`, and verifies the gateway is actually serving real responses (not just a 200 on an error page).

## Hard rules (NEVER violate)

1. **Idempotent.** If the gateway is already running and responding with real content, print a message and exit 0 — don't re-launch or touch the crontab.
2. **HTTP 200 ≠ working.** The reachability check in Step 4 MUST parse the `/health` response body and assert expected fields. A 200 with empty body or stub JSON means the gateway booted but isn't fully up yet. Keep waiting.
3. **Fail loudly if backup is missing.** If `~/.openclaw/disable-state/crontab.backup` doesn't exist, openclaw wasn't disabled via `/disable-openclaw` (or the state got wiped). Refuse to guess at a restore — surface the problem.
4. **Do NOT force-delete the disable-state backup.** Keep it in place even after successful enable — the next `/disable-openclaw` will archive it to `history/` automatically. This preserves audit trail.
5. **Do NOT edit crontab beyond the restore.** If Ben made other crontab changes while openclaw was disabled, those are his and the backup doesn't have them. Merge conflict handling is deliberately out of scope — see "Merge conflict" section below.
6. **Re-verify after 60 seconds.** The gateway can take 5-30 seconds to bind the port, and an additional 10-20 seconds for the supporting launchctl services to spin up. A single check at t+10s can false-fail.

## Step 0a — Set up on-disk run log

Every enable run captures its FULL output to a timestamped log, mirroring `/disable-openclaw`'s run-log pattern. Together, the paired logs + the `~/.openclaw/disable-state/` snapshots form the permanent audit trail of every disable→enable cycle.

```bash
RUNLOG_DIR=~/.openclaw/disable-state/run-logs
mkdir -p "$RUNLOG_DIR"
RUNLOG="$RUNLOG_DIR/$(date -u +%Y%m%dT%H%M%SZ)-enable.log"
exec > >(tee -a "$RUNLOG") 2>&1
echo "=== /enable-openclaw run started at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "=== PID: $$  TTY: $(tty 2>/dev/null || echo 'none')  USER: $(whoami) ==="
echo "=== Run log: $RUNLOG ==="
```

## Step 0 — Idempotency check

```bash
# Is the gateway already up and responding with real content?
HTTP_CODE=$(curl -s -o /tmp/gateway-health.json -w "%{http_code}" http://127.0.0.1:1492/health 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
  # Also parse the body — HTTP 200 ≠ working
  REAL=$(python3 -c "
import json, sys
try:
  d = json.load(open('/tmp/gateway-health.json'))
  print('ok' if isinstance(d, dict) and d else 'empty')
except: print('unparseable')
")
  if [ "$REAL" = "ok" ]; then
    echo "openclaw is already enabled and responding:"
    cat /tmp/gateway-health.json
    echo
    echo "nothing to do. exit 0"
    exit 0
  fi
fi
```

## Step 1 — Locate the backup

```bash
STATE=~/.openclaw/disable-state
if [ ! -f "$STATE/crontab.backup" ]; then
  echo "FAIL: $STATE/crontab.backup does not exist"
  echo "      This means openclaw was NOT disabled via /disable-openclaw, or"
  echo "      the backup got wiped. Refusing to guess at restore."
  echo
  echo "      If you know the state, manually:"
  echo "        1. Add this line to crontab: */2 * * * * /Users/benfife/clawd/scripts/gateway-watchdog.sh"
  echo "        2. open -a OpenClawGateway"
  echo "        3. Verify port 1492 is listening"
  exit 1
fi

echo "loaded backup from: $STATE"
echo "disabled at: $(cat $STATE/disabled-at.txt 2>/dev/null || echo '(unknown)')"
wc -l "$STATE/crontab.backup"
```

## Step 2 — Restore crontab

```bash
# Capture the current crontab for diff/merge inspection
CURRENT=$(crontab -l 2>/dev/null)

# Restore from backup (atomic replacement)
crontab "$STATE/crontab.backup"

# Verify the gateway-watchdog line is uncommented
if crontab -l | grep -q "^\*/2 \* \* \* \* .*gateway-watchdog\.sh\$"; then
  echo "✓ gateway-watchdog cron line restored (uncommented)"
else
  echo "✗ FAIL: after restore, watchdog line is not in the expected active state"
  echo "  current crontab openclaw lines:"
  crontab -l | grep -i "openclaw\|gateway-watchdog"
  exit 1
fi
```

### Merge conflict handling
If the current crontab had additions made while openclaw was disabled (e.g. Ben added a new unrelated cron entry), those will be LOST when we restore from the backup. This skill does not attempt to merge — the assumption is that crontab edits between disable and enable are the exception, not the rule. If a merge is needed, show the current crontab before restoring and let the operator decide:

```bash
# Optional merge check — print diff, ask operator to confirm
DIFF=$(diff <(echo "$CURRENT") "$STATE/crontab.backup" | head -20)
if [ -n "$DIFF" ]; then
  echo "WARN: crontab changed while openclaw was disabled. Diff before restore:"
  echo "$DIFF"
  # If in an interactive context, prompt. For now we just log and proceed.
fi
```

## Step 2.5 — Rename all `.plist.disabled` → `.plist` (reverses disable Step 4b)

`/disable-openclaw` renames 8 openclaw-related plists to `.plist.disabled` so macOS skips them at login. This step reverses that so launchd loads them on next session (and bootstrap in Step 6 can reach them).

```bash
for label in \
  ai.openclaw.gateway \
  com.bigmac.gateway-watchdog \
  com.benfife.agi-gateway-monitor \
  com.benfife.agi-session-monitor \
  com.bigmac.openclaw-token-enforcer \
  com.openclaw.auth-rotation \
  com.openclaw.autocommit-workspaces \
  com.openclaw.screenshot-watcher
do
  src=~/Library/LaunchAgents/${label}.plist.disabled
  dst=~/Library/LaunchAgents/${label}.plist
  if [ -f "$src" ]; then
    echo "  restore $label.plist.disabled → .plist"
    mv "$src" "$dst"
  elif [ -f "$dst" ]; then
    echo "  $label.plist already present"
  fi
done
```

## Step 2.6 — Re-add OpenClawGateway to macOS Login Items

```bash
# Adds OpenClawGateway.app back to "Login Items" so it relaunches at next login.
osascript <<'APPLESCRIPT'
tell application "System Events"
  if not (exists login item "OpenClawGateway") then
    make login item at end with properties {path:"/Applications/OpenClawGateway.app", hidden:false}
  end if
end tell
APPLESCRIPT

LIS=$(osascript -e 'tell application "System Events" to get the name of every login item' 2>&1 | tr ',' '\n' | grep -iE "openclaw" | head -1)
[ -n "$LIS" ] && echo "  ✓ OpenClawGateway in Login Items" || echo "  ⚠ failed to add OpenClawGateway to Login Items"
```

## Step 2.7 — Re-enable openclaw internal crons in `jobs.json`

`/disable-openclaw` flipped every `enabled: true → false` in `~/.openclaw/cron/jobs.json` (30 jobs) and captured which IDs had been enabled pre-disable into `~/.openclaw/disable-state/jobs-json-enabled.txt`. This step reads that list and restores `enabled: true` ONLY on those IDs (not all 30 — some may have been intentionally disabled before).

```bash
python3 - <<'PY'
import json, pathlib
jobs_path = pathlib.Path.home() / '.openclaw/cron/jobs.json'
snapshot = pathlib.Path.home() / '.openclaw/disable-state/jobs-json-enabled.txt'

if not snapshot.exists():
    print('  ⚠ no jobs-json-enabled.txt backup — leaving jobs.json as-is')
else:
    wanted = {line.strip() for line in snapshot.read_text().splitlines() if line.strip()}
    d = json.loads(jobs_path.read_text())
    jobs = d.get('jobs', d) if isinstance(d, dict) else d
    if isinstance(jobs, dict): jobs = jobs.get('jobs', [])
    n = 0
    for j in jobs if isinstance(jobs, list) else []:
        if isinstance(j, dict):
            jid = j.get('id') or j.get('name', '')
            if jid in wanted and j.get('enabled') is False:
                j['enabled'] = True
                n += 1
    jobs_path.write_text(json.dumps(d, indent=2))
    print(f'  ✓ re-enabled {n} of {len(wanted)} jobs in jobs.json')
PY
```

## Step 3 — Re-open OpenClawGateway.app

```bash
# Opening the .app re-registers the GUI launchctl entry automatically.
# This is the blessed way to restart the gateway — direct launchctl load
# would miss the random-suffix label generation.
open -a OpenClawGateway
echo "✓ OpenClawGateway.app re-opened"
```

**Why `open -a` and not `launchctl bootstrap`:** the main gateway launchctl label has a random suffix (`application.ai.openclaw.gateway.709719577.745339763`-style) that's generated fresh each time the .app boots. Directly bootstrapping with a stale label from the backup won't work. The .app bundle handles the re-registration correctly.

## Step 4 — Wait for gateway to bind port 1492 (up to 60s)

```bash
echo "waiting up to 60s for gateway to bind port 1492..."
for i in $(seq 1 30); do
  if lsof -iTCP:1492 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "  ✓ port 1492 bound at t+$((i*2))s"
    break
  fi
  sleep 2
done

if ! lsof -iTCP:1492 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "✗ FAIL: gateway did not bind port 1492 within 60s"
  echo "  check /tmp/openclaw-gateway.log for errors"
  tail -30 /tmp/openclaw-gateway.log 2>/dev/null
  exit 1
fi
```

## Step 5 — Real-content health assertion (HTTP 200 ≠ working)

**Important:** the openclaw gateway serves its Control UI HTML from the root and catch-all routes. `/health`, `/status`, `/_health` etc. all return the same ~692-byte SPA shell with `<title>OpenClaw Control</title>`. There is NO dedicated JSON health endpoint at those paths (confirmed by testing 2026-04-08). The `/api/*` routes return real 404s for unknown paths, proving the API router is live but doesn't expose a health endpoint by default.

Two valid assertions for "gateway is actually up":
1. **Root `/` returns HTTP 200 with the OpenClaw Control HTML shell** (contains `<title>OpenClaw Control</title>` — proves the static assets are being served)
2. **`/api/<something-unknown>` returns 404 with a JSON-ish body, NOT a 5xx or HTML** (proves the API router is initialized and responding)

```bash
# Wait an extra 5s for the gateway to fully initialize beyond just port binding
sleep 5

HTTP_CODE=$(curl -s -o /tmp/gateway-root.html -w "%{http_code}" http://127.0.0.1:1492/ 2>/dev/null)
if [ "$HTTP_CODE" != "200" ]; then
  echo "✗ FAIL: root / returned HTTP $HTTP_CODE"
  head -c 500 /tmp/gateway-root.html 2>/dev/null
  exit 1
fi

# Content assertion: must be the OpenClaw Control UI, not a stub or proxy error
if ! grep -q "OpenClaw Control" /tmp/gateway-root.html; then
  echo "✗ FAIL: root / returned 200 but the body isn't the OpenClaw Control UI"
  head -c 500 /tmp/gateway-root.html
  exit 1
fi
echo "  ✓ root / returns OpenClaw Control UI HTML"

# Secondary check: API router is live (expect 404 on unknown path, not 5xx)
API_CODE=$(curl -s -o /tmp/gateway-api-probe.txt -w "%{http_code}" http://127.0.0.1:1492/api/_nonexistent 2>/dev/null)
if [ "$API_CODE" != "404" ]; then
  echo "  WARN: /api/_nonexistent returned $API_CODE (expected 404 from a healthy API router)"
else
  echo "  ✓ API router responding (404 on unknown path)"
fi
```

## Step 6 — Bootstrap supporting LaunchAgents + verify

**Important:** `open -a OpenClawGateway` only starts the main GUI app — it does NOT auto-reload the 4 supporting LaunchAgents that `/disable-openclaw` booted out. Those agents have plist files at `~/Library/LaunchAgents/` that were unloaded with `launchctl bootout` during disable. They must be explicitly `launchctl bootstrap`'d back to return to the pre-disable state.

```bash
UID_NUM=$(id -u)
for label in \
  com.bigmac.openclaw-token-enforcer \
  com.openclaw.auth-rotation \
  com.openclaw.autocommit-workspaces \
  com.openclaw.screenshot-watcher
do
  plist=~/Library/LaunchAgents/${label}.plist
  echo "  ${label}"
  if [ -f "$plist" ]; then
    # bootstrap is silent on success; if the agent is already loaded, it prints "already loaded"
    launchctl bootstrap gui/$UID_NUM "$plist" 2>&1 | head -3 || echo "    bootstrap non-zero (may already be loaded)"
  else
    echo "    WARN: plist missing at $plist — supporting service will not be loaded"
  fi
done

echo
echo "launchctl entries for openclaw:"
launchctl list 2>&1 | grep -i openclaw | sort
COUNT=$(launchctl list 2>&1 | grep -ic openclaw)
echo "count: $COUNT"

if [ "$COUNT" -lt 5 ]; then
  echo "  WARN: only $COUNT openclaw launchctl entries found (expected 5)"
  echo "  Investigate missing entries:"
  for label in \
    application.ai.openclaw.gateway \
    com.bigmac.openclaw-token-enforcer \
    com.openclaw.auth-rotation \
    com.openclaw.autocommit-workspaces \
    com.openclaw.screenshot-watcher
  do
    launchctl list 2>&1 | grep -q "$label" || echo "    ✗ missing: $label"
  done
fi
```

Expected entries (5 total):
- `application.ai.openclaw.gateway.<random-suffix>` — main GUI app (re-registered by `open -a` in Step 3)
- `com.bigmac.openclaw-token-enforcer` — bootstrapped here
- `com.openclaw.auth-rotation` — bootstrapped here
- `com.openclaw.autocommit-workspaces` — bootstrapped here
- `com.openclaw.screenshot-watcher` — bootstrapped here

The random suffix on the main GUI label changes each boot — that's normal.

## Step 7 — Log to Turso

Real HTTP pipeline, not the bogus `facts add` CLI:

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

content = ("openclaw re-enabled via /enable-openclaw. Crontab restored from backup "
           "(gateway-watchdog active again), OpenClawGateway.app reopened, port 1492 "
           "bound, /health assertion passed. All launchctl entries auto-registered.")

body = {"requests":[{"type":"execute","stmt":{
  "sql":"INSERT INTO memory (agent_id, date, content, tags, created_by, created_by_session, created_by_platform) VALUES (?, ?, ?, ?, ?, ?, ?)",
  "args":[
    {"type":"text","value":"Claude"},
    {"type":"text","value":"NOW"},
    {"type":"text","value":content},
    {"type":"text","value":"openclaw,enabled,gateway,restore"},
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

## Step 8 — Final report

Output a concise summary:
- Backup that was restored from (path + original disable timestamp)
- Crontab: how many lines, whether watchdog is active
- Gateway: port 1492 bound at t+Xs, /health body content
- launchctl: N entries present
- **Expected behavior:** inter-agent messaging, gateway-routed Turso triggers, and any openclaw-driven Gemini calls are all back online
- **Billing note:** if disable was used for cost savings, Gemini billing will start accruing again — check the Console Billing report tomorrow to confirm

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/health` returns 200 but body is empty | Gateway port bound but not fully initialized | Wait another 30s and re-run |
| Port 1492 never binds | OpenClawGateway.app didn't actually launch | Check `/tmp/openclaw-gateway.log`; may need to manually `open -a OpenClawGateway` from the GUI |
| Some launchctl entries missing | Supporting service failed to start | Check `log show --predicate 'subsystem CONTAINS "openclaw"' --last 5m` |
| Crontab backup doesn't exist | openclaw wasn't disabled via `/disable-openclaw` | Manually re-add the gateway-watchdog cron line |
| Gateway binds but inter-agent messaging still fails | Supporting services didn't register | Wait 30s more; if still broken, `/disable-openclaw` + `/enable-openclaw` cycle |
