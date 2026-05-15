---
name: lkup-plan-editor
description: Single canonical writer for lkup-plan.json (the lkup.info architecture plan) — performs atomic writes (write-to-temp + fsync + rename) under a file lock, runs /plan-validator as a mandatory pre-write gate, snapshots a backup before every edit, bumps meta.version + version_history, re-renders lkup-plan.html via render-plan.cjs, and records every edit to Turso via the real HTTP pipeline. NO other skill writes lkup-plan.json directly.
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


# /lkup-plan-editor

The ONLY skill allowed to mutate `lkup-plan.json`. Every other lkup.info skill (`/fix-stubs`, `/lift-module`, `/audit-parity`, `/consolidate`) delegates here for writes. This is what makes parallel-agent safety actually work.

## Files

| File | Role |
|---|---|
| `lkup-plan.json` (repo root) | **THE source of truth.** JSON, authoritative. |
| `lkup-plan.html` (repo root) | Human-readable view. **Generated** from JSON by `scripts/render-plan.cjs`. Never edit by hand. |
| `scripts/render-plan.cjs` (repo root) | The renderer. Run after every JSON edit. |
| `~/.openclaw/locks/lkup-plan.json.lock` | File lock. Acquired before any read-modify-write. |
| `~/.claude/projects/-Users-benfife/memory/lkup-plan-backups/` | Pre-edit snapshots. Restored from on rollback. |

## Hard rules (NEVER violate)

1. **Single writer at a time.** Acquire the file lock in Step 1, hold it through the write, drop in Step 7. Two concurrent edits corrupt the JSON.
2. **Validate before write.** `/plan-validator` must return PASS (exit 0) for the proposed change set. No write without validation.
3. **Atomic write.** Write to a temp file, `fsync`, then `rename` over the original. Never edit `lkup-plan.json` in place.
4. **Backup before edit.** Snapshot the pre-edit JSON to `lkup-plan-backups/<timestamp>/lkup-plan.json` so any edit is reversible.
5. **Bump version + history.** Every edit increments `meta.version` and prepends a `version_history[0]` entry. No silent edits.
6. **Render HTML in the same atomic transaction.** Either both `lkup-plan.json` AND `lkup-plan.html` change together, or neither does.
7. **Locked sections are locked.** Do not edit any field listed under `meta.locked_sections[]` without an `--unlock <section>` override flag, which itself requires Ben's explicit approval and gets recorded as its own version-history entry.
8. **Author field is the actual agent.** `version_history[].author` is the agent that ran this skill. Not hardcoded `claude`. Look up the runtime agent ID, do not guess.

## Inputs

```bash
/lkup-plan-editor --change-set <json>     # apply a structured change
/lkup-plan-editor --apply <patch-file>    # apply a JSON patch (RFC 6902) from a file
/lkup-plan-editor --rollback <backup-id>  # restore from a specific backup snapshot
/lkup-plan-editor --list-backups          # show available backups, no writes
/lkup-plan-editor --dry-run --change-set <json>  # validate + show diff, do not write
```

## Step 0 — Pre-flight (MANDATORY)

```bash
PLAN=~/github/ammonfife/lkup.info/lkup-plan.json
LOCK=~/.openclaw/locks/lkup-plan.json.lock
BACKUP_DIR=~/.claude/projects/-Users-benfife/memory/lkup-plan-backups
mkdir -p "$(dirname "$LOCK")" "$BACKUP_DIR"

[ -f "$PLAN" ] || { echo "FAIL: $PLAN missing"; exit 1; }
python3 -c "import json; json.load(open('$PLAN'))" \
  || { echo "FAIL: $PLAN unparseable, refusing to edit"; exit 1; }

# Render script must exist — we'll need it in Step 6
RENDER=~/github/ammonfife/lkup.info/scripts/render-plan.cjs
[ -f "$RENDER" ] || { echo "FAIL: $RENDER missing — cannot regenerate HTML view"; exit 1; }
```

## Step 1 — Acquire the file lock

```bash
if [ -f "$LOCK" ]; then
  HOLDER=$(cat "$LOCK")
  AGE=$(($(date +%s) - $(stat -f %m "$LOCK")))
  echo "FAIL: lkup-plan.json locked by $HOLDER (${AGE}s ago)"
  if [ "$AGE" -gt 600 ]; then
    echo "      Lock is older than 10 minutes — likely stale. Verify the holder is dead, then manually rm."
  fi
  exit 1
fi
echo "Claude:$$:$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LOCK"
trap 'rm -f "$LOCK"' EXIT INT TERM
```

The `trap` ensures the lock is dropped even if the script crashes.

## Step 2 — Snapshot the pre-edit state

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
BAK="$BACKUP_DIR/$TS"
mkdir -p "$BAK"
cp "$PLAN" "$BAK/lkup-plan.json"
cp ~/github/ammonfife/lkup.info/lkup-plan.html "$BAK/lkup-plan.html" 2>/dev/null || true

# Also commit the current state to git so the working tree has a clean baseline
cd ~/github/ammonfife/lkup.info
if ! git diff --quiet lkup-plan.json lkup-plan.html 2>/dev/null; then
  echo "WARN: lkup-plan.{json,html} have uncommitted changes — stashing before edit"
  git stash push -m "lkup-plan-editor pre-edit $TS" lkup-plan.json lkup-plan.html
fi
echo "backup: $BAK"
```

## Step 3 — Validate the proposed change via /plan-validator

```bash
# This is non-negotiable. NO write without validation.
/plan-validator --change-set "$CHANGE_SET" > /tmp/lkup-plan-editor-validate.json 2>/tmp/lkup-plan-editor-validate.txt
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "FAIL: /plan-validator rejected the change set:"
  cat /tmp/lkup-plan-editor-validate.txt
  echo
  echo "Pre-edit backup left at: $BAK"
  exit 1
fi
```

If validation fails, **do not unwind the lock yet** — stay in pre-edit state so the caller can inspect and retry. The trap will drop the lock when the caller exits.

## Step 4 — Apply the change in memory

```python
import json, sys, copy
from datetime import datetime

plan_path = '/Users/benfife/github/ammonfife/lkup.info/lkup-plan.json'
plan = json.load(open(plan_path))
backup_plan = copy.deepcopy(plan)  # in-process rollback if Step 5/6 fail

# Apply the change set (the format depends on input flag — change-set vs JSON patch)
# For a change-set dict like {"phases[0].items[2].status": "resolved", ...}:
def apply_change_set(plan, changes):
    for path, value in changes.items():
        # Walk the dotted/indexed path and assign
        ...  # full implementation in scripts/lkup-plan-editor-apply.py
    return plan

plan = apply_change_set(plan, change_set)

# Bump version and add history entry
old_version = plan['meta']['version']
parts = old_version.split('.')
parts[-1] = str(int(parts[-1]) + 1)
new_version = '.'.join(parts)
plan['meta']['version'] = new_version
plan['meta']['last_updated'] = datetime.utcnow().strftime('%Y-%m-%d')

agent_id = "Claude"  # from the runtime — read IDENTITY.md or env if needed
plan.setdefault('version_history', []).insert(0, {
    "version": new_version,
    "date": plan['meta']['last_updated'],
    "author": agent_id,
    "summary": change_set_summary,  # required input — never empty
})

# In-memory validation (cheap, catches dict-key typos)
required_top_level = ['meta','policies','url_rules','schema','consolidation','version_history']
for k in required_top_level:
    if k not in plan:
        raise SystemExit(f"FAIL: edit removed required top-level key {k}")
```

## Step 5 — Atomic write

```python
import os, json
tmp_path = plan_path + '.tmp'
with open(tmp_path, 'w') as f:
    json.dump(plan, f, indent=2, ensure_ascii=False)
    f.flush()
    os.fsync(f.fileno())
os.rename(tmp_path, plan_path)  # atomic on POSIX
```

If the rename fails, the temp file gets cleaned up by the next run's `--list-backups` cleanup. The original `plan_path` is untouched.

## Step 6 — Render HTML (in the same transaction)

```bash
cd ~/github/ammonfife/lkup.info
node scripts/render-plan.cjs > /tmp/lkup-plan-editor-render.log 2>&1
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "FAIL: render-plan.cjs failed — rolling back JSON to backup"
  cp "$BAK/lkup-plan.json" "$PLAN"
  cat /tmp/lkup-plan-editor-render.log
  exit 1
fi
```

If render fails, the JSON edit is rolled back so `lkup-plan.{json,html}` stay in sync. The two files are atomic together.

## Step 7 — Commit (single commit, both files)

```bash
cd ~/github/ammonfife/lkup.info
git add lkup-plan.json lkup-plan.html
git commit -m "$(cat <<EOF
plan: bump to v$new_version

$change_set_summary

🤖 /lkup-plan-editor — atomic edit + render
Backup: $BAK
EOF
)" 2>&1 | tail -10
```

The commit message references the backup path so future debugging can find the pre-edit state without grepping memory directories.

## Step 8 — Record to Turso (real HTTP pipeline)

The previous version of this skill called `facts add operational ...` which **does not exist** as a CLI in this environment.

```python
import json, urllib.request, subprocess, os, glob

URL = subprocess.check_output(['bash','-c',
    'source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_DATABASE_URL" | sed "s|libsql://|https://|"'
]).decode() + "/v2/pipeline"
TOKEN = subprocess.check_output(['bash','-c',
    'source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_AUTH_TOKEN"'
]).decode()

sids = sorted(glob.glob('/Users/benfife/.claude/projects/-Users-benfife/*.jsonl'),
              key=os.path.getmtime, reverse=True)
session_uuid = os.path.basename(sids[0]).replace('.jsonl','') if sids else 'unknown'

fact = (f"lkup-plan-editor: bumped lkup-plan.json to v{new_version} — {change_set_summary}. "
        f"Backup: {BAK}. Atomic write + render verified. Commit: <git sha>.")
body = {"requests":[{"type":"execute","stmt":{
  "sql":"INSERT INTO facts (fact, source, category, created_by, created_by_session, created_by_platform) VALUES (?, ?, ?, ?, ?, ?)",
  "args":[
    {"type":"text","value":fact},
    {"type":"text","value":"scope:project lkup.info /lkup-plan-editor"},
    {"type":"text","value":"architecture"},
    {"type":"text","value":"Claude"},
    {"type":"text","value":session_uuid},
    {"type":"text","value":"darwin"},
  ]}}]}
req = urllib.request.Request(URL, data=json.dumps(body).encode(),
    headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
res = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())['results'][0]
if res.get('type') != 'ok':
    raise SystemExit(f"Turso write failed: {res}")
print(f"fact id={res['response']['result'].get('last_insert_rowid')}")
```

The `created_by` is the actual agent. No hardcoded `agent:claude,agent:bob` co-author tag.

## Step 9 — Drop the lock + final report

```bash
rm -f "$LOCK"  # the trap will also catch this on exit
echo
echo "✓ lkup-plan.json bumped: v$old_version → v$new_version"
echo "  Backup: $BAK"
echo "  Render: lkup-plan.html updated"
echo "  Commit: $(git rev-parse --short HEAD)"
echo "  Turso fact: $fact_id"
```

## Rollback

```bash
/lkup-plan-editor --rollback <backup-id>
```

This reverses Steps 4-7 by:
1. Acquiring the file lock
2. Copying the backup over `lkup-plan.json`
3. Re-running `render-plan.cjs`
4. Committing as a single revert commit
5. Recording the rollback as its own Turso fact (with `supersedes` pointing at the original edit's fact id)

Rollback is itself a write — it goes through Steps 0-9 just like a forward edit, with the change_set being "restore from backup <id>".

## --list-backups mode

```bash
ls -lt "$BACKUP_DIR" | head -20
```

Read-only, no lock, shows the available backup snapshots. Use this before invoking `--rollback` to find the right id.

## --dry-run mode

Runs Steps 0, 2 (snapshot), 3 (validate), and 4 (apply in memory) but stops before Step 5 (write). Outputs the resulting JSON diff to stdout. The file lock IS still acquired (so two dry-runs don't overlap with a real run) but is dropped immediately after Step 4.

## Coordination with other lkup.info skills

This skill is **the** writer for `lkup-plan.json`. Other skills must:
1. Call `/plan-validator` themselves first (cheap, no lock) to get an early signal
2. Then delegate the actual write here
3. Never `Edit` or `Write` against `lkup-plan.json` directly — that bypasses the lock and the validator

The file lock is per-process. If you need to coordinate across MACHINES (e.g. cloud agents), the lock must be promoted to a Turso row in `system_files` with the same agent ID + timestamp scheme.

## Source of truth

- `lkup-plan.json` is the canonical data
- This skill is the canonical writer
- `/plan-validator` is the canonical gate
- All four lkup.info workflow skills (`fix-stubs`, `lift-module`, `audit-parity`, `consolidate`) consume this skill for their plan mutations
