# Is "drain_comps_fanin has no invoker — queue is filling, not draining" still true?

**No. Both halves of that claim are false as of 2026-08-16 00:27 UTC.** It has invokers (three live wiring paths), and the queue is neither filling nor draining right now — it is *static*, because the drain dispatch is deliberately switched OFF by a kill-switch flag and there has been no marketplace traffic for ~12 hours.

The report file already knows this, partly: `audit/deployed-state.html` carries a **2026-08-09 addendum that explicitly marks this exact line "STALE"** (line ~545), but the top-of-report table row (line 249) was never updated. The document contradicts itself.

---

## 1. "No invoker" — false. There are three live invocation paths.

| # | Path | Live state |
|---|------|-----------|
| 1 | `trg_marketplace_obs_to_comps` (AFTER INSERT FOR EACH ROW on `raw.marketplace_observations`) → `marketplace_obs_to_comps_trg()` — enqueues the row, then fires a **debounced kick** (3s window for human lane `priority=10`, 15s for bulk) via `net.http_post` → EF `comps-rematch` `{fanin:true, batch:50}` | trigger enabled (`tgenabled='O'`) |
| 2 | `comps_fanin_drain_trg` (AFTER INSERT FOR EACH STATEMENT, same table) → `fire_comps_fanin_drain()` — 90s-debounced backstop via `net.http_post` → `comps-rematch` `{fanin:true, batch:150}` | trigger enabled; added 2026-08-09 (`20260809021500` / `20260809022113_w1_fanin_drain_trigger.sql`) |
| 3 | EF **`comps-rematch`** (slug `comps-rematch`, **ACTIVE, version 74**, deployed 2026-08-15) — its fanin mode runs `select processed, deferred, failed from public.drain_comps_fanin($batch, $deadline_ms)` over `backend_direct`, in a self-limiting multi-pass loop | deployed and current |

Additional callers: `public.drain_comps_fanin_batch(int)` self-chains through `net.http_post` → `/rest/v1/rpc/drain_comps_fanin_batch`; `src/pages/Coin.tsx` refresh calls `efPost('comps-rematch', {fanin:true,...})`; `supabase/functions/comp-acquire/index.ts` documents the same chain.

The old pg_cron job **42 `SELECT public.drain_comps_fanin(200);`** still exists but is `active=false` — retired on purpose (policy #880, "no crons, trigger-driven"). Its absence is *not* the absence of an invoker.

## 2. "Queue is filling, not draining" — false. It has drained ~67k rows.

`public.comps_fanin_queue` right now:

| metric | value |
|---|---|
| total rows | 173,220 |
| **done** (`done_at not null`) | **67,016** |
| parked (`parked_at not null`) | 28,162 |
| pending (neither) | 78,042 |
| pending with attempts ≥ 5 (exhausted) | **0** |
| pending with attempts = 0 (never tried) | 78,026 |
| pending on the human lane (`priority ≥ 10`) | 67,735 |
| oldest enqueue / newest enqueue | 2026-08-03 20:58 / 2026-08-15 12:02 |
| last successful drain | 2026-08-15 09:25 |

Completions by day — this is a lane that has demonstrably drained at scale:

```
2026-08-06  18,348      2026-08-11   4,352
2026-08-07  11,170      2026-08-13   5,093
2026-08-08   4,062      2026-08-14   1,061
2026-08-09  20,197      2026-08-15     352
2026-08-10   2,056
```

The 28,162 parked rows were parked in a 17-minute window on 2026-08-11 04:13–04:30 — that is the deliberate backlog park (`20260811040000_park_fanin_backlog_human_lane.sql`), not failure.

## 3. Live proof the drain function works today

```sql
select * from public.drain_comps_fanin(5, 8000);
-- processed=5, deferred=0, failed=0
```

Run just now against prod. The function executes, resolves comps, and marks rows done. Nothing about it is broken or unwired.

## 4. What IS true today (the real current state)

**Automatic dispatch is intentionally OFF via a kill-switch, not missing.**

```
public.enrichment_flags
  flag_key = 'comps_fanin_drain_enabled'
  enabled  = false
  notes    = "W1 comp-overhaul kill-switch: fan-in drain dispatch to comps-rematch
              (both the immediate per-row kick in marketplace_obs_to_comps_trg and the
              statement-level backstop comps_fanin_drain_trg). Set enabled=false to halt
              DISPATCH without touching the queue -- rows keep enqueuing, they just stop
              being kicked until re-enabled."
```

Both trigger functions read that flag and `return` early when it is false. So today: rows would still *enqueue* on new observations, but nothing auto-kicks the drain. Last kick recorded: `comps_fanin_kick.last_kick_at = 2026-08-11 07:48`; `enrichment_chain_state['comps_fanin_drain'].last_fired_at = 2026-08-11 07:47`.

**And it is not filling either.** Newest enqueue is 2026-08-15 12:02; `net._http_response` shows zero pg_net traffic since 2026-08-15 12:03; `is_scanning_session_active()` = false. The whole system has been idle ~12 hours. The queue is frozen, not growing.

One inconsistency worth flagging rather than resolving by guess: the flag row's `updated_at` is 2026-08-09 02:21, yet kicks demonstrably fired on 2026-08-11 07:48 — which requires the flag to have been true at that moment. Either `updated_at` is not maintained on that table or the flag was toggled without touching it. Unverified; the governing fact is the current value, `false`.

## 5. Corrected wording for the audit row

Replace the line at `audit/deployed-state.html:249` (and the same row in `audit/deployed-state-sections.html:320`, which is the grow-only fragment the report regenerates from — fixing only the HTML will be overwritten) with:

> `public.comps_fanin_queue` | work queue | `trg_marketplace_obs_to_comps` + `comps_fanin_drain_trg` → `comps-rematch` EF → `drain_comps_fanin()` | **Wired and functional** (live-verified: `drain_comps_fanin(5,8000)` → processed 5 / failed 0). Auto-dispatch is currently **halted by kill-switch** `enrichment_flags.comps_fanin_drain_enabled=false`; 67,016 done / 28,162 parked (deliberate 2026-08-11 park) / 78,042 pending, 0 attempt-exhausted. Queue is static, not filling — no observations since 2026-08-15 12:02.

## Files / objects touched in this verification

- `/Users/benfife/github/ammonfife/lkup.info/audit/deployed-state.html` (lines 249, 518, 545 — stale row + its own contradicting addendum)
- `/Users/benfife/github/ammonfife/lkup.info/audit/deployed-state-sections.html` (line 320 — the regeneration source of the stale row)
- `/Users/benfife/github/ammonfife/lkup.info/supabase/functions/comps-rematch/index.ts`
- `/Users/benfife/github/ammonfife/lkup.info/supabase/migrations/20260809022113_w1_fanin_drain_trigger.sql`
- `/Users/benfife/github/ammonfife/lkup.info/supabase/migrations/20260811040000_park_fanin_backlog_human_lane.sql`
- `/Users/benfife/github/ammonfife/lkup.info/docs/integrity/COMP_OVERHAUL_SPEC_2026-08-08.md` (already calls the line understated)
- DB: `public.comps_fanin_queue`, `public.drain_comps_fanin(int,int)`, `public.drain_comps_fanin_batch(int)`, `public.fire_comps_fanin_drain()`, `public.marketplace_obs_to_comps_trg()`, `public.enrichment_flags`, `public.enrichment_chain_state`, `public.comps_fanin_kick`, `cron.job` (42 inactive)
