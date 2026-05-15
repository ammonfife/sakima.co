---
name: plan-validator
description: Validate proposed changes against lkup-plan.json policies, URL rules, and schema constraints
user-invocable: true
---

# Plan Validator

Check proposed code changes against the canonical architecture plan (`lkup-plan.json`) before committing.

## Checks

1. **Policies** (`lkup-plan.json` → `policies[]`): No traderbea refs, desktop_scanner.py untouched, all clients write to Supabase, barcode never routes to /coins/, migration = COPY
2. **URL rules** (`url_rules`): /coin/ for slabs, /coins/ for types, barcode is primary key, service required for cert-only
3. **Schema** (`schema`): No new tables without checking, raw.* append-only, no price migration, frontend reads public.* only
4. **Consolidation** (`consolidation`): No auction_tools files modified, dual-write OK, correct target directories
5. **Do-NOT list**: No shadcn edits, no framework additions, no client barcode parsing for resolution, no setInterval revert, no api.lkup.info calls, no hardcoded prices
6. **Turso boundary** (Fact #384):
   - `src/` (React frontend) must NEVER import or call Turso/libSQL directly — Supabase only
   - `api-python/services/database.py` uses a legacy coin-scanner Turso DB (separate from bigmac-brain). It is NOT the BigMac agent workspace. `TURSO_DATABASE_URL` is not set on Cloud Run → `get_db()` returns `None` in production. This is **migration target → Supabase** (P2 backlog). Do not add new Turso reads/writes to api-python.
   - BigMac Turso URL (`bigmac-ammonfife.aws-us-west-2.turso.io`) must NEVER appear in any lkup.info code
   - Flag any new `libsql_client`, `@libsql/client`, or `turso.io` imports added outside of `api-python/services/database.py`

## Output

```
VIOLATION: [policy id] — [description]
  File: [path] Line: [number]
  Fix: [suggested fix]
```

Or: `PASS — all checks passed against lkup-plan.json v{version}`

## Bigmac Turso

Record violations as facts so they're visible to all agents:
```bash
# If violations found
facts add operational "Plan violation: [policy-id] in [file] — [description]" --tags lkup,violation,agent:Codex,agent:bob

# If a new policy is discovered or clarified during validation
facts add operational "[policy description]" --tags lkup,architecture,policy,agent:Codex,agent:bob

bigmac-sync push
```

### Tag Conventions
- **Project:** `lkup`, `consolidation`, `sakima`
- **Agents:** `agent:bob`, `agent:Codex`
- **Domain:** `architecture`, `validation`, `policy`
- **Status:** `status:verified`, `status:inbox`
