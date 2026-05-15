---
name: bigmac-sync-skills
description: Sync BigMac skills to and from Turso, and dump the skills index used for context injection across agent surfaces.
---

# bigmac-sync-skills — Master Skills Sync

Sync all BigMac agent skills to/from Turso. Turso is the central repo;
all Claude Code, OpenClaw, Gemini, Codex, and Grok instances pull from here.

## When to use
- After creating or editing a skill
- When an agent says it doesn't know how to do something that should be a skill
- To ensure all agents have the latest skill library
- On demand: "sync skills", "push my skills", "pull latest skills"

## Commands

```bash
# Full bidirectional sync (recommended)
bigmac-skills sync

# Push local → Turso only
bigmac-skills push

# Pull Turso → all local paths only
bigmac-skills pull

# Show what's in Turso vs local
bigmac-skills status

# Dump skills index for context injection
bigmac-skills context
```

## What it syncs

### Sources (push FROM)
- `~/.claude/skills/`   — Claude Code global skills
- `~/.openclaw/skills/` — OpenClaw installed skills
- `~/clawd/skills/`     — Clawd project skills

### Destinations (pull TO)
Same three directories — every agent instance gets the full library.

## Automatic sync
Skills are also synced automatically on every `bigmac-sync push` and `bigmac-sync pull`.

## If you are Poke (.poke sandbox)
- Keep the sync focused on Turso + local workspace files under /vercel/sandbox/workspace.
- Do not assume bigmac-skills, knowledge-search, or macOS Keychain helpers exist in PATH.
- Prefer direct Turso HTTP or repo-file updates when sandbox wrappers are missing.
## Do this now
Run `bigmac-skills sync` to push all current local skills to Turso and
pull back any skills added by other agents.
