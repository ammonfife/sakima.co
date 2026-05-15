---
name: fix-stubs
description: Fix broken stubs and wiring in lkup.info — Phase 0 of consolidation plan
---

# Fix Stubs

Wire frontend TODO stubs to Flask backend endpoints, fix URL/method mismatches, and port Node-only routes to Flask. Phase 0 of the auction_tools → lkup.info consolidation.

## Source of Truth

Read `lkup-plan.json` → `consolidation.phases[0]` for the full audit.

## Categories

**A. URL/method mismatches** — Flask has logic, frontend calls wrong path. Fix: add alias routes in Flask.
**B. Node-only routes** — Features in `api/src/` need equivalent Flask routes in `api-python/routes/`.
**C. Frontend TODO stubs** — Replace `// TODO:` with `fetch()` calls to Flask endpoints.
**D. Mock data** — Replace hardcoded arrays with Supabase queries.
**E. Orphan pages** — Fold wired logic from unused pages into the routed ones.
**F. Dead routes** — Redirect to React equivalents.

## Process

1. Read `lkup-plan.json` consolidation Phase 0 items
2. Pick the next unresolved item
3. Implement the fix
4. Test the endpoint
5. Update `lkup-plan.json` item status to `"resolved"`
6. Render HTML: `node scripts/render-plan.cjs`

## Constraints

- Do NOT modify `src/components/ui/`
- Do NOT modify any file in `auction_tools/`
- Flask routes go in `api-python/routes/`
- All `raw.*` writes are append-only

## Bigmac Turso

After each fix, record it and sync:
```bash
facts add operational "fix-stubs [item-id]: [description]" --tags lkup,consolidation,phase0,agent:Codex,agent:bob
bigmac-sync push
```

## Bigmac Turso Integration

After completing each stub fix or deploying to coin-price-proxy, update the shared Turso brain.

### Facts
```bash
# After a fix is deployed
facts add operational "Phase 0-[A/B/C/D/E/F] complete: [stub fixed] deployed to coin-price-proxy" --tags lkup,phase0,consolidation,agent:Codex,agent:bob

# After discovering something about the Flask/Node mismatch
facts add operational "lkup.info: [route] ported — [key detail]" --tags lkup,phase0,flask,agent:Codex
```

### Todos
```bash
# Mark done when deployed
todo done <id>
```

### Sync
```bash
bigmac-sync push
```

### Tag Conventions
- **Project:** `lkup`, `consolidation`, `phase0`, `sakima`
- **Agents:** `agent:bob`, `agent:Codex`
- **Domain:** `flask`, `frontend`, `architecture`
- **Status:** `status:verified`, `status:inbox`
