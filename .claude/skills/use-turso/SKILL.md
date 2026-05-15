---
name: use-turso
description: Query the BigMac Turso database via CLI shell or HTTP pipeline. Use the CLI shell with inline authToken URL for any bulk operation — no `turso auth login` required. Use HTTP pipeline only for small reads or single-row writes.
homepage: https://docs.turso.tech/sdk/cli
metadata:
  {
    "openclaw":
      {
        "emoji": "🗄️",
        "requires": { "bins": ["turso"] },
      },
  }
---

> [!IMPORTANT]
> **Cross-Platform Skill**: This skill is shared across Claude Code, OpenClaw, Gemini, and Codex. 
> Before executing, check the "Platform Blocks" below. If your current platform is missing, or if a command fails due to your unique toolset, **UPDATE THIS SKILL** by adding an `If you are [Platform]...` block detailing how your platform should execute it.

### If you are Claude (Claude Code / OpenClaw)
- Use your native `str_replace_editor` for targeted edits.
- You can spawn background tasks directly using `Bash run_in_background`.

### If you are Gemini (Antigravity / Google)
- Use your native `multi_replace_file_content` or `replace_file_content` tools.
- Background tasks should use the `run_command` tool with `WaitMsBeforeAsync` set appropriately.

### If you are Codex / Grok
- Use your respective file-editing APIs and terminal execution pipelines.


# Turso CLI & HTTP access (BigMac database)

Database: `libsql://bigmac-ammonfife.aws-us-west-2.turso.io`
Token in keychain: `turso-bigmac-token` (account `bigmac`).

## CLI shell (preferred for bulk ops)

**No `turso auth login` required.** Pass the DB token inline in the URL:

```bash
TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
DB="libsql://bigmac-ammonfife.aws-us-west-2.turso.io?authToken=$TOKEN"

# One-off query
echo "SELECT COUNT(*) FROM term_signals;" | turso db shell "$DB"

# From file
turso db shell "$DB" < script.sql

# Interactive
turso db shell "$DB"
```

The CLI uses a WebSocket connection — no 30s HTTP timeout.

**Use the CLI for:**
- Bulk INSERT / UPDATE / DELETE (>100 rows)
- JOINs across 1M+ row tables (e.g. memory, embeddings)
- Any query that takes >30s
- Interactive exploration
- **Any process that makes >1 Turso roundtrip per invocation** (see revised decision rule below)

### Multi-row / multi-statement patterns with CLI

Three patterns — use the strongest one that fits the workload.

**Pattern 1: Batched statements in one stdin stream** (simplest)

```bash
TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)
DB="libsql://bigmac-ammonfife.aws-us-west-2.turso.io?authToken=$TOKEN"

echo "
UPDATE term_signals SET emb_v = vector('[...]') WHERE term = 'foo';
UPDATE term_signals SET emb_v = vector('[...]') WHERE term = 'bar';
UPDATE term_signals SET emb_v = vector('[...]') WHERE term = 'baz';
" | turso db shell "$DB"
```

One WebSocket connection, N statements. No HTTP handshake per row. Use when you have many independent statements.

**Pattern 2: Transaction wrapper** (10-50× speedup, atomic)

```bash
echo "
BEGIN;
UPDATE term_signals SET emb_v = vector('[...]') WHERE term = 'foo';
UPDATE term_signals SET emb_v = vector('[...]') WHERE term = 'bar';
UPDATE term_signals SET emb_v = vector('[...]') WHERE term = 'baz';
COMMIT;
" | turso db shell "$DB"
```

All-or-nothing + single fsync at commit = massive speedup over N individual writes. Use for any UPDATE-heavy loop (embed-term-signals, embed-watcher trigram upserts, rebuild-day-counts).

**Pattern 3: Multi-row INSERT** (fastest when applicable)

```sql
INSERT INTO embeddings (source_table, source_id, chunk_index, chunk_text, emb_v) VALUES
  ('facts',  1, 0, '...', vector('[...]')),
  ('facts',  2, 0, '...', vector('[...]')),
  ('memory', 3, 0, '...', vector('[...]'));
```

One statement, many rows. Works for new inserts; can't batch per-row UPDATEs with different WHERE clauses this way.

### Driving the CLI from Node / Python

The CLI is just a binary that reads stdin. Pipe pre-built SQL through it from any language:

```js
// Node.js — batch N UPDATEs into one CLI invocation
import { spawnSync } from 'child_process';
const TOKEN = execSync('security find-generic-password -a bigmac -s turso-bigmac-token -w', {encoding:'utf8'}).trim();
const DB = `libsql://bigmac-ammonfife.aws-us-west-2.turso.io?authToken=${TOKEN}`;

const sql = ['BEGIN;', ...updates.map(u =>
  `UPDATE term_signals SET emb_v = vector('${JSON.stringify(u.vec)}') WHERE term = '${u.term.replace(/'/g, "''")}';`
), 'COMMIT;'].join('\n');

const r = spawnSync('turso', ['db', 'shell', DB], { input: sql, encoding: 'utf8' });
if (r.status !== 0) throw new Error(r.stderr);
```

```python
# Python — same idea
import subprocess
TOKEN = subprocess.check_output(['security','find-generic-password','-a','bigmac','-s','turso-bigmac-token','-w']).decode().strip()
DB="libsql://bigmac-ammonfife.aws-us-west-2.turso.io?authToken={TOKEN}"
sql = "BEGIN;\n" + "\n".join(updates) + "\nCOMMIT;"
subprocess.run(['turso','db','shell',DB], input=sql, text=True, check=True)
```

**String escaping**: always double single-quotes (`'` → `''`) in text values before interpolating into SQL. Consider building the SQL in a temp file + `turso db shell "$DB" < file.sql` if the command line would exceed ARG_MAX (~256KB on macOS).

### Driving Turso with cURL (programmatic HTTP writes)

For single-statement writes or small batches from shell scripts, use `curl` against the HTTPS endpoint. This is often more reliable than language-native libraries for simple tasks.

```bash
# Get a secret
TOKEN=$(secrets get turso-bigmac-token)
URL="https://bigmac-ammonfife.aws-us-west-2.turso.io"

# execute pattern (single write)
curl -X POST "$URL/v2/pipeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {
        "type": "execute",
        "stmt": {
          "sql": "INSERT INTO captains_log (topic, summary, agent) VALUES (?, ?, ?)",
          "args": [
            {"type": "text", "value": "Topic Name"},
            {"type": "text", "value": "Summary Text"},
            {"type": "text", "value": "agent-id"}
          ]
        }
      },
      { "type": "close" }
    ]
  }'
```

### Long-lived CLI sessions (for repeated multi-query workloads)

For scripts that make many queries over the lifetime of one invocation (like `knowledge-search`, which does ~18 queries per search), open ONE CLI shell at startup and pipe every query through it:

```bash
# Open CLI shell as a coprocess — stdin open for the whole script lifetime
coproc TURSO { turso db shell "$DB"; }

query() {
  echo "$1" >&${TURSO[1]}
  # Read response from ${TURSO[0]}
}

query "SELECT * FROM embeddings WHERE emb_v IS NOT NULL ORDER BY vector_distance_cos(emb_v, vector('[...]')) LIMIT 30;"
query "SELECT term, temporal_vector FROM term_signals WHERE partner_count < 15 LIMIT 5000;"
# ... 18 total queries, all through one WebSocket
```

Programmatically, Node's `child_process.spawn` + writing to stdin line-by-line does the same thing.

## HTTP pipeline (small reads, single writes, programmatic use)

```js
const TOKEN = execSync('security find-generic-password -a bigmac -s turso-bigmac-token -w', { encoding: 'utf8' }).trim();
const DB_URL = 'https://bigmac-ammonfife.aws-us-west-2.turso.io';

function toHrana(v) {
  if (v == null) return { type: 'null' };
  if (Number.isInteger(v)) return { type: 'integer', value: String(v) };
  if (typeof v === 'number') return { type: 'float', value: v };
  return { type: 'text', value: String(v) };
}

async function pipeline(requests) {
  const r = await fetch(`${DB_URL}/v2/pipeline`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ requests: [...requests, { type: 'close' }] }),
  });
  const d = await r.json();
  for (const res of d.results) if (res.type === 'error') throw new Error(res.error.message);
  return d.results;
}

// Single query
const res = await pipeline([{
  type: 'execute',
  stmt: { sql: 'SELECT * FROM term_signals WHERE term = ?', args: [toHrana('quantum mechanics')] },
}]);
const rows = res[0].response.result.rows;

// Batch (up to ~100 statements per request — stays under 30s)
await pipeline(
  topics.map(t => ({
    type: 'execute',
    stmt: { sql: 'INSERT OR IGNORE INTO term_signals (term) VALUES (?)', args: [toHrana(t)] },
  }))
);
```

**Use HTTP for:**
- Processes that make **exactly 1 Turso roundtrip per invocation**
- Ad-hoc diagnostic queries from a one-shot shell command
- Programmatic single-statement calls where you don't control the caller

**Do NOT use HTTP for:**
- Bulk writes >500 rows in a single statement
- Long UPDATEs on the memory / embeddings tables
- Anything hitting the ~30s request timeout
- **Any loop that UPDATEs / INSERTs per-row** — use CLI transactions instead (10-50× faster)
- **Any script that makes >1 query per invocation** — use a long-lived CLI session (eliminates N-1 handshakes)

### Decision rule (revised 2026-04-16)

The deciding factor is NOT "how many rows does one SQL statement touch" — it's **"how many Turso roundtrips does this process make in its lifetime"**:

| Roundtrips / invocation | Right tool |
|---|---|
| Exactly 1 | HTTP pipeline is fine |
| 2-10 | HTTP batched in one `/v2/pipeline` request (up to ~100 statements), OR one CLI command |
| 10-100 | CLI `BEGIN ... COMMIT` transaction, single invocation |
| 100+ | CLI transaction(s), each batch of 500-1000 statements |
| Long-lived process with unknown query count | Long-lived CLI shell coprocess |

### Performance observations from real workloads (2026-04-16)

**EMPIRICAL FINDING** — HTTP pipeline with BATCHED statements is FASTER than CLI for writes:

| Pattern | 20 UPDATEs timing | Notes |
|---|---|---|
| HTTP: 1 request, 20 `execute` statements in the `requests` array | **1.3s** | 1 handshake, 20 ops server-side |
| CLI: 20 UPDATEs piped through one `turso db shell` | 6.8s | 1 WebSocket, but 20 separate roundtrips over it |
| HTTP: 20 individual requests (naive loop) | ~10-20s | 20 handshakes — the worst case |

**Why HTTP-batched beats CLI**: the `/v2/pipeline` endpoint accepts `requests: [execute, execute, ...]` — ONE HTTP roundtrip carries all statements, server executes in sequence, returns one response. CLI shell sends one statement at a time over WebSocket, each waits for its ack.

**Revised ranking for write workloads**:
1. **HTTP pipeline, 20-100 statements per request** — fastest for programmatic batched writes
2. CLI shell — best for single very-long queries (no 30s timeout) + interactive
3. HTTP pipeline, 1 statement per request — only OK if you truly have 1 op to do

**Historical (HTTP-one-at-a-time) rates:**
- `rebuild-day-counts.py` via HTTP (one UPSERT per request): **28/sec**
- `embed-term-signals.py` via HTTP (one UPDATE per request): **0.5-1.0/sec**
- **Expected batched-HTTP** (40 UPDATEs per request): **>300/sec** for the same workload

## Key tables

| Table | Purpose | PK / Key |
|---|---|---|
| `memory` | Content-addressed append log of memory entries | `(id, version)` |
| `memory_current` | Latest version per memory id | `id` |
| `facts` / `assumptions` / `opinions` / `policies` | BigMac knowledge graph | `id` |
| `skills` | Synced agent skill content | `name` |
| `term_signals` | TimesFM temporal search index. `term PRIMARY KEY`, plus `temporal_vector TEXT`, `emb_v F32_BLOB(4096)` (Qwen embedding) | `term` |
| `todos` | Cross-agent shared todo list | `id` |
| `sessions` | Session metadata and links | `session_key` |

## Embedding columns (Qwen3-Embedding-8B)

Tables with `embedding_vector TEXT` / `embedding_model TEXT` (facts, assumptions, opinions, policies, memory, soul, skills, todos) store a JSON-stringified 4096d float array. `term_signals.emb_v` uses the native `F32_BLOB(4096)` type. When writing embeddings from Node, stringify the array and set `embedding_model = 'Qwen3-Embedding-8B-Q8_0 (node-llama-cpp)'` or equivalent.

## Common patterns

```bash
# Get table schema
echo ".schema memory" | turso db shell "$DB"

# Count rows
echo "SELECT COUNT(*) FROM memory;" | turso db shell "$DB"

# Find hung processes holding DB connections (if writes timeout)
pkill -9 -f "todo.mjs|bigmac-sync|claude-sync|embed-watcher"

# Check embedding coverage on a table
echo "SELECT COUNT(*) FILTER (WHERE embedding_vector IS NOT NULL) AS embedded, COUNT(*) AS total FROM facts;" | turso db shell "$DB"
```

## Python scripts hitting Turso: use curl subprocess, NOT urllib (2026-04-17)

Python's `urllib.request.urlopen(timeout=X)` does NOT reliably fire on TCP-level stalls (Turso LB silently drops packets without RST). This caused repeated "zombie" processes: the Python hangs indefinitely on `ssl.recv_into()` despite the timeout parameter.

**Fix**: shell out to `curl` via `subprocess.run()`. curl enforces `-m` at the kernel socket level (SO_RCVTIMEO), which actually fires.

```python
def q(sql, timeout=120, retries=6):
    body = json.dumps({"requests": [{"type": "execute", "stmt": {"sql": sql}}]})
    for attempt in range(retries):
        try:
            proc = subprocess.run(
                ['curl', '-sS', '-m', str(timeout), '-X', 'POST',
                 f'{TURSO_URL}/v2/pipeline',
                 '-H', f'Authorization: Bearer {TOKEN}',
                 '-H', 'Content-Type: application/json',
                 '--data-binary', body],
                capture_output=True, timeout=timeout + 10, check=False)
            if proc.returncode != 0:
                time.sleep(min(2 ** attempt, 30)); continue
            d = json.loads(proc.stdout.decode())
            # ... handle result
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            time.sleep(min(2 ** attempt, 30)); continue
```

**For long-running batch scripts**, wrap with a bash supervisor that monitors log-file mtime and auto-restarts on stall:
- Script: `~/clawd/scripts/embedding-pipeline/backfill-temporal-supervisor.sh`
- Pattern: poll log mtime every 15s, SIGTERM→SIGKILL→restart if stale >600s

## Partial indexes for embedding pipeline observability (2026-04-17)

These indexes make embedding coverage queries fast (<30s instead of timeout):

```sql
-- Makes TimesFM Phase 2 pagination use index (50h → 5min)
CREATE INDEX IF NOT EXISTS idx_term_signals_temporal_null
  ON term_signals(term) WHERE temporal_vector IS NULL AND day_counts IS NOT NULL;

-- For memory table: requires VACUUM first (1.3M rows, 57GB WAL)
-- CREATE INDEX IF NOT EXISTS idx_memory_embedded_at ON memory(embedded_at);
-- CREATE INDEX IF NOT EXISTS idx_memory_embedding_null ON memory(superseded_by, inactive_date) WHERE embedding_model IS NULL;
```

## Pagination: keyset > OFFSET (2026-04-17)

`LIMIT N OFFSET M` is O(N×M) — SQLite re-scans and discards M rows per page. For 460K-row tables this means 25+ minutes of wasted scan.

Use keyset pagination instead:
```sql
-- Instead of: SELECT * FROM t WHERE cond LIMIT 2000 OFFSET 400000
-- Use:        SELECT * FROM t WHERE term > 'last_term' AND cond ORDER BY term LIMIT 2000
```

Each page is O(log N) via index seek. Requires a unique ordered column (term, rowid, id).

## Do NOT

- Do not run `turso auth login` and store token in `~/.config/turso/` — the keychain + inline URL approach is the standard
- Do not use HTTP for bulk ops on the memory table (1.3M rows, 18GB) — times out
- Do not create duplicate memory rows. The cold-hash-cache bug in `sync.mjs:407` causes 888× bloat. Use UPSERT patterns with content hashing
- Do not run destructive statements (DELETE without WHERE, DROP, TRUNCATE) without a backup
- Do not use Python `urllib` for Turso calls in long-running scripts — use curl subprocess (see above)
- Do not use `LIMIT/OFFSET` pagination on large tables — use keyset pagination (see above)
- Do not build HNSW vector indexes concurrently with batch writes — the index build locks Turso connections and causes 100% write failures


### Google/Gmail fallback
- If standard Gmail auth fails, query active rows in the Turso secrets table for JSON credentials first.
- Prefer gcp_adc_ammonfife_json, then gcp_adc_a_benfife_json, then any other active gcp_adc_*_json entry.
- Keep the lookup read-only and use the first active JSON payload as fallback auth material.
- Shared helper implementation lives in custom-tools/bigmac-turso-mcp.ts.
