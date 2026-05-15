---
name: debloat
description: Controlled, FK-safe Turso row debloater. Finds identical-content duplicate rows within supersession chains (72.1x skills, 888x memory, soul_current crash patterns), rewires `superseded_by` pointers around middle-duplicates so no chain breaks, updates `*_current` pointer tables to land on the surviving row, and only then deletes hash-duplicate victims. Per-table transaction + full-table backup + dry-run confirmation required before any DELETE. SUPERSEDES the prior "NEVER delete Turso rows" HARD RULE — that rule was a bloat-containment workaround that let the problem compound; `/debloat` is the supervised cleanup it was waiting for.
---

# /debloat — Controlled Turso Row Debloater with FK Integrity + Reversible Backup

**Principle:** A row is **safe to delete** if and only if three conditions hold simultaneously:
1. Its `content_hash` equals its predecessor's in the supersession chain (zero-information duplicate).
2. No `*_current` pointer table points at it (or we redirect the pointer in the same transaction).
3. Every forward/back pointer around it can be rewired to preserve chain continuity.

Otherwise: **leave it alone.** This skill is conservative — it collapses middle-duplicates, not history.

**Reversibility invariant (Ben directive 2026-04-18):** every `/debloat` run dumps the full affected table to a durable `.sql.gz` BEFORE any DELETE, verifies the dump with `gunzip -t`, and documents the restore recipe. No run proceeds without a verified backup. Restore is one command: `gunzip -c <file> | turso db shell <url>`.

**Temporal-preservation invariant (Ben directive 2026-04-18):** when collapsing a content-dup cluster into a single surviving row, the surviving row MUST inherit the **earliest** `created_at` / `as_of_date` / `created_date` across the cluster — not the newest, and not its own original. This is non-negotiable because vector search and temporal search both use these timestamps to answer "when did this content first appear" — if we keep only the newest row's timestamp, every debloat run visibly rewrites history (content that first appeared 6 months ago now looks like it appeared yesterday).

Per-row coalesce rule before marking-superseded or deleting a cluster:
- `survivor.created_at   = MIN(cluster.created_at)`   — earliest first-observation for vector/temporal search
- `survivor.as_of_date   = MIN(cluster.as_of_date)`   — earliest "effective from"
- `survivor.created_date = MIN(cluster.created_date)` — earliest date-granularity
- `survivor.updated_at`  — **LEAVE UNTOUCHED**. Do NOT set to MAX or "now". See next paragraph.
- `survivor.embedding_vector / embedding_model / embedded_at` — COALESCE from cluster ONLY if survivor has NULL. Do NOT overwrite a non-NULL survivor embedding with a sibling's. If COALESCE fills an embedding, the three fields move as a triple (never fill `embedded_at` without its matching `embedding_vector`).

**Why `updated_at` must NOT be touched** (Ben caught this 2026-04-18 before the skill was run in anger): every differential-sync layer downstream (`claude-sync pull`, `embed-watcher`, derived-table cache invalidators) uses `updated_at` as its "is this row newer than what I have?" signal. Setting all survivors to `MAX(cluster.updated_at)` — which is almost always "near-now" because the last duplicate write IS the race that produced the cluster — makes every survivor look freshly-written to every downstream client. Each client's next sync would pull all survivors, miss them in its cold local hash cache, and re-INSERT the same supersede pattern that created the original bloat. `MAX(updated_at)` literally recreates the bug /debloat is fixing. Equivalent cascade through `embed-watcher`: `updated_at` change → re-embed → new `embedded_at` + `embedding_vector` → more "changed" signal → more downstream re-work.

The survivor's original `updated_at` is correct as-is — it represents when the row's content-as-it-stands was actually last written by a live process. Debloat is not a content change; it's a cleanup of redundant history. Surviving rows should look to downstream as "no change" so nothing reacts.

Execute this coalesce in the SAME transaction as the supersession/delete, BEFORE the UPDATE that marks the non-survivors superseded. Rolling back the coalesce is a single `UPDATE survivor SET created_at=<orig>, as_of_date=<orig>, ...` — record the originals to `$AUDIT_DIR/pre-coalesce-timestamps.json` before the UPDATE so rollback has what it needs. `updated_at` does NOT need to be recorded in the rollback file because we're not changing it.

**Why this skill exists:** `feedback_never_vacuum_or_delete_turso.md` banned DELETE + VACUUM as a safety net, but bloat kept compounding (memory 888x; skills 72.1x; soul `NOT NULL constraint failed: soul_current.soul_id` crashes blocking `claude-sync push` for every agent). The ban prevented accidental damage AND prevented any cleanup. `/debloat` is the supervised, reversible path forward.

---

## When to invoke

- `/debloat` → audit all known-bloated tables, no execute
- `/debloat <table>` → audit + dry-run proposal for that table
- `/debloat <table> --execute` → after Ben explicitly confirms the dry-run output
- Pre-flight inside `/exit-protocol` when the daily log mentions a sync crash
- After any `claude-sync push` that fails with `NOT NULL constraint failed: *_current.*_id`

**Never run `--execute` without Ben seeing the dry-run proposal in the same turn.** The script prints before/after counts and waits for confirmation. Confirmation is a safety hard stop — invoking `--execute` without it is a `awaiting-approval-for-non-safety-stop` inverted: here, approval actually is required.

---

## Step 0 — Identity + env

```bash
MY_SID_FULL=$(~/bin/my-claude-session-id 2>/dev/null || echo "manual")
MY_SID_SHORT=${MY_SID_FULL%%-*}
TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
TOK=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
[ -n "$TOK" ] || { echo "ERROR: no turso token in keychain"; exit 1; }

# Durable audit/backup dir (no /tmp per policy #766)
AUDIT_DIR=~/clawd/data/debloat/$(date +%Y-%m-%d)-${MY_SID_SHORT}
mkdir -p "$AUDIT_DIR"
```

**Turso CLI quirks learned during 2026-04-18 live run — read before writing execute SQL:**

1. **Dot-commands don't work.** `.headers on`, `.mode column`, `.tables`, `.schema` all return "unknown command or invalid arguments". Write pure SQL; default output already has headers in caps.

2. **`.dump <table>` is also broken.** Even as a single-arg invocation it outputs 20 bytes of nothing. Do NOT rely on `turso db shell "$URL" ".dump soul" | gzip` — the gzip will "succeed" (valid empty gzip) and `gunzip -t` will pass, but the file has zero INSERT statements. **Use JSON-based backup instead** (see Step 3 below).

3. **Multi-statement transactions break across turso CLI calls.** `BEGIN; UPDATE; UPDATE; DELETE; COMMIT;` fed via `turso db shell` heredoc may auto-commit each statement into its own implicit transaction, and the explicit `COMMIT` errors with "cannot commit - no transaction is active". **Use the libsql HTTP pipeline API** (`/v2/pipeline` POST) for real multi-statement transactions — all statements share one connection/session.

4. **`CREATE TEMP TABLE` doesn't persist across pipeline statements either.** Even inside a pipeline transaction, subsequent statements get "no such table: dedup_keepers". **Use inline subqueries** (repeat the SELECT in each statement) instead of temp tables.

5. **`soul.id` has NULL values.** Live probe 2026-04-18: 381 of 23,309 rows have `id IS NULL` (column is `INT, NOT NULL=0, PK=0` — not a proper primary key). `MAX(id)` / `MIN(id)` poisons `NOT IN` subqueries (returns NULL which is UNKNOWN in boolean context → zero rows match, DELETE becomes no-op). **Use `rowid` instead of `id`** for all keeper-selection aggregates — SQLite's built-in rowid is always non-null and unique. Separate todo #3418 for fixing the schema.

6. **`soul_current.soul_id` is NOT NULL.** If your UPDATE redirects a pointer to a keeper whose `id IS NULL`, you get `SQLITE_CONSTRAINT: NOT NULL constraint failed`. Check keeper has `id IS NOT NULL` before the UPDATE, OR just DELETE the stale pointer and let the next sync recreate it (for regenerable keys).

---

## Step 0.5 — Pre-audit schema probe (NEW — mandatory first run)

**Why:** column names vary per table in real schemas (learned the hard way). `skills_current` uses `(skill_name, file_path, skill_id)` not `(agent_id, key)`. `memory` table has NO `content_hash` column — only `content` + a timestamp. `facts`/`policies`/`opinions`/`assumptions` each store content in a table-named column (`fact`, `policy`, `opinion`, `assumption`) instead of a uniform `content`. Writing audit SQL assuming a canonical schema will fail mid-batch with `no such column` errors.

Run the probe first, **then** write audit SQL against actual schemas:

```bash
echo "=== pre-audit schema probe ==="
for t in soul memory skills soul_current memory_current skills_current facts policies opinions assumptions; do
  SCHEMA=$(turso db shell "$TURSO_URL?authToken=$TOK" "PRAGMA table_info($t);" 2>&1 | tail -n +2 | awk '{print $2}' | tr '\n' ',' | sed 's/,$//')
  printf "  %-20s %s\n" "$t:" "$SCHEMA"
done > "$AUDIT_DIR/schema-probe.out" 2>&1
cat "$AUDIT_DIR/schema-probe.out"
```

**Verified schemas as of 2026-04-18** (re-probe if this skill is run > 30 days from now):

| Table | Content column | Hash column | Active flag | Pointer table + FK column |
|---|---|---|---|---|
| `soul` | `content` | `content_hash` | `valid_until IS NULL` | `soul_current.soul_id` (PK: agent_id, key) |
| `memory` | `content` | **none — compute on-the-fly** | `valid_until IS NULL` | `memory_current.memory_id` (PK: agent_id, date) |
| `skills` | `content` | `content_hash` | `valid_until IS NULL` | `skills_current.skill_id` (PK: skill_name, file_path) |
| `facts` | `fact` | none — use `fact` column equality | `valid_until IS NULL` (or `active=1`) | none (use `superseded_by`) |
| `policies` | `policy` | none | `valid_until IS NULL` | none |
| `opinions` | `opinion` | none | `valid_until IS NULL` | none |
| `assumptions` | `assumption` | none | `valid_until IS NULL` | none |
| `violations` | n/a — append-only | n/a | n/a (no supersession) | SKIP — not a debloat target |
| `captains_log` | n/a — append-only with optional `admin_override` supersede | n/a | n/a | SKIP — amend-only |

---

## Step 1 — Audit bloat (read-only)

```bash
# Pure SQL — no dot-commands, will fail under turso db shell otherwise
cat > "$AUDIT_DIR/audit.sql" <<'SQL'
-- soul: has content_hash, has pointer table
SELECT 'soul' AS tbl,
  (SELECT COUNT(*) FROM soul) AS total,
  (SELECT COUNT(*) FROM soul WHERE valid_until IS NULL) AS active,
  (SELECT COUNT(DISTINCT content_hash) FROM soul WHERE valid_until IS NULL) AS distinct_active,
  (SELECT COUNT(*) FROM soul_current) AS pointer_rows,
  (SELECT COUNT(*) FROM soul_current WHERE soul_id NOT IN (SELECT id FROM soul)) AS pointer_orphans,
  (SELECT COUNT(*) FROM soul s JOIN soul p ON p.superseded_by = s.id
   WHERE s.content_hash = p.content_hash) AS chain_dupes;

-- skills: has content_hash, has pointer table
SELECT 'skills' AS tbl,
  (SELECT COUNT(*) FROM skills) AS total,
  (SELECT COUNT(*) FROM skills WHERE valid_until IS NULL) AS active,
  (SELECT COUNT(DISTINCT content_hash) FROM skills WHERE valid_until IS NULL) AS distinct_active,
  (SELECT COUNT(*) FROM skills_current) AS pointer_rows,
  (SELECT COUNT(*) FROM skills_current WHERE skill_id NOT IN (SELECT id FROM skills)) AS pointer_orphans,
  (SELECT COUNT(*) FROM skills s JOIN skills p ON p.superseded_by = s.id
   WHERE s.content_hash = p.content_hash) AS chain_dupes;

-- memory: NO content_hash column — use LENGTH + SUBSTR proxy for audit only
-- (for actual debloat, add content_hash column first via migration OR compute in-flight)
SELECT 'memory' AS tbl,
  (SELECT COUNT(*) FROM memory) AS total,
  (SELECT COUNT(*) FROM memory WHERE valid_until IS NULL) AS active,
  NULL AS distinct_active_hash,
  (SELECT COUNT(*) FROM memory_current) AS pointer_rows,
  (SELECT COUNT(*) FROM memory_current WHERE memory_id NOT IN (SELECT id FROM memory)) AS pointer_orphans,
  (SELECT COUNT(*) FROM memory m JOIN memory p ON p.superseded_by = m.id
   WHERE LENGTH(m.content) = LENGTH(p.content)
     AND SUBSTR(m.content,1,256) = SUBSTR(p.content,1,256)) AS chain_dupes_proxy;

-- facts/policies/opinions/assumptions: content lives in named column, no pointer table
SELECT 'facts' AS tbl,
  (SELECT COUNT(*) FROM facts) AS total,
  (SELECT COUNT(*) FROM facts WHERE valid_until IS NULL) AS active,
  (SELECT COUNT(*) FROM facts f JOIN facts p ON p.superseded_by = f.id
   WHERE f.fact = p.fact) AS chain_dupes;
SELECT 'policies' AS tbl,
  (SELECT COUNT(*) FROM policies) AS total,
  (SELECT COUNT(*) FROM policies WHERE valid_until IS NULL) AS active,
  (SELECT COUNT(*) FROM policies f JOIN policies p ON p.superseded_by = f.id
   WHERE f.policy = p.policy) AS chain_dupes;
SELECT 'opinions' AS tbl,
  (SELECT COUNT(*) FROM opinions) AS total,
  (SELECT COUNT(*) FROM opinions WHERE valid_until IS NULL) AS active,
  (SELECT COUNT(*) FROM opinions f JOIN opinions p ON p.superseded_by = f.id
   WHERE f.opinion = p.opinion) AS chain_dupes;
SELECT 'assumptions' AS tbl,
  (SELECT COUNT(*) FROM assumptions) AS total,
  (SELECT COUNT(*) FROM assumptions WHERE valid_until IS NULL) AS active,
  (SELECT COUNT(*) FROM assumptions f JOIN assumptions p ON p.superseded_by = f.id
   WHERE f.assumption = p.assumption) AS chain_dupes;
SQL

turso db shell "$TURSO_URL?authToken=$TOK" < "$AUDIT_DIR/audit.sql" > "$AUDIT_DIR/audit.out" 2>&1
cat "$AUDIT_DIR/audit.out"
```

**Compute bloat ratio = total / active.** Flag any table with ratio > 5x. BUT (learned 2026-04-18): **high ratio ≠ debloat target**. If `chain_dupes == 0`, the bloat is legitimate supersession history (different content per row). `/debloat` only removes *content-identical* chain-dupes. Only proceed to Step 2 if `chain_dupes > 0`.

**Reference baseline — live audit 2026-04-18** (for sanity-checking future runs):

| Table | Total | Active | Ratio | Chain dupes |
|---|---|---|---|---|
| soul | 23,309 | 2,626 | 8.9x | 0 (legit history) |
| skills | 9,570 | 1,250 | 7.7x | 0 (legit history) |
| memory | 10,796 | 10,796 | 1.0x | 1 (proxy — trivial) |
| facts | 797 | 796 | 1.0x | 17 (debloat target) |
| policies | 763 | 759 | 1.0x | 4 (small target) |
| opinions | 105 | 105 | 1.0x | 0 |
| assumptions | 79 | 79 | 1.0x | 2 (small target) |

## Live-run results 2026-04-18 (the skill's first real execution)

First production run on AGENT_CONTEXT.md cluster in soul table. Used to calibrate everything above:

| Metric | Before | After | Δ |
|---|---|---|---|
| AGENT_CONTEXT.md rows | 374 | 50 | −324 (−86.6%) |
| Claude agent cluster | 293 | 21 | −272 (−92.8%) |
| Unique content versions preserved | n/a | 50/50 | zero content lost |
| Orphan pointers pre-cleanup | 0 | 14 transient | expected (NOT NULL failure on id-null keepers) |
| Orphan pointers post-cleanup | 0 | 1 remaining (different key) | todo'd separately |
| `as_of_date` on survivors | mixed | unified to run-time | reader's staleness check now accurate |
| soul total | 23,309 | 22,985 | −324 |

**Key lessons encoded into the skill above:**
1. `.dump` doesn't work → JSON backup via `json_group_array` + HTTP pipeline
2. Multi-statement transactions fragment across `turso db shell` → use HTTP pipeline
3. TEMP TABLE doesn't persist across pipeline statements → use inline subqueries
4. `soul.id` has NULLs (381/23309) → use `rowid` for keeper selection, filter `id IS NOT NULL` before UPDATE *_current
5. `soul_current.soul_id` is NOT NULL → filter keepers to non-null id, OR delete orphan pointers and let regen repopulate
6. `as_of_date` is the canonical "last checked" column per policy #685 → UPDATE it post-dedup so reader freshness-check sees current timestamp

**Todos that landed from this run:**
- #3414 — fix supersedeSoul loop-supersede + flock + partial UNIQUE index
- #3415 — race-condition regression test for supersedeSoul
- #3417 — REGENERABLE_KEYS writer UPSERT-in-place for AGENT_CONTEXT.md
- #3418 — soul.id schema repair (set NOT NULL, backfill NULLs from rowid, mark as PRIMARY KEY)

---

**Correction (2026-04-18, after deeper probe):** the chain-adjacent predicate alone UNDERCOUNTS the real bloat. The true debloat targets fall into three disjoint bloat-shape buckets:

### Bloat shape taxonomy

| Shape | Definition | Detection SQL (soul as example) | v1 action | v2 action |
|---|---|---|---|---|
| **CHAIN-ADJACENT** | `p.superseded_by = v.id AND p.content_hash = v.content_hash` (pair of adjacent same-content rows) | already in Step 4 CTE | UPDATE+DELETE in batch | — |
| **CONTENT-DUPLICATE ACTIVES** | N rows share `content_hash` (or `content` if no hash) AND all have `valid_until IS NULL` — only one should be active (the one in `*_current`); the others are leaked-active from cross-session race | `SELECT content_hash, COUNT(*) FROM soul WHERE valid_until IS NULL GROUP BY content_hash HAVING COUNT(*) > 1;` | MARK-SUPERSEDED (set `valid_until=unixepoch()` + `superseded_by=<canonical.id>` on the non-canonical dupes) — NO DELETE | DELETE the mark-superseded rows after v1 verify passes |
| **ORPHAN-ACTIVE** | Flagged active but not pointed at by `*_current` (lost its pointer from earlier sync crashes) | `SELECT id FROM soul WHERE valid_until IS NULL AND id NOT IN (SELECT soul_id FROM soul_current);` | Determine canonical via `*_current`, then MARK-SUPERSEDED against it | DELETE after v1 verify |
| **REGENERABLE-KEY** | Content is auto-regenerated every session from upstream sources (e.g. `AGENT_CONTEXT.md` rebuilt from Turso every sync). History rows carry zero signal because the data is derivable from the source tables. | key matches the regenerable-key allowlist (currently: `AGENT_CONTEXT.md`) | UPDATE current row in-place (no supersession) + DELETE all historical rows for this key. Writer must also switch to UPDATE-in-place. | same as v1 — regenerable keys have no meaningful history to preserve |

### Why "mark-superseded first, delete later" (v1/v2 split)

- MARK-SUPERSEDED is fully reversible: `UPDATE ... SET valid_until = NULL, superseded_by = NULL WHERE id IN (<marked_ids>)`. Ben can roll back a bad pass with one UPDATE, no .sql.gz restore needed.
- DELETE is irreversible within the DB; a bad pass needs `gunzip -c backup.sql.gz | turso db shell ...` which is minutes, not seconds.
- First live audit (2026-04-18) found soul had ~2,538 content-dup active rows across 29 hash groups. If v1 marks them superseded wrong (e.g. picks a non-canonical row as the one to keep), rollback is instant. If v2 had deleted them, rollback is a full-table restore.

### Actual debloat targets as of 2026-04-18 first live audit

| Table | Pattern-1 chain-adjacent | Pattern-2 content-dup active groups | Pattern-3 orphan-active | Combined |
|---|---|---|---|---|
| soul | 0 | 29 groups / 2,538 redundant | 1,102 rows | ~2,538-3,640 rows |
| skills | 0 | ~978 rows (but `content_hash IS NULL` on all — use `content` col) | 1,003 | ~978-2,253 rows |
| memory | 1 proxy | ~675 rows by (agent_id,date) | 2,232 | ~2,900 rows |
| facts | 17 | (not measured — add to next audit) | n/a | ≥17 |
| policies | 4 | (not measured) | n/a | ≥4 |
| assumptions | 2 | (not measured) | n/a | ≥2 |

**Prior bloat claims (888x memory, 72.1x skills) were NOT chain-adjacent in live state** — they were *content-dup active* or *orphan-active* which the v1 audit SQL didn't catch. The 8.9x soul ratio and 7.7x skills ratio correspond mostly to the content-dup-active pattern, which IS a debloat target.

---

## Step 1.5 — Diagnose source of bloat (MANDATORY before any execute)

**Cleaning up rows without fixing the writer means every /debloat run re-fills the bucket.** This step finds the producer(s) of the bloat so we can ALSO `todo add` a fix for the upstream write path before running execute. Without it, the skill is a cron job that undoes itself.

For each table with non-trivial chain-dupes or content-dup actives, run the four source-diagnosis probes below and write output to `$AUDIT_DIR/source-diagnosis-<table>.out`.

### Probe 1 — Culprit agent/session/platform

Which writer produced the duplicate rows? If 80%+ of dupes share one `created_by_session` / `created_by_platform` / `created_by_machine`, that's the producer. If they spread evenly across all agents, it's a shared code path.

```sql
-- Top culprits for content-dup actives (soul example — adapt column for other tables)
WITH dupe_clusters AS (
  SELECT content_hash FROM soul WHERE valid_until IS NULL
  GROUP BY content_hash HAVING COUNT(*) > 1
)
SELECT
  COALESCE(s.created_by_session, 'null') AS session,
  COALESCE(s.created_by_platform, 'null') AS platform,
  COALESCE(s.created_by_machine, 'null') AS machine,
  COALESCE(s.created_by, 'null') AS agent,
  COUNT(*) AS dupe_rows_produced
FROM soul s
JOIN dupe_clusters dc ON s.content_hash = dc.content_hash
WHERE s.valid_until IS NULL
GROUP BY session, platform, machine, agent
ORDER BY dupe_rows_produced DESC
LIMIT 10;
```

**Interpretation rules:**
- ≥80% of dupes concentrated in one (session, platform) pair → that session's code path is the single producer. Read its sync code.
- Spread across 5+ sessions but one platform → the platform's shared writer is the producer.
- Spread across 5+ platforms → the cross-platform shared code (usually `~/clawd/scripts/sync.mjs`) is the producer.

### Probe 2 — Temporal pattern (burst vs steady-state)

When did the dupes get written? A tight time window (minutes) points at a race-condition / concurrent-write bug. Spread over weeks means a recurring write that should have been deduped on each run by the server-side hash-check but wasn't.

```sql
-- Per-cluster: how tight is the time window across the dupes?
WITH dupe_clusters AS (
  SELECT content_hash FROM soul WHERE valid_until IS NULL
  GROUP BY content_hash HAVING COUNT(*) > 1
)
SELECT
  s.content_hash,
  COUNT(*) AS dupe_count,
  MIN(s.created_at) AS first_seen,
  MAX(s.created_at) AS last_seen,
  (MAX(s.created_at) - MIN(s.created_at)) AS span_seconds,
  CASE
    WHEN (MAX(s.created_at) - MIN(s.created_at)) < 300 THEN 'burst-race (<5min)'
    WHEN (MAX(s.created_at) - MIN(s.created_at)) < 86400 THEN 'single-day recurring'
    WHEN (MAX(s.created_at) - MIN(s.created_at)) < 2592000 THEN 'multi-day recurring'
    ELSE 'multi-month recurring'
  END AS pattern
FROM soul s
JOIN dupe_clusters dc ON s.content_hash = dc.content_hash
WHERE s.valid_until IS NULL
GROUP BY s.content_hash
ORDER BY dupe_count DESC
LIMIT 20;
```

**Interpretation rules:**
- `burst-race` → concurrent writers with no flock or no hash-check read. Fix: add server-side `SELECT content_hash WHERE valid_until IS NULL` before INSERT.
- `single-day recurring` → a daily cron writes the same row with no dedup.
- `multi-day recurring` → every session start or every sync push re-writes regardless of change.
- `multi-month` → likely a one-off historical accumulation; fix is less urgent.

### Probe 3 — Key/content pattern

Which logical keys bloat most? If 10 keys produce 90% of dupes, those keys are the hotspots. Reading their content reveals which *kind* of data the broken writer handles.

```sql
SELECT
  s.agent_id, s.key,
  COUNT(*) AS dupe_rows,
  LENGTH(MAX(s.content)) AS content_bytes
FROM soul s
JOIN (
  SELECT content_hash FROM soul WHERE valid_until IS NULL
  GROUP BY content_hash HAVING COUNT(*) > 1
) dc ON s.content_hash = dc.content_hash
WHERE s.valid_until IS NULL
GROUP BY s.agent_id, s.key
ORDER BY dupe_rows DESC
LIMIT 20;
```

**Interpretation:** a hotspot list of (agent_id, key) pairs. Now read the code that writes to each: if `s.key = 'memory/MEMORY.md'` is top, `sync.mjs` memory path is the producer; if `s.key = 'skills/SKILL.md'` is top, `bigmac-skills push` is the producer; etc.

### Probe 4 — Writer path inspection (static)

Given Probes 1-3, identify the specific code paths. For `~/clawd/scripts/sync.mjs`:

```bash
grep -nE 'INSERT INTO (soul|memory|skills|facts|policies|opinions|assumptions)' ~/clawd/scripts/sync.mjs
grep -nE 'supersede|valid_until|content_hash' ~/clawd/scripts/sync.mjs
```

For each INSERT, check:
- Does it gate on `content_hash === existing.content_hash → return early`? If NO, that's a producer of content-dup bloat.
- Does it read from a local hash cache that isn't invalidated cross-session? If YES, that's the cold-cache cross-session bloat pattern.
- Does it run inside flock on the machine? If NO, concurrent writers race each other on the same content.

### Produce the diagnosis report

Write `$AUDIT_DIR/source-diagnosis-<table>.md`:

```
# Source-of-bloat diagnosis — <table>

## Culprits (from Probe 1)
| session | platform | machine | dupe rows |
|---|---|---|---|
| ... | ... | ... | ... |

## Temporal pattern (from Probe 2)
- N clusters in `burst-race` → likely concurrent-writer race
- M clusters in `multi-day recurring` → writer doesn't dedup on repeat runs

## Key hotspots (from Probe 3)
Top 10 (agent_id, key) pairs:
- ...

## Writer path (from Probe 4)
- `sync.mjs:<line>` — INSERT into <table> — has/does not have hash gate
- Producer verdict: <X> writer path at <file:line>

## Required fix (todo-add)
- `todo add 'fix bloat source in <file:line> — add pre-write hash gate (see debloat/source-diagnosis-<table>.md)' --tags=bloat-source,debloat,sync.mjs`
```

**HARD RULE:** the `todo add` for the writer fix MUST be executed before the `/debloat <table> --execute` pass. Cleaning up rows while the producer is still broken is the `repeat-same-workaround-3x` pattern — you'll find yourself running /debloat weekly.

If the diagnosis identifies the producer as a live code path, ALSO `todo add` a test: "add cross-session race-condition test for <file:line> — two processes should produce one row, not two". Tests keep the fix from regressing silently.

### Pre-existing bugs surfaced by the audit (log and fix separately)

- **skills.content_hash is NULL on all 1,250 active rows** — writer isn't populating it. Content-hash-based debloat on skills is impossible until backfill. Either (a) one-shot migration `UPDATE skills SET content_hash = <sha256(content)> WHERE content_hash IS NULL` or (b) fix the writer and wait. Log as todo.
- **memory has 2,232 active rows with no `memory_current` pointer** — means `knowledge-search --tables memory` is missing 21% of the active set. Downstream correctness bug, not just bloat. Log as todo.

---

## Step 2 — Dry-run: enumerate safe-delete candidates

**Safe-delete candidate (middle-duplicate):**
- Row V in chain `… → P → V → N …` (i.e., `P.superseded_by = V.id`)
- `V.content_hash == P.content_hash` (zero information in V)
- Pointer-table reference to V.id will be redirected to P.id in the same transaction

**Rewire plan per victim:**
- `UPDATE <t>_current SET <t>_id = P.id WHERE <t>_id = V.id` — pointer lands on surviving predecessor (same content by definition)
- `UPDATE <t> SET superseded_by = V.superseded_by WHERE id = P.id` — P now skips V, points to N
- `DELETE FROM <t> WHERE id = V.id`

**Dry-run SQL (count-only, no writes):**

```bash
cat > "$AUDIT_DIR/dryrun-skills.sql" <<'SQL'
SELECT v.id AS victim_id, p.id AS prev_id, v.superseded_by AS next_id,
       v.agent_id, v.key, v.content_hash
FROM skills v JOIN skills p ON p.superseded_by = v.id
WHERE v.content_hash = p.content_hash
ORDER BY v.id LIMIT 20;

SELECT COUNT(*) AS victims, SUM(LENGTH(content)) AS bytes_freed_approx
FROM skills v JOIN skills p ON p.superseded_by = v.id
WHERE v.content_hash = p.content_hash;

SELECT COUNT(*) AS pointer_redirects
FROM skills_current sc
WHERE sc.skill_id IN (
  SELECT v.id FROM skills v JOIN skills p ON p.superseded_by = v.id
  WHERE v.content_hash = p.content_hash
);
SQL

turso db shell "$TURSO_URL?authToken=$TOK" < "$AUDIT_DIR/dryrun-skills.sql" > "$AUDIT_DIR/dryrun-skills.out" 2>&1
```

**Report shape:**

```
🔎 /debloat dry-run — skills table
─────────────────────────────────
Current state:
  total=48,123  active=666  distinct_active=661  pointer_rows=666
  → 72.3x bloat ratio
Debloat plan:
  victims=47,457  (identical-content middle-duplicates)
  pointer_redirects=N
  bytes_freed_approx=~180 MB
Rewire plan:
  N      × UPDATE skills_current SET skill_id=<prev>
  47,457 × UPDATE skills SET superseded_by=<next> WHERE id=<prev>
  47,457 × DELETE FROM skills WHERE id=<victim>
Backup target:
  ~/clawd/data/debloat/2026-04-18-1db64396/skills.sql.gz
─────────────────────────────────
Confirm with: /debloat skills --execute
```

---

## Step 3 — Backup FIRST, always (reversibility invariant)

**`turso db shell ".dump <table>"` is broken** (outputs 20 bytes of garbage, see quirk #2 above). The old approach — dump-to-SQL — does NOT work against Turso. Use JSON-based backup via the HTTP pipeline or via a direct `SELECT json_group_array(...)` query instead. It's row-for-row restorable via INSERT replay.

```bash
# JSON backup of the rows we're about to touch (full content, every field)
TURSO_URL="$TURSO_URL" TOK="$TOK" AUDIT_DIR="$AUDIT_DIR" python3 <<'PY'
import subprocess, json, os
url, tok, ad = os.environ['TURSO_URL'], os.environ['TOK'], os.environ['AUDIT_DIR']
# Adjust the WHERE clause to scope to the table + rows you're about to modify.
# Use json_group_array + json_object to produce a single JSON array row.
sql = "SELECT json_group_array(json_object('rowid',rowid,'id',id,'agent_id',agent_id,'key',key,'content',content,'content_hash',content_hash,'created_date',created_date,'updated_at',updated_at,'as_of_date',as_of_date,'valid_until',valid_until,'superseded_by',superseded_by)) FROM soul WHERE key='AGENT_CONTEXT.md';"
res = subprocess.run(['turso', 'db', 'shell', f'{url}?authToken={tok}', sql],
                     capture_output=True, text=True, timeout=60)
for line in res.stdout.splitlines():
    if line.strip().startswith('['):
        data = json.loads(line.strip())
        path = f'{ad}/backup-pre-dedup.json'
        with open(path, 'w') as f: json.dump(data, f)
        print(f'  ✓ backup: {path}  rows={len(data)}  bytes={os.path.getsize(path)}')
        break
else:
    print(f'  ✗ parse failed; stderr[:300]: {res.stderr[:300]}')
    exit(1)
PY
```

**Row-count sanity:** compare the JSON array length against a live `SELECT COUNT(*)` for the same WHERE clause. If they differ, a concurrent writer added/removed rows during the backup window — abort and retry with fewer concurrent sessions.

**Restore recipe** (save as `$AUDIT_DIR/RESTORE.py`):

```python
#!/usr/bin/env python3
# Replay backup-pre-dedup.json back into soul via per-row INSERT
import json, subprocess, os, sys
url = os.environ['TURSO_URL']; tok = os.environ['TOK']
data = json.load(open(sys.argv[1]))
for r in data:
    cols = ','.join(k for k in r if k != 'rowid')
    placeholders = ','.join('?' for _ in r if _ != 'rowid')
    vals = [r[k] for k in r if k != 'rowid']
    # Use libsql HTTP pipeline (safer than CLI for scripted writes)
    # ... (see the pipeline invocation pattern in Step 4 below)
```

Non-negotiable: verify the JSON file parses and has the expected row count BEFORE proceeding to Step 4. If the JSON is malformed or short-count, abort.

**Restore recipe** (document in audit dir + captains-log):
```bash
# ONE-LINER RESTORE — paste this to roll back a debloat run
gunzip -c "$AUDIT_DIR/skills.sql.gz" | turso db shell "$TURSO_URL?authToken=$TOK"
# Then re-run Step 1 audit to confirm row counts match pre-run state.
```

Save this recipe as `$AUDIT_DIR/RESTORE.sh` — an executable script Ben can run without reading SKILL.md again.

Retention: keep `$AUDIT_DIR/` artifacts for 30 days. A separate `debloat-gc.sh` hook prunes older dirs.

---

## Step 4 — Execute (per-table, transactional, batched)

**Canonical execution path: libsql HTTP pipeline `/v2/pipeline`.** The `turso db shell` binary fragments multi-statement transactions and cannot hold temp tables or inline transaction state across heredoc-fed statements. The pipeline POST sends all statements on one connection, one transaction, with atomic commit/rollback.

```bash
TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
TOK=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
HTTPS_URL="${TURSO_URL/libsql:/https:}"

cat > /tmp/pipeline-request.json <<'EOF'
{"requests":[
  {"type":"execute","stmt":{"sql":"BEGIN"}},
  {"type":"execute","stmt":{"sql":"UPDATE soul_current SET ... WHERE ..."}},
  {"type":"execute","stmt":{"sql":"DELETE FROM soul WHERE ..."}},
  {"type":"execute","stmt":{"sql":"SELECT COUNT(*) FROM soul_current WHERE soul_id NOT IN (SELECT id FROM soul WHERE id IS NOT NULL)"}},
  {"type":"execute","stmt":{"sql":"COMMIT"}},
  {"type":"close"}
]}
EOF

curl -s -X POST "$HTTPS_URL/v2/pipeline" \
  -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
  -d @/tmp/pipeline-request.json
```

Each step returns `{type: ok, response: {result: {rows, rows_written, rows_read}}}` OR `{type: error, error: {...}}`. Inspect every step's result — a step's error does NOT abort subsequent steps (they run independently in pipeline order); an explicit BEGIN/COMMIT wraps them atomically IF all succeed. A failed step inside a transaction causes SQLite to abort the transaction on the next statement, usually with "no transaction is active" on the final COMMIT.

**Use `rowid` not `id`.** (See quirk #5.) Replace every `MAX(id)` / `MIN(id)` / `id NOT IN (...)` with `MAX(rowid)` / `MIN(rowid)` / `rowid NOT IN (...)`. Then when you need the row's actual `id` field (e.g. to write it into `soul_current.soul_id`), dereference via `SELECT s.id FROM soul s WHERE s.rowid = <selected-rowid> AND s.id IS NOT NULL`.

**Pre-check keeper has `id IS NOT NULL` before UPDATE-to-keeper.** (See quirk #6.) Otherwise the UPDATE hits `NOT NULL constraint failed: soul_current.soul_id`. Two options:
- Option A: filter keepers to those with non-null id: add `AND s.id IS NOT NULL` to the keeper-selection WHERE clause.
- Option B (for regenerable keys): just DELETE the orphaned `*_current` row. Next sync regenerates the content and repopulates the pointer.

**Do NOT issue a single 47K-row DELETE.** Turso serializes writes at the DB; a huge transaction holds a write lock and stalls every other agent's sync for its full duration. Batch at 500 victims per transaction.

**CRITICAL — batch must process only "chain heads"**, not every predecessor-victim pair. A chain `A→B→C` where all three rows share a hash produces TWO same-content pairs `(A,B)` and `(B,C)`. If both are processed in one batch, the UPDATE rewires `A.superseded_by = B.superseded_by = C`, but DELETE removes both B and C — leaving A pointing at a deleted C (FK orphan). The `NOT EXISTS` subclause below filters out predecessors that are themselves same-content victims, so each batch only touches one pair per chain and the loop converges over O(max-chain-length / 2) passes.

```bash
cat > "$AUDIT_DIR/execute-skills.sql" <<'SQL'
BEGIN TRANSACTION;

  -- Shared CTE: victims selected in this batch.
  -- A victim V's predecessor P must NOT itself be a same-content victim of an
  -- earlier row — i.e., P is a "chain head" for its same-content sub-chain.
  WITH head_victims AS (
    SELECT v.id AS victim_id, p.id AS prev_id, v.superseded_by AS next_id,
           -- capture victim's timestamps so predecessor can inherit the earliest
           v.created_at AS v_created_at, v.created_date AS v_created_date,
           v.embedding_vector AS v_embed, v.embedding_model AS v_embed_model,
           v.embedded_at AS v_embedded_at
    FROM skills v
    JOIN skills p ON p.superseded_by = v.id
    WHERE v.content_hash = p.content_hash
      AND NOT EXISTS (
        SELECT 1 FROM skills p2
        WHERE p2.superseded_by = p.id
          AND p2.content_hash = p.content_hash
      )
    LIMIT 500
  )

  -- 1. Redirect pointer-table rows landing on victims → point at predecessor
  --    (same content by definition, so no information loss)
  UPDATE skills_current
  SET skill_id = (SELECT prev_id FROM head_victims WHERE victim_id = skills_current.skill_id LIMIT 1)
  WHERE skill_id IN (SELECT victim_id FROM head_victims);

  -- 2. Coalesce victim's earliest-timestamp + any embedding INTO the surviving predecessor
  --    (temporal-preservation invariant — predecessor is the survivor, must inherit earliest
  --    created_at / created_date across the cluster so vector+temporal search don't lose
  --    "when this content first appeared"). Note: in the chain-collapse case, the predecessor
  --    created_at is usually already older than the victim's — but not guaranteed if a batch
  --    has collapsed rows out of order across passes, so always MIN().
  UPDATE skills
  SET created_at   = MIN(skills.created_at,
                         (SELECT v_created_at   FROM head_victims WHERE prev_id = skills.id LIMIT 1)),
      created_date = CASE
                       WHEN (SELECT v_created_date FROM head_victims WHERE prev_id = skills.id LIMIT 1) < skills.created_date
                         OR skills.created_date IS NULL
                       THEN (SELECT v_created_date FROM head_victims WHERE prev_id = skills.id LIMIT 1)
                       ELSE skills.created_date
                     END,
      embedding_vector = COALESCE(
        skills.embedding_vector,
        (SELECT v_embed FROM head_victims WHERE prev_id = skills.id LIMIT 1)
      ),
      embedding_model = COALESCE(
        skills.embedding_model,
        (SELECT v_embed_model FROM head_victims WHERE prev_id = skills.id LIMIT 1)
      ),
      embedded_at = COALESCE(
        skills.embedded_at,
        (SELECT v_embedded_at FROM head_victims WHERE prev_id = skills.id LIMIT 1)
      )
  WHERE id IN (SELECT prev_id FROM head_victims);

  -- 3. Rewire each predecessor to skip its victim
  UPDATE skills
  SET superseded_by = (SELECT next_id FROM head_victims WHERE prev_id = skills.id LIMIT 1)
  WHERE id IN (SELECT prev_id FROM head_victims);

  -- 4. Delete the now-orphaned middle-duplicates (or leaf-duplicates)
  DELETE FROM skills WHERE id IN (SELECT victim_id FROM head_victims);

  -- 4. FK integrity probe — these three MUST be zero or ROLLBACK
  SELECT 'orphan_pointers' AS chk, COUNT(*) FROM skills_current WHERE skill_id NOT IN (SELECT id FROM skills);
  SELECT 'orphan_supersedes' AS chk, COUNT(*) FROM skills WHERE superseded_by IS NOT NULL AND superseded_by NOT IN (SELECT id FROM skills);
  SELECT 'active_without_pointer' AS chk, COUNT(*) FROM skills s WHERE s.valid_until IS NULL
    AND NOT EXISTS (SELECT 1 FROM skills_current sc WHERE sc.skill_id = s.id);

COMMIT;
SQL
```

**Leaf-duplicate (last-unique → current) is handled automatically** by the same pattern: when victim V is the current leaf (`*_current.<t>_id = V.id` AND `V.superseded_by IS NULL`), step 1 redirects the pointer to predecessor P (same content), step 2 rewires `P.superseded_by = V.superseded_by = NULL` so P becomes the new leaf, step 3 deletes V. No special case needed — the `NULL`-propagation through the subquery does the right thing.

**Loop until no more chain-dupes:** re-run the chain-dupe count from Step 1 after each batch. When it hits 0, table is clean. Memory at 1.3M rows with typical chain depth ≤20 → one head-victim pair per chain per pass × ~20 passes × 500 rows/batch ≈ ~52K batches ≈ 80-90 min wall time. Slower than a naive single-pass approach, but single-pass would FK-orphan on every chain longer than 2, so correctness beats speed here.

---

## Step 4b — MARK-SUPERSEDED pass (v1 for Pattern-2 and Pattern-3 bloat)

**Run this BEFORE Step 4's chain-collapse**, separately per table, still with backup and dry-run. This pass handles the bloat shapes that are NOT chain-adjacent — **content-duplicate actives** and **orphan-actives**. It does NOT delete; it reactivates supersession semantics so a later pass (v2) can chain-collapse them like any other history.

### SQL for content-duplicate actives (soul example)

```sql
-- Dry-run: identify canonical (one in *_current, or newest if none pointed)
-- and mark the rest as superseded against it.
WITH hash_groups AS (
  SELECT content_hash,
    -- canonical: pointer-target first, else newest by updated_at
    COALESCE(
      (SELECT sc.soul_id FROM soul_current sc
       JOIN soul s2 ON sc.soul_id = s2.id
       WHERE s2.content_hash = soul.content_hash AND s2.valid_until IS NULL LIMIT 1),
      (SELECT s3.id FROM soul s3
       WHERE s3.content_hash = soul.content_hash AND s3.valid_until IS NULL
       ORDER BY s3.updated_at DESC LIMIT 1)
    ) AS canonical_id
  FROM soul
  WHERE valid_until IS NULL
  GROUP BY content_hash
  HAVING COUNT(*) > 1
)
SELECT s.id AS to_mark_id, hg.canonical_id, s.content_hash, LENGTH(s.content) AS bytes
FROM soul s
JOIN hash_groups hg ON s.content_hash = hg.content_hash
WHERE s.valid_until IS NULL
  AND s.id != hg.canonical_id
LIMIT 20;  -- sample; remove LIMIT for full list

-- Execute (after Ben confirms):
BEGIN TRANSACTION;
  WITH hash_groups AS ( /* same CTE as above */ ),
       cluster_stats AS (
         -- Per-cluster aggregates for the temporal-preservation coalesce.
         -- Note: updated_at is NOT aggregated — the survivor keeps its own
         -- updated_at so downstream differential-sync doesn't treat the row
         -- as "freshly changed" and re-pull/re-embed the entire cluster
         -- of survivors. (Ben directive 2026-04-18 — catches self-defeating
         -- MAX(updated_at) design that would recreate the bloat pattern.)
         SELECT content_hash,
                MIN(created_at)   AS min_created_at,
                MIN(as_of_date)   AS min_as_of,
                MIN(created_date) AS min_created_date
         FROM soul WHERE valid_until IS NULL
         GROUP BY content_hash HAVING COUNT(*) > 1
       )

  -- STEP 1: coalesce the survivor's timestamps to cluster-min BEFORE marking others superseded
  --        (temporal-preservation invariant — vector/temporal search must still see earliest appearance)
  --        updated_at intentionally NOT set — see cluster_stats comment above.
  UPDATE soul
  SET created_at   = (SELECT min_created_at   FROM cluster_stats WHERE content_hash = soul.content_hash),
      as_of_date   = (SELECT min_as_of        FROM cluster_stats WHERE content_hash = soul.content_hash),
      created_date = (SELECT min_created_date FROM cluster_stats WHERE content_hash = soul.content_hash),
      -- preserve embedding if survivor lacks one but a sibling has one
      embedding_vector = COALESCE(
        soul.embedding_vector,
        (SELECT s2.embedding_vector FROM soul s2
         WHERE s2.content_hash = soul.content_hash AND s2.embedding_vector IS NOT NULL
         LIMIT 1)
      ),
      embedding_model = COALESCE(
        soul.embedding_model,
        (SELECT s2.embedding_model FROM soul s2
         WHERE s2.content_hash = soul.content_hash AND s2.embedding_vector IS NOT NULL
         LIMIT 1)
      ),
      embedded_at = COALESCE(
        soul.embedded_at,
        (SELECT s2.embedded_at FROM soul s2
         WHERE s2.content_hash = soul.content_hash AND s2.embedding_vector IS NOT NULL
         LIMIT 1)
      )
  WHERE id IN (SELECT canonical_id FROM hash_groups);

  -- STEP 2: now mark the non-survivor cluster members superseded against the survivor
  UPDATE soul
  SET valid_until = unixepoch(),
      superseded_by = (SELECT canonical_id FROM hash_groups hg WHERE hg.content_hash = soul.content_hash)
  WHERE id IN (
    SELECT s.id FROM soul s
    JOIN hash_groups hg ON s.content_hash = hg.content_hash
    WHERE s.valid_until IS NULL AND s.id != hg.canonical_id
    LIMIT 500
  );

  -- STEP 3: FK + coalesce integrity probes
  SELECT 'dangling_supersede' AS chk, COUNT(*) FROM soul
    WHERE superseded_by IS NOT NULL AND superseded_by NOT IN (SELECT id FROM soul);
  SELECT 'survivor_timestamp_too_new' AS chk, COUNT(*) FROM soul s
    JOIN (SELECT content_hash, MIN(created_at) AS min_ca FROM soul GROUP BY content_hash) agg
    ON s.content_hash = agg.content_hash
    WHERE s.valid_until IS NULL AND s.created_at > agg.min_ca;  -- MUST be 0 after coalesce
COMMIT;
```

**Before COMMIT, dump pre-coalesce timestamps to $AUDIT_DIR/pre-coalesce-timestamps.json** so rollback can restore them if the coalesce itself goes wrong:

```bash
turso db shell "$TURSO_URL?authToken=$TOK" <<'SQL' > "$AUDIT_DIR/pre-coalesce-timestamps.json" 2>&1
SELECT json_group_array(json_object(
  'id', id, 'created_at', created_at, 'as_of_date', as_of_date,
  'created_date', created_date, 'updated_at', updated_at,
  'embedding_vector', embedding_vector, 'embedding_model', embedding_model,
  'embedded_at', embedded_at
)) FROM soul
WHERE id IN (
  SELECT canonical_id FROM (
    WITH hash_groups AS ( /* canonical-selection CTE */ )
    SELECT DISTINCT canonical_id FROM hash_groups
  )
);
SQL
```

Rollback recipe (if post-verify finds a wrong canonical got picked): replay the pre-coalesce-timestamps.json values back into the rows via per-row UPDATE. Store the recipe as `$AUDIT_DIR/RESTORE-TIMESTAMPS.sh`.

Loop in 500-row batches until `SELECT COUNT(*) FROM soul WHERE valid_until IS NULL GROUP BY content_hash HAVING COUNT(*) > 1` returns zero groups.

### SQL for orphan-active rows

```sql
-- Active rows not in *_current → if they have a same-(agent_id, key) row that IS in
-- *_current, mark them superseded against it. If nothing matches, leave alone (may be
-- legitimate pre-pointer history that just never got its pointer written).
BEGIN TRANSACTION;
  UPDATE soul
  SET valid_until = unixepoch(),
      superseded_by = (
        SELECT sc.soul_id FROM soul_current sc
        WHERE sc.agent_id = soul.agent_id AND sc.key = soul.key
        LIMIT 1
      )
  WHERE valid_until IS NULL
    AND id NOT IN (SELECT soul_id FROM soul_current)
    AND EXISTS (
      SELECT 1 FROM soul_current sc
      WHERE sc.agent_id = soul.agent_id AND sc.key = soul.key
    )
  -- batch cap
  AND id IN (
    SELECT id FROM soul
    WHERE valid_until IS NULL AND id NOT IN (SELECT soul_id FROM soul_current)
    LIMIT 500
  );
COMMIT;
```

### Rollback (v1 only — trivial because no DELETE happened)

If the mark-superseded pass produced wrong results, roll back with:

```sql
-- Restore to pre-v1 state for rows marked in this run
UPDATE soul
SET valid_until = NULL, superseded_by = NULL
WHERE valid_until >= <run_start_unixepoch>
  AND valid_until <= <run_end_unixepoch>
  AND superseded_by IS NOT NULL;
```

Record `<run_start_unixepoch>` and `<run_end_unixepoch>` in `$AUDIT_DIR/v1-timespan.txt` at run time so rollback is deterministic. This is *in addition to* the full-table backup from Step 3 — v1 rollback is cheap; v2 rollback needs the dump.

---

## Step 4c — Regenerable-key sweep (most-recent-only per agent/key)

**Applies to keys in the regenerable-key allowlist** (defined in sync.mjs `REGENERABLE_KEYS` constant, currently just `AGENT_CONTEXT.md`). These keys are rebuilt from upstream source tables on every session start/sync, so their history rows carry zero information — the source data IS the history, and lives elsewhere. Ben directive 2026-04-18: "AGENT_CONTEXT.md per agent/user most recent only, since all other can be found in history".

### Detection (per-key, per-agent)

```sql
-- How many rows exist per (agent_id, key) for regenerable keys?
SELECT agent_id, key, COUNT(*) AS total_rows,
       SUM(CASE WHEN valid_until IS NULL THEN 1 ELSE 0 END) AS active_rows,
       SUM(CASE WHEN valid_until IS NOT NULL THEN 1 ELSE 0 END) AS history_rows
FROM soul
WHERE key IN ('AGENT_CONTEXT.md')  -- extend allowlist as needed
GROUP BY agent_id, key
ORDER BY total_rows DESC;
```

Goal: every (agent_id, key) pair in this result should have `total_rows = active_rows = 1` and `history_rows = 0`. Anything else is debloatable with zero risk of data loss (because the key is regenerable).

### Execute (requires partial unique index to be in place first)

```sql
BEGIN TRANSACTION;

  -- 1. Pick the newest row per (agent_id, key) as the keeper
  --    "Newest" by created_at (OR updated_at if created_at is uniform). For
  --    regenerable keys, temporal-preservation invariant is INVERTED — we want
  --    the most-recent content (= most-recent regeneration of the cache), not
  --    the earliest occurrence, because the cache value is a snapshot of the
  --    upstream source state at regen time.
  WITH keepers AS (
    SELECT id FROM soul s
    WHERE key IN ('AGENT_CONTEXT.md')
      AND id = (
        SELECT id FROM soul s2
        WHERE s2.agent_id = s.agent_id AND s2.key = s.key
          AND s2.valid_until IS NULL
        ORDER BY s2.updated_at DESC, s2.created_at DESC, s2.id DESC
        LIMIT 1
      )
  )

  -- 2. Redirect *_current pointer to the keeper (if it was pointing elsewhere)
  UPDATE soul_current
  SET soul_id = (
    SELECT k.id FROM keepers k
    JOIN soul s ON s.id = k.id
    WHERE s.agent_id = soul_current.agent_id AND s.key = soul_current.key
    LIMIT 1
  )
  WHERE key IN ('AGENT_CONTEXT.md');

  -- 3. DELETE every row for these keys that isn't the keeper
  --    (both superseded AND any orphan-active non-keeper rows)
  DELETE FROM soul
  WHERE key IN ('AGENT_CONTEXT.md')
    AND id NOT IN (SELECT id FROM keepers);

  -- 4. FK probes
  SELECT 'orphan_pointers' AS chk, COUNT(*) FROM soul_current
    WHERE soul_id NOT IN (SELECT id FROM soul);
  SELECT 'regenerable_row_count' AS chk, COUNT(*) FROM soul
    WHERE key IN ('AGENT_CONTEXT.md');  -- should equal distinct (agent_id, key) pairs, e.g. 10 if 10 agents

COMMIT;
```

### Why this is safe to DELETE (not just mark-superseded)

Unlike the general debloat path where v1 mark-superseded is required before v2 DELETE (so rollback is cheap), regenerable keys can jump straight to DELETE because:

1. **Source-of-truth is elsewhere.** AGENT_CONTEXT.md is a denormalized read of Turso facts/policies/memory/soul tables. The upstream data is authoritative; the file is a cache.
2. **Rollback via regeneration, not restore.** If DELETE was wrong, just run `agent-context.mjs` on any machine — it produces the canonical current file from source tables in seconds. No .sql.gz replay needed for this specific pattern.
3. **Temporal-preservation invariant doesn't apply.** For source-data keys (soul files like AGENTS.md, memory files, skills), MIN(created_at) matters because first-observation is load-bearing signal. For regenerable cache keys, every rebuild produces a snapshot at rebuild time; earlier snapshots are just earlier cache states, not earlier observations of any real signal.

### Prerequisite — writer must match

**Before running this sweep, the writer in `sync.mjs` must be updated** to treat regenerable keys differently (see Turso todo #3417):

```js
// In sync.mjs, inside supersedeSoul (or a new writeRegenerable fn):
const REGENERABLE_KEYS = new Set(['AGENT_CONTEXT.md']);

if (REGENERABLE_KEYS.has(key)) {
  // UPSERT in place — no supersession chain
  const result = await db(
    `UPDATE soul SET content=?, content_hash=?, updated_at=unixepoch()
     WHERE agent_id=? AND key=? AND valid_until IS NULL`,
    [content, localHash, agentId, key]
  );
  if (result.rowsAffected === 0) {
    // No existing row — INSERT
    await db(
      `INSERT INTO soul (agent_id, key, content, content_hash, created_date,
                         updated_at, as_of_date, valid_until)
       VALUES (?, ?, ?, ?, ?, unixepoch(), unixepoch(), NULL)`,
      [agentId, key, content, localHash, new Date().toISOString().slice(0, 10)]
    );
  }
  return 'upserted-regenerable';
}
// ... existing supersedeSoul logic for non-regenerable keys
```

If this writer change isn't deployed before the sweep runs, the next sync will re-bloat the key (though more slowly, because the server-side hash-check at sync.mjs:215 at least catches NO-OP writes once there's a single active row to compare against).

### Live example — what this would free on the current DB

From the 2026-04-18 audit:
- 290 dupes for `(Claude, AGENT_CONTEXT.md)` → 1 keeper, 289 DELETED
- 14 `(q, ...)` → 1 keeper, 13 DELETED
- 11 `(main, ...)` → 1 keeper, 10 DELETED
- 9 `(moneypenny, ...)` → 1 keeper, 8 DELETED
- ... etc across 10+ agents
- **Total: ~365 rows reclaimed, ~10 rows remaining (one per agent) — ~97% reduction for this key alone**

---

### When to progress v1 → v2 (actual DELETE)

Only after:
- v1 mark-superseded completed on the table
- Post-verify green (downstream sync paths still pass)
- At least 24h wall-clock has passed with no downstream complaints
- `knowledge-search` results unchanged or improved
- Ben explicitly confirms in-turn that v1 results look right

Then v2 = Step 4 chain-collapse runs normally on the now-superseded rows.

**If any FK probe returns > 0: ROLLBACK immediately** (don't COMMIT), log the offending row IDs to `$AUDIT_DIR/fk-orphans.log`, and stop. Ben reviews the specific rows before continuing. The transaction boundary guarantees the bad state never persists.

**Progress tracking:** after every 10 batches, append a line to `$AUDIT_DIR/progress.log`: `batch_N: victims_remaining=X, bytes_freed_so_far=Y`. Lets Ben see progress during long runs without attaching a new shell.

---

## Step 5 — Verify

Re-run Step 1's audit. Compare before/after.

```
📊 /debloat verify — skills table
─────────────────────────────────
BEFORE: total=48,123  active=666  pointer_orphans=0  chain_dupes=47,457
AFTER:  total=666     active=666  pointer_orphans=0  chain_dupes=0
Ratio:  72.3x → 1.0x ✓
Bytes freed: ~180 MB (estimated from SUM(LENGTH(content)))
Backup at:   ~/clawd/data/debloat/2026-04-18-1db64396/skills.sql.gz
Restore via: ~/clawd/data/debloat/2026-04-18-1db64396/RESTORE.sh
─────────────────────────────────
```

**Smoke-test downstream consumers:**
- `claude-sync pull` → no `NOT NULL constraint` crashes
- `knowledge-search "test query" --tables skills` → returns results, same-or-faster
- `bigmac-skills pull` → diff against a fresh pull from a peer machine (optional, if available)

**If any downstream breaks:** restore is one command:
```bash
bash ~/clawd/data/debloat/$(date +%Y-%m-%d)-*/RESTORE.sh
```

---

## Step 6 — Report + re-enable disabled sync paths

Post captains-log entry:

```bash
captains-log add \
  --topic="turso debloat - skills" \
  --type=milestone \
  --summary="/debloat skills: 48,123 → 666 rows (72.3x → 1.0x). 47,457 identical-content middle-duplicates deleted, superseded_by chains rewired, zero FK orphans at verify. Backup at $AUDIT_DIR/skills.sql.gz (180MB gunzipped). Restore recipe at $AUDIT_DIR/RESTORE.sh. Downstream smoke-tests green." \
  --turso="skills" \
  --files="$AUDIT_DIR/audit.out,$AUDIT_DIR/skills.sql.gz,$AUDIT_DIR/RESTORE.sh" \
  --tags="debloat,skills,turso,fk-safe,reversible"
```

**Re-enable sync paths** disabled during the bloat era: `~/clawd/scripts/sync.mjs` has two `/* DISABLED */` blocks (soul lines 278-310; memory lines 321-470) tagged with todo #3409. After debloat verifies clean for all three tables, remove both block comments (keep the defensive hash-check pattern inside the memory-append path — see related skill `/sync-tighten`). Close todo #3409.

---

## Edge cases

- **Row is both pointer-target AND chain-middle-dupe.** Redirect pointer first (Step 4 UPDATE 1), rewire predecessor second (UPDATE 2), delete third. All three in same transaction — never split across batches.
- **Chain with >2 consecutive identical hashes** (A → B → C → D, all same hash). One pass collapses to A → D by deleting B and C in same batch. If the loop doesn't converge in 3 passes, something's wrong — stop, read `$AUDIT_DIR/progress.log`, investigate.
- **Pointer table has duplicate rows** (`(agent_id, key)` appearing twice). Not a debloat target — separate schema-integrity bug. Log to `$AUDIT_DIR/schema-anomalies.log` and skip that key.
- **`content_hash` IS NULL on some rows.** Treat NULL as its own bucket — do NOT collapse NULL-hash against valid-hash. The SQL `v.content_hash = p.content_hash` where either side is NULL evaluates to NULL (falsy) — safe by default, but verify the query plan doesn't coerce.
- **Cross-table FK from outside the known set.** Before debloating a table, check `PRAGMA foreign_key_list(<table>)` and scan every other table for FK references. As of 2026-04-18, the three targets (`soul`, `memory`, `skills`) have no known outside-table FKs. Re-verify if new tables are added.
- **`turso db shell .dump` is slow** on memory (1.3M rows → 5-10 min dump). Run in a background shell (`run_in_background:true`), wait for completion before Step 4.
- **Concurrent peer sync mid-debloat.** A peer pushes a new row while /debloat runs. New row is outside our snapshot, safe. But if peer's push creates a chain-dupe DURING our run, we miss it this pass. Run `/debloat` again after the next sync burst to catch the tail.
- **Power loss / network drop mid-batch.** Each batch is its own `BEGIN … COMMIT`. A drop rolls back the uncommitted batch — no partial-write corruption possible. Re-run `/debloat <table> --execute` and it picks up where it left off (idempotent).

---

## Anti-patterns

- **DON'T run a single giant transaction.** Turso serializes writes; a 47K-row transaction holds a write lock and stalls every agent's sync for its full duration.
- **DON'T skip the backup.** First runs of this skill need a restore path. `.dump` is cheap (one-time per debloat); restore is priceless.
- **DON'T delete rows with NULL `content_hash`.** Treat NULL as separate bucket — never equal to anything, including another NULL.
- **DON'T use VACUUM.** Acquires exclusive DB lock, blocks every reader. SQLite reclaims free-list pages gradually on subsequent writes after DELETE — no manual VACUUM needed.
- **DON'T re-enable `sync.mjs` disable blocks before post-verify is green.** FK orphans + re-enabled sync = new crash class, harder to diagnose than the original.
- **DON'T cascade debloat across tables without per-table confirmation.** Each table has its own FK graph, its own edge cases. `/debloat skills` → verify → `/debloat soul` → verify → `/debloat memory`. Three separate confirmations, three separate backups.
- **DON'T bytes-equal short-circuit.** If comparing local content to Turso content, use `hash == hash`, never `bytes == bytes`. Same-length different-content edits (line reorder, char transposition) produce identical byte counts but different hashes.

---

## Supersession of prior rule

`feedback_never_vacuum_or_delete_turso.md` is SUPERSEDED by this skill's existence.

- **Prior rule (2026-04-17):** NEVER VACUUM or delete Turso rows; work around bloat with partial indexes only.
- **New rule (2026-04-18):** VACUUM remains banned (full-DB exclusive lock, risks blocking every agent). DELETE is permitted **only via `/debloat` skill**, which requires: (1) full-table `.sql.gz` backup with `gunzip -t` + row-count verify, (2) dry-run output reviewed by Ben, (3) per-batch FK integrity probe with ROLLBACK on any orphan, (4) post-verify against downstream sync paths, (5) restore recipe saved alongside backup. Unsupervised DELETE from any other code path is still banned.

The old rule was correct for its era (bloat-containment without a cleanup path); the new rule is correct now that the cleanup path exists and is reversible.

---

## Related

- `/VIOLATION` + `/SELF-REVIEW` — running `--execute` without prior Ben confirmation is a genuine safety hard stop; self-report if skipped.
- `/exit-protocol` — checks audit output and flags bloated tables in the daily log so the next session sees them.
- `/captains-log` — every debloat run posts one entry with before/after counts + backup path.
- `~/clawd/scripts/sync.mjs` — disabled blocks for soul (lines 278-310) and memory (lines 321-470) sync paths, tagged with todo #3409. Re-enable after debloat verify clears all three tables.
- Turso table `push_lock` — memory sync's session-level mutex. Unrelated to debloat; lives inside the disabled path currently.
- Turso todo #3394 — skills table bloat (72.1x), canonical tracking todo for first `/debloat` run.
- Turso todo #3409 — sync.mjs re-enable after debloat, close once all three tables post-verified.
