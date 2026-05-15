---
name: plan-validator
description: Validate proposed code changes against the canonical lkup-plan.json — enforces architecture policies, URL rules, schema constraints, the consolidation hard exclusions, the global lkup.info screenshot-proof rule, the HTTP-200-≠-working rule, and the do-not list. Produces structured JSON output, fails loudly on violations, and is the mandatory gate for any /lkup-plan-editor or /fix-stubs status mutation. Records every violation as an operational fact in Turso via the real HTTP pipeline.
user-invocable: true
---

@~/.claude/skills/lkup-shared-context/CONTEXT.md

# /plan-validator

Single-purpose gate: read the proposed change set, walk every rule in `lkup-plan.json`, and either return PASS or a structured list of violations. Nothing else.

**This skill is the mandatory pre-write gate** for any mutation of `lkup-plan.json` and for any `status: resolved` transition on a Phase 0 / Phase 1 item. `/fix-stubs`, `/lift-module`, `/lkup-plan-editor`, and `/consolidate` all delegate here before writing.

## Hard rules (NEVER violate)

1. **Read-only.** This skill never mutates the repo or `lkup-plan.json`. Any write attempt is a programming error.
2. **Fail loud, never silent.** Exit non-zero on any violation. Do not return PASS with warnings tucked into the output.
3. **Structured output.** JSON to stdout, human-readable text to stderr. Callers parse JSON; humans read stderr.
4. **No HTTP 200 ≠ working.** Any check that hits an endpoint must parse the body and assert content, not just status code. Per the global `scope:global` HTTP-200 policy.
5. **Screenshot proof must exist** for any `pending → resolved` transition under validation. Per the global lkup.info Screenshot-Proof Rule.
6. **No co-author tag inflation.** When recording a violation as a fact in Turso, the `created_by` is the SINGLE agent that ran the validator. Do not pre-tag `agent:claude,agent:bob`.

## Inputs

The validator accepts one of:

- `--change-set <json>` — inline JSON describing the proposed mutation, e.g. `'{"phases[0].items[2].status":"resolved","screenshot":"screenshots/fix-stubs/fix-A-2026-04-08.png"}'`
- `--diff-file <path>` — path to a unified diff to validate against the policies
- `--current` — validate the current working tree against `lkup-plan.json` (no proposed change; checks for existing violations)
- `--items <id1,id2,...>` — validate the listed items in `lkup-plan.json` against their declared assertions

If invoked with no arguments, default to `--current`.

## Step 0 — Pre-flight (MANDATORY)

Before validating, search for relevant context on the change being validated:
```bash
# Search for prior decisions, policies, and session discussions about this domain
knowledge-search "<description of the proposed change>" --multi --limit 10 2>/dev/null
```

```bash
PLAN=~/github/ammonfife/lkup.info/lkup-plan.json
[ -f "$PLAN" ] || { echo "FAIL: $PLAN missing" >&2; exit 1; }
python3 -c "import json; json.load(open('$PLAN'))" 2>&1 \
  || { echo "FAIL: $PLAN unparseable" >&2; exit 1; }

# Schema sanity — required top-level keys
python3 - <<'PY' || exit 1
import json, sys
d = json.load(open('PLAN_PATH_HERE'))
required = ['meta','policies','url_rules','schema','consolidation']
missing = [k for k in required if k not in d]
if missing: sys.exit(f"FAIL: lkup-plan.json missing top-level keys: {missing}")
PY
```

This skill is read-only, so no file lock is needed. But it WILL refuse to validate against an unparseable plan.

## Checks (in order)

Run every check. Collect all violations. Do not short-circuit on the first failure — the caller wants the full list.

### 1. Policies (`lkup-plan.json` → `policies[]`)
For each policy in the array, evaluate its `predicate` against the change set. Standard policies that must always be checked:
- `no-traderbea-refs` — grep for `traderbea` in any file under change. Flag matches.
- `desktop-scanner-untouched` — `auction_tools/production/scanners/unified/desktop_scanner.py` and any file it imports must be untouched in the diff. Even reformatting counts.
- `all-clients-write-supabase` — any new write path must target Supabase tables, not Turso, not Firestore, not local files.
- `barcode-never-routes-to-coins` — no React route or Flask route may map a barcode-shaped path to `/coins/`. Use `/coin/` (singular) for slabs.
- `migration-equals-copy` — any migration step must COPY data, never move/cut. Source remains in place until cutover proven.

### 2. URL rules (`url_rules`)
- `/coin/<cert>` → slab page (singular path = singular cert)
- `/coins/<type>` → type/category browse page (plural path = plural items)
- Barcode value is the **primary key** of the slab page; anything else is a query string
- `cert-only` lookups MUST include a `service` parameter (NGC, PCGS, ANACS, ICG, CAC) — without it, the cert number is ambiguous

### 3. Schema (`schema`)
- No new tables created without an entry in `schema.tables[]`
- `raw.*` writes must be append-only (no `UPDATE` / `DELETE` / `UPSERT` against `raw.*`)
- Frontend (`src/`) reads `public.*` only; never `raw.*`, never `staging.*`
- No price column migration without an entry in `schema.migrations[]`

### 4. Consolidation (`consolidation`)
- No file in `~/github/ammonfife/auction_tools/` modified in the diff
- Dual-write is OK (both auction_tools and lkup.info running) but a single-write that abandons one side is a violation unless `consolidation.cutovers[]` lists the feature as cutover
- Target directories per category: Flask routes → `api-python/routes/`, shared TS modules → `shared/<name>/`, React pages → `src/pages/`

### 5. Do-NOT list
Walk `lkup-plan.json` → `do_not[]` and grep the diff for each pattern:
- No edits under `src/components/ui/` (shadcn — shared UI)
- No new framework dependencies in `package.json`
- No client-side barcode parsing for resolution (server is authoritative)
- No `setInterval` revert (was removed deliberately — anyone re-introducing it is fighting old code)
- No calls to `api.lkup.info` from the frontend (use relative `/api/*`)
- No hardcoded prices in any TypeScript or Python file

### 6. Turso boundary (Fact #384)
- `src/` (React) must NEVER import `libsql_client`, `@libsql/client`, or any module under `turso.io`
- `api-python/services/database.py` is the ONLY allowed Turso surface in lkup.info, and it points at the legacy coin-scanner DB (NOT bigmac-brain). It is migration target → Supabase (P2 backlog). Do not add new reads/writes here.
- `bigmac-ammonfife.aws-us-west-2.turso.io` URL must NEVER appear in lkup.info code (it's the BigMac brain, separate ecosystem)
- Flag any new Turso/libSQL imports added outside `api-python/services/database.py`

### 7. Status transition rules (only when validating a change set)
For any item moving from `pending → resolved`:
- Item must have an `assertions.response_shape` field declared
- A screenshot artifact must exist at `screenshots/fix-stubs/<item-id>-<YYYYMMDD>.png` (or per the item's category directory)
- `last_modified_by` must be the agent currently running the validator (catches concurrent-edit races)
- The fix's commit must be in the local git history (not just staged)
- Item must currently be claimed by the same agent (`assigned_to == <self>` AND `status == 'in-progress'`) — you can't resolve work you didn't claim

For any item moving from `pending → in-progress` (work claim):
- `assigned_to` must be set to the agent making the claim
- `claimed_at` must be set to a Unix timestamp within the last 60 seconds (no time-traveling claims)
- `claimed_by_session` must be set to the session UUID for stale-claim attribution

For an item moving from `in-progress → in-progress` with a new `assigned_to` (claim steal):
- **REJECT** unless the change set includes `--steal` AND a `steal_reason` field
- **REJECT** if the previous `claimed_at` is less than 15 minutes ago (claim is fresh, not stale)
- **REJECT** if the previous `assigned_to` is in the live agent presence list (Turso `sessions` table with `active=1` and recent `updated_at`)
- If all three checks pass, allow the steal but record the previous claim's session UUID + timestamp in a `steal_history` field on the item for audit

For `in-progress → resolved` and `in-progress → blocked`:
- Only the current `assigned_to` agent may make these transitions
- Reject any other agent's attempt with "claim mismatch"

Status transitions OTHER than the above (e.g. `resolved → pending` for revert) are allowed without the screenshot requirement but must include a `comments` field explaining why and require the `assigned_to` to be cleared.

### 8. HTTP 200 ≠ working (when an item declares an endpoint)
For each item with an `endpoint` field, hit the endpoint with `curl`, parse the JSON body, and assert the response matches `assertions.response_shape`. A 200 with empty body or stub JSON is NOT a pass.

```python
import json, urllib.request
def assert_endpoint(item):
    url = f"http://127.0.0.1:5000{item['endpoint']}"
    try:
        r = urllib.request.urlopen(url, timeout=10)
    except Exception as e:
        return f"FAIL: connection: {e}"
    if r.status != 200:
        return f"FAIL: status={r.status}"
    body = json.loads(r.read())
    expected = item.get('assertions', {}).get('response_shape', {})
    for key, kind in expected.items():
        if key not in body:
            return f"FAIL: response missing key '{key}'"
        if kind == 'list' and not isinstance(body[key], list):
            return f"FAIL: '{key}' is not a list"
        if kind == 'list' and len(body[key]) == 0:
            return f"FAIL: '{key}' is an empty list (likely a stub)"
    return "PASS"
```

## Output

### Stdout (machine-readable)
```json
{
  "verdict": "PASS" | "FAIL",
  "plan_version": "5.19",
  "checks_run": 8,
  "violations": [
    {
      "policy_id": "no-traderbea-refs",
      "severity": "CRITICAL",
      "file": "src/pages/CoinPage.tsx",
      "line": 42,
      "description": "Reference to traderbea in import statement",
      "fix": "Remove the import; the traderbea-era price feed has been replaced by the consensus engine in shared/pricing/."
    }
  ],
  "screenshots_verified": ["screenshots/fix-stubs/fix-A-2026-04-08.png"],
  "screenshots_missing": []
}
```

### Stderr (human-readable)
```
VIOLATION: no-traderbea-refs (CRITICAL)
  File: src/pages/CoinPage.tsx Line: 42
  Description: Reference to traderbea in import statement
  Fix: Remove the import; the traderbea-era price feed has been replaced
       by the consensus engine in shared/pricing/.

PASS — all checks passed against lkup-plan.json v5.19
```

Or, if any violation:
```
FAIL — 3 violations against lkup-plan.json v5.19
```

Exit code: `0` on PASS, `1` on FAIL, `2` on plan-file errors.

## Recording violations to Turso

Use the real HTTP pipeline. The previous version of this skill called `facts add operational ...` which **does not exist** as a CLI in this environment.

```python
import json, urllib.request, subprocess, os, glob
URL = subprocess.check_output(['bash','-c',
    'source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_DATABASE_URL" | sed "s|libsql://|https://|"'
]).decode() + "/v2/pipeline"
TOKEN = subprocess.check_output(['bash','-c',
    'source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_AUTH_TOKEN"'
]).decode()

# Current Claude Code session id
sids = sorted(glob.glob('/Users/benfife/.claude/projects/-Users-benfife/*.jsonl'),
              key=os.path.getmtime, reverse=True)
session_uuid = os.path.basename(sids[0]).replace('.jsonl','') if sids else 'unknown'

def record_violation(v):
    fact = (f"plan-validator: {v['policy_id']} ({v['severity']}) in {v['file']}:{v.get('line','?')} — "
            f"{v['description']}")
    body = {"requests":[{"type":"execute","stmt":{
      "sql":"INSERT INTO facts (fact, source, category, created_by, created_by_session, created_by_platform) VALUES (?, ?, ?, ?, ?, ?)",
      "args":[
        {"type":"text","value":fact},
        {"type":"text","value":"scope:project lkup.info /plan-validator"},
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
    return res['response']['result'].get('last_insert_rowid')
```

Tag conventions: violations get `category=operational`. New policies discovered during validation get `category=architecture`. The `created_by` is the SINGLE agent invoking the validator (no co-author pre-tagging).

## Coordination with other lkup.info skills

`/plan-validator` is read-only and stateless — multiple agents may run it concurrently against the same `lkup-plan.json` without coordination. The file lock (`~/.openclaw/locks/lkup-plan.json.lock`) is only required for skills that WRITE the plan. This skill is invoked by other skills as a gate; it should be fast (sub-second per check) and idempotent.

## Source of truth

- `lkup-plan.json` is the canonical input
- This skill emits the canonical violation list
- Callers (`/fix-stubs`, `/lift-module`, `/lkup-plan-editor`, `/consolidate`) must check this skill's exit code before any write
- A non-zero exit from this skill blocks the calling skill's write step
