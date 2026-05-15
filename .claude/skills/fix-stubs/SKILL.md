---
name: fix-stubs
description: Fix broken stubs and wiring in lkup.info — Phase 0 of the auction_tools → lkup.info consolidation. Wires frontend TODO stubs to Flask backend endpoints, fixes URL/method mismatches, ports Node-only routes to Flask, replaces mock data with Supabase queries, folds orphans into routed pages, redirects dead routes. Enforces the global lkup.info screenshot-proof rule and the HTTP-200-≠-working rule, coordinates with parallel agents via a file-lock, and validates every lkup-plan.json mutation through /plan-validator before writing.
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


# /fix-stubs

Phase 0 of the auction_tools → lkup.info consolidation: wire up frontend TODO stubs, fix URL/method mismatches, port Node-only routes, replace mock data, fold orphans, redirect dead routes.

Source of truth for the work list: `lkup-plan.json` → `consolidation.phases[0]`.

## Hard rules (NEVER violate)

1. **Do NOT modify `src/components/ui/`** — shared UI library, breaks every page if mutated.
2. **Do NOT modify any file under `auction_tools/`** — that codebase is being consolidated AWAY from. Editing it creates the exact divergence consolidation is removing. The only valid auction_tools touch is `git rm` after a port is verified.
3. **Flask routes go in `api-python/routes/`** and only there. Do not add Flask logic to `api/src/`.
4. **All `raw.*` writes are append-only.** No `UPDATE` / `DELETE` / synthetic backfills against `raw.*`. Per `lkup_no_synthetic_data.md`.
5. **HTTP 200 ≠ working.** Endpoint tests must parse the response body and assert expected fields. A 200 with empty body or stub JSON is NOT working. Per the global `scope:global` HTTP-200 policy.
6. **Screenshot proof is mandatory.** No item is marked `"resolved"` in `lkup-plan.json` without a screenshot artifact on disk that visually demonstrates the working feature. Per the global lkup.info Screenshot-Proof Rule (MEMORY.md). Code pushed ≠ done. Deployed ≠ done. Screenshot of working feature = done.
7. **Single writer at a time.** A file lock at `~/.openclaw/locks/lkup-plan.json.lock` is acquired before any read-modify-write of `lkup-plan.json`. Two agents racing on this file will silently overwrite each other's status updates.
8. **Backup before destructive edits.** Snapshot the file (or use `git stash`) before each multi-line write. Use the local filesystem under `~/.claude/projects/-Users-benfife/memory/fix-stubs-backups/<timestamp>/` for any non-git files.

## Categories

| Code | Category | Fix pattern |
|---|---|---|
| **A** | URL/method mismatches | Flask has logic, frontend calls wrong path. **Fix:** add alias routes in Flask (don't move the frontend — keep the diff small). |
| **B** | Node-only routes | Features in `api/src/` need equivalent Flask routes in `api-python/routes/`. **Fix:** port the route handler 1:1, parameterize on the Node version's request shape, run the assertion suite from Step 4. |
| **C** | Frontend TODO stubs | Replace `// TODO:` with `fetch()` to a Flask endpoint. **Fix:** never invent the URL — read it from the rendered Flask routes list (Step 0). |
| **D** | Mock data | Replace hardcoded arrays with Supabase queries. **Fix:** scope the query to current user / row-level-security where relevant. |
| **E** | Orphan pages | Fold wired logic from unused pages into the routed ones. **Fix:** delete the orphan only AFTER the merge is screenshot-verified. |
| **F** | Dead routes | Redirect to React equivalents. **Fix:** Flask `301` redirect, no rewrite of the destination. |

## Step 0 — Pre-flight (MANDATORY, runs every invocation)

Refuse to proceed if any check fails. No silent skipping.

```bash
PLAN=~/github/ammonfife/lkup.info/lkup-plan.json
LOCK=~/.openclaw/locks/lkup-plan.json.lock
mkdir -p "$(dirname "$LOCK")"

# 0a. lkup-plan.json must exist and parse
[ -f "$PLAN" ] || { echo "FAIL: $PLAN missing"; exit 1; }
python3 -c "import json; json.load(open('$PLAN'))" || { echo "FAIL: $PLAN unparseable"; exit 1; }

# 0b. Schema sanity — phase 0 must exist with at least one item
python3 - <<'PY' || exit 1
import json, sys
d = json.load(open('PLAN_PATH_HERE'))
phases = d.get('consolidation', {}).get('phases', [])
if len(phases) < 1: sys.exit("FAIL: no consolidation.phases[0]")
items = phases[0].get('items', [])
if not items: sys.exit("FAIL: phases[0].items empty")
PY

# 0c. File lock — acquire or fail loudly
if [ -f "$LOCK" ]; then
  HOLDER=$(cat "$LOCK")
  AGE=$(($(date +%s) - $(stat -f %m "$LOCK")))
  echo "FAIL: lkup-plan.json is locked by $HOLDER (${AGE}s ago)."
  echo "      If that lock is stale (>10min) and you've confirmed no other"
  echo "      agent is mid-edit, manually rm $LOCK and retry."
  exit 1
fi
echo "Claude:$$:$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LOCK"
trap 'rm -f "$LOCK"' EXIT INT TERM

# 0d. Confirm /plan-validator is available — we need it before writing
[ -f ~/.claude/skills/plan-validator/SKILL.md ] || \
  { echo "FAIL: /plan-validator skill missing — required for write gate"; exit 1; }

# 0e. Confirm Flask routes list is fresh — render the route table
cd ~/github/ammonfife/lkup.info/api-python && python3 -c "
from flask import Flask
import importlib, pkgutil, routes
app = Flask(__name__)
for _, name, _ in pkgutil.iter_modules(routes.__path__):
    mod = importlib.import_module(f'routes.{name}')
    if hasattr(mod, 'register'):
        mod.register(app)
for r in app.url_map.iter_rules():
    print(f'  {r.methods - {\"HEAD\",\"OPTIONS\"}:>20}  {r.rule}')
" > /tmp/fix-stubs-flask-routes.txt
echo "Flask route inventory: /tmp/fix-stubs-flask-routes.txt ($(wc -l < /tmp/fix-stubs-flask-routes.txt) routes)"
```

If 0c fails because the lock is held, **do not** delete it without confirming the holder is dead. Two-agent races on `lkup-plan.json` corrupt the canonical work list — recovery is manual.

## --list mode (read-only inspection)

Invoke `/fix-stubs --list` to see the next unresolved item without acquiring the lock or making any edits:

```bash
python3 - <<'PY'
import json
d = json.load(open('/Users/benfife/github/ammonfife/lkup.info/lkup-plan.json'))
items = d['consolidation']['phases'][0].get('items', [])
unresolved = [i for i in items if i.get('status') != 'resolved']
print(f"unresolved Phase 0 items: {len(unresolved)} / {len(items)}")
for i in unresolved[:5]:
    print(f"\n  [{i.get('id','?')}] {i.get('category','?')}  {i.get('title','?')}")
    print(f"    file:   {i.get('file','?')}")
    print(f"    detail: {i.get('detail','')[:160]}")
PY
```

Use `--list` before each work session to confirm what's left. Use `--list <category>` to filter (e.g. `--list B` for Node-only ports only).

## Step 1 — Pick the next CLAIMABLE item

After Step 0 succeeds, pick the next item from `lkup-plan.json` → `consolidation.phases[0].items[]` that satisfies ALL of:
- `status NOT IN ('resolved', 'in-progress')` — not done, not actively being worked
- `assigned_to IS NULL` OR `assigned_to == <self agent id>` — unclaimed, or already mine
- Stale-claim recovery: an item with `status='in-progress'` whose `claimed_at` is older than **15 minutes** AND whose `assigned_to` is not in the live agent presence list (per `bigmac-inbox` or the Turso `sessions` table) is reclaimable. Reset its status to `pending` and proceed to claim it.

Default order: oldest unresolved first. Override with `/fix-stubs <item-id>` to target a specific id (still subject to the claim filter).

```python
import json, os, time
plan = json.load(open('/Users/benfife/github/ammonfife/lkup.info/lkup-plan.json'))
items = plan['consolidation']['phases'][0].get('items', [])
SELF = "Claude"  # this agent's id
NOW = int(time.time())
STALE_SECONDS = 15 * 60

def is_claimable(item):
    s = item.get('status', 'pending')
    if s == 'resolved':
        return False
    if s == 'in-progress':
        owner = item.get('assigned_to')
        claimed = item.get('claimed_at', 0)
        if owner == SELF:
            return True  # resuming our own work
        if NOW - claimed > STALE_SECONDS:
            return True  # stale claim, recoverable
        return False  # actively claimed by someone else
    return True  # pending or blocked — claimable

candidates = [i for i in items if is_claimable(i)]
if not candidates:
    print("No claimable Phase 0 items. Either everything is resolved or another agent is mid-work on the rest.")
    exit(0)
target = candidates[0]
print(f"picked: {target['id']} (status was {target.get('status','pending')})")
```

## Step 1.5 — Claim the item (delegated to /lkup-plan-editor)

**Before reading any source or making any edit**, write the claim to `lkup-plan.json` via the canonical writer. This is what stops two agents from picking the same item.

```bash
/lkup-plan-editor --change-set "{
  \"phases[0].items[$IDX].status\": \"in-progress\",
  \"phases[0].items[$IDX].assigned_to\": \"Claude\",
  \"phases[0].items[$IDX].claimed_at\": $(date +%s),
  \"phases[0].items[$IDX].claimed_by_session\": \"$SESSION_UUID\"
}"
```

The lkup-plan-editor acquires its own lock around the write, so the claim is atomic. If two agents try to claim the same item simultaneously, the second one's `/lkup-plan-editor` invocation will see `status='in-progress'` and **/plan-validator must REJECT** the claim because the status transition `in-progress (theirs) → in-progress (mine)` is not legal without an explicit `--steal` flag and a stale-claim justification.

If the claim succeeds, this skill is now the exclusive worker on this item until either:
- Step 7 marks it `resolved` (and clears `assigned_to`)
- Step 6 validation fails and rolls back to `pending` (and clears `assigned_to`)
- The skill crashes — leaves the claim stale, recoverable after 15 minutes by another agent

**Heartbeat:** for long-running steps (E2B screenshot capture, npm builds, anything >5 minutes), refresh the claim:
```bash
/lkup-plan-editor --change-set "{\"phases[0].items[$IDX].claimed_at\": $(date +%s)}"
```
This is what keeps the 15-minute stale-claim timer from firing on legitimate slow work.

## Step 2 — Backup

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
BAK=~/.claude/projects/-Users-benfife/memory/fix-stubs-backups/$TS
mkdir -p "$BAK"
cp ~/github/ammonfife/lkup.info/lkup-plan.json "$BAK/lkup-plan.json"
# Snapshot every file the item names as a target
cd ~/github/ammonfife/lkup.info && git stash push -u -m "fix-stubs $ITEM_ID pre-edit" || echo "(nothing to stash)"
```

The pre-edit `git stash` is the rollback path if the fix breaks the local Flask server or the frontend build. Leave the stash in place until Step 6 verifies success.

## Step 3 — Implement the fix

Apply the category-appropriate pattern from the table above. Constraints:

- **Edit the smallest possible diff.** Adding an alias is preferable to moving the original.
- **Preserve existing handler signatures** in Flask. The auction_tools port is already producing parallel logic — don't add a third variant.
- **No new dependencies.** If a fix needs a new package, stop and surface it as a blocker — do not silently add to `requirements.txt`.
- **No `// TODO`-shaped replacements.** A wired fetch with a real endpoint is the minimum acceptable output. If the endpoint isn't ready, the item is a Category B (port the route first), not a Category C.

## Step 4 — Test the endpoint (HTTP 200 ≠ working)

This is the rule that catches the most bugs. The test must do BOTH:

```bash
# Status check (necessary but not sufficient)
curl -s -o /tmp/fix-stubs-resp.json -w "%{http_code}" "http://127.0.0.1:5000<route>" > /tmp/fix-stubs-status

# Content check (the part the original skill skipped)
python3 - <<PY
import json, sys
status = open('/tmp/fix-stubs-status').read().strip()
if status != '200':
    sys.exit(f"FAIL: status={status}")
try:
    body = json.load(open('/tmp/fix-stubs-resp.json'))
except json.JSONDecodeError as e:
    sys.exit(f"FAIL: response is not JSON: {e}")
# Item-specific assertions go here. At minimum:
if not body or (isinstance(body, dict) and 'error' in body):
    sys.exit(f"FAIL: 200 with empty/error body: {str(body)[:200]}")
if isinstance(body, list) and len(body) == 0:
    sys.exit(f"WARN: empty list — verify this is the expected state, not a stub")
print("body assertion OK")
PY
```

The item's `lkup-plan.json` entry should declare its expected response shape under `assertions.response_shape`. If that field is missing, add it as part of this fix and surface to Ben — undocumented expected shapes are how silent regressions ship.

## Step 5 — Capture screenshot proof (MANDATORY for resolved status)

Per the global lkup.info Screenshot-Proof Rule. No item moves to `"status": "resolved"` without an artifact at:

```
~/github/ammonfife/lkup.info/screenshots/fix-stubs/<item-id>-<YYYYMMDD>.png
```

Capture path:
- **Use the `/use-e2b` skill** to drive a desktop sandbox to the rendered page and capture the screenshot. Do NOT use Ben's owner browser.
- The screenshot must show the actual rendered feature working — a list with real data, a form returning a real success message, etc. A blank page or a loading spinner is not proof.
- Filename pattern is checked by `/plan-validator` in Step 6 — do not deviate.

If E2B is unavailable, **stop and surface as a blocker**. Do not skip the screenshot.

## Step 6 — Validate via /plan-validator before writing

Before mutating `lkup-plan.json`, run `/plan-validator` against the proposed change. The validator enforces:
- Schema and URL rules
- Screenshot artifact existence at the expected path
- Status transition legality (e.g. `pending → resolved` requires both a body assertion AND a screenshot reference)

```bash
# Pseudocode — actual invocation depends on /plan-validator's interface
/plan-validator --change-set "phases[0].items[$ITEM_ID].status=resolved,screenshot=<path>"
```

If validation fails, **do not write**. Surface the failure, leave the item at its prior status, and unwind the git stash from Step 2.

## Step 7 — Update lkup-plan.json (delegated to /lkup-plan-editor)

Do NOT edit `lkup-plan.json` directly with a text Edit. Use the `/lkup-plan-editor` skill, which handles:
- Re-acquiring the file lock cleanly
- Atomic write (write-to-temp, fsync, rename)
- Rendering the HTML view via `node scripts/render-plan.cjs` immediately after
- Recording the editor's identity in the entry's `last_modified_by` field

This delegation is what prevents two `/fix-stubs` runs (or `/fix-stubs` + `/lkup-plan-editor`) from corrupting the JSON with concurrent writes.

## Step 8 — Record to Turso (real HTTP pipeline, not the bogus `facts add` CLI)

The previous version of this skill called `facts add operational ...` which **does not exist** as a CLI in this environment. Use the Turso HTTP pipeline directly:

```bash
python3 - <<'PY'
import json, urllib.request, subprocess, time, os
URL = subprocess.check_output(['bash','-c',
    'source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_DATABASE_URL" | sed "s|libsql://|https://|"'
]).decode() + "/v2/pipeline"
TOKEN = subprocess.check_output(['bash','-c',
    'source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_AUTH_TOKEN"'
]).decode()

# Find the current Claude Code session id from the most recently touched .jsonl
import glob, os
sids = sorted(glob.glob('/Users/benfife/.claude/projects/-Users-benfife/*.jsonl'),
              key=os.path.getmtime, reverse=True)
session_uuid = os.path.basename(sids[0]).replace('.jsonl','') if sids else 'unknown'

ITEM_ID = os.environ.get('ITEM_ID','?')
DESCRIPTION = os.environ.get('DESCRIPTION','?')
SCREENSHOT = os.environ.get('SCREENSHOT','?')

fact = (f"fix-stubs {ITEM_ID}: {DESCRIPTION}. "
        f"Screenshot: {SCREENSHOT}. "
        f"Body assertion: passed. Phase 0 of auction_tools→lkup.info consolidation.")

body = {"requests":[{"type":"execute","stmt":{
  "sql":"INSERT INTO facts (fact, source, category, created_by, created_by_session, created_by_platform) VALUES (?, ?, ?, ?, ?, ?)",
  "args":[
    {"type":"text","value":fact},
    {"type":"text","value":"scope:project lkup.info /fix-stubs"},
    {"type":"text","value":"operational"},
    {"type":"text","value":"Claude"},
    {"type":"text","value":session_uuid},
    {"type":"text","value":"darwin"},
  ]}}]}
req = urllib.request.Request(URL, data=json.dumps(body).encode(),
    headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
r = urllib.request.urlopen(req, timeout=20).read().decode()
res = json.loads(r)['results'][0]
if res.get('type')=='ok':
    print(f"fact recorded: id={res['response']['result'].get('last_insert_rowid')}")
else:
    raise SystemExit(f"FAIL: {res}")
PY
```

Note: the `created_by` is the **single** agent that did the work — not a hardcoded `agent:claude,agent:bob` pair. If this run is genuinely co-authored (e.g. Claude Code did the Flask port and Bob did the Supabase wiring), use `comma`-separated agent IDs in a separate `tags` field on the fact, not as the author.

## Step 9 — Sync local memory (if applicable)

```bash
# Only run if you wrote to ~/clawd/agents/<youragent>/memory/ — Claude Code's
# memory lives under ~/.claude/projects/, which is synced via claude-sync push
# (or naturally on session end).
bigmac-sync push 2>/dev/null || true
```

For Claude Code specifically, no manual sync is needed for `~/.claude/projects/-Users-benfife/memory/` writes — they're picked up automatically. The Turso write in Step 8 is the durable record.

## Step 10 — Drop the file lock and unstash

```bash
rm -f ~/.openclaw/locks/lkup-plan.json.lock
# Only drop the stash if Step 6 validation passed AND Step 4 body assertion passed.
# Otherwise leave the stash for manual review.
cd ~/github/ammonfife/lkup.info && git stash drop  # only if everything passed
```

The `trap` from Step 0 will also clean the lock if the script exits abnormally — belt and braces.

## Step 11 — Final report

Output a concise summary:
- Item id, category, file edited
- Body assertion: PASS / FAIL with the actual response shape
- Screenshot: path
- Turso fact id
- Items remaining in Phase 0 (re-run `--list` count)
- If anything was skipped: which check failed and why

## Coordination with parallel agents

There is at least one other Claude agent that touches `lkup.info`. To avoid races:

1. **Always acquire the file lock in Step 0** before reading `lkup-plan.json` for write.
2. **Never hold the lock across long-running operations** (E2B screenshot capture, Flask server restart). If you need to pause, drop the lock, do the work, re-acquire for the write step.
3. **Check `last_modified_by` on the item before writing** — if another agent updated the item while you were working, abort and re-run from Step 1.
4. **Tag your fact in Step 8** with `agent:claude` (or whichever agent invoked the skill). Search Turso for `agent:<other> AND fix-stubs` before starting a session to see what the other agent has touched recently.

## Source of truth

- `lkup-plan.json` → `consolidation.phases[0]` is the canonical work list
- `/plan-validator` is the single gate for `lkup-plan.json` mutations
- `/lkup-plan-editor` is the single writer for `lkup-plan.json`
- This skill is the workflow that drives the loop; it does not own the data
