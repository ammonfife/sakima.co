---
name: resync-agents
description: Full audit and resync of all 12 OpenClaw Claude Code agents — refreshes Turso policies, regenerates ~/.claude/agents/*.md, syncs all agent memories, checks symlinks, and flags stale content in CLAUDE.md and AGENTS.md.
user-invocable: true
---

# /resync-agents

Perform a full audit and resync of the BIGMAC agent system for Claude Code. Execute all steps without pausing for approval.

> **⚡ RUN STEP 8 FIRST** — Step 8 (cross-platform consistency audit) must run BEFORE Step 1 (regeneration).
> It checks for diverged skills, stale paths, .openclaw contamination, missing knowledge snapshots,
> push-before-pull violations, and memory coalescing issues. Finding these BEFORE regenerating prevents
> overwriting with bad state. Execute: jump to Step 8, complete it, then return to Step 1.
>
> **PUSH ALL WORKSPACES BEFORE ANY PULL** (Step 2): push every `~/bigmac-state/agents/<name>/` workspace
> AND `claude-sync push` BEFORE pulling anything. Pulling first nukes unpushed work from other agents.

## Step 1 — Regenerate all 12 Claude Code agent definitions

Run the generator (this also refreshes each agent's AGENT_CONTEXT.md from Turso first):

```bash
/Users/benfife/clawd/scripts/generate-claude-agents.sh
```

Verify output: `ls ~/.claude/agents/*.md | wc -l` should return 12.

If any agent fails Turso refresh, note it but continue — the cached AGENT_CONTEXT.md will be used.

## Step 2 — Sync all agent memories to Turso

For each agent workspace in `/Users/benfife/clawd/agents/`, run `bigmac-sync push` to ensure memories are persisted:

```bash
for agent in main bob watchdog garcia computer q moneypenny lance vandam 007 chloe drj; do
  workspace="/Users/benfife/clawd/agents/$agent"
  [ -d "$workspace" ] || continue
  echo "Syncing $agent..."
  (cd "$workspace" && bigmac-sync push) 2>/dev/null || echo "  warn: sync failed for $agent"
done
```

Then push Claude Code's own memory:
```bash
claude-sync push
```

## Step 3 — Audit symlinks

Check for broken or unexpected symlinks in the agent ecosystem:

```bash
# Core symlinks that must exist
links=(
  "/usr/local/bin/openclaw"
  "/usr/local/bin/bigmac-sync"
  "~/.openclaw/agents/main/sessions/claude_logs"
  "~/bin/bigmac-msg"
  "~/bin/lobster"
  "~/bin/claude"
  "~/clawd/agents/007/USER.md"
)

for link in "${links[@]}"; do
  expanded="${link/#\~/$HOME}"
  if [ -L "$expanded" ]; then
    target=$(readlink "$expanded")
    if [ ! -e "$expanded" ]; then
      echo "BROKEN SYMLINK: $expanded -> $target"
    fi
  elif [ ! -e "$expanded" ]; then
    echo "MISSING: $expanded"
  fi
done
```

Report any broken or missing symlinks. Do NOT auto-fix symlinks — flag them for Ben.

**Known intentional symlink:** `-Users-benfife-unified-scanner-logs/memory/MEMORY.md` -> primary MEMORY.md (created 2026-03-07). This is correct — do not replace it with a stub.

## Step 4 — Verify agent file completeness

For each generated agent file, confirm it contains the required sections:

```bash
for agent in main bob watchdog garcia computer q moneypenny lance vandam 007 chloe drj; do
  file="$HOME/.claude/agents/$agent.md"
  if [ ! -f "$file" ]; then
    echo "MISSING: $file"
    continue
  fi
  lines=$(wc -l < "$file")
  has_heartbeat=$(grep -c "HEARTBEAT.md" "$file" || true)
  has_inbox=$(grep -c ".inbox" "$file" || true)
  has_memory=$(grep -c "/memory/" "$file" || true)
  echo "$agent: ${lines}L | heartbeat=$has_heartbeat inbox=$has_inbox memory=$has_memory"
done
```

Any agent file missing HEARTBEAT.md, .inbox, or /memory/ references should be regenerated individually:
```bash
/Users/benfife/clawd/scripts/generate-claude-agents.sh <agent-name>
```

## Step 5 — Check MEMORY.md line count

```bash
wc -l ~/.claude/projects/-Users-benfife/memory/MEMORY.md
```

If over 200 lines: read the file, identify the largest sections, extract them to topic files in the same `memory/` directory, and replace with a one-line pointer. The 200-line limit is hard — content beyond it is truncated from every session's context.

## Step 6 — Refresh CLAUDE.md violation patterns + check for stale content

### 6a — Refresh Common Violation Patterns section (always run)

Pull all behavior-correction policies from Turso — system + operational categories:

```bash
~/clawd/scripts/bigmac-policies list --category system 2>/dev/null
~/clawd/scripts/bigmac-policies list --category operational 2>/dev/null
```

Read the current `## Common Violation Patterns (learned from all agents)` section in `/Users/benfife/.claude/CLAUDE.md`.

**Rewrite that section** with a fresh distillation of the patterns found in the Turso pull. The category list is open — add new categories whenever the policies reveal a distinct pattern not already covered; remove categories that no longer appear.

For each category, include both sides:
- **DON'T:** the specific banned phrases/behaviors (concrete, quote-style examples where possible)
- **DO:** the correct alternative behavior — what good looks like

This gives agents a positive model to aim for, not just a list of bans. Example structure:
```
**Category name (frequency / scope):**
- DON'T: [specific phrases or pattern]
- DO: [correct replacement behavior]
```

Add any new patterns not already present. Remove any that no longer appear in Turso policies. Update the "Source: Turso policies #..." citation at the bottom to reflect the current full list of relevant policy IDs.

Back up before editing:
```bash
cp /Users/benfife/.claude/CLAUDE.md /Users/benfife/.claude/CLAUDE.md.bak-$(date +%Y%m%d-%H%M%S)
```

### 6b — Check for stale content in CLAUDE.md and AGENTS.md

Read the following files and compare against current Turso state:

- `/Users/benfife/.claude/CLAUDE.md` — global governance
- `/Users/benfife/clawd/agents/*/AGENTS.md` — per-agent role specs

Also pull global-scoped policies:
```bash
~/clawd/scripts/bigmac-policies list --scope global 2>/dev/null | head -40
```

Flag (do not auto-edit) any policy in Turso that contradicts or is absent from CLAUDE.md. Summarize discrepancies. Only edit CLAUDE.md if the fix is clear and additive (adding a missing fact/path/rule). For structural changes or removals, list them for Ben to approve.

## Step 7 — Verify AGENT_CONTEXT.md freshness

For each agent, check that AGENT_CONTEXT.md was updated in this run:

```bash
for agent in main bob watchdog garcia computer q moneypenny lance vandam 007 chloe drj; do
  ctx="/Users/benfife/clawd/agents/$agent/AGENT_CONTEXT.md"
  if [ -f "$ctx" ]; then
    age=$(($(date +%s) - $(stat -f %m "$ctx")))
    echo "$agent AGENT_CONTEXT.md: ${age}s old"
  else
    echo "$agent AGENT_CONTEXT.md: MISSING"
  fi
done
```

Any file older than 1 hour after the generator ran indicates a Turso refresh failure for that agent.

## Step 8 — Cross-platform consistency audit

Check that every AI provider on this machine has consistent instruction files,
skills, context, and project pointers. Run this every resync — drift between
providers is invisible until an agent starts from the wrong place.

### 8a — Provider dir inventory

```bash
echo "=== Provider dirs ==="
for dir in ~/.claude ~/.codex ~/.agents ~/.gemini ~/.openclaw; do
  [ -d "$dir" ] || continue
  skills_count=$(ls "$dir/skills/" 2>/dev/null | wc -l | tr -d ' ')
  instructions=$(ls "$dir/CLAUDE.md" "$dir/AGENTS.md" "$dir/instructions.md" 2>/dev/null | tr '\n' ' ')
  echo "  $dir: skills=$skills_count instructions=${instructions:-none}"
done
```

### 8b — Skills duplication / divergence check

The `.agents/` and `.gemini/` skill dirs often contain duplicates of skills
in `~/.claude/skills/`. Flag any skill that exists in both locations with
different content hashes (silently-diverged copy = danger).

```bash
CLAUDE_SKILLS=~/.claude/skills
for provider_dir in ~/.agents ~/.gemini/.claude/skills ~/.codex/skills; do
  [ -d "$provider_dir" ] || continue
  for skill in "$provider_dir"/*/SKILL.md; do
    skill_name=$(basename "$(dirname "$skill")")
    canonical="$CLAUDE_SKILLS/$skill_name/SKILL.md"
    if [ -f "$canonical" ]; then
      if ! diff -q "$canonical" "$skill" >/dev/null 2>&1; then
        echo "DIVERGED: $skill_name in $provider_dir vs ~/.claude/skills"
      fi
    else
      echo "EXTRA: $skill_name in $provider_dir (not in ~/.claude/skills)"
    fi
  done
done
```

**Fix:** `bigmac-skills sync` pushes canonical versions from Turso to all
registered provider dirs. If `.agents/` skills are a legacy copy, symlink them:
```bash
ln -sf ~/.claude/skills ~/.agents/skills  # or per-skill symlinks
```

### 8c — Instruction file consistency

Each provider's "start here" instruction file should reference the same
canonical boot sequence (lkup_knowledge.md → NEXT_SESSION.md → AGENTS.md).

Check these exist and point to the right places:

```bash
# Claude: ~/.claude/CLAUDE.md (global), lkup.info project CLAUDE.md
# Gemini/Antigravity: ~/.gemini/AGENTS.md or ~/.gemini/instructions.md
# Codex: ~/.codex/AGENTS.md
# VSCode: .vscode/settings.json claude.instructions or project CLAUDE.md

for f in ~/.claude/CLAUDE.md ~/.codex/AGENTS.md ~/.gemini/AGENTS.md ~/.agents/AGENTS.md; do
  [ -f "$f" ] || { echo "MISSING: $f"; continue; }
  # Check for lkup_knowledge reference
  grep -q "lkup_knowledge\|lkup.info\|NEXT_SESSION" "$f" 2>/dev/null \
    && echo "OK: $f references lkup project" \
    || echo "GAP: $f has no lkup.info boot reference"
done
```

### 8d — lkup_knowledge.md reachability per provider

The canonical knowledge snapshot at `~/github/ammonfife/lkup.info/lkup_knowledge.md`
should be reachable or referenced from every provider's working context.

```bash
# Symlink it into provider dirs that need it
KNOWLEDGE="$HOME/github/ammonfife/lkup.info/lkup_knowledge.md"
[ -f "$KNOWLEDGE" ] || { echo "MISSING: lkup_knowledge.md"; }

for dir in ~/.codex ~/.agents; do
  [ -d "$dir" ] || continue
  if [ ! -f "$dir/lkup_knowledge.md" ] && [ ! -L "$dir/lkup_knowledge.md" ]; then
    echo "MISSING link: $dir/lkup_knowledge.md -> $KNOWLEDGE"
    # Auto-fix: ln -sf "$KNOWLEDGE" "$dir/lkup_knowledge.md"
  fi
done
```

**Auto-fix when found:** create symlinks rather than copies — the file updates on
every lkup.info `git push`, so copies immediately go stale.

### 8e — AGENT_CONTEXT.md equivalents per surface

Claude Code gets AGENT_CONTEXT.md from Turso via `claude-sync pull`. Other
surfaces need equivalent injection. Flag any provider missing a context file
modified in the last 24h.

```bash
for dir in ~/.codex ~/.agents ~/.gemini; do
  [ -d "$dir" ] || continue
  ctx="$dir/AGENT_CONTEXT.md"
  if [ ! -f "$ctx" ]; then
    echo "MISSING context: $ctx"
  else
    age=$(($(date +%s) - $(stat -f %m "$ctx" 2>/dev/null || echo 0)))
    [ "$age" -gt 86400 ] && echo "STALE context: $ctx (${age}s old)"
  fi
done
```

### 8f — Home-dir orientation files

These files route agents landing in non-repo directories to the right project:

```bash
for f in ~/README.md ~/bigmac-state/PROJECTS.md ~/.claude/PROJECTS.md; do
  [ -f "$f" ] \
    && grep -q "lkup.info\|ammonfife" "$f" 2>/dev/null \
    && echo "OK: $f" \
    || echo "MISSING or stale: $f"
done
```

---

## Step 9 — Report

Output a concise summary:
- How many agent files were regenerated
- Which (if any) Turso refreshes failed
- Which (if any) symlinks are broken or missing
- MEMORY.md line count (flag if > 200)
- Any CLAUDE.md policy discrepancies found
- Agent AGENT_CONTEXT.md age (flag any > 1 hour old post-run)
- **Cross-platform findings:** diverged skills, missing instruction files, stale AGENT_CONTEXT.md, missing lkup_knowledge.md links, missing home-dir orientation files
- Final status: CLEAN or NEEDS ATTENTION (list items)

Do not output intermediate command results — only the final summary table.
