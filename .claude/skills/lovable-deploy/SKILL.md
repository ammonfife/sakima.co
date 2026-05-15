---
name: lovable-deploy
description: Deploy lkup.info via E2B desktop sandbox — uses /use-e2b to drive Playwright against the Lovable web UI's Publish button. Verifies the deploy succeeded by hitting the live site afterward and parsing real content (HTTP 200 ≠ working rule). Captures a post-deploy screenshot as proof per the global lkup.info screenshot-proof rule. Records every deploy to Turso via the real HTTP pipeline. Auto-falls back from saved-cookie mode to interactive --setup mode if the Lovable session expired.
user-invocable: true
---

@~/.claude/skills/lkup-shared-context/CONTEXT.md

> [!IMPORTANT]
> **Cross-Platform Skill**: This skill is shared across Claude Code, OpenClaw, Gemini, and Codex. 
> Before executing, check the "Platform Blocks" below. If your current platform is missing, or if a command fails due to your unique toolset, **UPDATE THIS SKILL** by adding an `If you are [Platform]...` block detailing how your platform should execute it.

### If you are Claude (Claude Code / OpenClaw)
- Use your native `str_replace_editor` for targeted edits.
- You can spawn background tasks directly using `Bash run_in_background`.

### If you are Gemini (Antigravity / Google)
- Use your native `multi_replace_file_content` or `replace_file_content` tools.
- Background tasks should use the `run_command` tool with `WaitMsBeforeAsync` set appropriately.

### If you are Codex / Grok
- Use your respective file-editing APIs and terminal execution pipelines.


# /lovable-deploy

Push the current lkup.info changes live by clicking the Lovable Publish button via a Playwright-driven browser inside an E2B desktop sandbox.

The actual driver script is `~/github/ammonfife/lkup.info/scripts/lovable-deploy.py`. This skill is the procedure that wraps the script with the right pre-flight checks, post-deploy verification, screenshot capture, and Turso recording.

## Hard rules (NEVER violate)

1. **Never use Ben's owner browser.** Per the global E2B-default policy, all browser automation runs inside an E2B desktop sandbox. The skill MUST use `/use-e2b` (or the deploy script's E2B path) and NEVER set `profile="chrome"`.
2. **HTTP 200 ≠ working.** Post-deploy verification MUST parse real page content from the live site, not just check the status code. A 200 with a stale cached page, an error template, or a build-failure landing page is NOT a successful deploy.
3. **Screenshot proof is mandatory.** Capture a post-deploy PNG of the live site showing real content. Per the global lkup.info Screenshot-Proof Rule. Code pushed to Lovable ≠ done. Lovable accepting the push ≠ done. Screenshot of the live site rendering correctly = done.
4. **No silent fallback to setup.** If the saved-cookie session is expired and `--setup` is needed, surface that to the operator EXPLICITLY. The setup flow requires interactive GitHub login — running it without surfacing means the operator may not realize a manual step is queued.
5. **Single agent author on Turso writes.** No co-author tag inflation.
6. **Pin the deploy to a git SHA.** Record `git rev-parse HEAD` BEFORE pushing so the Turso fact unambiguously says "what code shipped."

## Inputs

```bash
/lovable-deploy                       # standard deploy: cookies → publish → verify → screenshot → record
/lovable-deploy --setup               # first-time / re-auth: opens VNC for GitHub login, saves cookies, exits
/lovable-deploy --dry-run             # walk the pipeline but don't actually click Publish — useful for verifying the sandbox + cookies still work
/lovable-deploy --skip-verify         # deploy and skip the post-deploy content check (DANGEROUS — only for known-broken health endpoints)
```

## Step 0 — Pre-flight

```bash
SCRIPT=~/github/ammonfife/lkup.info/scripts/lovable-deploy.py
[ -f "$SCRIPT" ] || { echo "FAIL: $SCRIPT missing"; exit 1; }

# Pin the deploy SHA
cd ~/github/ammonfife/lkup.info
DEPLOY_SHA=$(git rev-parse --short HEAD)
DEPLOY_REF=$(git symbolic-ref --short HEAD 2>/dev/null || echo "(detached)")

# The local working tree must be clean OR the operator must opt in via --dirty
if ! git diff --quiet HEAD && [ "$ALLOW_DIRTY" != "1" ]; then
  echo "FAIL: lkup.info has uncommitted changes — refusing to deploy a dirty tree"
  echo "      Either commit or set ALLOW_DIRTY=1 (which records the dirty state in the Turso fact)"
  git status --short
  exit 1
fi

# E2B token must be available
[ -n "$E2B_API_KEY" ] || \
  E2B_API_KEY=$(security find-generic-password -a bigmac -s e2b-api-key -w 2>/dev/null) || \
  { echo "FAIL: E2B_API_KEY missing — required for sandbox creation"; exit 1; }

# Saved sandbox id (re-use across runs to skip the chromium install + auth)
SANDBOX_ID_FILE=~/.openclaw/lovable-sandbox-id
echo "deploying $DEPLOY_REF @ $DEPLOY_SHA"
```

## Step 1 — Acquire / verify the E2B sandbox

```bash
if [ -f "$SANDBOX_ID_FILE" ]; then
  SBX=$(cat "$SANDBOX_ID_FILE")
  echo "reusing saved sandbox: $SBX"
  # Health-check it via /use-e2b
  if ! sbx ls 2>/dev/null | grep -q "$SBX"; then
    echo "saved sandbox $SBX is gone; will create a new one"
    rm "$SANDBOX_ID_FILE"
    SBX=""
  fi
fi
if [ -z "$SBX" ]; then
  # Claim from the warm pool first per the global E2B pool policy
  POOL_RESP=$(curl -s "https://e2b-pool-lb.sakima-api.workers.dev/pool/desktop")
  SBX=$(echo "$POOL_RESP" | python3 -c "import json,sys;print(json.load(sys.stdin).get('sandbox_id',''))")
  if [ -z "$SBX" ]; then
    echo "pool returned empty; falling back to fresh sandbox creation"
    # Use the latest desktop template — read from sbx templates, do not hardcode
    TEMPLATE=$(sbx templates 2>/dev/null | grep bigmac-desktop-v | sort -V | tail -1)
    SBX=$(sbx new "$TEMPLATE" --json | python3 -c "import json,sys;print(json.load(sys.stdin)['id'])")
  fi
  echo "$SBX" > "$SANDBOX_ID_FILE"
fi
```

## Step 2 — Verify saved Lovable cookies (or trigger setup mode)

The deploy script saves auth state inside the sandbox at `/home/user/.lovable-auth-state.json`. This file lives as long as the sandbox does. If the sandbox died or the cookies expired, the deploy click will fail.

```bash
# Quick non-destructive check: open Lovable in the sandbox browser, look for the
# logged-in account avatar element. The deploy script's --check mode does this.
python3 "$SCRIPT" --check --sandbox "$SBX"
RC=$?
if [ "$RC" -ne 0 ]; then
  if [ "$MODE" = "setup" ]; then
    echo "Running interactive --setup. VNC URL will follow — log in via GitHub there."
    python3 "$SCRIPT" --setup --sandbox "$SBX"
    exit 0  # setup is a separate run; the operator runs deploy again after
  else
    echo "FAIL: Lovable session not authenticated. Run /lovable-deploy --setup first."
    echo "      That opens VNC for interactive GitHub login (ammonfife@gmail.com)."
    exit 1
  fi
fi
```

**Never silently switch from deploy to setup** — that would queue an interactive step the operator doesn't know about. If auth is missing, fail loudly and tell the operator to run `--setup` explicitly.

## Step 3 — Click Publish (the deploy)

```bash
if [ "$DRY_RUN" = "1" ]; then
  echo "[--dry-run] would invoke $SCRIPT --sandbox $SBX --deploy"
  exit 0
fi
python3 "$SCRIPT" --deploy --sandbox "$SBX" 2>&1 | tee /tmp/lovable-deploy-$DEPLOY_SHA.log
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "FAIL: lovable-deploy.py exited $RC"
  echo "      Log: /tmp/lovable-deploy-$DEPLOY_SHA.log"
  exit 1
fi
```

The script clicks Publish and waits for Lovable's confirmation toast. Lovable typically takes 30-90 seconds to actually push to GitHub + trigger the Cloudflare Pages build. The script returns when Lovable says "Published" — but that's NOT the same as the live site being updated. Step 4 handles the gap.

## Step 4 — Wait for the deploy to land + verify content (HTTP 200 ≠ working)

```bash
# Cloudflare Pages build typically completes 60-180s after Lovable publish
echo "waiting for Cloudflare Pages build to complete..."
DEADLINE=$(($(date +%s) + 300))  # 5 minute timeout

while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  # Hit the live site
  STATUS=$(curl -s -o /tmp/lovable-deploy-live.html -w "%{http_code}" https://lkup.info/)
  if [ "$STATUS" != "200" ]; then
    echo "  status=$STATUS, retrying in 10s"
    sleep 10
    continue
  fi
  # Parse content — look for a string that proves the deploy landed.
  # Best signal: the build embeds the git SHA into a meta tag or footer.
  # If the project doesn't yet do this, fall back to checking that the page
  # has expected user-visible content (not a maintenance page, not an error).
  if grep -q "$DEPLOY_SHA" /tmp/lovable-deploy-live.html; then
    echo "✓ live site shows commit $DEPLOY_SHA"
    break
  fi
  if grep -qi "<title[^>]*>lkup" /tmp/lovable-deploy-live.html \
     && ! grep -qi "error\|maintenance\|build failed" /tmp/lovable-deploy-live.html; then
    echo "✓ live site responds with the lkup.info template (commit verification not available)"
    break
  fi
  sleep 10
done

if [ "$(date +%s)" -ge "$DEADLINE" ]; then
  echo "FAIL: deploy verification timeout — Cloudflare Pages did not produce a working build in 5 minutes"
  echo "      Last live page: /tmp/lovable-deploy-live.html"
  exit 1
fi
```

The body assertion is the entire point. A 200 from `lkup.info/` could be:
- A stale cached version (CDN didn't update)
- The previous build still serving (Cloudflare's atomic swap hasn't fired)
- A build-failure landing page from Cloudflare
- A maintenance template

Only a body that contains the new SHA (or at minimum the expected lkup.info template structure with no error markers) counts as a successful deploy.

**Recommendation for the lkup.info build:** embed `process.env.GIT_SHA` into a `<meta name="git-sha" content="...">` tag in `index.html` so this verification can be deterministic across deploys. If that's not in place yet, capture a fact about it for future hardening.

## Step 5 — Capture post-deploy screenshot

Per the global lkup.info Screenshot-Proof Rule. The script's Playwright session is still attached, use it to take a screenshot of the live site:

```bash
SHOT=~/github/ammonfife/lkup.info/screenshots/lovable-deploy/$DEPLOY_SHA-$(date -u +%Y%m%dT%H%M%SZ).png
mkdir -p "$(dirname "$SHOT")"
python3 "$SCRIPT" --screenshot --sandbox "$SBX" --url https://lkup.info/ --output "$SHOT"
[ -f "$SHOT" ] || { echo "FAIL: screenshot not captured at $SHOT"; exit 1; }
echo "screenshot: $SHOT"
```

The screenshot must show:
- The live site at `https://lkup.info/` (URL bar visible)
- Real rendered content (not a loading spinner, not an error page)
- Browser chrome so the artifact is verifiable as live

Skip the screenshot ONLY if `--skip-verify` was passed AND log the omission as a fact in Step 6.

## Step 6 — Record the deploy to Turso (real HTTP pipeline)

The previous version of this skill said "Script auto-records to Turso on success" via `facts add operational ...` — but that CLI **does not exist** in this environment, and the script's recording call (if it existed at all) would have silently no-op'd. Replace inline:

```python
import json, urllib.request, subprocess, os, glob, sys

URL = subprocess.check_output(['bash','-c',
    'source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_DATABASE_URL" | sed "s|libsql://|https://|"'
]).decode() + "/v2/pipeline"
TOKEN = subprocess.check_output(['bash','-c',
    'source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_AUTH_TOKEN"'
]).decode()
sids = sorted(glob.glob('/Users/benfife/.claude/projects/-Users-benfife/*.jsonl'),
              key=os.path.getmtime, reverse=True)
session_uuid = os.path.basename(sids[0]).replace('.jsonl','') if sids else 'unknown'

deploy_sha = sys.argv[1]    # e.g. 'a1b2c3d'
screenshot = sys.argv[2]    # path to the screenshot artifact
verified = sys.argv[3]      # '1' or '0'

fact = (f"lovable-deploy: lkup.info pushed to live, commit {deploy_sha}. "
        f"Screenshot: {screenshot}. "
        f"Live-content verification: {'PASSED' if verified=='1' else 'SKIPPED'}. "
        f"Sandbox: {os.environ.get('SBX','?')}.")

body = {"requests":[{"type":"execute","stmt":{
  "sql":"INSERT INTO facts (fact, source, category, created_by, created_by_session, created_by_platform) VALUES (?, ?, ?, ?, ?, ?)",
  "args":[
    {"type":"text","value":fact},
    {"type":"text","value":"scope:project lkup.info /lovable-deploy"},
    {"type":"text","value":"operational"},
    {"type":"text","value":"Claude"},
    {"type":"text","value":session_uuid},
    {"type":"text","value":"darwin"},
  ]}}]}
req = urllib.request.Request(URL, data=json.dumps(body).encode(),
    headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
res = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())['results'][0]
if res.get('type') != 'ok':
    raise SystemExit(f"Turso write failed: {res}")
print(f"deploy fact: id={res['response']['result'].get('last_insert_rowid')}")
```

`created_by` is the SINGLE agent that ran the deploy. No `agent:claude,agent:bob` co-author pre-tagging. If a deploy failed the verification step, record THAT as a separate fact under `category=operational` with a `tags` field including `failure` so the failure is discoverable.

## Step 7 — Final report

```
=== /lovable-deploy summary ===
Commit:     <DEPLOY_SHA> (<DEPLOY_REF>)
Sandbox:    <SBX>
Lovable:    Published (script returned 0)
Live site:  https://lkup.info/ — verified content match
Screenshot: <SHOT>
Turso fact: <id>
Duration:   <total seconds>
```

## Session lifetime

Auth state persists inside the sandbox at `/home/user/.lovable-auth-state.json`. Lives as long as the sandbox (typically up to 24h on the warm pool). When the sandbox is recycled, run `--setup` to re-authenticate.

The saved sandbox id at `~/.openclaw/lovable-sandbox-id` is automatically reused across runs. If reuse fails (sandbox gone), Step 1 detects it and provisions a fresh one — but cookies will be missing, so you'll need to run `--setup` after.

## Failure modes and recovery

| Symptom | Likely cause | Recovery |
|---|---|---|
| `--check` fails: not authenticated | Sandbox died, or Lovable cookies expired | Run `/lovable-deploy --setup` |
| Click Publish but Lovable shows error | Lovable build fails on the source | Read Lovable error in the log; usually a TS error in the recent push |
| Deploy "succeeds" but live site stale | Cloudflare CDN cache not invalidated yet, OR Cloudflare Pages build still running | Wait + retry; if persistent, check the Cloudflare Pages build dashboard |
| Live site returns 200 but wrong content | Stale cache OR wrong project deployed | Verify SHA in `<meta>` tag; if absent, the project needs the SHA-injection fix |
| Screenshot is blank / loading spinner | Playwright captured before page hydrated | Add a wait-for-selector to the screenshot step targeting an element that only renders after JS hydration |
| `lovable-deploy.py` not found | Script missing from the lkup.info repo | The driver script lives in the repo, not this skill — clone or pull the repo |

## Source of truth

- The driver script `~/github/ammonfife/lkup.info/scripts/lovable-deploy.py` owns the Playwright logic
- This skill owns the procedure (pre-flight, content verification, screenshot, Turso recording)
- The live site `https://lkup.info/` is the canonical "is this deployed?" answer — never trust Lovable's "Published" toast alone
