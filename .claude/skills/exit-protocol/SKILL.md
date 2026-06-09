---
name: exit-protocol
description: 'Save all session state durably before /exit or before context compaction. Multi-thread-safe — never overwrites another session''s state. Moves /tmp artifacts to durable locations, updates WORKFLOW_AUTO.md using the thread-sentinel contract, appends to daily memory, pushes to Turso, commits + pushes any dirty git repos touched this session, and records background jobs so the next session can resume them. Invoke as `/exit-protocol` (auto-detects mode), `/exit-protocol compact`, or `/exit-protocol exit`.'
---

# /exit-protocol — Durable-State Save Before Compaction or Exit

This document outlines the protocol for saving all session state durably before exiting or compacting the context. It is designed to be multi-thread-safe and prevent data loss.

---

## When to run

- **Before** `/exit` — always.
- **Before context compaction** — whenever the runtime warns about approaching limits, OR whenever auto-compact is disabled and you see the summary-trigger threshold.
- **On any graceful shutdown** — battery &lt; 2%, rate-limit warning, SIGINT from user.
- **Manually** — any time you want a durable checkpoint mid-session.

Two modes:

ModeTriggerWhat's different`compact`Pre-compaction checkpointWrites a PRE-COMPACT CHECKPOINT block to `memory/today.md` with resume instructions. WORKFLOW_AUTO.md thread block updated to reflect mid-session state. Background jobs and crons captured by ID so they can be rejoined post-compaction.`exit`End of sessionWrites an END-OF-SESSION summary. Dirty git repos get committed + pushed (with confirmation). Background jobs are explicitly noted as "handed off — next session resumes."

If no arg is given, detect: if `bash ps` shows a compaction trigger in flight → `compact`, else → `exit`.

---

## Step 0 — Identify your thread slug

Nothing else can happen safely without this. The slug is how WORKFLOW_AUTO.md and the daily memory log know which thread you are.

```bash
# Stable slug candidates (pick the first that applies)
# 1. Git repo basename (if session has been editing a specific repo)
#    e.g. lkup.info, sakima.co, heimdall-archive
# 2. Project name from conversation context
#    e.g. openclaw, avalara-reports, son-research-plan
# 3. Ad-hoc topic slug (kebab-case)
```

If ambiguous, ASK the user — "I'm about to save session state; what thread slug should I use? (e.g., [lkup.info](http://lkup.info), heimdall, son-research-plan)". Do NOT guess.

Export it for the rest of the steps:

```bash
THREAD_SLUG="lkup.info"   # or whatever fits
```

---

## Step 0.5 — DEEP-READ CONTRACT (mandatory — do NOT skip, do NOT shortcut)

**This is the single most important step. A checkpoint built on a partial read is worse than no checkpoint — it gives false confidence and lets work fall through the cracks.** (Ben hard rule 2026-06-09, after an exit-protocol run that filtered/tailed instead of reading deep, used "likely" about unread content, and had to be pushed 3× to go deep.)

**The whole point of an exit-protocol is to capture the FULL ARC and catch the MISSES.** A "done/shipped/verified" claim in the punch-list is exactly the kind of thing that's silently wrong; the deep read is how you catch it. Going deep is the job — not an optional nicety, not "if time."

### Read these IN FULL — never a "random tail number"

1. **The current session jsonl, in full** (`~/.claude/projects/<slug>/<session-id>.jsonl`). Extract **both** the user (Ben) messages **and** the assistant text blocks. A `tail -N` is a guess; read the whole window. If the file is huge, page through it (offset windows), but cover **every** turn — do not sample.
2. **Prior exit-protocols / compacts — go BACK through MULTIPLE.** A single session has usually compacted 2–5×; each compaction summary is lossy. Read backward through the chain (this session's earlier compaction summaries, the prior session jsonls, the last several daily-memory checkpoints, the WORKFLOW thread block's prior `[claude@…]` entries) until you have the **continuous arc**, not just the last fragment. The misses live in the seams between compactions.
3. **Subagent transcripts** (`/private/tmp/claude-501/<slug>/<session-id>/tasks/*.output`, and any sidechain `*.jsonl` modified in the window). The subagent *results* also surface as `<task-notification>` blocks in the main jsonl — read those — but when a finding is load-bearing, open the subagent's own transcript. Different subagents produce different artifact shapes (conversation jsonl vs. raw command-output dumps); **read the raw bytes to know which** before describing it.
4. **`~/.claude/history.jsonl` — read a LONG-TERM 2-weeks+ window, not just this session** (user-typed prompts only: `display`/`project`/`sessionId`/`timestamp`; assistant + subagent replies are NOT here, they're in the session jsonls). Filter by `project` to the slug and read **at least the last 2 weeks** of Ben's verbatim prompts across ALL sessions on this thread — this is how you get cross-session context, the evolution of his intent, and the *clearer* (later, more-considered) version of a decision. A single session's prompts are a slice; the 2-week arc is the real intent.

### Intent over time — conflicts are NOT automatic pivots (Ben hard rule 2026-06-09)

A later statement that contradicts an earlier one does **not** automatically mean "the earlier was wrong, pivot." **Ben may have changed his mind** — or he may be mid-thought, testing, or speaking loosely. Before you treat a contradiction as a settled correction:
- **Look for OTHER supporting context.** Is the new statement repeated, emphatic, verbatim, acted-upon? Or is it a one-off aside? Does the 2-week history show a *trend* toward the new position, or is it an outlier?
- **Weight by recency AND conviction AND repetition** — not recency alone. A casual recent remark does not override a deliberate, multiply-restated standing rule. A deliberate, multiply-restated recent rule DOES update an old one (that's a real mind-change — honor it).
- **When the evidence is mixed, capture BOTH positions as the open question** in the checkpoint ("Ben said X on date1, then Y on date2 — unresolved; look for a third data point") rather than silently picking one and acting on it.
- This is the inverse of "heavy credence to whimsical remarks": don't ignore a real mind-change, but don't manufacture a pivot from a stray line either. The 2-week history + the conviction/repetition signal is how you tell them apart.

### Hard rules for the read

- **NEVER assert what an artifact contains before reading it.** If a parser/filter returns empty, `head -c`/`tail -c` the **raw bytes** first, then describe — never infer from a failed parse.
- **The word "likely" (and "probably", "presumably", "should be") is a BS hook** — if you're about to write it about session content, you haven't read enough. Go read the actual thing.
- **Don't filter to snippets when the job is the full picture.** A final-text-only or tail-only extraction is a shortcut that drops the arc. Capture every user prompt verbatim and every substantive assistant/subagent finding in the window.
- **Catch the misses actively.** As you read, hold each "✅ done / shipped / verified" claim against the live state (git log, DB, the actual file). Flag any that don't hold — those corrections are the highest-value output of the checkpoint. Cascade corrected ground-truth back into the docs the next session reads first (see `/cascade-verified-state`).
- **Heavy credence to whimsical remarks is a trap.** An off-hand "let's just…" or a one-line aside is NOT a directive to redesign or drop a workstream. Weight a remark by how load-bearing + repeated + verbatim it is. When in doubt, capture it as a noted hint, don't act as if it's a settled decision.

### Enumerate-then-read (do this before writing anything)

State your read-surface up front, then read each item fully before drafting the checkpoint. Only after you've read the full main jsonl (both roles), walked back through the prior compactions/checkpoints for the continuous arc, read the 2-week history.jsonl arc, and opened every load-bearing subagent transcript — proceed to Step 1.

### Optional but recommended on lkup.info: deploy `/lkup-historian`

When the thread slug is `lkup.info` (or any lkup work), the exit-protocol MAY (and usually should) **dispatch `/lkup-historian`** as a background agent (Ben 2026-06-09). It audits recent session activity against the canonical ground-truth (distilled history, memory, `lkup_knowledge.md`, policy #858, the regression-landmine classes) and **flags regressions, landmine attempts, canonical-model violations, agent-asserted false confidence, and drift from Ben's verbatim intent** — exactly the misses the deep read is meant to catch, but cross-checked by an independent agent. It writes findings to Turso (facts/todos/violations), durable + cross-agent. Run it in the background early so its findings land before you finalize the checkpoint; fold any flags into the WORKFLOW thread block + daily checkpoint. It flags + files, it does NOT auto-mutate prod — safe to fire-and-incorporate. Dispatch: `/lkup-historian 12` (default 6h; widen for a long session).

---

## Step 1 — Durability sweep (move /tmp to durable locations)

Anything the session created in `/tmp/` or `/private/tmp/` that matters must move. `/tmp` is cleared by macOS at boot and by cron hygiene.

**Scan what you wrote:**

```bash
# Find files in /tmp owned by the current user, modified this session
find /tmp /private/tmp -maxdepth 2 -user "$USER" -mtime -1 2>/dev/null 
  -not -path '*/gogcli/*' 
  -not -path '*/.gemini-sync-*' 
  -not -path '*gemini-*' 
  | head -50
```

**Classification rules:**

KindDestinationPython / Node scripts you wrote`~/gemini/scripts/<project>/` or `~/bin/` if user-wideHTML for copy-paste delivery`~/.gemini/projects/-Users-$USER/memory/scratch/<slug>/`Logs, overnight build output`~/gemini/logs/`SQL migrations, fixture datarepo's actual `migrations/` or `scripts/` dirOne-off throwaway inputsdelete (with user confirmation if large)

**Never**: leave a script you referenced in Turso memory or WORKFLOW_AUTO.md in `/tmp` — the reference will dangle after the next reboot.

---

## Step 2 — Update WORKFLOW_AUTO.md (multi-thread contract)

See `~/.gemini/projects/-Users-$USER/WORKFLOW_AUTO.md` top-of-file "Edit Contract." Abbreviated here:

1. Use `Edit` (or `Edit` with `replace_all: false`), **NOT** `Write`.
2. Find your block: `<!-- THREAD:<slug> START -->` through `<!-- THREAD:<slug> END -->`.
3. Replace just that block.
4. If no block exists, `Edit` the end of file to append a new sentinel-wrapped block.
5. **NEVER touch another thread's sentinels.**

**⚠️ MULTI-SESSION PRESERVATION — HARD RULE (violated 2026-05-14):**

WORKFLOW_AUTO.md is shared across ALL parallel Claude/Codex/Gemini sessions. The thread block you own is a **cumulative log**, not a replacement. Violating this destroys other sessions' work.

- **DO NOT delete existing `[claude@XXXXXXXX]` entries** inside your thread block — those are from other sessions working the same thread
- **ONLY ADD** your session's entries under `**Completed This Session [claude@YOUR_SHORT_SID]:**`
- **ONLY ADD** your session's open items under `**Open [claude@YOUR_SHORT_SID]:**`
- **ONLY ADD** your resume steps — do NOT remove steps from prior sessions
- **Updating the header** (Project, Last update, Status, Session) is the ONLY line you may replace, not the body

**The correct pattern:**

```
<!-- THREAD:lkup.info START -->
**Project:** ... (update)
**Last update:** ... (update)
**Status:** ... (update)
**Session:** claude@NEW_SID (update)

**Completed [claude@OLD_SID_1]:**   ← KEEP — do not delete
- ...existing entries...

**Completed [claude@NEW_SID]:**     ← ADD — your new work
- ...your entries...

**Open [claude@OLD_SID_1]:**        ← KEEP — do not delete
- ...existing items...

**Resume Instructions:**
1. ...prior steps...                ← KEEP
2. ...your new steps...             ← ADD
<!-- THREAD:lkup.info END -->
```

**Pre-flight sanity — run before ANY edit to WORKFLOW_AUTO.md:**

```bash
# 1. Read the ENTIRE existing block first — never edit blind
grep -n "THREAD:${THREAD_SLUG}" ~/.claude/projects/-Users-benfife/WORKFLOW_AUTO.md

# 2. Count existing session entries — if this goes DOWN after your edit, you deleted something
grep -c "claude@" ~/.claude/projects/-Users-benfife/WORKFLOW_AUTO.md

# 3. Confirm only your slug is being touched
grep -oE 'THREAD:[^ ]+ START' ~/.claude/projects/-Users-benfife/WORKFLOW_AUTO.md
```

**Block content to write:**

- **Project:** human-readable name
- **Last update:** `YYYY-MM-DD HH:MM MDT`
- **Status:** `active` | `paused` | `blocked` | `complete`
- **Current Goal:** 1 paragraph
- **Completed This Session:** commits + shipped items + decisions
- **In Progress / Pending:** what next session picks up
- **Key Context:** paths, constants, decisions that would be lost otherwise
- **Resume Instructions:** numbered steps, starting from "read this block"

Pre-flight sanity:

```bash
grep -oE 'THREAD:[^ ]+ START' ~/.gemini/projects/-Users-$USER/WORKFLOW_AUTO.md
# Confirm your slug appears (or is about to be appended). Any other slug = another thread; do not touch.
```

---

## Step 3 — Append to daily memory log (APPEND ONLY — SHARED FILE)

**Pre-flight: run `/SELF-REVIEW` first.** Scan your own turns this session — including the exit-protocol run itself — against the BIGMAC pattern catalog. Two patterns are especially common DURING an exit-protocol and must be checked: `claim-without-search` (claiming "full picture" from a partial read — see Step 0.5) and `single-sample-extrapolation` (asserting an artifact's contents before reading it). Put the violation count in the checkpoint header, e.g. `🗜️ PRE-COMPACT CHECKPOINT — <slug> [2 violations self-reported]`.

The daily log is a firehose. **NEVER overwrite — multiple agents write to this file concurrently.**
Using `Write` on a daily log file DESTROYS all other agents' entries for the day.
Always use `>>` (bash append) or `Edit` to add content. Never `Write`.

```bash
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)
LOG=~/.gemini/projects/-Users-$USER/memory/${DATE}.md

# If we rolled over past midnight, today.md symlink may be stale — rotate first
ln -sf "${DATE}.md" ~/.gemini/projects/-Users-$USER/memory/today.md
ln -sf "$(date -v-1d +%Y-%m-%d).md" ~/.gemini/projects/-Users-$USER/memory/yesterday.md

# MANDATORY: derive the short session id from the canonical walk-up helper.
# Do NOT type a placeholder or guess — /switch-accounts gates on this label
# (must match within 2 min of now). Wrong label = failed downstream gate.
SESS_FULL=$(~/bin/my-gemini-session-id)
SESS_SHORT=${SESS_FULL%%-*}
[ -n "$SESS_SHORT" ] || { echo "ERROR: cannot derive session id for checkpoint label — aborting checkpoint write" >&2; exit 1; }
```

**For** `compact` **mode** (header MUST include `gemini@${SESS_SHORT}`):

```markdown
## [HH:MM MDT gemini@<SESS_SHORT>] 🗜️ PRE-COMPACT CHECKPOINT — <slug>

**Session:** `<SESS_FULL>`
**Captured at:** <ISO timestamp>

**<slug> git state:**
- HEAD: `<sha>` (branch)
- Last commit: "<msg>"
- Ahead of origin: <N> commits

**Active plan doc:** <path, if any>

**Resume instructions:**
1. Read `WORKFLOW_AUTO.md` THREAD:<slug> block
2. Read daily memory tail since this checkpoint
3. Pull Turso context: `gemini-sync pull`
4. Check TaskList, CronList, background `Bash run_in_background` processes
5. Resume the in-progress workstream
```

**For** `exit` **mode** (header MUST include `gemini@${SESS_SHORT}`):

```markdown
## [HH:MM MDT gemini@<SESS_SHORT>] END OF SESSION — <slug>

**Shipped:** <commits, files, deploys>
**Open threads:** <what's still in_progress>
**Handed off:** <any background agents/jobs that continue>
**Next-session first action:** <one concrete step>
```

---

## Step 4 — Update MEMORY.md (index only — SHARED FILE — only if warranted)

**MEMORY.md is shared across all agents and sessions. Use `Edit` to add a bullet line. NEVER use `Write` on MEMORY.md — it wipes every other agent's memory entries.**

[MEMORY.md](http://MEMORY.md) is an INDEX, not a journal. Update it only when:

- You created a new persistent feedback memory (`feedback_*.md`)
- You created a new project memory with long-term relevance
- You introduced a new hard rule that future sessions must know

Use `Edit` to add one line in the right section. **Do not use** `Write` **on [MEMORY.md](http://MEMORY.md).**

If the new memory is ephemeral (task progress, debug notes, session-specific state), DO NOT add to [MEMORY.md](http://MEMORY.md) — it belongs in the daily log only.

---

## Step 5 — Turso sync (PUSH FIRST, then any optional pull)

**Always push before pull.** At exit/compact, the local state is the authority — it contains this session's unsaved work. If you pull first, you can overwrite local edits with stale Turso state that's missing what we just wrote. The sync merge is newest-wins, so pushing first guarantees our newest edits land in Turso; any subsequent pull is additive.

```bash
# 1. PUSH FIRST — our local state is the source of truth right now
gemini-sync push
```

Then, only if another agent might have written something we need to merge into local state before the session ends:

```bash
# 2. Optional pull (post-push), only if you need the latest Turso additions reflected on disk
gemini-sync pull
```

**NEVER run VACUUM or DELETE on Turso.**

---

## Step 6 — Scripts / skills durability

If you **created or modified a skill** during this session:

```bash
# Verify it's in the canonical location
ls -la ~/.gemini/skills/<skill-name>/SKILL.md

# Sync to Turso skills table (part of gemini-sync push)
gemini-sync push
```

If you **created a binary/script** used by downstream sessions:

- Must live in `~/bin/` (on PATH) or `~/gemini/scripts/` (canonical)
- Must be marked executable: `chmod +x <path>`
- Any Turso-referenced script path must be durable (`/tmp` is banned)

---

## Step 7 — Background jobs handoff

List anything still running that the next session needs to know about:

```bash
# Show running Bash run_in_background processes started by Gemini
ps aux | grep -E "gemini" | grep -v grep
```

**For each:** write a line in the WORKFLOW_AUTO.md thread block under "In Progress" including:

- PID or trigger ID
- What it's doing
- Expected completion
- How the next session can check status

---

## Step 8 — Inbox READ-ONLY inspection (do NOT drain at exit)

**Never clear the inbox at exit or compact.**

```bash
# READ-ONLY inspection — do not modify .inbox
test -s ~/.gemini/projects/-Users-$USER/.inbox && {
  echo "📬 Pending messages in .inbox — carrying to next session:"
  cat ~/.gemini/projects/-Users-$USER/.inbox
}
```

---

## Step 9 — Commit + push dirty git repos (exit mode)

Only in `exit` mode.

Auto-commit locations (no confirmation needed):

- `/Users/$USER/github/ammonfife/*`
- **Any repo whose remote URL starts with** `git@github.com:ammonfife/` **or** `https://github.com/ammonfife/`**.**
- **Local-only repos**
- `~/.gemini/`

### Per-repo flow

```bash
# Find repos the session touched
for dir in ~/.gemini ~/github/ammonfife/*; do
  [ -d "$dir/.git" ] || continue
  cd "$dir"
  git status --porcelain | grep -q . || continue
  # ... auto-commit flow
done
```

### Special case: `~/.gemini/`

If `~/.gemini/.git` exists → treat as a standard auto-commit repo.

If `~/.gemini/.git` does NOT exist → **initialize it and commit**.

---

## Step 10 — Final verification

Before reporting "done":

```bash
# 1. Thread block exists + is current
grep -A2 "THREAD:${THREAD_SLUG} START" ~/.gemini/projects/-Users-$USER/WORKFLOW_AUTO.md | head -5

# 2. Daily memory updated
tail -20 ~/.gemini/projects/-Users-$USER/memory/today.md

# 3. Turso sync fired
pgrep -f "gemini-sync push" && echo "sync in flight" || echo "sync complete"

# 4. No dangling /tmp references in thread block
grep -c "/tmp/" ~/.gemini/projects/-Users-$USER/WORKFLOW_AUTO.md

# 5. Skills + scripts survived the move
[ -f ~/.gemini/skills/<any-skill-touched>/SKILL.md ] && echo "skill ok"
```

---

## Output format

```
🗜️ Exit protocol: <compact|exit> — thread <slug>
─────────────────────────────────────────────────
• Thread block updated:   WORKFLOW_AUTO.md ✓
• Daily log appended:     memory/YYYY-MM-DD.md ✓
• /tmp migrated:          <N> files moved to <dest>
• Turso sync:             fired (gemini-sync push PID <n>)
• Background jobs:        <N> running, captured in thread block
• Git state:              <clean | committed N files, pushed>
• Inbox:                  <N> messages drained
─────────────────────────────────────────────────
Safe to <compact | exit>.
```
