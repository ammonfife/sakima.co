# Should you flip `comps_fanin_drain_enabled` back on?

**No — not right now, and not as-is.** Two blockers, one live and one structural:

1. **A scanning session is active as I write this.** `public.is_scanning_session_active()` = `true`, newest observation `2026-08-16 00:33:01Z`, 105 rows enqueued in the current hour. Fan-in mode is *deliberately not* gated on that check (`supabase/functions/comps-rematch/index.ts:73`), so flipping the flag dispatches immediately, into live traffic. That is the exact condition that produced the 2026-08-11 outage.
2. **The first dispatch would not process the 105 fresh rows — it would start eating a 67,795-row priority-10 backlog.** `drain_comps_fanin` orders `priority DESC, attempts ASC, enqueued_at DESC`, and there are 67,795 unparked, undone, priority-10 rows waiting. At the per-row cost I measured below, that is hours of matcher work contending with a live show, on a pool with `CONNECTION LIMIT 5`.

The flag is not what is broken. Fix ordering and throughput first, then enable — order given at the end.

---

## Verified findings (measured, as-of `2026-08-16 00:34Z` unless noted)

### The queue

| Metric | Value |
|---|---|
| Total rows | 173,220 |
| Undone | 106,204 |
| Undone **and drainable** (not parked) | 78,077 |
| Parked (invisible to `drain_comps_fanin`) | 28,162 |
| Done | 67,016 |
| Rows with `last_error` | 1,068 (913 `lock timeout`, 155 `deadlock detected`) |
| Oldest undone | 2026-08-05 05:22:14Z — **parked** |
| Oldest undone *and drainable* | 2026-08-11 04:30:36Z (4.8 days, not moving) |
| Newest enqueued | 2026-08-16 00:33:01Z |
| Last drained | 2026-08-16 00:30:07Z |

### The drain has never actually stopped — it is starved, not off

Rows drained per day, with the flag `false` since ~Aug 11: Aug 12 = 0, Aug 13 = 5,093, Aug 14 = 1,061, Aug 15 = 352, Aug 16 (6h) = 5. Intake over the same window: 22,243 / 36,531 / 6,287.

The five rows drained in the last six hours were all enqueued `2026-08-15 12:02:58Z` by `comp_acquire_ef` and completed **12.5 hours later**. That is the `/coin` refresh button: `src/pages/Cert.tsx:921` posts `comps-rematch {fanin:true, batch:25}` straight to the Edge Function and never consults the DB flag. It is the only live drain path, and it is user-initiated.

So this is **"running but starved," not "not dispatched."** Meanwhile the current hour's 105 enqueued rows are 0% drained — the live scan lane's own comps are not being matched in real time. That is the genuine cost of leaving the flag off, and it is the strongest argument for eventually turning it on.

### Per-row cost (measured directly, this session)

`lkup_resolve_comp_v2` over the 5 head-of-queue rows, `EXPLAIN ANALYZE`:

- cold: 6,101 ms / 5 rows = **1,220 ms/row**
- warm re-run, same rows: 3,181 ms / 5 rows = **636 ms/row**

Caveat, per measurement hygiene: an unrelated query had been active 2.3 h during both runs, so treat 636 ms as the warm floor. This is the **matcher alone** — the real drain cost per row is higher, because `populate_comps_from_marketplace` inserts into `public.comps`, which fires six row-level BEFORE triggers plus four statement-level AFTER triggers (`comps_council_emit`, `comps_enrich_ebay_trg`, `comps_refresh_pipeline`, `comps_barcode_decode_drain_trg`), several of which issue their own HTTP posts.

Note this is measured *after* commit `10ab17e4b` ("spine gate 145x faster", Aug 11 03:08). The 145x index win did **not** move the per-row cost through this path — it is still in the same band as the 762 ms/row measured on Aug 9.

### Throughput vs intake — marginal, not hopeless

- 7-day intake (Aug 9–15): 126,986 rows = **18,141/day average**, with peaks of 36,531 (Aug 14) and 30,820 (Aug 9).
- Best observed drain with the flag on: **20,197/day** (Aug 9); 18,348 on Aug 6, which *exceeded* that day's intake of 12,029.

So the drain can beat an average day and loses badly on a 30k day. Net drawdown at best ≈ 2k/day → roughly **39 days** to clear the 78k drainable backlog, assuming intake stays at average. It will not clear it during show weeks.

### Why it is off (the containment measure)

`enrichment_flags.updated_at` reads `2026-08-09 02:21:13Z` — **do not use that as the flip time.** That timestamp is the row's *insert*, from migration `20260809022113_w1_fanin_drain_trigger.sql`, which inserted the flag with `enabled = true`. There is no trigger on `enrichment_flags` to bump `updated_at` on UPDATE, and `track_commit_timestamp` is off, so the column has been frozen since creation.

The real off-time comes from the dispatch state: `enrichment_chain_state.comps_fanin_drain.last_fired_at = 2026-08-11 07:47:22Z` and `comps_fanin_kick.last_kick_at = 2026-08-11 07:48:17Z`, both frozen while 85k observations have arrived since. **Dispatch stopped ~2026-08-11 07:48Z.**

The surrounding context is commit `49f04c553` (Ben, Aug 10 22:23 MDT), *"fix(show-prep): park 27,965-row comp backlog…"*, quoting Ben directly: *"we do NOT want those 27k draining right now"* and *"i need ALL human lane… working."* Its migration header records the incident: `lkup_resolve_comp_v2` at 445–634 ms/row from the per-row trigger, one `/scan` enqueuing ~700 rows (705 measured in one minute) ≈ 9 minutes of matcher work per scan; `comps-rematch` holding a `backend_direct` slot (limit 5) up to 100 s → **`53300 too many connections`, 57× during the outage**, with live surfaces 504ing.

This is a containment measure taken during a live show, for a cause that is still present. That is the answer to "why is it off."

---

## Retractions — prior findings this audit disproves

These are in `audit/sessions/20260809/scripts/skill_addendum_20260815.md` and Turso todo **#12787**. Both should be corrected in place.

**1. "Nothing ever parks — no code path SETS `parked_at`, so poison rows retry forever."** Wrong in its premise. 28,162 rows *are* parked, all within **four distinct minutes** (`2026-08-11 04:13:53Z` → `04:30:02Z`) — the one-time bulk `UPDATE` in migration `20260811040000_park_fanin_backlog_human_lane.sql`. The 27,110 parked rows with `NULL last_error` that #12787 calls "undiagnosable" are simply that deliberate park. **There is no mystery park path to hunt.** The real defect is the adjacent one: no *automatic* park exists, so chronically failing rows never get demoted.

**2. "`oldest_undone` frozen at 2026-08-05 is the proof of LIFO starvation."** That row is parked — it is frozen because Ben froze it. The honest proof is the oldest *drainable* row: `2026-08-11 04:30:36Z`, 4.8 days old and not advancing while newer rows drain. LIFO starvation is still real (both `drain_comps_fanin` and `drain_comps_fanin_batch` order `enqueued_at DESC`); the cited evidence was the wrong row.

**3. "`populate_comps_from_marketplace` uses ILIKE identity matching and writes `coin_lkup_uuid` itself."** Not supported by the live function body. `coin_lkup_uuid` appears exactly once, at offset 3604, **read-only inside a `CASE` predicate** that decides `match_version`; it is absent from the `INSERT` column list and from every `ON CONFLICT DO UPDATE SET` assignment. The two `ILIKE`s are on `s.buying_format` (`'%auction%'`, `'%fixed%'`) classifying `sale_state` — nothing to do with identity. Identity is set downstream by `trg_comps_match → _comps_match_on_write → lkup_resolve_comp_v2`. Damage count either way: **5 of 39,975 bound comps carry no `match_kind` (0.01%)**. Latent at most; not a reason to keep the flag off.

**4. "Ceiling below intake by construction (~18.2k/day)."** That arithmetic assumes one 15-second drain call per 90-second debounce. It omits the Edge Function's own loop — `FANIN_WALL_MS = 100_000` with up to **60 passes** per invocation (`comps-rematch/index.ts:91,98`), each pass a fresh `drain_comps_fanin` call. Observed reality beat the estimate on Aug 6 (18,348 drained vs 12,029 intake). The ceiling is *marginal*, not structurally below intake — which changes the fix from "redesign" to "raise headroom."

---

## Unverified

- **Whether the 28,162 parked rows are still worth draining.** Their observations are 5–11 days old; whether the resulting comps are still useful comps is a business call I can't measure. Settled by sampling ~50 parked rows and checking whether the listing is still live/priced.
- **What throughput the drain reaches with the current spine index.** My 636 ms/row is the matcher only. Settled by running `drain_comps_fanin(50, 20000)` once in a quiet window and reading `processed` against elapsed — that is a mutation, so I did not run it.
- **Whether `lkup_resolve_comp_v2` is the matcher Ben wants on this path.** `_comps_match_on_write` calls it live on every comps write (contradicting the stored note that it has zero callers), but `docs/integrity/BEN_MATCHING_REQUIREMENTS_2026-08-09.md` governs which matcher is canonical, and W3 owns that decision.

---

## Landmine to fix before anyone touches this again

`public.drain_comps_fanin_batch` filters only `done_at is null and attempts < 5` — **it does not check `parked_at`.** Anything that calls it walks straight through Ben's 28,162-row containment park. It also self-chains via `net.http_post` to its own PostgREST RPC, so a single kick keeps going on its own. It currently has no caller in the repo (only the generated `database.types.ts`), so it is dormant — but it is one RPC call away from undoing the park, silently.

---

## What I'd do instead, in this order

1. **Now (flag stays off):** nothing during the live session. If you want the current scan's comps matched, hit the `/coin` refresh button — that path already works and bypasses the flag.
2. **Add `parked_at is null` to `drain_comps_fanin_batch`.** One line, removes the containment bypass.
3. **Fix the ordering** to FIFO or age-weighted within each priority band (keep `priority DESC` first so a live scan still jumps the queue). Without this, enabling the flag leaves the 4.8-day tail permanently unreachable — you would be adding load without ever finishing.
4. **Add automatic parking after N attempts,** writing `last_error`, so the 1,068 lock-timeout/deadlock rows stop being retried and every park is diagnosable.
5. **Then enable — in a quiet window, watched.** Prove it with the effect, not the flag: `processed` climbing, `oldest drainable enqueued_at` *advancing*, `backend_direct` connections staying under 5, and no `53300` in the logs. Rollback is one UPDATE back to `false`; the queue is untouched either way (the flag gates dispatch only — rows keep enqueuing regardless).
6. **Decide the 28,162 parked rows separately,** as an explicit unpark once throughput exceeds intake with headroom — not as a side effect of flipping a flag.

Durable corrections from this audit belong in the grow-only addendum `audit/sessions/20260809/scripts/skill_addendum_20260815.md` (retractions 1–4) and against Turso todo **#12787**, whose premise (a) is now resolved: the mass-park was migration `20260811040000`, not an unknown code path.
