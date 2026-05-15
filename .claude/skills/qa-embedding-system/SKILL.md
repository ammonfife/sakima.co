---
name: qa-embedding-system
description: End-to-end QA of the BigMac embedding + semantic-search stack. Checks (1) embed-watcher + embed-sessions daemon health, (2) LM Studio model load state (correct model loaded, no fallback to in-process native-llama-cpp), (3) data integrity across all source tables (active flag, valid_until, superseded_by consistency), (4) vector-space consistency (all 8 tables + embeddings table on same model label), (5) embedding coverage percentages, (6) knowledge-search functional sanity (known queries return expected results, both default and --multi paths), (7) orphan embeddings (source row deleted but embeddings row remains), (8) term_signals + session_files backfill freshness, (9) supersession leakage (search returns superseded content). Runs read-only — reports issues, never mutates. Use when onboarding a new agent, after big schema changes, or on a weekly cadence to catch drift.
user-invocable: true
---

# /qa-embedding-system

Comprehensive health-check of the full embedding pipeline — from raw Turso rows, through embed-watcher's inline + chunked writes, to the `embeddings` table with native `vector_distance_cos`, to knowledge-search's fusion layer. Designed to catch the exact class of drift we already hit once (MODEL_NAME label drift, superseded-row leakage, 3s-timeout-triggered native fallback, ambiguous model name resolution, stale per-table config).

## Quick-run gap finder

For a fast data-gap audit with optional auto-fix, use the dedicated Python QA script:

```bash
# Report gaps only
~/clawd/venv/bin/python ~/clawd/scripts/embedding-pipeline/qa-embedding-gaps.py

# Report + show sample rows for each gap
~/clawd/venv/bin/python ~/clawd/scripts/embedding-pipeline/qa-embedding-gaps.py --verbose

# Report + auto-restart dead workers
~/clawd/venv/bin/python ~/clawd/scripts/embedding-pipeline/qa-embedding-gaps.py --fix
```

Checks: term_signals coverage (emb_v, temporal_vector, day_counts, emb_v_chunk_avg, active), source-table embedding_model coverage, embeddings table chunk gaps (>8KB source rows without chunks), boilerplate detection readiness (HNSW index + session_spread), worker liveness, LM Studio health.

## Pipeline scripts (all at ~/clawd/scripts/embedding-pipeline/)

| Script | Purpose | Turso method |
|---|---|---|
| `embed-watcher-short-loop.sh` | Bash loop running `embed-watcher` per-pass (replaces zombie-prone `--daemon` mode) | Node HTTP via embed-watcher |
| `embed-term-signals.py` | Qwen3-Embedding-8B on every term → `emb_v` column | Python HTTP batched |
| `embed-sessions.mjs` | Chunk + embed all Claude/agent session transcripts | Node HTTP |
| `backfill-temporal-vectors.py` | TimesFM 2.5 on day_counts → `temporal_vector` column | Python curl subprocess |
| `backfill-temporal-supervisor.sh` | Bash supervisor: watches log mtime, auto-restarts on stall >600s | Wrapper |
| `rebuild-day-counts.py` | Rebuild day_counts from embeddings table (one-time fix) | Python HTTP batched |
| `qa-embedding-gaps.py` | QA: find data gaps + optionally restart dead workers | Python curl |

### Known failure patterns (discovered 2026-04-16/17)

1. **embed-watcher `--daemon` mode zombies** under LM Studio Parallel:4 contention. Fix: short-loop with fresh process per pass.
2. **Python `urllib` hangs forever** on stalled Turso TCP reads. Fix: use `curl` subprocess with `-m` timeout.
3. **LIMIT/OFFSET pagination is O(N×pages)** on large tables. Fix: keyset pagination (`WHERE term > 'last' ORDER BY term LIMIT N`).
4. **Phase 1 COUNT(*) on un-indexed NULL predicates** takes 60s+. Fix: skip the count, defer to row count during processing.
5. **Phase 8 writes fail 100%** when HNSW index build is concurrent. Fix: don't overlap index builds with batch writes.
6. **embed-watcher re-embeds same rows** when Turso UPDATE (to mark `embedding_model`) times out but LM Studio embedding succeeded. Fix: increase db() timeout to 60s with 3× retry.

## When to run

- **After any embed-watcher or knowledge-search change** — smoke test before committing.
- **Weekly cadence** — catches slow drift (new bigmac-embed legacy resurrecting, label pollution from a new embedding script someone writes).
- **After schema migrations** — e.g. if `soul` gets a new supersession column.
- **When onboarding a new agent** — quick way to verify the whole stack is functional for them.
- **After a LM Studio update or model reload** — verify the expected embedding model is still the one serving requests.

## Hard rules (NEVER violate)

1. **Read-only.** This skill MUST NOT mutate Turso, files, or process state. It's a diagnostic. If something is wrong, the output tells you what skill to run to fix it (e.g. `/disable-openclaw`, or a manual query).
2. **Timeout on every Turso call** — soul is bloated, some COUNT queries take >15s. Each section has its own timeout budget so one slow query doesn't block the rest.
3. **Skip rather than block** on any individual check failure. Print `⚠️ skipped: <reason>` and continue. Total runtime target <90s.
4. **Never output vectors.** Even in verbose mode — just dims + first 3 floats as a signature for identity-checks.
5. **Classify severity**: ✅ ok, ⚠️ warning (doesn't block search, but should fix), ❌ critical (search returns wrong results or pipeline is stalled).
6. **Record baseline** — write a compact timestamped report to `~/.claude/logs/qa-embedding-YYYY-MM-DD.md`. Next run can diff against it.

## Output format

All sections print section-header + status + inline details. End with a compact summary table. Exit 0 if no ❌ (warnings are OK), exit 1 if any ❌.

## Step 1 — Daemon health

```bash
echo "## 1. Daemon health"

# embed-watcher (the canonical embedding daemon)
EW_PIDS=$(pgrep -f "node /Users/benfife/bin/embed-watcher" 2>/dev/null)
if [ -n "$EW_PIDS" ]; then
  RSS_GB=$(ps -p $(echo $EW_PIDS | awk '{print $1}') -o rss= 2>/dev/null | awk '{printf "%.2f", $1/1024/1024}')
  if awk "BEGIN {exit !($RSS_GB > 5)}" 2>/dev/null; then
    echo "  ❌ embed-watcher: RSS=${RSS_GB} GB — native-llama-cpp fallback fired (should be <0.5 GB if using LM Studio HTTP)"
  else
    echo "  ✅ embed-watcher: PID $(echo $EW_PIDS | tr '\n' ' ') RSS=${RSS_GB} GB (LM Studio HTTP path)"
  fi
else
  echo "  ⚠️  embed-watcher: not running (check ~/Library/LaunchAgents/com.bigmac.embed-watcher.plist and crontab)"
fi

# embed-sessions (session backfill pipeline — may not always be running)
ES_PIDS=$(pgrep -f "node /private/tmp/embed-sessions.mjs" 2>/dev/null)
if [ -n "$ES_PIDS" ]; then
  RSS_GB=$(ps -p $(echo $ES_PIDS | awk '{print $1}') -o rss= 2>/dev/null | awk '{printf "%.2f", $1/1024/1024}')
  echo "  ℹ️  embed-sessions backfill: PID $(echo $ES_PIDS | tr '\n' ' ') RSS=${RSS_GB} GB"
else
  echo "  ℹ️  embed-sessions: not running (normal — only runs during session backfill)"
fi

# Check for stray processes that can re-introduce the old label
ORPHANS=$(pgrep -f "bigmac-embed$" 2>/dev/null | head -5)
if [ -n "$ORPHANS" ]; then
  echo "  ⚠️  bigmac-embed running: $ORPHANS — should be only via nightly cron (30 4 * * *)"
fi
```

## Step 2 — LM Studio model state

```bash
echo
echo "## 2. LM Studio"

if ! lms server status 2>&1 | grep -q "running"; then
  echo "  ❌ LM Studio server not running — embed-watcher will fall back to 8GB native-llama-cpp per process"
else
  # Probe the embedding endpoint
  RESP=$(curl -s -m 30 http://localhost:1234/v1/embeddings \
    -H 'Content-Type: application/json' \
    -d '{"input":"qa-probe","model":"text-embedding-hf_qwen_qwen3-embedding-8b"}' 2>&1)
  DIM=$(echo "$RESP" | python3 -c "import json,sys;print(len(json.load(sys.stdin)['data'][0]['embedding']))" 2>/dev/null)
  if [ "$DIM" = "4096" ]; then
    echo "  ✅ LM Studio embedding endpoint: Qwen3-Embedding-8B serving 4096-dim"
  else
    echo "  ❌ LM Studio embedding endpoint returned unexpected dim: ${DIM:-error}"
  fi

  # Check for stray LLMs that aren't needed (openclaw uses these; if openclaw is off, they waste RAM)
  STRAY=$(lms ps 2>&1 | grep -E "qwen3.5-9b|qwen2.5-coder-7b" | head -3)
  if [ -n "$STRAY" ]; then
    if pgrep -f openclaw-gateway >/dev/null 2>&1; then
      echo "  ℹ️  openclaw-only LLMs loaded (expected — gateway is up):"
    else
      echo "  ⚠️  openclaw-only LLMs loaded but gateway is DOWN (waste of RAM):"
    fi
    echo "$STRAY" | sed 's/^/      /'
  fi
fi
```

## Step 3 — Data integrity (delegate to bigmac-embed --audit)

```bash
echo
echo "## 3. Data integrity (bigmac-embed --audit)"
timeout 45 bigmac-embed --audit 2>&1 | sed 's/^/  /'
```

## Step 4 — Vector-space consistency (MODEL_NAME uniformity)

```bash
echo
echo "## 4. Vector-space consistency"

python3 - <<'PY'
import json, urllib.request, subprocess
URL = "https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline"
TOKEN = subprocess.check_output(['security','find-generic-password','-a','bigmac','-s','turso-bigmac-token','-w']).decode().strip()

def q(sql):
    body = {"requests":[{"type":"execute","stmt":{"sql": sql, "args":[]}}]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        return d['results'][0]['response']['result']['rows']
    except Exception as e:
        return None

models = {}
for tbl in ['facts','assumptions','opinions','policies','memory','soul','skills','todos','secrets','violations']:
    r = q(f"SELECT embedding_model, COUNT(*) FROM {tbl} WHERE embedding_model IS NOT NULL GROUP BY embedding_model")
    if r is None:
        print(f"  ⚠️  {tbl}: query failed/timeout")
        continue
    for row in r:
        m = row[0].get('value','?')
        n = int(row[1]['value'])
        models.setdefault(m, {})[tbl] = n

r = q("SELECT model, COUNT(*) FROM embeddings GROUP BY model")
if r:
    for row in r:
        m = row[0].get('value','?')
        n = int(row[1]['value'])
        models.setdefault(m, {})['embeddings'] = n

if len(models) == 1:
    total = sum(sum(v.values()) for v in models.values())
    print(f"  ✅ {total:,} rows across all tables on single model: {list(models.keys())[0]!r}")
elif len(models) == 0:
    print("  ⚠️  no embedded rows found")
else:
    print(f"  ❌ VECTOR SPACE SPLIT: {len(models)} distinct model labels in use")
    for m, tbls in models.items():
        print(f"    {m!r}: {tbls}")
    print("    Cross-table cosine is NOT valid until this is rectified.")
PY
```

## Step 5 — Coverage per table

```bash
echo
echo "## 5. Embedding coverage"

python3 - <<'PY'
import json, urllib.request, subprocess
URL = "https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline"
TOKEN = subprocess.check_output(['security','find-generic-password','-a','bigmac','-s','turso-bigmac-token','-w']).decode().strip()

def q(sql, timeout=15):
    body = {"requests":[{"type":"execute","stmt":{"sql": sql, "args":[]}}]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
        return d['results'][0]['response']['result']['rows']
    except Exception as e:
        return None

TABLES = {
    'facts': '(active=1 OR active IS NULL)',
    'assumptions': '(active=1 OR active IS NULL)',
    'opinions': '(active=1 OR active IS NULL)',
    'policies': 'active=1',
    'memory': 'inactive_date IS NULL',
    'soul': '(valid_until IS NULL OR valid_until > unixepoch())',
    'skills': "valid_until IS NULL AND file_path='SKILL.md'",
    'todos': "(status != 'deleted' OR status IS NULL)",
    'secrets': "(status IS NULL OR status != 'revoked')",
    'violations': '1=1',
}

for tbl, filt in TABLES.items():
    r = q(f"SELECT SUM(CASE WHEN embedding_model IS NOT NULL THEN 1 ELSE 0 END) emb, COUNT(*) tot FROM {tbl} WHERE {filt}", timeout=25)
    if r is None:
        print(f"  ⚠️  {tbl:12}: timeout")
        continue
    emb = int(r[0][0].get('value',0) or 0)
    tot = int(r[0][1]['value'])
    pct = (emb/tot*100) if tot else 0
    marker = '✅' if pct >= 95 else '⚠️ ' if pct >= 50 else '❌'
    print(f"  {marker} {tbl:12}: {emb:>5}/{tot:<5} = {pct:5.1f}%")
PY
```

## Step 6 — embeddings table health

```bash
echo
echo "## 6. embeddings table"

python3 - <<'PY'
import json, urllib.request, subprocess
URL = "https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline"
TOKEN = subprocess.check_output(['security','find-generic-password','-a','bigmac','-s','turso-bigmac-token','-w']).decode().strip()
def q(sql):
    body = {"requests":[{"type":"execute","stmt":{"sql": sql, "args":[]}}]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
    try: return json.loads(urllib.request.urlopen(req, timeout=20).read().decode())['results'][0]['response']['result']['rows']
    except: return None

# Per-source-table counts
r = q("SELECT source_table, COUNT(*) FROM embeddings GROUP BY source_table ORDER BY 2 DESC")
if r:
    print('  chunks per source_table:')
    for row in r:
        print(f'    {row[0][\"value\"]:15} {int(row[1][\"value\"]):>6}')

# Check emb_v coverage (native vector column vs JSON)
r = q("SELECT SUM(CASE WHEN emb_v IS NOT NULL THEN 1 ELSE 0 END) native, SUM(CASE WHEN vector IS NOT NULL THEN 1 ELSE 0 END) json, COUNT(*) tot FROM embeddings")
if r:
    native, jsn, tot = int(r[0][0]['value']), int(r[0][1]['value']), int(r[0][2]['value'])
    if native == tot: print(f'  ✅ native emb_v F32_BLOB: {native:,}/{tot:,} (100%)')
    elif native < tot: print(f'  ⚠️  native emb_v: {native:,}/{tot:,} ({native/tot*100:.1f}%) — {tot-native} rows have JSON only (backfill needed)')
PY
```

## Step 7 — knowledge-search functional sanity

```bash
echo
echo "## 7. knowledge-search sanity"

# Known-good queries that should return meaningful results
echo "  Probe 1: default search"
timeout 30 knowledge-search "embed-watcher pipeline" --limit 3 --json 2>/dev/null | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
    n = len(d)
    if n >= 1:
        print(f'    ✅ returned {n} results')
        for r in d[:3]:
            print(f'      {r[\"table\"]}  score={r[\"score\"]:.3f}  id={r[\"id\"]}')
    else:
        print(f'    ❌ 0 results — search broken or index empty')
except Exception as e:
    print(f'    ❌ parse error: {e}')
" 2>&1 || echo "    ❌ timeout/error"

echo "  Probe 2: --multi (n-gram fusion + temporal)"
timeout 45 knowledge-search "openclaw gateway disable" --multi --limit 3 --json 2>/dev/null | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
    n = len(d)
    print(f'    ✅ returned {n} results' if n >= 1 else f'    ❌ 0 results')
except: print('    ❌ --multi path broken')
" 2>&1 || echo "    ❌ timeout (--multi >45s indicates temporal-boost or chunk query stuck)"

# Self-referential sanity: this skill's description should be findable if skills are indexed
echo "  Probe 3: skills index coverage"
timeout 20 knowledge-search "embedding system QA health check" --tables skills --limit 3 --json 2>/dev/null | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
    n = len(d)
    print(f'    ✅ skills index has {n} hits for probe' if n >= 1 else '    ⚠️  skills index empty or not matched')
except: print('    ⚠️  skills path failed')
" 2>&1 || echo "    ⚠️  skills probe timeout"
```

## Step 8 — Supersession leakage (critical for search correctness)

```bash
echo
echo "## 8. Supersession leakage check"

python3 - <<'PY'
import json, urllib.request, subprocess
URL = "https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline"
TOKEN = subprocess.check_output(['security','find-generic-password','-a','bigmac','-s','turso-bigmac-token','-w']).decode().strip()
def q(sql):
    body = {"requests":[{"type":"execute","stmt":{"sql": sql, "args":[]}}]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
    try: return json.loads(urllib.request.urlopen(req, timeout=20).read().decode())['results'][0]['response']['result']['rows']
    except: return None

# Rows that are superseded but still have embedding_vector populated
# → will appear in semantic search results despite being "dead"
for tbl in ['facts','policies','skills','memory','soul']:
    r = q(f"SELECT COUNT(*) FROM {tbl} WHERE superseded_by IS NOT NULL AND embedding_vector IS NOT NULL")
    if r:
        n = int(r[0][0]['value'])
        marker = '✅' if n == 0 else '⚠️ '
        print(f'  {marker} {tbl:12}: {n} superseded rows still embedded (will surface in search)')
PY
```

## Step 9 — term_signals + session_files freshness

```bash
echo
echo "## 9. Temporal index freshness"

python3 - <<'PY'
import json, urllib.request, subprocess, datetime
URL = "https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline"
TOKEN = subprocess.check_output(['security','find-generic-password','-a','bigmac','-s','turso-bigmac-token','-w']).decode().strip()
def q(sql):
    body = {"requests":[{"type":"execute","stmt":{"sql": sql, "args":[]}}]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
        headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
    try: return json.loads(urllib.request.urlopen(req, timeout=20).read().decode())['results'][0]['response']['result']['rows']
    except: return None

r = q("SELECT COUNT(*), MAX(last_seen) FROM term_signals")
if r:
    n = int(r[0][0]['value'])
    last = r[0][1].get('value','?')
    age_days = (datetime.date.today() - datetime.date.fromisoformat(last)).days if last and last != '?' else 999
    marker = '✅' if age_days <= 1 and n > 5000 else '⚠️ '
    print(f'  {marker} term_signals: {n:,} terms, last_seen={last} ({age_days}d old)')

r = q("SELECT COUNT(*) FROM session_files")
if r:
    n = int(r[0][0]['value'])
    marker = '✅' if n > 100000 else '⚠️ '
    print(f'  {marker} session_files: {n:,}')
PY
```

## Step 10 — Summary + baseline log

```bash
echo
echo "## Summary"

# Count each marker type from the full output stream above
# (In practice, this step re-collects the section headers. Simpler: just state totals
# by re-running the critical checks or tracking them in a variable earlier. For now,
# we emit a timestamped log that can be diffed next run.)

LOGDIR=~/.claude/logs
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/qa-embedding-$(date +%Y-%m-%d).md"
echo "(full report also saved to $LOGFILE)"
# Re-run with tee:  /qa-embedding-system 2>&1 | tee "$LOGFILE"
```

## Failure → fix mapping

| Red flag | Fix |
|---|---|
| embed-watcher RSS > 5 GB | `lms server restart && pkill -f embed-watcher && launchctl kickstart gui/$(id -u)/com.bigmac.embed-watcher` — forces HTTP path |
| LM Studio not running | `lms server start` + verify `lms ps` shows the embedding model |
| Vector space split (>1 distinct model label) | Rename rows with non-canonical label — see 2026-04-16 migration |
| Coverage <50% on a table | Run `bigmac-embed --limit 500` once; check embed-watcher logs |
| Supersession leakage >0 | Add `AND superseded_by IS NULL` to TABLE_CONFIGS filters in knowledge-search |
| --multi timeout >45s | Check temporal index size (term_signals); reduce query k or threshold |
| session_files old | Run `~/clawd/scripts/sync-session-files.mjs --all` |
| term_signals stale | Embed-watcher extracts these; trigger a fresh batch |

## What this skill does NOT do

- Does not mutate Turso state. Use other skills to repair issues.
- Does not test individual session JSONL file parsing — that's embed-sessions.mjs's job.
- Does not audit the knowledge-search code itself (only its output). Use `/lift-and-constrain knowledge_search` for code audit.
- Does not benchmark performance. Different skill.
