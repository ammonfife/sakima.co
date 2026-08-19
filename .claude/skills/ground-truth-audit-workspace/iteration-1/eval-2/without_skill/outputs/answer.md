# Should you flip `comps_fanin_drain_enabled` back on?

**Not as a bare flip.** Re-park the stale backlog first (one reversible UPDATE), then flip. Flipping the flag alone today does something materially different from what it did the last time it was on, and the difference is ~78,000 rows.

All numbers below are measured live in `vsotvatntzlrzrhemayh` on 2026-08-15, full-table counts, no samples.

---

## 1. Correcting the reason on file

The repo ledger and the last two sessions say the flag was *"set to false on 2026-08-09 to prevent a repeat of the 2026-08-11 pg_net trigger-storm outage."* That is chronologically impossible, and it is wrong.

`enrichment_flags.updated_at` reads `2026-08-09 02:21:13.740414+00` — but that is exactly the timestamp of migration `20260809022113_w1_fanin_drain_trigger.sql`, which **inserted the row with `enabled = true`**. There is no `updated_at` maintenance on that table, so the column still shows row-creation time and tells you nothing about when the value flipped.

The real last-dispatch stamps:

| Evidence | Value |
|---|---|
| `comps_fanin_kick.last_kick_at` | `2026-08-11 07:48:17Z` |
| `enrichment_chain_state.last_fired_at` ('comps_fanin_drain') | `2026-08-11 07:47:22Z` |

Dispatch ran until **2026-08-11 ~07:48Z**, then stopped dead. The flag was flipped off *that morning, during show prep* — after the 03:00–04:30Z outage work, not before it. Your own knowledge snapshot records the decision verbatim: *"DELIBERATE TRADEOFF STATED TO BEN: comps_fanin_drain_enabled=FALSE for the show... 928 drainable, 28,162 parked... Flip with: update public.enrichment_flags set enabled=true... The tradeoff disappears once the batch-match build (todo #12774) lands."*

So it was always meant to be flipped back. The question is only whether the preconditions still hold.

## 2. They don't. The "~100k undone" splits two ways

```
undone total        106,204
  parked            28,162   invisible to drain_comps_fanin
  LIVE HEAD         78,077   drainable right now
    of which pri>=10  67,730 human lane
```

When Ben accepted the tradeoff on 08-11, the live head was **928 rows**. It is now **78,077**. That is the whole answer.

The `parked_at` mechanism (migration `20260811040000_park_fanin_backlog_human_lane.sql`) is what made the flag safe to flip: it froze the 28k backlog so the drain could "only ever see fresh work." But parking was a **one-time manual UPDATE** run between `04:13:53Z` and `04:30:02Z` on 08-11. I verified across all schemas that `drain_comps_fanin` is the *only* database object that references `parked_at`, and it only ever reads it. **Nothing re-parks.** Every row enqueued in the four days since has landed unparked in the live head, and 87% of it carries priority 10.

Flip the flag as-is and the drain doesn't sip fresh work — it starts a 78k-row grind.

## 3. The matcher got worse, not better

Measured today via `EXPLAIN ANALYZE` over 25 pending queue rows:

| Path | Cost/row | Context |
|---|---|---|
| `lkup_resolve_comp_v2` (live write path via `trg_comps_match` → `_comps_match_on_write`) | **1,338 ms** | 33,443 ms / 25 rows |
| `lkup_resolve_or_match_comp` (EF drain / rematch path) | **1,790 ms** | 44,753 ms / 25 rows |

Baselines: **762 ms/row** (W1, 2026-08-09) and **445–634 ms/row** (2026-08-11, the measurement that motivated the shutdown). Current cost is **2.1–3.0x worse** than when the lane was switched off.

Note what this rules out: todo #12783 blamed the cost on `public.comps` never having been `ANALYZE`d. That is no longer true — `comps`, `spine`, `coins`, `marketplace_observations` and `lkup_series_keyword` were all analyzed 2026-08-14 11:18–11:20Z. The regression survived the fix that was supposed to explain it. Something else changed and hasn't been found.

Arithmetic on the flip:
- 78,077 live-head rows x 1.338 s = **~29 hours** of continuous matcher work.
- `drain_comps_fanin` is **single-flight** (global advisory lock, migration `20260811043000`) — exactly one drain cluster-wide, so there is no parallel speedup. It pins 1 of the 5 `backend_direct` slots essentially continuously for those 29 hours.
- Inflow is 6k–36k rows/day, i.e. **2.2–13.6 h/day** of matcher work at current cost. On a heavy day the lane is roughly break-even *after* it catches up.

The LIFO ordering (`priority DESC, attempts ASC, enqueued_at DESC`) does protect live scans — a fresh scan still goes to the head of the queue. The risk isn't live-scan latency; it's a drain that never reaches empty and therefore never releases the pooler slot, against a pool with a documented saturation history (policy #757, and the 57 `53300 too many connections for role backend_direct` errors in the 02:52–03:02Z window on 08-11).

## 4. The flag is not the gate its name implies — fix this too

Your knowledge base contains an unresolved contradiction: *"the flag has been FALSE since 08-09, yet the queue IS draining — so that flag is not the gate its name implies and is a misleading control surface."* Resolved:

`drain_comps_fanin` does **not** check `comps_fanin_drain_enabled` (verified against `prosrc`). Only two objects read it — `marketplace_obs_to_comps_trg` (the per-row kick) and `fire_comps_fanin_drain` (the statement-level backstop). It gates **dispatch**, not drain. Anything that invokes the `comps-rematch` EF directly — notably the `/coin` refresh button — drains the queue regardless. That is why 5,093 rows drained on 08-13 and 352 today with the flag "off."

Both scheduled invokers (cron jobs 41 `comps-rematch-drain` and 42 `drain-comps-fanin`) are inactive, consistent with the crons-off-permanently policy (#880).

This ambiguity has now caused two separate sessions to reason wrongly about this lane. Either make `drain_comps_fanin` honor the flag, or rename it `comps_fanin_dispatch_enabled`.

## 5. Recommended sequence

**Do not flip during a live show.** The 08-11 shutdown was show-driven; confirm nothing is streaming first.

1. **Re-park the stale backlog.** Only **105** live-head rows were enqueued in the last 6 hours (65 of them human-lane). Parking everything older restores almost exactly the 08-11 condition that made the flag safe:
   ```sql
   update public.comps_fanin_queue
      set parked_at = now()
    where done_at is null and parked_at is null
      and enqueued_at < now() - interval '6 hours';
   -- reverse: update ... set parked_at = null where parked_at > <timestamp of this run>;
   ```
   Rows are retained, not dropped. This is fully reversible.
2. **Then flip the flag on**, and watch for 30 minutes: live-head depth, `net._http_response` 5xx/timeouts, and `53300 backend_direct` errors. Current pg_net health is fine (332/397 responses 200 in the last 6h), so you have a clean baseline to compare against.
3. **Investigate the 1,338 ms/row regression before draining the ~106k parked rows.** Post-ANALYZE it is 2–3x the number that justified the shutdown, and the previously assumed cause is gone. Draining 106k rows at that cost is 39+ hours of pooler occupancy.
4. **Land the batch-match build (todo #12774)** — match the whole eBay batch in one set-based pass, then one insert with `coin_lkup_uuid` already attached. Migration `20260811043000` explicitly calls the single-flight guard "a stopgap for the show" and names this as the real fix. The backlog is not drainable at per-row trigger cost; it's drainable at batch cost.
5. **Add a standing park rule.** A one-time manual UPDATE as the sole thing separating "fresh work" from "78k-row grind" is the actual defect here, and it silently decayed over four days with nothing reporting it.

## 6. What stays broken while it's off

New marketplace observations are still **captured** to `raw.marketplace_observations` and **queued** — nothing is being lost. They just aren't minted into `public.comps`, so new comps don't appear on `/coin`. Identity, pricing, and OBS do not depend on the fan-in (proven live on 08-11: a scan returned full guide + melt with the drain off). Currently 57,445 of 97,420 comps are unmatched.

Also worth noting: 1,068 undone rows carry a `last_error`, and per the prior session's finding, much of the earlier park came from lock timeouts and deadlocks that recorded no `last_error` at all — a park path that writes no diagnosis. Worth closing while you're in here.
