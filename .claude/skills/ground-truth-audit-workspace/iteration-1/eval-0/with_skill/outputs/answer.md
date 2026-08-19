# Is `drain_comps_fanin has no invoker — queue is filling, not draining` still true?

**Short answer: half of it. The queue really is filling far faster than it drains, but "has no invoker" is wrong — and it was wrong when it was written. An invoker fired 48 seconds before I took my snapshot.**

All numbers below are live from `vsotvatntzlrzrhemayh`, **as of 2026-08-16 00:30:55 UTC** unless stated.

---

## Verdict on the two halves of the claim

| Half of the claim | Verdict | Measurement |
|---|---|---|
| `drain_comps_fanin` has **no invoker** | **FALSE** | Real call site in `supabase/functions/comps-rematch/index.ts:99`; last successful drain `done_at = 2026-08-16 00:30:07` — 48s before I measured |
| Queue is **filling, not draining** | **TRUE in effect** | 7 days: **127,026 enqueued vs 33,116 drained** (3.8:1). Last 6h: **40 in / 5 out** |

The honest restatement: *the fan-in drain has exactly one live invoker, and it is a human pressing a button. Every automatic invoker is disabled — on purpose.*

---

## Verified findings

### 1. Queue state (full table, not a sample)

| metric | value |
|---|---|
| total rows | 173,260 |
| done | 67,021 |
| not done | 106,239 |
| — of which **parked** (invisible to the drain) | 28,162 |
| — of which **drainable** | 78,077 |
| oldest drainable | 2026-08-11 04:30:36Z (**4.8 days, frozen**) |
| oldest not-done incl. parked | 2026-08-05 05:22:14Z |
| last drain | 2026-08-16 00:30:07Z |
| rows carrying `last_error` | 1,068 |

Daily in/out, last 10 days (`enqueued_at` vs `done_at`):

```
08-06  in 12,029  out 18,348
08-07  in 10,145  out 11,170
08-08  in 12,989  out  4,062
08-09  in 30,820  out 20,197
08-10  in  2,886  out  2,056
08-11  in 26,351  out  4,352
08-12  in  1,868  out      0
08-13  in 22,243  out  5,093
08-14  in 36,531  out  1,061
08-15  in  6,287  out    352
```

### 2. Invoker inventory — they exist, they're just switched off

| Invoker | State | Evidence |
|---|---|---|
| EF `comps-rematch` `{fanin:true}` → `drain_comps_fanin(batch, deadline_ms)` | **LIVE, not flag-gated** | `supabase/functions/comps-rematch/index.ts:99` — a real call site, `select processed, deferred, failed from public.drain_comps_fanin(...)`. Invoked by the /coin refresh button (`src/pages/Coin.tsx`) |
| Statement trigger `comps_fanin_drain_trg` on `raw.marketplace_observations` → `fire_comps_fanin_drain` | **present + enabled, but inert** | `pg_trigger.tgenabled='O'`; body returns early because `enrichment_flags.comps_fanin_drain_enabled = FALSE` |
| Row trigger `trg_marketplace_obs_to_comps` → `marketplace_obs_to_comps_trg` | **enqueues always; kick is inert** | Same flag check. This is the *filler*, still fully live |
| pg_cron 42 `drain-comps-fanin` (`* * * * *`, `SELECT public.drain_comps_fanin(200)`) | **inactive** | `cron.job.active = false`; **0 runs in 7 days** |
| pg_cron 41 `comps-rematch-drain` | **inactive** | `cron.job.active = false` |
| `lkup_maintenance_tick` | **deliberately yielded** | Migration `20260806190947` removed the drain block; only a comment remains — not a call site |

**`enrichment_flags.comps_fanin_drain_enabled = FALSE`, `updated_at = 2026-08-09 02:21:13Z`** — set ~6 minutes after the migration that wired the drain trigger, and unchanged for 7 days. It gates **only the two trigger paths** (the only two `pg_proc` bodies that read it). The EF path ignores it, which is why rows still complete daily.

### 3. Why it's off — this is containment, not neglect

- **Flag false since 2026-08-09** to stop a repeat of the pg_net trigger-storm outage (`lkup_knowledge.md`: "set deliberately 2026-08-09 to prevent a repeat of the 2026-08-11 pg_net trigger-storm outage").
- **28,162 rows parked in a 17-minute window, 2026-08-11 04:13:53–04:30:02Z** by migration `20260811040000_park_fanin_backlog_human_lane.sql`. Ben, quoted in that migration: *"we do NOT want those 27k draining right now"* and *"i need ALL human lane, and refreshes … ALL working in human lane."* The backlog was parked rather than the lane disabled, so live-scan comps kept working during a show.

**Do not flip the flag as a "fix."** `agents/scheduled/update-state-diagrams/SKILL.md:252` lists four defects to fix first (LIFO starvation, throughput ceiling below intake, no parking path, latent ILIKE identity write), and policy #880 makes the inactive crons deliberate.

### 4. The real defect is starvation, not absence of a drain

`drain_comps_fanin` orders `priority desc, attempts asc, enqueued_at **DESC**` — newest first. Under sustained backlog the tail is unreachable:

- **72,244 of 78,077 drainable rows (92.5%) are more than 24h old.**
- `oldest_drainable` has been pinned at **2026-08-11 04:30:36Z** — the instant the mass-park ended — for five days. A frozen oldest-unprocessed timestamp is the LIFO-starvation signature.

Per-row cost is ~762ms through the `public.comps` BEFORE-trigger chain (recorded in the `drain_comps_fanin` function comment), and the per-call wall-clock budget was cut 120s → 15s on 2026-08-11, so a call clears roughly 19 rows regardless of `batch=150`.

Classification: **running but starved**, with automatic dispatch disabled. Not "not dispatched," and not "failing when it runs" — the 500/503 statement-timeout failures described in the older audit block are no longer what's happening.

### 5. The audit page already corrects itself — and the correction is now stale too

`audit/deployed-state.html:545-548` flags this exact line **STALE** as of 2026-08-09, citing "undone 12,265 → 5,962 while total grew 45,870 → 56,287" as proof of draining. That proof no longer holds: drainable is now **78,077**.

The line keeps coming back because it lives in `audit/deployed-state-sections.html:589` — the grow-only curated file that survives regeneration by design. It is a **frozen artifact rendered inside a page that reads as live**. Fixing the sentence in the generated HTML alone will not stop it reappearing.

### 6. Two numbers that look contradictory but aren't

`agents/scheduled/update-state-diagrams/SKILL.md:252` reports "101,780 undone … oldest_undone 2026-08-05." I report 78,077 drainable, oldest 2026-08-11. Both are right: **that count includes the 28,162 parked rows; mine excludes them.** Parked rows are filtered out by `drain_comps_fanin` (`and q.parked_at is null`), so they cannot be reached and their age is not a drain-latency signal. Quote both or the reading is wrong.

---

## Unverified

- **Which client fired the 00:30:07Z drain.** The fanin lane runs over `backend_direct`, so it leaves no `net._http_response` row (`net._http_response` is empty for the last 30 minutes). Settled by the `comps-rematch` Edge Function invocation logs for that minute.
- **`enrichment_chain_state.comps_fanin_drain` shows `last_fired_at = 2026-08-11 07:47:22Z`**, which the current `fire_comps_fanin_drain` body cannot produce with the flag false since 08-09 (the flag check precedes the chain-state update). Either a prior function definition or a manual update wrote it. Settled by reading migrations `20260811033000` / `20260811043000` bodies against the git history of that function.
- **`parked_at` has no writer.** No `pg_proc` body sets it — only `drain_comps_fanin` reads it. The 28,162 parks came from ad-hoc SQL. That means the "park after N attempts" behaviour the docs assume does not exist in code; 1,068 error rows retry forever.

## Retracted (this session)

- I concluded mid-audit that **"no live invoker is firing — last drain was 15h ago"** based on `max(done_at) = 2026-08-15 09:25:31Z`. Three minutes later the same query returned `2026-08-16 00:30:07Z`. The drain is demand-driven and bursty (hourly buckets: 5, then nothing for 15h, then 103, 249, 236, 35…), so **a single `max(done_at)` reading understates it.** Rate over a window is the right measure; a last-seen timestamp is not.

---

## What I'd change on the page

Replace the flag text at `audit/deployed-state-sections.html:589` (the grow-only source, not the generated HTML) with something that survives:

> `public.comps_fanin_queue` — drain is **live but manual-only**. `drain_comps_fanin` is invoked solely by `comps-rematch {fanin:true}` (the /coin refresh button); cron 42/41 are inactive per policy #880 and both trigger paths are gated off by `enrichment_flags.comps_fanin_drain_enabled = false` (since 2026-08-09, deliberate containment). Net 7d: 127,026 in / 33,116 out. 78,077 drainable + 28,162 parked; `oldest_drainable` frozen at 2026-08-11 due to LIFO ordering. **Do not re-enable the flag as a fix** — see the four defects in `agents/scheduled/update-state-diagrams/SKILL.md:252`. *(as-of 2026-08-16)*

And give that object-map block an explicit as-of stamp, since it does not regenerate.
