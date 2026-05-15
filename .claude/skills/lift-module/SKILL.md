---
name: lift-module
description: Port a Python module from auction_tools/ to TypeScript in lkup.info — Phase 1 of the auction_tools → lkup.info consolidation. ALWAYS runs an already-working detection gate first to avoid porting over a lkup.info implementation that's already production-quality (the TS side is sometimes ahead of the Python). Only ports when the lkup.info side is missing or stub. Reads the source completely, ports constants and edge cases, generates a parity test fixture, runs /audit-parity, requires PASS before any /lkup-plan-editor status update, captures a screenshot of the ported module live in lkup.info before marking resolved (per the global screenshot-proof rule), records every port to Turso via the real HTTP pipeline.
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


# /lift-module

Phase 1 of the auction_tools → lkup.info consolidation: when a Python business-logic module in `auction_tools/` does NOT yet have a working equivalent in `lkup.info/shared/<name>/`, lift it across as a TypeScript module so it's reusable across web, desktop, extension, and mobile.

**Critical: this skill is NOT a one-way "Python is the truth" port.** Some `lkup.info/shared/` modules have already been independently developed and are production-quality. This skill MUST detect that case in Step 0.5 and refuse to overwrite working code. The auction_tools Python is the **fallback source** when the lkup.info side is missing or stub — it is not automatically canonical.

Source of truth: `lkup-plan.json` → `consolidation.phases[1].modules[]`.

## Hard rules (NEVER violate)

1. **NEVER overwrite a working lkup.info implementation with an auction_tools port.** Step 0.5 (already-working detection) is the gate that catches this. If the lkup.info side already exists with non-trivial content AND has tests AND is wired into a real consumer, the auction_tools Python is NOT canonical for this module. Mark the item resolved with `provenance: "pre-existing lkup.info implementation"` and STOP. Surface to the operator. Do not even read the Python source.
2. **Do NOT modify `auction_tools/`.** Not the Python source, not the surrounding files. The Python keeps working through and after the port. Per the consolidation hard constraint.
3. **Server stays authoritative for resolution.** Even after the TS port lands, the server is still the source of truth for any scan/lookup result. The TS module exists for client-side preview, validation, and offline fallback — never as the canonical answer.
4. **Test parity is mandatory** (when porting). Every test case in the Python source — inline doctests, pytest cases, fixture files, hand-written examples in docstrings — gets a matching TS test that asserts identical output. `/audit-parity` runs both sides and must return PASS before status moves.
5. **Screenshot proof on first use** — when the TS port goes live in lkup.info (via a page that imports it), capture a screenshot showing it producing the expected output on a real input. No screenshot, no `resolved` status. (Applies to both fresh ports and pre-existing implementations being marked resolved.)
6. **No invented constants.** Every magic number, regex, prefix table, error message, and edge case that exists in the Python source MUST appear in the TS port. Diff the constants by hand if necessary. (Only applies when porting — not when keeping a pre-existing TS implementation.)
7. **No new dependencies.** If the port needs a new npm package, stop and surface it as a blocker. Do not silently add to `package.json`.
8. **Single writer for `lkup-plan.json`.** Status updates after a successful port go through `/lkup-plan-editor`, never inline.

## Module map (current as of plan v5.x — re-read on every invocation)

| Module | Source (auction_tools/) | Target (lkup.info/shared/) | Owner |
|---|---|---|---|
| Barcode parser | `lkup_info_site/cloud_run/libs/barcode_parser/` | `barcode-parser/` | server-authoritative; client preview only |
| Pricing engine | `production/scanners/unified/enrichment/price_fetcher.py` + `item_valuator.py` | `pricing/` | server-authoritative |
| Coin title parser | `collection_enrichment/coin_xref_enrichment.py` | `coin-parser/` | shared (deterministic — safe for client) |
| Label generator | `desktop_scanner.py` (label sections) | `labels/` | shared (rendering only — no I/O) |

If the table here drifts from `lkup-plan.json`, **the JSON wins** — re-read the plan in Step 1.

## Inputs

```bash
/lift-module <module-name>     # port a specific module from the table above
/lift-module --list            # show next unported module without doing anything
/lift-module --status          # show port status of every module in the plan
```

## Step 0 — Pre-flight

```bash
PLAN=~/github/ammonfife/lkup.info/lkup-plan.json
[ -f "$PLAN" ] || { echo "FAIL: $PLAN missing"; exit 1; }

# Validate the plan parses and has phase 1
python3 - <<'PY' || exit 1
import json, sys
d = json.load(open('PLAN_PATH_HERE'))
phases = d.get('consolidation', {}).get('phases', [])
if len(phases) < 2: sys.exit("FAIL: no consolidation.phases[1]")
modules = phases[1].get('modules', [])
if not modules: sys.exit("FAIL: phases[1].modules empty")
PY

# auction_tools must exist and be untouched
[ -d ~/github/ammonfife/auction_tools ] || { echo "FAIL: auction_tools missing"; exit 1; }
cd ~/github/ammonfife/auction_tools
if ! git diff --quiet HEAD; then
  echo "FAIL: auction_tools has uncommitted changes — refusing to port from a dirty source"
  echo "      The Python source must be a known commit so the TS port can pin against it."
  exit 1
fi
SOURCE_SHA=$(git rev-parse --short HEAD)
echo "auction_tools source pinned at: $SOURCE_SHA"
```

## Step 0.5 — Already-working detection gate (MANDATORY, runs every invocation before Step 1)

Before reading a single line of the Python source, determine whether the lkup.info side already has a production-quality implementation. If it does, **abort the port** and mark the item resolved with provenance pointing at the existing TS code.

```bash
TARGET=~/github/ammonfife/lkup.info/shared/$MODULE_NAME

# Signal 1: target directory exists with non-trivial content
if [ ! -d "$TARGET" ]; then
  echo "  signal 1 (target dir exists): NO — proceeding to port"
  ALREADY_WORKING=0
elif [ "$(find "$TARGET" -name '*.ts' -not -path '*/node_modules/*' | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')" -lt 50 ]; then
  echo "  signal 1: target dir exists but <50 lines of TS — looks like a stub, proceeding to port"
  ALREADY_WORKING=0
else
  echo "  signal 1: target dir has substantial TS content"
  SIGNAL_1=1
fi

# Signal 2: target has its own tests (not the python-cases.json fixture-only kind)
TS_TEST_LINES=$(find "$TARGET/__tests__" -name '*.test.ts' -not -name '*python-cases*' 2>/dev/null \
  | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
if [ "${TS_TEST_LINES:-0}" -ge 30 ]; then
  echo "  signal 2 (independent tests exist): YES (${TS_TEST_LINES} lines)"
  SIGNAL_2=1
else
  echo "  signal 2: no independent tests found"
fi

# Signal 3: target is imported by at least one real consumer in src/
CONSUMERS=$(grep -rln "from ['\"].*shared/$MODULE_NAME" \
  ~/github/ammonfife/lkup.info/src \
  ~/github/ammonfife/lkup.info/api-python 2>/dev/null \
  | grep -v node_modules | grep -v __tests__)
if [ -n "$CONSUMERS" ]; then
  N=$(echo "$CONSUMERS" | wc -l)
  echo "  signal 3 (real consumers): YES — $N file(s):"
  echo "$CONSUMERS" | sed 's/^/      /'
  SIGNAL_3=1
else
  echo "  signal 3: no consumers in src/ or api-python/"
fi

# Signal 4: a screenshot artifact exists for this module
SHOTS=$(ls ~/github/ammonfife/lkup.info/screenshots/lift-module/$MODULE_NAME-*.png 2>/dev/null)
if [ -n "$SHOTS" ]; then
  echo "  signal 4 (screenshot proof exists): YES"
  echo "$SHOTS" | sed 's/^/      /'
  SIGNAL_4=1
else
  echo "  signal 4: no screenshot artifact"
fi

# Signal 5: explicit flag in lkup-plan.json
EXPLICIT=$(python3 -c "
import json
plan = json.load(open('/Users/benfife/github/ammonfife/lkup.info/lkup-plan.json'))
mods = plan['consolidation']['phases'][1].get('modules', [])
m = next((x for x in mods if x.get('name')=='$MODULE_NAME'), None)
if m and m.get('provenance') == 'pre-existing lkup.info implementation':
    print('1')
")
if [ "$EXPLICIT" = "1" ]; then
  echo "  signal 5 (explicit pre-existing flag in plan): YES"
  SIGNAL_5=1
fi

# Decision
SCORE=$((${SIGNAL_1:-0} + ${SIGNAL_2:-0} + ${SIGNAL_3:-0} + ${SIGNAL_4:-0} + ${SIGNAL_5:-0}))
echo "  detection score: $SCORE / 5"

if [ "$SCORE" -ge 3 ] || [ "$SIGNAL_5" = "1" ]; then
  cat <<DECISION

╔══════════════════════════════════════════════════════════════╗
║ ALREADY-WORKING DETECTED: $MODULE_NAME
║ The lkup.info side appears to already have a production
║ implementation. ABORTING the port to avoid overwriting good
║ code with an auction_tools rewrite.
║
║ Recommended action: skip the port and mark this Phase 1 item
║ resolved with provenance="pre-existing lkup.info implementation".
║
║ Run /audit-parity --module $MODULE_NAME --against-existing
║ to verify the existing TS implementation matches the Python
║ behavior on the same fixture (see /audit-parity for details).
║ A passing parity check is a stronger signal of "this is fine"
║ than the heuristics above.
║
║ If you DISAGREE with this detection and want to force the port
║ anyway, re-run with --force-overwrite (and be ready to defend
║ why the existing TS code needs to be replaced).
╚══════════════════════════════════════════════════════════════╝

DECISION
  if [ "$FORCE_OVERWRITE" != "1" ]; then
    echo "Aborting. Use --force-overwrite to proceed regardless."
    exit 0  # not an error — this is the correct behavior
  fi
  echo "WARN: --force-overwrite specified. Proceeding to port over the existing implementation."
elif [ "$SCORE" -ge 1 ]; then
  cat <<PARTIAL
  WARN: partial signals of an existing implementation (score $SCORE/5).
  The lkup.info side has SOME content but not enough to be confident.
  Proceeding to Step 1 (read Python source) but you should manually
  inspect $TARGET before doing the actual port in Step 3.
PARTIAL
fi
```

**Decision matrix:**

| Score | Meaning | Default action |
|---|---|---|
| 5/5 | All signals present | ABORT — mark resolved with `pre-existing` provenance |
| 3-4/5 | Strong evidence of pre-existing impl | ABORT (unless `--force-overwrite`) |
| 1-2/5 | Partial evidence | WARN, proceed to read source but operator must inspect manually before Step 3 |
| 0/5 | No evidence | Proceed normally — fresh port |

Signal 5 (explicit `provenance` flag in the plan) overrides the score: if the plan says it's pre-existing, it's pre-existing regardless of the heuristic count.

The `--force-overwrite` flag should be used **rarely**. Document the reason in the Turso fact (Step 9).

## --list and --status modes (read-only)

```python
import json
plan = json.load(open('/Users/benfife/github/ammonfife/lkup.info/lkup-plan.json'))
modules = plan['consolidation']['phases'][1].get('modules', [])

# --list
unported = [m for m in modules if m.get('status') != 'resolved']
print(f"unported Phase 1 modules: {len(unported)} / {len(modules)}")
for m in unported[:5]:
    print(f"\n  {m.get('name','?')}")
    print(f"    source: {m.get('source','?')}")
    print(f"    target: {m.get('target','?')}")
    print(f"    parity_tests: {len(m.get('parity_tests', []))}")

# --status
for m in modules:
    s = m.get('status','pending')
    mark = {'resolved':'✓','blocked':'⚠','pending':'·'}.get(s,'?')
    print(f"  {mark} {m.get('name','?')}  ({s})")
```

## Step 0.75 — Pick a CLAIMABLE module + claim it before reading source

After Step 0.5 (already-working detection) decides this module IS due for a port, the orchestrator must CLAIM the work item before doing anything that takes time. Without a claim, two agents reading the same Python source in parallel produce duplicate ports and racing commits.

Pick the next claimable module:
```python
import json, time
plan = json.load(open('/Users/benfife/github/ammonfife/lkup.info/lkup-plan.json'))
modules = plan['consolidation']['phases'][1].get('modules', [])
SELF = "Claude"; NOW = int(time.time()); STALE = 15*60

def is_claimable(m):
    s = m.get('status','pending')
    if s == 'resolved': return False
    if s == 'in-progress':
        if m.get('assigned_to') == SELF: return True
        if NOW - m.get('claimed_at',0) > STALE: return True
        return False
    return True
```

Claim it (atomic via /lkup-plan-editor):
```bash
/lkup-plan-editor --change-set "{
  \"phases[1].modules[$IDX].status\": \"in-progress\",
  \"phases[1].modules[$IDX].assigned_to\": \"Claude\",
  \"phases[1].modules[$IDX].claimed_at\": $(date +%s),
  \"phases[1].modules[$IDX].claimed_by_session\": \"$SESSION_UUID\"
}"
```

If `/lkup-plan-editor` rejects the write because /plan-validator says the item is already in-progress (and not stale, and not yours), pick the next claimable module instead. Do not steal claims without `--steal` and a stale-claim justification.

**Heartbeat for long steps.** Reading a 5000-line Python source + porting + parity testing can take >15 minutes. Refresh the claim periodically:
```bash
/lkup-plan-editor --change-set "{\"phases[1].modules[$IDX].claimed_at\": $(date +%s)}"
```

**Release on exit.** On success, Step 8 already transitions the item from `in-progress → resolved` (clearing the claim implicitly). On failure, transition from `in-progress → blocked` (with a `comments` field explaining why). On crash, the claim goes stale after 15 minutes and another agent can recover it. Never leave an item in-progress with a live claim and no actual worker.

## Step 1 — Read the Python source COMPLETELY

```bash
# Don't skim — read every file. Edge cases live in the bottom 20% of long files.
SOURCE=$(python3 -c "import json; print(json.load(open('$PLAN'))['consolidation']['phases'][1]['modules'][$IDX]['source'])")
find ~/github/ammonfife/auction_tools/$SOURCE -type f \( -name "*.py" -o -name "*.json" -o -name "*.csv" -o -name "*.yaml" \) | xargs wc -l
```

For each Python file in the source:
- Read top to bottom (no skimming)
- List every constant, regex, prefix table, magic number
- List every doctest, pytest case, example in docstring
- List every error message and exception type
- List every imported helper from elsewhere in `auction_tools/` — those become the "this module also depends on…" backlog

Write all of the above into a planning file at `/tmp/lift-module-<name>-source-survey.md`. The TS port must replicate every entry on that list.

## Step 2 — Snapshot existing target (if any)

```bash
TARGET=~/github/ammonfife/lkup.info/shared/<name>
TS=$(date -u +%Y%m%dT%H%M%SZ)
BAK=~/.claude/projects/-Users-benfife/memory/lift-module-backups/$TS
mkdir -p "$BAK"
[ -d "$TARGET" ] && cp -r "$TARGET" "$BAK/"
cd ~/github/ammonfife/lkup.info && git stash push -u -m "lift-module $MODULE pre-edit" -- shared/<name> || true
```

If the target directory already exists, the port is incremental — diff against the snapshot at the end. If it doesn't exist, this is a fresh port.

## Step 3 — Create the TypeScript module

Layout convention (matches existing lkup.info shared modules):
```
shared/<name>/
  index.ts            # public API (exports only)
  <name>.ts           # main implementation
  constants.ts        # all magic numbers, prefixes, lookup tables
  types.ts            # TS interfaces matching Python's expected shapes
  __tests__/
    <name>.test.ts    # parity tests against the Python fixture
    fixtures/
      python-cases.json  # generated in Step 4
```

**Implementation rules:**
- **One TS function per Python function.** Same name (camelCase if Python was snake_case), same args, same return shape.
- **Constants live in `constants.ts`.** Never inline a magic number in the implementation.
- **Use `as const`** for lookup tables so TS catches invalid keys at compile time.
- **No `any`.** Every input and output is typed. If Python returns `dict`, the TS version returns a typed interface.
- **Preserve error messages exactly.** A test that asserts `expect(fn).toThrow('Invalid barcode prefix: 0183')` must match the Python error string.

## Step 4 — Generate the parity test fixture from Python

```python
# scripts/generate-parity-fixture.py — run from auction_tools/
import json, importlib.util, inspect

spec = importlib.util.spec_from_file_location("source", "<python source path>")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cases = []

# 1. Pull docstring examples
for name, obj in inspect.getmembers(mod, inspect.isfunction):
    doc = inspect.getdoc(obj) or ""
    # Parse >>> blocks
    ...

# 2. Run any inline test cases
# 3. Run pytest collection if pytest exists
# 4. Hand-add any cases the source documents in comments

with open('python-cases.json', 'w') as f:
    json.dump({
        "source_sha": "<auction_tools git sha>",
        "module": "<module-name>",
        "generated_at": "...",
        "cases": cases,  # [{name, function, args, expected}]
    }, f, indent=2)
```

The fixture is the contract. Every case in `python-cases.json` becomes a TS test in `__tests__/<name>.test.ts` that runs the TS function with the same `args` and asserts the result equals `expected`.

## Step 5 — Run /audit-parity

```bash
/audit-parity --module <name> --fixture shared/<name>/__tests__/fixtures/python-cases.json
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "FAIL: /audit-parity returned non-zero — port is not at parity yet"
  echo "      DO NOT mark resolved. Fix the diffs and re-run."
  exit 1
fi
```

`/audit-parity` runs both implementations side-by-side and produces a CRITICAL/WARN/INFO classification. CRITICAL must be empty. WARN should be empty for `resolved` status (anything in WARN indicates a missing edge case). INFO is OK.

## Step 6 — Wire the module into a real lkup.info page

A ported module in `shared/` is meaningless until something imports it. Add or update at least one consumer:
- Barcode parser → wire into `src/pages/Scan.tsx` for client-side preview
- Pricing engine → wire into `src/components/PriceCalculator.tsx`
- Coin title parser → wire into `src/pages/CoinPage.tsx`
- Label generator → wire into the print-preview component

Run the Flask + frontend dev servers locally and hit the page that imports the new module with a real input.

## Step 7 — Capture screenshot proof

Per the global lkup.info Screenshot-Proof Rule. Use the `/use-e2b` skill to drive a desktop sandbox to the consumer page, supply a real input, and capture a PNG showing the module producing the expected output.

```
~/github/ammonfife/lkup.info/screenshots/lift-module/<name>-<YYYYMMDD>.png
```

The screenshot must show:
- A real input on the page (not a placeholder)
- The TS module's output rendered visibly
- Browser chrome (URL bar, etc.) so the screenshot is verifiable as live

If E2B is unavailable, **stop and surface as a blocker**. Do not skip.

## Step 8 — Update lkup-plan.json via /lkup-plan-editor

Never edit `lkup-plan.json` directly. Delegate:

```bash
/lkup-plan-editor --change-set "{\"phases[1].modules[$IDX].status\":\"resolved\",\"phases[1].modules[$IDX].screenshot\":\"screenshots/lift-module/<name>-<date>.png\",\"phases[1].modules[$IDX].source_sha\":\"$SOURCE_SHA\"}"
```

`/lkup-plan-editor` will run `/plan-validator` first, which enforces the screenshot existence and the status transition rules. If validation fails, the edit is blocked and you stay on the previous status.

## Step 9 — Record to Turso (real HTTP pipeline)

The previous version called `facts add operational ...` which **does not exist** as a CLI in this environment.

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

fact = (f"lift-module {MODULE_NAME}: ported Python→TS, source SHA {SOURCE_SHA}, "
        f"{N_TESTS} parity tests passing, screenshot {SCREENSHOT_PATH}, "
        f"consumer wired in {CONSUMER_FILE}.")
body = {"requests":[{"type":"execute","stmt":{
  "sql":"INSERT INTO facts (fact, source, category, created_by, created_by_session, created_by_platform) VALUES (?, ?, ?, ?, ?, ?)",
  "args":[
    {"type":"text","value":fact},
    {"type":"text","value":"scope:project lkup.info /lift-module"},
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
```

`created_by` is the SINGLE agent that ran the port. No `agent:claude,agent:bob` co-author tagging.

If the port surfaced any new edge case or constant the Python source didn't document explicitly, record THAT as a separate fact under `category=architecture` so future ports of related modules can reference it.

## Step 10 — Drop the stash + final report

```bash
cd ~/github/ammonfife/lkup.info && git stash drop  # only if Steps 5-8 all passed
rm -f /tmp/lift-module-${MODULE_NAME}-source-survey.md
```

Output:
- Module name + source SHA
- Test count and parity verdict
- Screenshot path
- Consumer file(s) wired
- Plan version after the bump
- Turso fact id
- Items remaining in Phase 1 (re-run `--status`)

## Coordination with parallel agents

The TS port itself is in `shared/<name>/` which other agents may also touch. Use:
- `git stash` checkpoint (Step 2) so concurrent edits surface as merge conflicts at unstash time
- `/plan-validator` `--current` mode at Step 0 to detect any other agent's in-flight edits to `lkup-plan.json`
- The file lock acquired by `/lkup-plan-editor` in Step 8

Two agents running `/lift-module <same-module>` simultaneously is unsafe. The plan validator and the file lock will catch the second one and refuse, but the FIRST one will have done significant work that the second now has to redo. Coordinate via the plan: only one agent should claim a Phase 1 module at a time. Claim by setting `status: in-progress` and `assigned_to: <agent>` BEFORE Step 1, via `/lkup-plan-editor`.

## Source of truth

- `lkup-plan.json` → `consolidation.phases[1].modules[]` is the canonical work list
- **The lkup.info `shared/<name>/` side wins when it already has a working implementation.** Do not assume Python is canonical. Step 0.5 enforces this — when the TS side has substantial content + tests + consumers + screenshots, it IS the source of truth and the auction_tools Python becomes a parity REFERENCE, not a porting source.
- `auction_tools/` is the **fallback source** when the lkup.info side is missing or stub. Pinned by SHA at Step 0 in either case so the parity reference doesn't drift.
- `/audit-parity` is the canonical parity check (and supports `--against-existing` mode for the pre-existing case)
- `/plan-validator` is the canonical write gate
- `/lkup-plan-editor` is the canonical writer
