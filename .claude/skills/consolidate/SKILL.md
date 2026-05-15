---
name: consolidate
description: Master orchestrator for the auction_tools → lkup.info consolidation. Walks every phase in lkup-plan.json sequentially, dispatches the right phase skill (/fix-stubs, /lift-module, /audit-parity, etc.) for each unresolved item, enforces the global hard constraint that auction_tools/ remains fully working throughout, gates every phase transition on /plan-validator passing, requires screenshot proof per item per the global lkup.info screenshot-proof rule, never edits lkup-plan.json directly (delegates to /lkup-plan-editor), and records every phase milestone to Turso via the real HTTP pipeline. Resumable from any interruption — reads the plan to find the first non-done phase and the first unresolved item within it.
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


# /consolidate

Master orchestrator for the auction_tools → lkup.info consolidation. Walks `lkup-plan.json` → `consolidation.phases[]` in order. Picks up wherever it left off. Never enumerates work items inline (the previous version of this skill hardcoded a 9-item list that staled the moment the plan changed) — always reads the live plan.

## Hard rules (NEVER violate)

1. **`auction_tools/` MUST remain fully working throughout.** Nothing modified, moved, or deleted there. Both repos coexist. Cutover per-feature only after proven in production.
2. **The plan is the source of truth, not this skill.** Do not hardcode item lists, fix names, or step counts inside this file. Read `lkup-plan.json` on every invocation.
3. **Delegate, never inline.** Phase 0 → `/fix-stubs`. Phase 1 → `/lift-module` + `/audit-parity`. Plan writes → `/lkup-plan-editor`. Plan reads/validation → `/plan-validator`. This skill is the conductor; the section skills do the work.
4. **Every phase transition is gated on `/plan-validator` PASS.** A phase doesn't move from `in-progress` to `done` without a green validator.
5. **Screenshot proof is required for every item with a UI surface** per the global lkup.info Screenshot-Proof Rule. Code pushed ≠ done. Deployed ≠ done. Screenshot of working feature = done.
6. **Single writer for `lkup-plan.json`.** Only `/lkup-plan-editor` writes the plan. This skill never invokes `Edit` or `Write` against `lkup-plan.json` directly.
7. **Resumable.** If interrupted at any step, the next invocation walks the plan and picks up from the first unresolved item.
8. **No sub-skill recursion races.** This skill holds NO file locks itself. Each sub-skill acquires its own locks. If two `/consolidate` runs are active, the sub-skills' locks will serialize the writes — the orchestrator stays stateless.

## Inputs

```bash
/consolidate                          # full pipeline from current resume point
/consolidate --phase <n>              # only run phase n (e.g. --phase 1 to lift modules)
/consolidate --status                 # show current state of every phase, no work
/consolidate --dry-run                # walk the pipeline but call sub-skills with --dry-run
/consolidate --resume                 # explicit resume from last checkpoint (default behavior anyway)
```

## Step 0 — Pre-flight

```bash
PLAN=~/github/ammonfife/lkup.info/lkup-plan.json
[ -f "$PLAN" ] || { echo "FAIL: $PLAN missing"; exit 1; }
python3 -c "import json; json.load(open('$PLAN'))" \
  || { echo "FAIL: $PLAN unparseable"; exit 1; }

# Hard constraint check #1 — auction_tools is clean
cd ~/github/ammonfife/auction_tools
git diff --quiet HEAD \
  || { echo "FAIL: auction_tools/ has uncommitted changes — refusing to consolidate from a dirty source"; exit 1; }
SOURCE_SHA=$(git rev-parse --short HEAD)

# Hard constraint check #2 — every required sub-skill is present
for s in plan-validator lkup-plan-editor fix-stubs lift-module audit-parity use-e2b; do
  [ -f ~/.claude/skills/$s/SKILL.md ] \
    || { echo "FAIL: required sub-skill missing: /$s"; exit 1; }
done

# Sanity check — current plan state validates against itself
/plan-validator --current > /tmp/consolidate-pre-validate.json 2>/tmp/consolidate-pre-validate.txt
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "FAIL: current plan state has existing violations — fix before consolidating"
  cat /tmp/consolidate-pre-validate.txt
  exit 1
fi
```

The pre-validate is critical: if the plan already has violations BEFORE we start, the orchestrator would attribute them to its own work. Fix existing violations first.

## --status mode

Reads the plan and prints a one-line summary per phase plus the next unresolved item:

```python
import json
plan = json.load(open('/Users/benfife/github/ammonfife/lkup.info/lkup-plan.json'))
phases = plan['consolidation']['phases']
for i, p in enumerate(phases):
    name = p.get('name', f'Phase {i}')
    status = p.get('status', 'pending')
    items = p.get('items') or p.get('modules') or []
    resolved = sum(1 for x in items if x.get('status') == 'resolved')
    total = len(items)
    mark = {'done':'✓','in-progress':'·','pending':' '}.get(status,'?')
    print(f"  {mark} Phase {i}: {name}  ({status}, {resolved}/{total})")
    if status == 'in-progress':
        next_item = next((x for x in items if x.get('status') != 'resolved'), None)
        if next_item:
            print(f"      next: {next_item.get('id') or next_item.get('name','?')}")
```

Use `--status` to see where you are without doing any work. Use it before invoking the orchestrator to confirm the resume point.

## Step 1 — Pick the resume point

```python
import json
plan = json.load(open('/Users/benfife/github/ammonfife/lkup.info/lkup-plan.json'))
phases = plan['consolidation']['phases']

# First phase that isn't 'done' is where we start
for i, p in enumerate(phases):
    if p.get('status') != 'done':
        START_PHASE = i
        break
else:
    print("All phases done. Nothing to do.")
    sys.exit(0)
```

If `--phase <n>` was passed, override and run only that phase.

## Step 2 — Walk the phases

For each phase from `START_PHASE` onward:

```python
phase = phases[i]
name = phase.get('name', f'Phase {i}')
print(f"\n=== Phase {i}: {name} ===")

# Mark phase as in-progress via /lkup-plan-editor
if phase.get('status') != 'in-progress':
    subprocess.run(['/lkup-plan-editor', '--change-set',
        f'{{"phases[{i}].status":"in-progress","phases[{i}].started_at":"{now()}"}}'])

# Dispatch to the right sub-skill based on the phase kind
phase_kind = phase.get('kind')  # one of: stubs, lift, desktop, extension, enrichment, repo
dispatch = {
    'stubs':      run_phase_stubs,        # delegates to /fix-stubs
    'lift':       run_phase_lift,         # delegates to /lift-module + /audit-parity
    'desktop':    run_phase_desktop,
    'extension':  run_phase_extension,
    'enrichment': run_phase_enrichment,
    'repo':       run_phase_repo,
}
handler = dispatch.get(phase_kind)
if handler is None:
    print(f"FAIL: unknown phase kind '{phase_kind}' on phase {i}")
    sys.exit(1)
handler(phase, i)

# After every phase: validate, then mark done
validate_or_die()
subprocess.run(['/lkup-plan-editor', '--change-set',
    f'{{"phases[{i}].status":"done","phases[{i}].completed_at":"{now()}"}}'])

# Between every step: verify the hard constraints still hold
verify_auction_tools_unchanged()
verify_lkup_info_serves_200_with_real_content()  # NOT just status — body content too
record_milestone_to_turso(f"Phase {i} ({name}) complete")
```

## Phase handlers

Each handler is a thin wrapper that walks `phase.items` (or `phase.modules`) and dispatches the appropriate sub-skill per item. **None of them enumerate the items inline.** They all read from the plan.

### `run_phase_stubs` (Phase 0)
```python
def run_phase_stubs(phase, idx):
    items = phase.get('items', [])
    for item in items:
        if item.get('status') == 'resolved':
            continue
        item_id = item.get('id')
        print(f"  → /fix-stubs {item_id}")
        rc = subprocess.run(['/fix-stubs', item_id]).returncode
        if rc != 0:
            print(f"  ✗ /fix-stubs {item_id} failed (rc={rc}) — stopping phase")
            return  # leave phase in-progress, do not continue
        # /fix-stubs handles its own /lkup-plan-editor call for the status update
```

### `run_phase_lift` (Phase 1)
```python
def run_phase_lift(phase, idx):
    modules = phase.get('modules', [])
    for m in modules:
        if m.get('status') == 'resolved':
            continue
        name = m.get('name')
        # /lift-module Step 0.5 already runs the already-working detection gate.
        # If a module's lkup.info side is already production-quality, /lift-module
        # will exit 0 without porting and print the ABORT banner. The orchestrator
        # treats that as success — the item is resolved with `pre-existing`
        # provenance, no Python was overwritten, and we move on.
        print(f"  → /lift-module {name}")
        rc = subprocess.run(['/lift-module', name]).returncode
        if rc != 0:
            print(f"  ✗ /lift-module {name} failed (rc={rc}) — stopping phase")
            return
        # After every module: re-read the plan to check whether the item ended up
        # marked resolved with `pre-existing` provenance. If so, log a milestone
        # so the consolidation history shows which modules were already-built vs
        # newly-ported.
        plan_after = json.load(open('/Users/benfife/github/ammonfife/lkup.info/lkup-plan.json'))
        m_after = next((x for x in plan_after['consolidation']['phases'][idx]['modules']
                        if x.get('name') == name), None)
        if m_after and m_after.get('provenance') == 'pre-existing lkup.info implementation':
            record_milestone(f"Phase 1 module {name}: kept pre-existing lkup.info implementation, no port", 'architecture')
        elif m_after and m_after.get('status') == 'resolved':
            record_milestone(f"Phase 1 module {name}: ported Python→TS, parity verified", 'operational')
```

### `run_phase_desktop` (Phase 2)
Wrap the existing React frontend as a desktop window. The plan should declare:
- `framework` (Tauri vs Electron — make the choice once, record in plan)
- `native_bindings[]` (each USB/BT/printer integration as its own item)
- `parity_target` (auction_tools/desktop_scanner.py is the comparison)

For each native binding item, the handler ports it to the desktop scaffold and runs both the desktop wrap AND the original Python desktop_scanner.py side-by-side as a parity verification. Both must work simultaneously through this phase.

### `run_phase_extension` (Phase 3)
Walk `phase.scripts[]` — each entry is a content script (NGC scraper, PCGS scraper, Whatnot overlay, etc.) being ported into a unified extension manifest. Each script becomes its own item with its own screenshot requirement.

### `run_phase_enrichment` (Phase 4)
Walk `phase.functions[]` — each is a Python enrichment function being ported to a Supabase Edge Function or Cloud Run Job. Old launchd crons stay running until the new pipeline produces matching output for N consecutive nights (configured per function).

### `run_phase_repo` (Phase 5)
Validate the final directory layout matches `phase.structure`. This is a structural assertion phase, no code changes. Failures here mean a previous phase produced files in the wrong place.

## Between every phase

These checks run AFTER every successful phase, BEFORE marking it done:

```bash
# 1. /plan-validator must pass against the current state
/plan-validator --current || { echo "FAIL: post-phase validator"; exit 1; }

# 2. auction_tools must be unchanged
cd ~/github/ammonfife/auction_tools
[ "$(git rev-parse HEAD)" = "$SOURCE_SHA" ] \
  || { echo "FAIL: auction_tools HEAD moved during phase — investigate"; exit 1; }
git diff --quiet HEAD \
  || { echo "FAIL: auction_tools dirty after phase"; exit 1; }

# 3. lkup.info still serves real content (HTTP 200 ≠ working)
curl -s http://127.0.0.1:5000/api/health > /tmp/consolidate-health.json
python3 -c "
import json
d = json.load(open('/tmp/consolidate-health.json'))
assert d.get('status') == 'ok', f'health endpoint not ok: {d}'
assert 'version' in d and d['version'], 'health response missing version field'
" || { echo "FAIL: lkup.info health check (body content, not just 200)"; exit 1; }

# 4. desktop_scanner.py still launches and runs its smoke test
cd ~/github/ammonfife/auction_tools
python3 production/scanners/unified/desktop_scanner.py --smoke-test \
  || { echo "FAIL: desktop_scanner.py broken — phase reverted nothing but consolidation drift"; exit 1; }

# 5. record the milestone
record_milestone_to_turso "Phase $i complete"
```

## Recording milestones to Turso (real HTTP pipeline)

The previous version called `facts add operational ...` which **does not exist** as a CLI in this environment. Replace inline:

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

def record_milestone(text, category='operational'):
    body = {"requests":[{"type":"execute","stmt":{
      "sql":"INSERT INTO facts (fact, source, category, created_by, created_by_session, created_by_platform) VALUES (?, ?, ?, ?, ?, ?)",
      "args":[
        {"type":"text","value":f"consolidate: {text}"},
        {"type":"text","value":"scope:project lkup.info /consolidate"},
        {"type":"text","value":category},
        {"type":"text","value":"Claude"},
        {"type":"text","value":session_uuid},
        {"type":"text","value":"darwin"},
      ]}}]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())['results'][0]
    if res.get('type') != 'ok':
        raise SystemExit(f"Turso write failed: {res}")
    return res['response']['result'].get('last_insert_rowid')
```

Categories:
- `operational` — phase completion, item resolution, smoke-test passes
- `architecture` — decisions made during the phase (e.g. "Phase 2: chose Tauri over Electron because the native USB binding for X is Rust-only")
- The `created_by` is the SINGLE agent running the orchestrator. Tags can be a separate field but the author is one agent.

## --dry-run mode

Walks the pipeline calling each sub-skill with its own `--dry-run` flag (or `--list` for skills that have one). Produces the full work plan that WOULD be executed, with no writes. Useful for previewing a long phase before kicking it off.

## Resume semantics

If `/consolidate` is interrupted (Ctrl-C, crash, machine reboot), the next invocation:
1. Reads `lkup-plan.json`
2. Finds the first phase whose `status != 'done'`
3. Inside that phase, finds the first item whose `status != 'resolved'`
4. Picks up from that item

No state file is needed — the plan IS the state. The `started_at` / `completed_at` timestamps on each phase are the audit trail.

If a sub-skill failed mid-item, the item's `status` will be whatever the sub-skill last set it to (typically `pending` or `blocked`). Resume re-attempts that item from scratch.

## Final report

After every phase or after the orchestrator completes:

```
=== /consolidate run summary ===
Started:      <timestamp>
Phases run:   N
Phases done:  M
Items resolved this run: K
Plan version: vX.Y → vX.Z (after the bumps)
auction_tools SHA: <pinned source>
Hard constraints:
  ✓ auction_tools/ unchanged
  ✓ lkup.info /api/health responds with real content
  ✓ desktop_scanner.py smoke test passes
  ✓ /plan-validator current state: PASS
Turso facts recorded: <list of fact ids>
Next: <name of next unresolved item, if any>
```

## Source of truth

- `lkup-plan.json` is the canonical work list
- `/plan-validator` is the canonical pre-write gate
- `/lkup-plan-editor` is the canonical writer
- `/fix-stubs`, `/lift-module`, `/audit-parity` are the canonical workers
- This skill is the canonical orchestrator — it owns NO data, holds NO locks, enforces NO rules that the sub-skills don't already enforce
