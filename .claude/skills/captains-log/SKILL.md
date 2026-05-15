---
name: captains-log
description: Post, browse, and amend entries in the shared cross-agent `captains_log` Turso table. Every Claude Code / OpenClaw / subagent session uses this to leave a short human-readable trail at hooks, task completions, and topic shifts — with links to the session chunk, memory rows, Turso writes, files, commits, and URLs — so every other agent can browse what everyone else is doing. Use when the user says "/captains-log", "log this", "add a captains log entry", "check the ship's log", "what have other agents been up to", "before switching topics write a log", or when you are about to compact, exit, ship a milestone, or hand off to another agent.
---

<!-- READ ENTIRE FILE — this skill is auto-loaded via @import in CLAUDE.md. Every step + anti-pattern is load-bearing. Override Read tool line limits if needed. (Ben 2026-04-18) -->

# /captains-log — Cross-Agent Conversational Index

A shared, immutable-by-default log stored in Turso. Every agent on this machine (claude, bob, lance, computer, openclaw, etc.) posts short human-readable entries so other agents can read them and stay aware of each other's scopes.

**Table:** Turso `captains_log` (on `bigmac-ammonfife`)
**CLI:** `~/bin/captains-log` (on `$PATH`)
**Design doc:** `~/.claude/projects/-Users-benfife/memory/project_captains_log_2026-04-18.md`

---

## When to invoke

**BLOCKING — must call captains-log before any of these:**

- Before `/exit` or `/exit-protocol`
- Before auto-compaction
- When shifting topics mid-session (e.g., finishing lkup consensus → starting capacitor camera)
- When marking a milestone or completion that the user would brag about in a standup
- When handing off work to another agent (always log before `/msg`-ing the recipient)
- When discovering something surprising (hidden coupling, lost data, bug with non-obvious cause)
- When you've written a new hard-rule feedback memory or policy
- When you've shipped a commit other agents should know about

**ALSO use when** the user asks "what are other agents doing", "check the ship's log", "any updates from X", or invokes `/captains-log` directly.

**Never log** every tool call or minor edit. Rule of thumb: if the next session skim-reading the last 20 entries wouldn't care, don't log it. The captain's log is for topic-level and session-state-shift events.

---

## Step 0 — Ensure your identity is exported

```bash
# Auto-detect for Claude Code sessions
if [ -z "$CAPTAINS_LOG_SESSION" ]; then
    SESSION_JSONL=$(ls -t ~/.claude/projects/-Users-benfife/*.jsonl 2>/dev/null | head -1)
    if [ -n "$SESSION_JSONL" ]; then
        export CAPTAINS_LOG_SESSION=$(basename "$SESSION_JSONL" .jsonl)
        export CAPTAINS_LOG_SLUG="claude@${CAPTAINS_LOG_SESSION:0:8}"
    fi
fi
export CAPTAINS_LOG_AGENT="${CAPTAINS_LOG_AGENT:-claude}"
export CAPTAINS_LOG_PLATFORM="${CAPTAINS_LOG_PLATFORM:-claude-code}"
export CAPTAINS_LOG_MACHINE="${CAPTAINS_LOG_MACHINE:-$(hostname -s)}"
```

For non-Claude-Code agents, set `CAPTAINS_LOG_AGENT` (bob, lance, …) and a real session identifier before calling.

---

## Step 1 — Browse recent activity FIRST (optional but recommended)

Before writing your entry, skim what other agents have logged since you were last awake. Two views:

```bash
captains-log list --active --limit=20          # last 20 not-superseded across all agents
captains-log list --active --since=$(date -v-1d +%Y-%m-%d)  # anything since yesterday
captains-log list --topic=<slug> --active      # history of a specific thread
captains-log list --agent=bob --limit=10       # what bob is up to
```

Read any entry with meaty cross-refs:

```bash
captains-log show <id>
```

This step catches two bugs: (a) you're about to redo work another agent just shipped, (b) another agent posted a handoff you missed.

---

## Step 2 — Write your entry

### Required fields

- `--topic=` — 1-line slug. Reuse existing topic slugs when continuing someone else's thread so `list --topic=<slug>` groups the history. Examples: `heimdall formula DSL`, `lkup consensus migration`, `gongbo scraper modal`, `cloud cron migration`, `avalara monthly report may`.
- `--summary=` — markdown, 2–6 sentences. Tell the next reader: what you shipped, why, what's next. Plain English, not status-update-speak. Use `--summary=-` to read from stdin for multi-line.
- `--type=` — one of: `shift` (topic change), `completion` (task done), `hook` (auto-fired), `milestone` (worth celebrating / shipped), `handoff` (passing to another agent), `note` (default), `compact` (pre-compact), `exit` (session end), `recap` (Claude Code auto-recap OR any end-of-task summary >3 sentences that would otherwise only live in conversation — Ben 2026-04-18 hard rule: every recap in conversation MUST dual to captain's log with proper metadata, or it evaporates).

### Cross-reference fields (fill every applicable one)

| Flag | Format | Purpose |
|---|---|---|
| `--chunk=` | `<jsonl>#Lstart-Lend` or `bigmac-sessions show <id>` | Pointer into your session transcript so a future reader can replay the exact moment |
| `--memory=` | comma-sep paths | Memory files you wrote or heavily referenced |
| `--turso=` | `table:id,table:id` | Turso rows you wrote (e.g. `facts:821,todos:3387,policies:764`) |
| `--files=` | comma-sep paths | Local files you edited |
| `--commits=` | `repo@sha:msg,...` | Git commits you pushed |
| `--urls=` | comma-sep URLs | External links (deploys, PRs, tickets, Supabase dashboards) |
| `--tags=` | comma-sep | For filtering — reuse consistent tag vocabulary |

### Example — milestone log

```bash
captains-log add \
  --topic="heimdall audience formula DSL" \
  --type=milestone \
  --summary="Shipped the AST-based formula evaluator in /api/audience_trend. cbrt/abs/sqrt/**/+/-/*/div all work; __import__ probe is blocked by the whitelist walker. Verified linear formula matches weighted-sum baseline bit-for-bit. Tesla+Rivian-Honda-Ford peaks June, troughs January as expected." \
  --chunk="/Users/benfife/.claude/projects/-Users-benfife/d205580a-5198-4cda-b783-c0aec50cfb1b.jsonl" \
  --memory="/Users/benfife/.claude/projects/-Users-benfife/memory/feedback_heimdall_population_std.md" \
  --files="/Users/benfife/github/ammonfife/heimdall-archive/06_scheme_L_2026/phase1/demo_server.py" \
  --commits="heimdall-archive@abc123:audience formula DSL with safe AST evaluator" \
  --tags="heimdall,formula,ast,ship"
```

### Example — handoff log

```bash
captains-log add \
  --topic="gongbo scraper modal" \
  --type=handoff \
  --summary="Diagnosed: CF Worker returns success:true but extract is empty because page.click() never hits the TOS dismiss button. Handing to Lance — he knows the gongbo-scraper Worker best. Root cause is a selector issue, not the protocolTimeout Task #20 claims. See Turso todo #3390 for the checked-ownership trail." \
  --turso="todos:3390" \
  --urls="https://gongbo-scraper.sakima-api.workers.dev" \
  --tags="lkup,cloudflare,gongbo,handoff-to-lance"
```

---

## Step 3 — Amend only your own entries (if needed)

**Semantic clarification (Ben 2026-04-18):** the cross-reference fields
(`related_commits`, `related_turso_writes`, `related_files`,
`related_memory_paths`, `related_urls`, `tags`) are **append-only** JSON
arrays. The CLI verb is `captains-log amend <id>` for historical reasons,
but the operation on cross-refs is strictly additive — `amend` never
removes or replaces existing entries, only appends new ones. The `summary`
field CAN be rewritten (polish/clarification). The SQL schema comment
currently reads "can be amended" — TODO: when captains_log table is next
migrated, update to "append-only cross-refs + summary polish". Verb stays
`amend`; semantics are append.

You can extend cross-refs or polish the summary of YOUR OWN logs later:

```bash
captains-log amend <id> --tags="heimdall,formula,ast,ship,verified" \
                        --commits="repo@newsha:verification + tests"
```

**Not allowed:** editing another session's log (wrapper rejects); changing `agent`, `session_id`, `created_at`, `platform`, or `machine` on any log (Turso trigger rejects).

**If you need to correct another session's log:** write your own new entry, then `captains-log supersede <their-id> --with=<your-id>` if you have admin rights (`CAPTAINS_LOG_ADMIN=1`) OR just link to the correction in your summary.

---

## Step 4 — Browse patterns cheat-sheet

```bash
# "What's happening right now" — active work across all agents
captains-log list --active --limit=30

# "What's been the story on X" — thread history
captains-log list --topic="<slug>" --limit=50

# "What did Lance ship today" — per-agent filter
captains-log list --agent=lance --since=$(date +%Y-%m-%d)

# "Show me compact points" — find resume markers
captains-log list --type=compact --limit=10
captains-log list --type=exit --limit=10

# "Show me handoffs I might own" — tag filter
captains-log list --tag=handoff-to-claude

# "Before I start on <topic>, show full history"
captains-log list --topic="<slug>"
```

---

## Anti-patterns

- **DON'T log every tool call.** Per-topic and per-session-state-shift only.
- **DON'T invent a new topic slug for an existing thread.** Run `list --topic=<fuzzy>` first to reuse.
- **DON'T put secrets, tokens, or PII in summaries.** Turso is shared infra; logs are indexed + embeddable.
- **DON'T amend another agent's log.** Supersede or write your own.
- **DON'T use the admin-override without a very good reason.** Every override is counted in `admin_override_count` and audited to a slug + timestamp.
- **DON'T forget to set the identity env vars.** A log with `CAPTAINS_LOG_SESSION=unknown` is only slightly better than no log.

---

## Related skills + context

- `/exit-protocol` — should call captains-log with `--type=exit` (or `compact`) as part of its Step 3 daily-log append.
- `/refresh-my-context` — should include `captains-log list --active --limit=20` output so agents pick up recent shifts.
- `/resync-agents` — has a natural hook: after regenerating agent `.md` files, log a `--type=hook` entry.
- `bigmac-sessions` CLI — good for building `--chunk=` refs that link back to session transcripts.
- Design + schema: `~/.claude/projects/-Users-benfife/memory/project_captains_log_2026-04-18.md`
