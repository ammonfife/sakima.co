---
name: audit-parity
description: Verify behavior parity between an auction_tools/ Python module and its lkup.info/shared/ TypeScript port. Runs both implementations against a shared fixture (python-cases.json) generated from the Python source's docstrings, doctests, and pytest cases, diffs the outputs, classifies differences as CRITICAL / WARN / INFO, emits structured JSON to stdout for caller consumption, captures a side-by-side diff artifact, refuses to return PASS if any CRITICAL exists, and records the verdict to Turso via the real HTTP pipeline. Mandatory gate before /lift-module marks a port resolved.
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


# /audit-parity

Verify the auction_tools Python implementation and the lkup.info TypeScript implementation produce the same outputs on the same inputs. This is the gate `/lift-module` calls before status moves from `pending → resolved`.

**Critical: this skill does NOT assume the Python is canonical.** Some lkup.info `shared/` modules are already production-quality and the TS side is the truth — `/lift-module` Step 0.5 catches those cases and aborts the port. When a pre-existing TS implementation is being audited (`--against-existing` mode), this skill flips the framing: the TS is canonical and the Python is the parity REFERENCE. Same fixture, same diff, but the verdict text and the recorded fact reflect which side was already known-good.

Both modes produce a machine-readable JSON verdict and a human-readable side-by-side diff artifact.

## Hard rules (NEVER violate)

1. **Read-only on both sides.** This skill never modifies the Python source, the TypeScript port, or `lkup-plan.json`. If a parity test reveals a bug in either side, surface it as a finding — don't auto-fix.
2. **Do NOT modify `auction_tools/`.** Per the consolidation hard constraint. Even formatting whitespace counts as a modification.
3. **Use the same fixture for both sides.** Both implementations must consume the **same** `python-cases.json` so the diff is an apples-to-apples comparison. If the fixture is missing, regenerate it from the Python source — don't run partial coverage.
4. **CRITICAL means CRITICAL.** A CRITICAL difference (different output for the same input) blocks `READY` status unconditionally. There is no "small CRITICAL" — if outputs differ on the same input, the port is broken.
5. **No HTTP-200-≠-working trap.** This skill doesn't hit endpoints, but if a parity case involves an upstream service call, the assertion is on parsed body content, not status code.
6. **Single agent author on Turso writes.** No co-author tag inflation.
7. **The PARITY REPORT artifact is the single source of truth** for the verdict. Stdout JSON is a summary; the artifact is the audit trail.

## Inputs

```bash
/audit-parity --module <name>                                # default: TS port being verified against Python source
/audit-parity --module <name> --against-existing             # FLIP: TS is canonical, Python is reference (use when lkup.info side was developed independently)
/audit-parity --module <name> --fixture <path>               # use a specific fixture file
/audit-parity --module <name> --case <case-name>             # run a single named case
/audit-parity --module <name> --regenerate-fixture           # regenerate python-cases.json from the Python source first
/audit-parity --list                                         # show modules and their last audit verdict
/audit-parity --diff-only                                    # produce the diff artifact, no verdict (debugging)
```

## Modes

This skill has two modes that produce the same JSON output but tag the verdict differently:

### Default mode (Python is the reference implementation)
Use when `/lift-module` has just done a fresh port and wants to confirm the new TS code matches the Python it was lifted from. The Python's behavior is the spec; TS divergence from Python is a port bug. Produced fact: `audit-parity <module>: TS port matches Python source`.

### `--against-existing` mode (TS is the canonical implementation, Python is the reference)
Use when `/lift-module` Step 0.5 detected a pre-existing lkup.info implementation and aborted the port. This mode runs the Python against the same fixture and reports differences but treats them as **reference points**, not port bugs. A divergence here is a discussion item ("the TS evolved past the Python — confirm the new behavior is correct, then either backport to Python or document the intentional drift in the plan"). Produced fact: `audit-parity <module>: pre-existing TS verified against Python reference`.

The verdict logic is the same in both modes — same fixture, same diff, same CRITICAL/WARN/INFO classification. Only the surrounding narrative changes.

## Where things live

| Artifact | Path |
|---|---|
| Python source | `~/github/ammonfife/auction_tools/<source-path>/` (per `lkup-plan.json` → `phases[1].modules[i].source`) |
| TypeScript port | `~/github/ammonfife/lkup.info/shared/<name>/` |
| Shared fixture | `~/github/ammonfife/lkup.info/shared/<name>/__tests__/fixtures/python-cases.json` |
| Run output (Python) | `/tmp/audit-parity/<name>/python-output.json` |
| Run output (TS) | `/tmp/audit-parity/<name>/ts-output.json` |
| Side-by-side diff | `/tmp/audit-parity/<name>/diff.html` |
| Final report artifact | `~/github/ammonfife/lkup.info/parity-reports/<name>-<YYYYMMDD>.json` |

## Key parity checks per module

These are the **minimum** coverage requirements. Modules may add more in `phases[1].modules[i].parity_tests[]`.

| Module | Required parity coverage |
|---|---|
| **Barcode parser** | All service prefixes (NGC/PCGS/CAC/ANACS/ICG and historical), all barcode formats (8-, 16-, 18-, 20-digit), QR-encoded variants, Ser# variants, malformed inputs (each known failure mode) |
| **Pricing engine** | Melt calculation across all metals + purities, margin tier boundaries (the off-by-one edge cases), consensus logic with 1/2/3 sources, missing-data fallbacks, currency handling |
| **Coin title parser** | All 40+ US series listed in `coin_xref_enrichment.py`, year-and-denomination routing, Morgan/Peace inference, mint mark parsing, error coin nomenclature |
| **Label generator** | QR format byte-for-byte, thermal printer layouts (CTP800BD, Rollo, Dymo, Zebra), font fallbacks, multi-line wrapping at exact pixel widths |

If the Python source has an edge case the table above doesn't enumerate (e.g. a weird historical NGC prefix only valid for certs after 2024), that case MUST be in the fixture and MUST be checked. If it isn't, this skill should add it during fixture regeneration.

## Step 0 — Pre-flight

```bash
PLAN=~/github/ammonfife/lkup.info/lkup-plan.json
[ -f "$PLAN" ] || { echo "FAIL: $PLAN missing"; exit 1; }

# Resolve module name → source + target paths from the plan
MODULE_INFO=$(python3 - <<PY
import json, sys
plan = json.load(open("$PLAN"))
mods = plan['consolidation']['phases'][1].get('modules', [])
for m in mods:
    if m.get('name') == "$MODULE_NAME":
        print(json.dumps(m))
        sys.exit(0)
sys.exit("FAIL: module $MODULE_NAME not in lkup-plan.json")
PY
) || exit 1
SOURCE=$(echo "$MODULE_INFO" | python3 -c "import json,sys;print(json.load(sys.stdin)['source'])")
TARGET=$(echo "$MODULE_INFO" | python3 -c "import json,sys;print(json.load(sys.stdin)['target'])")

# Both sides must exist
[ -d ~/github/ammonfife/auction_tools/$SOURCE ] \
  || { echo "FAIL: Python source missing: auction_tools/$SOURCE"; exit 1; }
[ -d ~/github/ammonfife/lkup.info/$TARGET ] \
  || { echo "FAIL: TS target missing: lkup.info/$TARGET"; exit 1; }

# auction_tools must be clean — pin the source SHA
cd ~/github/ammonfife/auction_tools
git diff --quiet HEAD || { echo "FAIL: auction_tools dirty — refusing to audit against an unpinned source"; exit 1; }
SOURCE_SHA=$(git rev-parse --short HEAD)

# Output dir
mkdir -p /tmp/audit-parity/$MODULE_NAME
mkdir -p ~/github/ammonfife/lkup.info/parity-reports
```

## Step 1 — Locate or regenerate the fixture

```bash
FIXTURE=~/github/ammonfife/lkup.info/shared/$MODULE_NAME/__tests__/fixtures/python-cases.json

if [ ! -f "$FIXTURE" ] || [ "$REGENERATE" = "1" ]; then
  echo "Generating python-cases.json from $SOURCE..."
  cd ~/github/ammonfife/auction_tools
  python3 - <<PY > "$FIXTURE.tmp"
import json, importlib.util, importlib.machinery, inspect, doctest, pkgutil, sys, os
sys.path.insert(0, "$SOURCE")
# Walk every .py in the source tree
cases = []
for root, _, files in os.walk("$SOURCE"):
    for f in files:
        if not f.endswith('.py') or f.startswith('test_'): continue
        path = os.path.join(root, f)
        spec = importlib.util.spec_from_file_location("m", path)
        try:
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        except Exception as e:
            print(f"  WARN: import failed: {path}: {e}", file=sys.stderr); continue
        # 1. Doctests
        finder = doctest.DocTestFinder()
        for dt in finder.find(mod):
            for ex in dt.examples:
                cases.append({
                    "source_file": path,
                    "function": dt.name,
                    "kind": "doctest",
                    "code": ex.source.strip(),
                    "expected_repr": ex.want.strip(),
                })
        # 2. Module-level _PARITY_CASES if defined
        if hasattr(mod, '_PARITY_CASES'):
            for c in mod._PARITY_CASES:
                cases.append({**c, "source_file": path, "kind": "explicit"})
print(json.dumps({
    "source_sha": "$SOURCE_SHA",
    "module": "$MODULE_NAME",
    "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "case_count": len(cases),
    "cases": cases,
}, indent=2))
PY
  mv "$FIXTURE.tmp" "$FIXTURE"
  echo "fixture written: $FIXTURE ($(python3 -c "import json;print(json.load(open('$FIXTURE'))['case_count'])") cases)"
fi
```

If the fixture has fewer than the minimum case count for the module (defined in `phases[1].modules[i].parity_min_cases`, default 10), **fail** — the audit isn't worth running on a stub fixture.

## Step 2 — Run the Python side

```bash
cd ~/github/ammonfife/auction_tools
python3 - <<PY > /tmp/audit-parity/$MODULE_NAME/python-output.json
import json, sys, traceback
sys.path.insert(0, "$SOURCE")
fixture = json.load(open("$FIXTURE"))
results = []
for c in fixture['cases']:
    try:
        # Reconstitute the function and call it with the recorded args
        # (full eval logic in audit-parity-runner.py)
        ns = {}
        exec(c['code'], ns)
        result = ns.get('_result', ns.get('__last__'))
        results.append({"name": c.get('function','?'), "ok": True, "result": repr(result)})
    except Exception as e:
        results.append({"name": c.get('function','?'), "ok": False, "error": f"{type(e).__name__}: {e}"})
print(json.dumps({"side":"python","source_sha":"$SOURCE_SHA","results":results}, indent=2))
PY
```

## Step 3 — Run the TypeScript side

```bash
cd ~/github/ammonfife/lkup.info
npx vitest run --reporter=json shared/$MODULE_NAME/__tests__/$MODULE_NAME.test.ts \
  > /tmp/audit-parity/$MODULE_NAME/ts-output.json
```

The TS test file is expected to read `python-cases.json` and emit one Vitest case per fixture entry. Vitest's JSON reporter gives us per-case pass/fail with the actual produced value.

## Step 4 — Diff and classify

```python
import json, sys
py = json.load(open(f"/tmp/audit-parity/{MODULE_NAME}/python-output.json"))
ts = json.load(open(f"/tmp/audit-parity/{MODULE_NAME}/ts-output.json"))

# Index TS results by case name
ts_by_name = {}
for tf in ts.get('testResults', []):
    for tc in tf.get('assertionResults', []):
        ts_by_name[tc.get('title','?')] = tc

verdict = {"CRITICAL": [], "WARN": [], "INFO": [], "PASS": 0}

for py_case in py['results']:
    name = py_case['name']
    ts_case = ts_by_name.get(name)

    # Case missing entirely on the TS side
    if ts_case is None:
        verdict["WARN"].append({
            "case": name, "kind": "missing_in_ts",
            "detail": "Python case has no corresponding TS test",
        })
        continue

    py_ok = py_case['ok']
    ts_ok = ts_case.get('status') == 'passed'

    # Both error — same exception type? Same message?
    if not py_ok and not ts_ok:
        py_err = py_case.get('error','')
        ts_err = ts_case.get('failureMessages',[''])[0]
        if py_err.split(':')[0] != ts_err.split(':')[0]:
            verdict["WARN"].append({
                "case": name, "kind": "exception_class_diff",
                "py": py_err, "ts": ts_err,
            })
        else:
            verdict["PASS"] += 1
        continue

    # One side errors, the other doesn't — CRITICAL
    if py_ok != ts_ok:
        verdict["CRITICAL"].append({
            "case": name, "kind": "one_side_threw",
            "py_ok": py_ok, "ts_ok": ts_ok,
            "py": py_case.get('result') if py_ok else py_case.get('error'),
            "ts": ts_case,
        })
        continue

    # Both succeeded — compare values
    py_val = py_case.get('result','')
    ts_val = ts_case.get('produced','')  # depends on TS reporter format
    if py_val != ts_val:
        verdict["CRITICAL"].append({
            "case": name, "kind": "value_diff",
            "py": py_val, "ts": ts_val,
        })
    else:
        verdict["PASS"] += 1

# Final verdict
ready = (len(verdict["CRITICAL"]) == 0 and len(verdict["WARN"]) == 0)
verdict["verdict"] = "READY" if ready else ("NOT READY" if verdict["CRITICAL"] else "READY WITH WARNINGS")
print(json.dumps(verdict, indent=2))
```

**Severity rules:**
- **CRITICAL** — same input, different output (or one side throws, the other doesn't). Blocks `READY` status. Cannot be marked-as-known-issue.
- **WARN** — Python case missing from TS, or both sides error but with different exception classes. Blocks `READY`, but is fixable by adding the missing test or normalizing the error.
- **INFO** — both sides produce the same value but with stylistic differences (whitespace in serialized output, dict key ordering, etc.). Does NOT block. Recorded for visibility only.

## Step 5 — Generate side-by-side diff artifact

For every CRITICAL and WARN, write a row to `/tmp/audit-parity/<name>/diff.html` with:
- Case name
- Input (the args)
- Python output (or exception)
- TS output (or exception)
- Diff highlighting (use `difflib.HtmlDiff` or a per-character diff for short values)

The HTML artifact is the human-debuggable record. The JSON output to stdout is the machine record.

## Step 6 — Write the final report artifact

```bash
REPORT=~/github/ammonfife/lkup.info/parity-reports/$MODULE_NAME-$(date -u +%Y%m%d).json
python3 - <<PY > "$REPORT"
import json
verdict = json.load(open("/tmp/audit-parity/$MODULE_NAME/verdict.json"))
print(json.dumps({
    "module": "$MODULE_NAME",
    "source_sha": "$SOURCE_SHA",
    "ts_target": "$TARGET",
    "fixture": "$FIXTURE",
    "fixture_case_count": ${FIXTURE_CASE_COUNT},
    "verdict": verdict["verdict"],
    "passed": verdict["PASS"],
    "critical": verdict["CRITICAL"],
    "warn": verdict["WARN"],
    "info": verdict["INFO"],
    "diff_artifact": "/tmp/audit-parity/$MODULE_NAME/diff.html",
    "audited_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "audited_by": "Claude",
}, indent=2))
PY
```

The persistent report at `~/github/ammonfife/lkup.info/parity-reports/<name>-<date>.json` is what `/lift-module` and `/lkup-plan-editor` will look at when validating a `pending → resolved` transition. It must exist for any port to be marked resolved.

## Step 7 — Print the verdict to stdout

```bash
cat <<EOF
PARITY REPORT: $MODULE_NAME
Source: auction_tools/$SOURCE @ $SOURCE_SHA
Port:   lkup.info/$TARGET
Tests:  $PASS_COUNT / $TOTAL_COUNT pass
        CRITICAL: $CRIT_COUNT
        WARN:     $WARN_COUNT
        INFO:     $INFO_COUNT
Verdict: $VERDICT
Report:  $REPORT
Diff:    /tmp/audit-parity/$MODULE_NAME/diff.html
EOF

# Exit code: 0 = READY, 1 = READY WITH WARNINGS, 2 = NOT READY
case "$VERDICT" in
  "READY") exit 0 ;;
  "READY WITH WARNINGS") exit 1 ;;
  *) exit 2 ;;
esac
```

`/lift-module` checks for exit `0`. Anything non-zero blocks the status update.

## Step 8 — Record to Turso (real HTTP pipeline)

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

fact = (f"audit-parity {MODULE_NAME}: {VERDICT} — {PASS_COUNT}/{TOTAL_COUNT} pass, "
        f"{CRIT_COUNT} CRITICAL, {WARN_COUNT} WARN. Source SHA {SOURCE_SHA}. "
        f"Report: parity-reports/{MODULE_NAME}-{DATE}.json")
body = {"requests":[{"type":"execute","stmt":{
  "sql":"INSERT INTO facts (fact, source, category, created_by, created_by_session, created_by_platform) VALUES (?, ?, ?, ?, ?, ?)",
  "args":[
    {"type":"text","value":fact},
    {"type":"text","value":"scope:project lkup.info /audit-parity"},
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

# If NOT READY, also record each blocker as its own fact so they're discoverable
if VERDICT == "NOT READY":
    for blocker in CRITICAL_LIST:
        fact = f"parity blocker {MODULE_NAME}/{blocker['case']}: {blocker['kind']} — py={blocker.get('py','?')[:120]} ts={blocker.get('ts','?')[:120]}"
        # ... insert with category=operational, tag with blocker
```

## --list mode (read-only inventory)

```python
import os, json, glob
from datetime import datetime

reports_dir = "~/github/ammonfife/lkup.info/parity-reports"
plan = json.load(open("/Users/benfife/github/ammonfife/lkup.info/lkup-plan.json"))
modules = plan['consolidation']['phases'][1].get('modules', [])

for m in modules:
    name = m['name']
    # Find the most recent report for this module
    pattern = os.path.expanduser(f"{reports_dir}/{name}-*.json")
    reports = sorted(glob.glob(pattern), reverse=True)
    if not reports:
        print(f"  · {name}  (never audited)")
        continue
    r = json.load(open(reports[0]))
    age_d = (datetime.utcnow() - datetime.fromisoformat(r['audited_at'].replace('Z',''))).days
    mark = {'READY':'✓','READY WITH WARNINGS':'⚠','NOT READY':'✗'}.get(r['verdict'],'?')
    print(f"  {mark} {name}  ({r['verdict']}, {age_d}d ago, {r['passed']}/{r.get('passed',0)+len(r['critical'])+len(r['warn'])} pass)")
```

## Coordination with parallel agents

`/audit-parity` is read-only on both source and target — multiple agents can run it concurrently against the same module without coordination. The shared fixture is stable (regenerated only when `--regenerate-fixture` is passed). The output paths under `/tmp/audit-parity/` are namespaced by module so concurrent runs of DIFFERENT modules don't collide.

If two agents run `/audit-parity --module <same>` concurrently with `--regenerate-fixture`, they may race on the fixture write — the second one wins. This is benign because the fixture is deterministic from the (pinned) Python source SHA, so the result is the same either way.

## Source of truth

- `lkup-plan.json` → `consolidation.phases[1].modules[]` declares which modules are in scope
- **The "canonical implementation" depends on mode:**
  - **Default mode** — `auction_tools/<source>/` Python is canonical, `lkup.info/shared/<name>/` TS is the port being verified
  - **`--against-existing` mode** — `lkup.info/shared/<name>/` TS is canonical (it's already shipped), `auction_tools/<source>/` Python is the parity REFERENCE used to find documented behavior the TS might be missing
- Both Python and TS are pinned by SHA at Step 0 in either mode, so the parity reference doesn't drift
- `python-cases.json` is the canonical fixture — generated from the Python source's docstrings/doctests/explicit cases. The fixture is the same in both modes; only the verdict narrative changes
- `parity-reports/<name>-<date>.json` is the canonical audit verdict for a specific run
- This skill's exit code is what `/lift-module` checks before status updates: `0` = READY (verdict can promote `pending → resolved`), non-zero = blocked
- **If a divergence is found in `--against-existing` mode**, that is NOT necessarily a bug. It is a discussion item — the TS may have intentionally evolved past the Python. Surface to the operator with both outputs side-by-side and let them decide (a) backport TS behavior to Python, (b) document the intentional drift in the plan, or (c) revert TS to match Python. Never auto-revert.
