---
name: bigmac-sync
description: Sync agent workspace files (SOUL.md, MEMORY.md, memory/*.md) to/from Turso database with versioning.
homepage: https://turso.tech/
metadata: {"moltbot":{"emoji":"🔄","requires":{"bins":["bigmac-sync"]}}}
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

### If you are Poke (.poke sandbox)
- Set BIGMAC_WORKSPACE to /vercel/sandbox/workspace when that checkout is mounted there.
- Do not rely on macOS Keychain; read TURSO_AUTH_TOKEN and TURSO_DATABASE_URL from the sandbox environment or an injected env file.
- If security or other external binaries are missing, treat that as an environment limitation and use direct Turso HTTP calls instead of shell fallbacks.
- If agent-context.mjs is absent, do not swallow the failure; surface it so AGENT_CONTEXT generation can be patched.

# bigmac-sync - Turso Workspace Sync

Sync agent workspace files to/from Turso database with automatic versioning.

## Commands

```bash
# Pull latest from Turso (run at session start)
bigmac-sync pull

# Push changes to Turso (run after any file edit)
bigmac-sync push

# Check sync status
bigmac-sync status
```

## Auto-detection

- Detects `agent_id` from current directory
- Syncs agent-namespaced files only
- Secrets, facts, todos are GLOBAL (shared across all agents)

## Synced Files

**Agent-namespaced:**
- `SOUL.md`, `IDENTITY.md`, `USER.md`, `MEMORY.md`
- `AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`
- `memory/*.md` (daily logs)
- `memory/reference/*.md` (reference docs)

**Global (all agents):**
- Secrets (via `secrets` CLI)
- Facts (via `facts` CLI)
- Todos (via `todo` CLI)

## Versioning

- Automatic snapshots before push
- Keeps 4 versions from last 24h
- Keeps 1 daily snapshot for older files
- Stored in `.versions/` directory

## Workflow

```bash
# Session start
cd ~/clawd/agents/steve
bigmac-sync pull  # Get latest

# Do work, edit files
echo "Fixed API bug" >> memory/$(date +%Y-%m-%d).md
bigmac-sync push  # Save to Turso

# Edit MEMORY.md
echo "## Lessons\n- Always check logs" >> MEMORY.md
bigmac-sync push  # Save to Turso
```

## Rules

1. **Always pull at session start**
2. **Always push after file edits**
3. **Don't ask permission** — auto-sync
4. **Commit to git before push** (auto-handled)

## Configuration

- Database: `libsql://bigmac-ammonfife.aws-us-west-2.turso.io`
- Token: Keychain `turso-bigmac-token` (account: `bigmac`)
- Tables: `soul`, `memory`, `facts`, `machines`, `todos`, `secrets`

## Notes

- Located at: `/Users/benfife/clawd/scripts/bigmac-sync`
- Requires Turso token in keychain
- Auto-commits to git before push
- Skips unchanged files (hash-based)
