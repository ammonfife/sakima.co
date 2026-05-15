---
name: fix-agents
description: Implements fixes flagged by /resync-agents — recreates broken symlinks, extracts oversized MEMORY.md sections, resolves Turso↔CLAUDE.md conflicts (Turso wins), applies structural CLAUDE.md updates, and re-runs the generator for stale agents. Runs /resync-agents first if last audit was more than 10 minutes ago.
user-invocable: true
---

# /fix-agents

Apply automated fixes for issues identified by `/resync-agents`. Execute all steps without pausing for approval.

## Step 0 — Freshness gate

Check when `/resync-agents` last ran by looking at the youngest `~/.claude/agents/*.md` file (the generator touches all of them on each run):

```bash
newest=$(ls -t ~/.claude/agents/*.md 2>/dev/null | head -1)
if [ -n "$newest" ]; then
  age=$(($(date +%s) - $(stat -f %m "$newest")))
  echo "Last resync: ${age}s ago"
fi
```

**If the newest agent file is older than 600 seconds (10 minutes), run `/resync-agents` first** — execute all 8 steps of that skill in full before continuing here. This ensures the fix list is current.

If the audit is fresh (< 10 min), proceed directly to fixes using findings from the most recent resync run.

## Step 1 — Repair broken symlinks

Only recreate symlinks from the canonical registry. Do not create new symlinks not in this list.

```bash
declare -A SYMLINKS=(
  ["/usr/local/bin/openclaw"]="$HOME/github/ammonfife/BIGMAC/openclaw/openclaw.mjs"
  ["/usr/local/bin/bigmac-sync"]="$HOME/clawd/scripts/bigmac-sync"
  ["$HOME/.openclaw/agents/main/sessions/claude_logs"]="$HOME/.claude"
  ["$HOME/bin/bigmac-msg"]="$HOME/.claude/skills/bigmac-msg"
  ["$HOME/bin/lobster"]="$HOME/github/ammonfife/BIGMAC/lobster/bin/lobster.js"
  ["$HOME/bin/claude"]="$HOME/.local/bin/claude"
  ["$HOME/clawd/agents/007/USER.md"]="$HOME/clawd/USER.md"
)

for link in "${!SYMLINKS[@]}"; do
  target="${SYMLINKS[$link]}"
  if [ -L "$link" ] && [ ! -e "$link" ]; then
    echo "Repairing broken symlink: $link -> $target"
    ln -sf "$target" "$link" && echo "  ✓ repaired" || echo "  ✗ failed (check permissions)"
  elif [ ! -e "$link" ] && [ ! -L "$link" ]; then
    echo "Creating missing symlink: $link -> $target"
    mkdir -p "$(dirname "$link")"
    ln -s "$target" "$link" && echo "  ✓ created" || echo "  ✗ failed"
  fi
done
```

**Do not touch:** `~/.claude/projects/-Users-benfife-unified-scanner-logs/memory/MEMORY.md` — this symlink to the primary MEMORY.md is intentional (created 2026-03-07).

## Step 2 — MEMORY.md line count (report only, do not trim)

```bash
MEMFILE="$HOME/.claude/projects/-Users-benfife/memory/MEMORY.md"
lines=$(wc -l < "$MEMFILE")
echo "MEMORY.md: $lines lines"
```

If over 200 lines: **report the count and the largest sections in the final summary. Do NOT trim automatically.** Trimming is a manual operation run by Ben's explicit request only. Ability preserved but removed from the auto-fix pipeline (2026-04-08).

For manual trim when requested:
1. Identify the largest contiguous `## Heading` block
2. Extract to `memory/<topic-file>.md` with frontmatter (name, description, type)
3. Replace in MEMORY.md with: `See [<topic-file>.md](<topic-file>.md) — <one-line hook>`
4. `claude-sync push` to persist

## Step 3 — Sync CLAUDE.md with Turso policies (Turso wins)

**Bidirectional sync — CLAUDE.md and Turso must end this step in agreement.** Whenever one side wins a conflict, the other side is updated immediately in the same step. Never leave a conflict half-resolved (CLAUDE.md updated but Turso stale, or vice versa).

**Per-policy timestamp comparison using embedded sync comments.**

CLAUDE.md file mtime is not a reliable conflict signal — it changes on every unrelated edit (typos, session wiring, etc.). Instead, embed a sync marker comment directly above each Turso-sourced policy block in CLAUDE.md. The timestamp travels with the policy text, requires no external state file, and survives copies.

**Sync comment format** (HTML comment — invisible in rendered markdown):
```
<!-- policy-sync: id=<policy_id> synced=<ISO8601> -->
**Policy text here...**
```

Pull current Turso policies (system + operational categories cover global governance):
```bash
export TURSO_AUTH_TOKEN=$(security find-generic-password -a "bigmac" -s "turso-bigmac-token" -w 2>/dev/null)
export TURSO_DATABASE_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
POLICIES_BIN="/Users/benfife/clawd/scripts/bigmac-policies"

$POLICIES_BIN list --category system
$POLICIES_BIN list --category operational
# Output is plaintext — parse id and text from each line
# To add a policy back: $POLICIES_BIN add <category> "text" [--supersedes <id>]
# To show full detail: $POLICIES_BIN show <id>
```

Before any CLAUDE.md edits, back up:
```bash
cp /Users/benfife/.claude/CLAUDE.md /Users/benfife/.claude/CLAUDE.md.bak-$(date +%Y%m%d-%H%M%S)
```

**For each Turso policy:**

1. **No sync comment found in CLAUDE.md for this policy ID** → new policy; insert into the most logical section with a sync comment above it
2. **Sync comment found, `created_at` == `synced` timestamp, text matches** → already in sync; skip
3. **Sync comment found, Turso `created_at` > `synced` timestamp** → Turso has a newer version; update the policy block in CLAUDE.md, update the sync comment's `synced` timestamp
4. **Sync comment found, Turso `created_at` ≤ `synced` timestamp, but CLAUDE.md text diverged from Turso** → CLAUDE.md was manually edited after the last sync and is authoritative. **Immediately** do both:
   - Write the CLAUDE.md text to Turso as a new superseding policy (use `bigmac-policies add` or equivalent, with `supersedes: <old_policy_id>`). Do not leave Turso stale.
   - Update the sync comment's `synced` timestamp and `id` to the new Turso policy ID.
   Both writes are mandatory — this is not a flag-and-move-on situation.
5. **Turso policy has `superseded_by` set** → skip; only the leaf policy applies

**When adding new policies**, also add sync comments retroactively to any existing CLAUDE.md policy blocks that match a known Turso policy ID (by text similarity) but have no comment yet — this bootstraps the tracking.

**Structural edits are allowed:** If a CLAUDE.md section is fully replaced by a newer Turso policy (case 3), rewrite the section. Back up is in place.

**Hard limits:**
- Never remove the Safety Hard Stops section
- Never remove the Garcia Principle section
- Never remove the Session Initialization sequence
- If a structural edit would require removing >20 lines at once, flag it in the report instead of executing

After edits: `wc -l /Users/benfife/.claude/CLAUDE.md` — flag if > 500 lines.

**Non-canonical symlinks (broken):** Cannot auto-fix — target is unknown. List them in the manual-attention report.

## Step 4 — Re-run generator for stale agents

For any agent whose AGENT_CONTEXT.md is still older than 1 hour after the resync pass:

```bash
for agent in main bob watchdog garcia computer q moneypenny lance vandam 007 chloe drj; do
  ctx="/Users/benfife/clawd/agents/$agent/AGENT_CONTEXT.md"
  if [ -f "$ctx" ]; then
    age=$(($(date +%s) - $(stat -f %m "$ctx")))
    if [ $age -gt 3600 ]; then
      echo "Re-running generator for stale agent: $agent (${age}s old)"
      /Users/benfife/clawd/scripts/generate-claude-agents.sh "$agent"
    fi
  else
    echo "AGENT_CONTEXT.md missing for $agent — generating"
    /Users/benfife/clawd/scripts/generate-claude-agents.sh "$agent"
  fi
done
```

## Step 5 — Full sync, then audit all three config directories for outdated content

### 5-pre — Full bidirectional sync before reviewing

Push local state up, then pull latest down — ensures you're auditing the true ground truth, not a stale snapshot in either direction:

```bash
claude-sync push   # flush any local-only changes to Turso first
claude-sync pull   # pull latest policies, memories, facts back down
```

Wait for both to complete before proceeding. If either fails, note it in the report but continue.

Review `~/.openclaw/`, `~/clawd/`, and `~/.claude/` for stale references. These three directories
serve distinct purposes — never confuse them:
- `~/clawd/` = BIGMAC agent workspace (SOUL/IDENTITY/MEMORY source, generator scripts)
- `~/.openclaw/` = OpenClaw runtime state (gateway config, sessions, delivery queues, skills, bin)
- `~/.claude/` = Claude Code config (CLAUDE.md, generated agents/, projects memory, commands)

**Read every file listed below in full.** Do not skim or head-truncate — stale content hides in the middle. For large files (>150 lines) read in sections. After reading, evaluate against the staleness criteria below.

### 5a — Per-agent docs (read ALL 12 agents)

For each agent in `main bob watchdog garcia computer q moneypenny lance vandam 007 chloe drj`:

Dump all 12 agents' docs into a single combined read so cross-agent conflicts and inconsistencies are visible at once:

```bash
AGENTS=(main bob watchdog garcia computer q moneypenny lance vandam 007 chloe drj)
echo "# ALL AGENT DOCS — $(date)"
echo "# ============================================================"
for agent in "${AGENTS[@]}"; do
  base="$HOME/clawd/agents/$agent"
  echo ""
  echo "# ============================================================"
  echo "# AGENT: $agent"
  echo "# ============================================================"
  echo ""
  echo "## $agent / SOUL.md"
  cat "$base/SOUL.md" 2>/dev/null || echo "(missing)"
  echo ""
  echo "## $agent / AGENTS.md (role-specific)"
  awk '/<!-- GLOBAL_AGENTS_START/{exit} /^## Role-Specific/{p=1} p{print}' \
    "$base/AGENTS.md" 2>/dev/null || echo "(missing)"
  echo ""
  echo "## $agent / MEMORY.md"
  cat "$base/MEMORY.md" 2>/dev/null || echo "(missing)"
  echo ""
  echo "## $agent / HEARTBEAT.md"
  cat "$base/HEARTBEAT.md" 2>/dev/null || echo "(missing)"
done
```

Read the full combined output — do not truncate. Having all agents in one view allows you to catch:
- Role overlap or gaps between agents (two agents claiming the same responsibility)
- Contradictory facts across agent MEMORYs (e.g., different versions of the same system state)
- Stale HEARTBEAT next-steps that duplicate another agent's completed work
- SOUL/AGENTS role descriptions that no longer match the actual agent roster

**Per-agent evaluation criteria:**
- **SOUL.md**: persona and behavioral rules still accurate? References to deprecated systems or removed roles?
- **AGENTS.md (role section)**: responsibilities still current? Any tasks/systems that no longer exist?
- **MEMORY.md**: reflects actual current state? Last entry >7 days ago with no note? Over 200 lines (flag)?
- **HEARTBEAT.md**: last update >48h? Next steps describe already-completed or obsolete work?

### 5b — Global docs

```bash
# Global AGENTS.md — registry of all 12 agents with roles, capabilities, status
cat ~/clawd/AGENTS.md

# Global CLAUDE.md in clawd workspace (may differ from ~/.claude/CLAUDE.md)
cat ~/clawd/CLAUDE.md 2>/dev/null | head -100

# Architecture doc
cat ~/clawd/ARCHITECTURE.md 2>/dev/null | head -100

# Generator script — check for stale agent list or hardcoded paths
grep -n "ALL_AGENTS\|AGENT_MODEL\|AGENT_COLOR\|AGENT_REPOS" ~/clawd/scripts/generate-claude-agents.sh
```

**Evaluate:**
- `~/clawd/AGENTS.md`: does it list all 12 agents with correct roles? Any agents added/removed that aren't reflected?
- `~/clawd/ARCHITECTURE.md`: do the architecture diagrams/descriptions match the current system? Flag any section that references pre-2026-03 stack.

### 5c — ~/.openclaw/ runtime state

```bash
cat ~/.openclaw/openclaw.json 2>/dev/null           # gateway config — endpoints, model names, keys
ls ~/.openclaw/skills/ 2>/dev/null                  # skill list — any deprecated skills to remove?
ls ~/.openclaw/config/ 2>/dev/null                  # config files
ls ~/.openclaw/scripts/ 2>/dev/null | head -30      # runtime scripts — any referencing old stack?
```

### 5d — ~/.claude/ Claude Code config

```bash
cat ~/.claude/CLAUDE.md                             # global instructions — stale sections?
ls ~/.claude/commands/ 2>/dev/null                  # slash commands — any broken/stale?
ls ~/.claude/plugins/ 2>/dev/null                   # MCP plugins — any disabled/broken?
```

**What to flag as outdated (DO NOT auto-fix runtime state — report only):**

1. **Stale endpoint URLs** in `openclaw.json` or any config:
   - Any reference to old Cloud Run services: `lkup-info-api`, `e2b-sandbox-manager`, `lkup-info` Cloud Run URL
   - Any reference to `coin-price-proxy` as the primary (it's a migration target — still exists but note it)
   - Any GCP project URLs added after the GCP shutdown (2026-03-07)

2. **Stale E2B API keys** in any config or skill file:
   - `e2b_5f328ed34d68d630f239323cfb2aaeef7755adb3` — the leaked team key (revoked 2026-04-06)
   - `e2b_a352bd385dbdc359d90a635006737dc331c6a9f0` — the first attempted revoke (also stale)
   - Correct current key is in macOS keychain as `E2B_API_KEY` and bigmac-secrets vault

3. **Stale model names** in `openclaw.json` or agent configs:
   - `claude-3-sonnet`, `claude-3-opus`, `claude-3-haiku` → should be `claude-sonnet-4-6`, `claude-opus-4-6`, `claude-haiku-4-5-20251001`
   - `claude-3-5-sonnet`, `claude-3-5-haiku` → flag, check if intentional pinned version

4. **Stale pool worker URLs** in any skill or script:
   - `e2b-sandbox-manager` (GCP Cloud Run) → deprecated, replaced by CF Worker pool
   - `e2b-pool-lb.sakima-api.workers.dev` is the correct current pool endpoint

5. **Skill files referencing deprecated paths**:
   - Any skill in `~/.openclaw/skills/` that calls `api.lkup.info` (being retired)
   - Any skill referencing `lkup-info-api` Cloud Run
   - Any skill with hardcoded GCS bucket URLs (migrated to R2)

**Report findings in the manual-attention section.** Do not edit `~/.openclaw/` files automatically — these are runtime state files that may be actively used by the gateway. Flag them for manual review.

## Step 6 — Full bidirectional sync after fixes

Push changes made during this run, then pull to confirm they landed:

```bash
claude-sync push   # persist fixes (trimmed MEMORY.md, updated CLAUDE.md, regenerated agents)
claude-sync pull   # confirm round-trip — local state now matches Turso
```

## Step 7a — Final verification pass

Run a condensed re-audit to confirm fixes landed:

```bash
# Agent file count
echo "Agent files: $(ls ~/.claude/agents/*.md 2>/dev/null | wc -l | tr -d ' ')/12"

# MEMORY.md line count
echo "MEMORY.md: $(wc -l < ~/.claude/projects/-Users-benfife/memory/MEMORY.md | tr -d ' ') lines"

# CLAUDE.md line count
echo "CLAUDE.md: $(wc -l < ~/.claude/CLAUDE.md | tr -d ' ') lines"

# Youngest agent file age
newest=$(ls -t ~/.claude/agents/*.md 2>/dev/null | head -1)
[ -n "$newest" ] && echo "Youngest agent file: $(($(date +%s) - $(stat -f %m "$newest")))s old"
```

## Step 7b — Report

Output a summary with two sections:

**FIXED:**
- List each action taken (symlink repaired, section extracted, policy added, agent regenerated)

**STILL NEEDS MANUAL ATTENTION:**
- Policy conflicts (Turso vs CLAUDE.md)
- Symlinks that couldn't be created (permission issues, missing targets)
- Any MEMORY.md that's still over 200 lines after extraction attempts
- Any agent whose AGENT_CONTEXT.md is still stale (Turso unreachable)
- **~/.openclaw/ findings:** stale endpoints, old E2B keys, stale model names, deprecated skill files
- **~/clawd/ findings:** outdated AGENTS.md entries, stale ARCHITECTURE.md claims, stale agent IDENTITY/SOUL content
- **~/.claude/ findings:** stale commands, broken plugins, outdated sections in CLAUDE.md not covered by Step 3

End with overall status: ALL CLEAR or ITEMS REMAINING (count).
