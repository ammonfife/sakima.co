---
name: consolidate
description: Run the full auction_tools → lkup.info consolidation pipeline — orchestrates all phases in order
---

# Consolidate

Master orchestrator for the auction_tools → lkup.info consolidation. Runs through all phases sequentially, invoking the appropriate skill for each step.

## Hard Constraint

**ALL code in `~/github/ammonfife/auction_tools/` MUST remain fully working throughout.** Nothing modified, moved, or deleted there. Both repos coexist. Cutover per-feature only after proven in production.

## Pipeline

### Step 1: Validate Current State
Run `/plan-validator` checks against the current codebase. Fix any existing violations before proceeding.

### Step 2: Phase 0 — Fix Stubs (`/fix-stubs`)
Read `lkup-plan.json` → `consolidation.phases[0]`. For each unresolved item:

1. **fix-A**: Add Flask GET alias for `/api/talking-points` in `api-python/routes/talking_points.py`
2. **fix-A**: Add Flask alias `/api/listing-draft` in `api-python/routes/listing_gen.py`
3. **fix-B**: Port OBS state endpoints to Flask (`POST/GET /api/obs-state` + copy `obs.html`)
4. **fix-B**: Port dealer endpoints to Flask (`GET /api/dealer/:slug`, `POST /api/dealer/:slug/vip`)
5. **fix-C**: Wire DealerPage.tsx VIP form to Flask endpoint
6. **fix-C**: Wire DealerPage.tsx contact form to Flask endpoint
7. **fix-D**: Replace Shows.tsx MOCK_SHOWS with Supabase query
8. **fix-E**: Fold DealerStorefront.tsx wired logic into DealerPage.tsx
9. **fix-F**: Redirect Flask `/scanner` to `https://lkup.info/scan`

After each fix: update `lkup-plan.json` Phase 0 item status, run `node scripts/render-plan.cjs`.

### Step 3: Phase 1 — Shared Core (`/lift-module`)
For each module in `lkup-plan.json` → `consolidation.phases[1].modules`:

1. Port barcode parser (Python → TypeScript in `shared/barcode-parser/`)
2. Port pricing engine (→ `shared/pricing/`)
3. Port coin title parser (→ `shared/coin-parser/`)
4. Port label generator (→ `shared/labels/`)

After each port: run `/audit-parity` to verify behavior matches. Update plan status.

### Step 4: Phase 2 — Desktop App
1. Choose framework (Electron vs Tauri) based on native binding needs
2. Scaffold `desktop/` directory with main process + preload
3. Wrap React web UI as desktop window
4. Add native USB/BT/printer bindings one at a time
5. Test each feature against desktop_scanner.py original
6. Both run simultaneously during transition

### Step 5: Phase 3 — Unified Extension
1. Scaffold `extension/` with single manifest
2. Port coin-cert-scraper content scripts (NGC/PCGS/CAC/ANACS/ICG)
3. Port whatnot-price-overlay injection + matching logic
4. Build live label printing from scratch (hot-label is not ours)
5. Add eBay purchase import
6. Shared popup UI (React, same design system)
7. Background service worker with Supabase realtime

### Step 6: Phase 4 — Enrichment Pipeline
1. Port spot price updater to Supabase Edge Function
2. Port coin_xref enrichment to Edge Function
3. Port pricing rollup to Edge Function
4. Port eBay comp refresher to Cloud Run Job
5. Port AI review to Cloud Run Job
6. Verify nightly pipeline runs from new services
7. Old launchd crons stay running until new pipeline proven

### Step 7: Phase 5 — Repo Structure
Verify final directory layout matches target in `lkup-plan.json` → `consolidation.phases[5].structure`.

### Step 8: Final Validation
1. Run `/plan-validator` — all checks must pass
2. Run `/audit-parity` on every ported module
3. Verify all auction_tools code still works unchanged
4. Update `lkup-plan.json` version + render HTML

## Between Each Step

- Commit working code (don't batch across phases)
- Update `lkup-plan.json` with progress
- Run `node scripts/render-plan.cjs`
- Verify `lkup.info` still serves HTTP 200
- Verify auction_tools desktop scanner still works
- **Sync Turso** (see Bigmac section below)

## Bigmac Turso Integration

After completing each phase or significant milestone, update the shared Turso brain so all agents (Bob, Codex, etc.) stay aligned.

### Facts
Record architectural decisions and discoveries:
```bash
# After a phase completes
facts add operational "Phase 0 complete: all 9 stub fixes deployed to coin-price-proxy" --tags lkup,consolidation,agent:Codex,agent:bob

# After discovering something important during a port
facts add operational "barcode parser: NGC 0183 prefix only valid for certs after 2024" --tags lkup,barcode,agent:Codex

# After a key decision
facts add operational "Desktop app: chose Tauri over Electron — smaller binary, Rust native bindings" --tags lkup,consolidation,architecture,agent:Codex,agent:bob
```

### Todos
Track remaining work:
```bash
# Add work items from the plan
todo add "Phase 1: port barcode parser to TypeScript" --tags=lkup,consolidation --assign=Codex --priority=high
todo add "Phase 3: rebuild hot-label functionality from scratch" --tags=lkup,consolidation,extension --assign=bob --priority=normal
```

### Sync
After any Turso writes:
```bash
bigmac-sync push
```

### Tag Conventions
- **Project:** `lkup`, `consolidation`, `sakima`
- **Agents:** `agent:bob`, `agent:Codex`
- **Domain:** `architecture`, `barcode`, `pricing`, `extension`, `desktop`, `enrichment`
- **Status:** `status:verified`, `status:inbox`

## Resume

If interrupted, read `lkup-plan.json` → `consolidation.phases[*]` to find the first phase with status != `"done"`, then the first unresolved item within it. Pick up from there.
