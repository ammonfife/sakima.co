---
name: lovable-deploy
description: Deploy lkup.info to Lovable production. Uses the programmatic API (no E2B/Playwright needed) — JWT auto-renews via Firebase refresh_token. Falls back to E2B Playwright only if the API fails. Verifies the deploy by checking /build-info for the new SHA. Records every deploy to Turso.
user-invocable: true
---

@~/.claude/skills/lkup-shared-context/CONTEXT.md

> [!IMPORTANT]
> **Cross-Platform Skill**: This skill is shared across Claude Code, OpenClaw, Gemini, and Codex.

### If you are Claude (Claude Code / OpenClaw)
- Use `Bash` for shell commands and the Python auto-deploy script.

### If you are Gemini (Antigravity / Google)
- Use `run_command` with `WaitMsBeforeAsync`.

### If you are Codex / Grok
- Use native terminal execution.


# /lovable-deploy

Deploy the current lkup.info `prod` branch to Lovable (live site).

**Primary path (API)**: Uses `scripts/lovable-auto-deploy.py` — no E2B, no Playwright, no browser.
**Fallback (E2B)**: Only if the API fails (network error, token revoked, etc.).

---

## Step 0 — Pre-flight: is a deploy needed?

```bash
cd ~/github/ammonfife/lkup.info

# Get the SHA currently deployed (from live /build-info endpoint)
DEPLOYED_SHA=$(curl -s "https://lkup.info/build-info" | python3 -c "
import sys,json
try: d=json.load(sys.stdin); print(d.get('sha','unknown'))
except: print('unknown')
" 2>/dev/null)
echo "Deployed: $DEPLOYED_SHA"

# Get what's on origin/prod
PROD_SHA=$(git rev-parse origin/prod)
echo "On prod:  ${PROD_SHA:0:40}"

# If they match, skip the deploy
if [ "$DEPLOYED_SHA" = "$PROD_SHA" ]; then
  echo "✅ Already up to date — no deploy needed"
  exit 0
fi
echo "Deploying ${PROD_SHA:0:8}..."
```

**If already current → skill done, no deploy needed.**

Also check for build errors before deploying:
```bash
cd ~/github/ammonfife/lkup.info && npm run build 2>&1 | tail -5
# If build fails, fix it before deploying
```

---

## Step 1 — Deploy via API (primary path)

```bash
python3 ~/github/ammonfife/lkup.info/scripts/lovable-auto-deploy.py
```

This script:
1. Calls `securetoken.googleapis.com` with the stored `lovable_firebase_refresh_token` → gets fresh JWT
2. POSTs `{}` to `https://api.lovable.dev/projects/{PROJECT_ID}/deployments?async=true`
3. Polls `/deployments/{id}/progress` until `status=completed`
4. Auto-saves the rotated refresh_token back to bigmac-secrets

**Credentials required in bigmac-secrets:**
- `lovable_firebase_refresh_token` — Firebase refresh token (long-lived, self-renewing)
- `lovable_firebase_api_key` — Firebase API key for gpt-engineer-390607 project

**If the API returns "Invalid token" or any error:** jump to Step 2 (E2B fallback).

---

## Step 2 — Fallback: E2B Playwright (only if API fails)

Use only when Step 1 fails. The E2B path clicks the Publish button via a real browser.

```python
# Get fresh JWT from scope captures if available
import subprocess, json

# Check if there's a live JWT in network_scope (from recent Lovable browser visit)
# JWT must be <1h old — scope captures include request_headers.Authorization
supa = subprocess.check_output([...])  # query network_scope for api.lovable.dev

# If no live JWT: open Lovable in Chrome (extension auto-scopes lovable.dev)
# Then use the captured JWT
import subprocess
subprocess.run(["open", "-a", "Google Chrome",
    "https://lovable.dev/projects/198cfbd3-f2a7-4365-ae7a-94cc5c555bd9"])
# Wait ~15s for scope to capture the JWT, then retry Step 1
```

If no JWT is available at all, use full E2B Playwright via the old `lovable-deploy.py`:
```bash
python3 ~/github/ammonfife/lkup.info/scripts/lovable-deploy.py
```

---

## Step 3 — Verify the deploy landed

Wait 60-120s after deploy triggers (Cloudflare Pages build takes time).

```bash
# Poll /build-info until SHA matches or timeout
EXPECTED_SHA=$(cd ~/github/ammonfife/lkup.info && git rev-parse HEAD)
DEADLINE=$(($(date +%s) + 300))

while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  LIVE=$(curl -s "https://lkup.info/build-info" | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print(d.get('sha','?'))" 2>/dev/null)
  if [ "$LIVE" = "$EXPECTED_SHA" ]; then
    echo "✅ Deploy verified — /build-info shows ${EXPECTED_SHA:0:8}"
    break
  fi
  echo "  waiting... live=$LIVE"
  sleep 15
done
```

**HTTP 200 ≠ working.** The `/build-info` SHA check is the real verification.

---

## Step 4 — Record to Turso

```python
import subprocess, json, os, glob

TURSO_URL = os.environ.get("TURSO_DATABASE_URL","").replace("libsql://","https://")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN","")
sha = subprocess.check_output(["git","rev-parse","HEAD"]).decode().strip()

# Find current session
sids = sorted(glob.glob(os.path.expanduser("~/.claude/projects/-Users-benfife/*.jsonl")),
              key=os.path.getmtime, reverse=True)
session_uuid = os.path.basename(sids[0]).replace(".jsonl","") if sids else "unknown"

fact = f"lovable-deploy: lkup.info pushed to live. SHA={sha[:8]}. Verified via /build-info."
body = {"requests":[{"type":"execute","stmt":{"sql":
    "INSERT INTO facts (fact,source,category,created_by,created_by_session,created_by_platform) VALUES (?,?,?,?,?,?)",
    "args":[
      {"type":"text","value":fact},
      {"type":"text","value":"lovable-deploy skill"},
      {"type":"text","value":"operational"},
      {"type":"text","value":"Claude"},
      {"type":"text","value":session_uuid},
      {"type":"text","value":"darwin"},
    ]}}]}

import urllib.request
req = urllib.request.Request(f"{TURSO_URL}/v2/pipeline", data=json.dumps(body).encode(),
  headers={"Authorization":f"Bearer {TURSO_TOKEN}","Content-Type":"application/json"})
urllib.request.urlopen(req, timeout=20)
print("✅ Recorded to Turso")
```

---

## Sending a chat to Lovable

```bash
python3 ~/github/ammonfife/lkup.info/scripts/lovable-auto-deploy.py --chat "fix the hero section font"
```

The `--chat` flag POSTs to `/projects/{id}/edits` with the message instead of deploying.
Lovable will process the request and push a new commit to prod when done.

---

## Auto-deploy on push

Every `git push origin prod` automatically triggers a deploy via the pre-push hook
(`.githooks/pre-push` calls `lovable-auto-deploy.py` in background). No manual step needed.

---

## Failure modes

| Symptom | Cause | Fix |
|---|---|---|
| "Invalid token" from API | JWT expired or refresh_token revoked | Open Lovable in Chrome (scope captures new JWT) then retry |
| refresh_token stale | Not used in >6 months | Re-login to Lovable.dev in Chrome with scope enabled |
| Build errors on push | TypeScript/lint failures | Fix errors, then re-push |
| /build-info shows old SHA after 5min | Cloudflare cache | Wait up to 10min; if still stale, check Lovable dashboard |

---

## Credentials location

- `bigmac-secrets get lovable_firebase_refresh_token` — Firebase refresh_token
- `bigmac-secrets get lovable_firebase_api_key` — Firebase API key
- Project ID: `198cfbd3-f2a7-4365-ae7a-94cc5c555bd9`
- Firebase project: `gpt-engineer-390607`
