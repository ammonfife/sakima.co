---
name: bigmac-realtime
description: Cross-platform realtime event subscriber. Bridges Turso (durable) with Supabase (ephemeral notifications) and filesystem .inbox files.
---

# bigmac-realtime - Cross-Agent Notification Bridge

Use `bigmac-realtime-agent` to receive "pushed" notifications from other agents, project updates, or global system events without polling the database.

## Usage

```bash
# Basic: listen for your agent's events in the current project
bigmac-realtime-agent <session_uuid> <agent_id> [project_tag] [timeout_sec]

# Advanced: subscribe to specific tables (overrides defaults)
bigmac-realtime-agent <session_uuid> <agent_id> [project_tag] [timeout_sec] "facts,todos,messages"
```

### Parameters

- `session_uuid`: Your current unique session ID (derive via `~/bin/my-claude-session-id` or platform equivalent).
- `agent_id`: Your identity (e.g., `gemini`, `claude`, `poke`). Also set via `BIGMAC_AGENT` env var.
- `project_tag`: (Optional) Filter for a specific project (e.g., `lkup.info`, `heimdall`).
- `timeout_sec`: (Optional) How long to wait for an event (default 300, max 7200).
- `tables`: (Optional) Comma-separated list of tables to subscribe to.

## Behavior

1. **Long-Polling Background Task**: Must be run via background execution tools (e.g., Gemini's `run_command` or Claude's `Bash run_in_background`).
2. **Batching**: Once a relevant event is detected, the agent waits 10 seconds to catch further changes, then prints a JSON summary and exits.
3. **Relevance Filtering**:
   - **Direct Messages**: Rows in `messages` where `to_agent === AGENT_ID`.
   - **Session Inbox**: Rows in `session_inbox` matching your `SESSION_ID`.
   - **Project Scope**: Facts, Todos, Policies, Memory, and Commits tagged with your `project_tag`.
   - **Global**: All `captains_log` and `violations` updates.
4. **Platform-Agile Inbox**: Automatically watches `.inbox` files across Claude, Gemini, Codex, and OpenClaw projects.

## Platform Auto-Detection (2026-05-19)

The agent automatically detects the running platform and logs `[platform=X agent=Y]` on startup. Override with env vars.

| Detected Platform | Trigger |
|---|---|
| `codex` | `CODEX_SESSION_ID` or `CODEX_WORKSPACE` env var |
| `devin` | `DEVIN_SESSION_ID` or `DEVIN_RUN_ID` env var |
| `e2b` | `E2B_SANDBOX_ID` env var or `/home/user/clawd` exists |
| `gemini` | `GEMINI_SESSION_ID` env var |
| `claude-code-local` | `~/.claude` + `~/bigmac-state` both exist (local Mac) |
| `claude-code` | `~/.claude` exists, no bigmac-state |
| `unknown` | None of the above |

Override: `BIGMAC_PLATFORM=codex BIGMAC_AGENT=my-agent bigmac-realtime-agent ...`

## Credential Chain (Automatic)

Creds resolved in this order — no setup needed on local Mac, env vars sufficient on remote:

1. `BIGMAC_SUPABASE_SERVICE_KEY` env var
2. `SUPABASE_SERVICE_ROLE_KEY` env var (alias)
3. `BIGMAC_KEY` env var (short alias)
4. macOS keychain: `bigmac_supabase_service_role_key` → `supabase_lkup_service_role_key` → anon keys (local-mac only)
5. Turso secrets table (if `TURSO_AUTH_TOKEN` + `TURSO_DATABASE_URL` set — works in any sandbox)

## Platform-Specific Usage

### Local Mac (Claude Code)
```bash
# Runs automatically via session-start.sh hook (since 2026-05-19)
# Manual launch:
MY_SID=$(~/bin/my-claude-session-id)
bigmac-realtime-agent "$MY_SID" "claude" "lkup.info" 7200 \
  > ~/.claude/projects/-Users-benfife/.realtime-events.json &
```

### Gemini (Antigravity)
```bash
# Launch via run_command (Gemini-native background exec)
run_command(CommandLine: "bigmac-realtime-agent \"$SID\" \"gemini\" \"lkup.info\" 3600")
command_status(CommandId: "...")
```

### Codex / Devin (remote sandbox)
```bash
# Set creds in sandbox bootstrap, then run normally:
export BIGMAC_SUPABASE_SERVICE_KEY="eyJ..."  # from Turso secrets or provided
bigmac-realtime-agent "$SID" "codex" "lkup.info" 3600
```

### E2B Sandbox
```bash
# E2B has full internet + TURSO_AUTH_TOKEN set:
export TURSO_AUTH_TOKEN="..."
export TURSO_DATABASE_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
bigmac-realtime-agent "$E2B_SESSION_ID" "e2b" "" 3600  # auto-fetches key from Turso
```

## Hook Integration (2026-05-19)

`bigmac-realtime-agent` is now wired into two Claude Code hooks in `bigmac-state/scripts/hooks/`:

- **`session-start.sh`**: Launches agent at session start, output → `.realtime-events.json`. **Events are AWARENESS ONLY** — do not act without explicit instruction from Ben.
- **`postcompact-hook.sh`**: Re-subscribes after context compaction (compaction kills all background processes).

Events file: `~/.claude/projects/-Users-benfife/.realtime-events.json`

## Available Tables

Subscribable tables (Realtime enabled):
`todos`, `facts`, `policies`, `events`, `commits`, `agents`, `captains_log`, `session_inbox`, `messages`, `memory`, `insights`, `violations`, `branches`, `projects`, `opinions`, `assumptions`, `agent_sessions`, `agent_context`, `extension_config`.

> [!NOTE]
> Supabase Realtime works on **tables**, not views. Subscribe to source tables, not views.

## Troubleshooting

### 401 Unauthorized
- Service role key expired or project ID mismatch.
- Fix: update keychain entry or set `BIGMAC_SUPABASE_SERVICE_KEY`.

### No Events Received
- Incorrect `project_tag` filtering too strictly.
- Fix: run without project tag to see global firehose: `bigmac-realtime-agent $SID $AGENT "" 60`

### Inbox Not Processed
- The agent must be **running** when inbox is written — starting it after is a race.
- Fix: ensure session-start hook runs first, or use `sessions_send` which handles timing.

### Agent Stalled
- Use `run_in_background: true` (Claude) or `run_command` (Gemini).

## Poke Ecosystem (M, Mog, Poke) — 2026-05-19

Three cloud agents with distinct roles, all subscribable via this agent:

| Agent | Email / Alias | Phone | MCP Token Key | Scope | Role |
|---|---|---|---|---|---|
| **Poke** | poke@gptagency.ai | +16504336288 | mcp_token_poke_main | admin | Full BIGMAC surface + iMessage bridge. NOT Bob. Spawns any subagent. |
| **M** | m@gptagency.ai / m.poke@gptagency.ai | +16502835397 | mcp_token_poke_m | admin | Main orchestrator (BigMac M persona). High-level cross-project. |
| **Mog** | mog@gptagency.ai / mog.poke@gptagency.ai | +16502488932 | mcp_token_poke_mog | limited | Field executor, all BIGMAC + personal projects, cloud-only. |

### Usage in Poke repo / cloud env

```bash
# M (orchestrator)
MCP_AGENT_ID=m bigmac-realtime-agent "$SID" "m" "lkup.info" 7200

# Mog (field executor)
MCP_AGENT_ID=mog bigmac-realtime-agent "$SID" "mog" "lkup.info" 7200

# Poke (GM/bridge)
MCP_AGENT_ID=poke bigmac-realtime-agent "$SID" "poke" "" 7200
```

Identity is auto-detected from env vars and shown on startup:
```
🚀 Connecting to: ... [platform=poke-cloud agent=poke scope=admin role="GM + iMessage/SMS bridge + sysadmin"]
```

### Inbox paths watched (includes Poke-specific)
- `/app/poke/.inbox`
- `/app/mog/.inbox`
- `/app/m/.inbox`
- `~/.poke/.inbox`
- `$BIGMAC_INBOX_DIR/.inbox` (set this in cloud env for session-specific)

### Credential setup for Poke cloud env
```bash
# Option A: env var (simplest)
export BIGMAC_SUPABASE_SERVICE_KEY="eyJ..."  # from Turso or provided at deploy

# Option B: Turso secrets (if Turso access available)
export TURSO_AUTH_TOKEN="..."
export TURSO_DATABASE_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
# Agent auto-fetches BIGMAC key from Turso secrets table
```
