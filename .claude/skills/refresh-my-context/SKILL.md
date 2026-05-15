---
name: refresh-my-context
description: Force-refresh Claude Code session context — bypasses the 5-min PreToolUse throttle to immediately pull latest Turso facts/policies/memory, regenerate AGENT_CONTEXT.md, drain the inbox, and rebake all 12 subagent .md files. Use when you know other agents have written new facts/policies or messages that you need to see NOW, not in the next 5 minutes. Also use after /resync-agents or after manual Turso writes.
---

# /refresh-my-context — Force-Refresh Claude's Session Context

**What this does (and why you'd invoke it):**

The PreToolUse hook already pulls Turso state + rebakes subagents every 5 minutes (throttled via flock). That's usually enough. This skill is the **escape hatch** when you need it NOW:

- Another agent (bob, chloe, lance…) just wrote a Turso fact/policy you need to act on
- An inter-agent message dropped into `.inbox` or the Turso `messages` table
- You just ran `/resync-agents` or manually updated something in Turso
- The 5-min throttle window started 4min ago and you don't want to wait

## What gets refreshed

1. **`claude-sync pull --force`** (if supported; falls back to plain `claude-sync pull` + `rm /tmp/.claude-sync-done`): pulls latest from Turso, regenerates `AGENT_CONTEXT.md`, re-runs `generate-claude-agents.sh` which rebakes all 12 subagent `.md` files.
2. **Inbox drain:** reads `~/.claude/projects/-Users-benfife/.inbox`, appends to `.read`, clears `.inbox`. Also runs `bigmac-inbox check Claude` for Turso messages.
3. **Symlink rotation:** refreshes `memory/today.md` + `memory/yesterday.md` in case the date rolled over.
4. **Reports what changed:** diffs the previous and new `AGENT_CONTEXT.md` and summarizes: new policies, new facts, new messages. Lists stale subagent .md files that got rebaked.

## How to invoke

User types `/refresh-my-context`. You then:

```bash
# 1. Force sync (bypass 5-min throttle)
rm -f /tmp/.claude-sync-done
claude-sync pull

# 2. Drain inbox
INBOX=~/.claude/projects/-Users-benfife/.inbox
READ=~/.claude/projects/-Users-benfife/.read
if [ -s "$INBOX" ]; then
  cat "$INBOX" >> "$READ"
  : > "$INBOX"
fi
bigmac-inbox check Claude 2>/dev/null || true

# 3. Rotate symlinks (in case date rolled)
cd ~/.claude/projects/-Users-benfife/memory
ln -sf "$(date +%Y-%m-%d).md" today.md
ln -sf "$(date -v-1d +%Y-%m-%d).md" yesterday.md

# 4. Report
echo "--- AGENT_CONTEXT.md freshness ---"
stat -f "%Sm" ~/.claude/projects/-Users-benfife/AGENT_CONTEXT.md
echo "--- subagent .md freshness ---"
ls -lat ~/.claude/agents/*.md | head -5
echo "--- inbox drained (last 5 lines) ---"
tail -5 "$READ"
```

After running: Re-read `AGENT_CONTEXT.md` with the Read tool to pull the fresh content into this conversation's context. The `@import` in CLAUDE.md only resolves at session start and at PreCompact — a mid-session refresh of the underlying file does NOT re-inject into context automatically. Reading it back is how fresh content enters active context.

## Important: the read-back is the point

Refreshing the file on disk does not refresh your conversation context. After this skill runs, explicitly Read `AGENT_CONTEXT.md` (and any other critical @imported files like `WORKFLOW_AUTO.md`, `MEMORY.md`) so the content enters the conversation as tool output — that's the only way mid-session refresh actually reaches your working memory.

## When NOT to use this

- When the 5-min throttle hasn't elapsed and you have no specific reason to bypass — just wait.
- For bulk Turso queries: use the `use-turso` skill directly, don't wrap it in a context refresh.
- When the work is scoped to code/files outside Turso — you don't need a fresh context for that.

## Related

- `/resync-agents` — full audit of all 12 BIGMAC agents (broader than this)
- `/fix-agents` — implements findings from /resync-agents
- `claude-sync push/pull` — lower-level, what this skill wraps
- `bigmac-inbox check <agent>` — Turso-persisted message check
