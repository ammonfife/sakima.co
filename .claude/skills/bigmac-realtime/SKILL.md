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

- `session_uuid`: Your current unique session ID (derive via `~/bin/my-Codex-session-id` or platform equivalent).
- `agent_id`: Your identity (e.g., `gemini`, `claude_2`, `poke`).
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

## Platform Specifics

### If you are Gemini (Antigravity)
Run in the background and check `command_status` periodically:
```bash
# Launch
run_command(CommandLine: "/Users/benfife/bin/bigmac-realtime-agent \"$SID\" \"gemini\" \"lkup.info\" 3600")

# Check
command_status(CommandId: "...")
```

### If you are Claude (Claude Code / OpenClaw)
Run with `run_in_background: true`:
```bash
bigmac-realtime-agent $SID claude_2 lkup.info 3600
```

## Available Tables
Subscribable tables (Realtime enabled):
`todos`, `facts`, `policies`, `events`, `commits`, `agents`, `captains_log`, `session_inbox`, `messages`, `memory`, `insights`, `violations`, `branches`, `projects`, `opinions`, `assumptions`, `agent_sessions`, `agent_context`.

> [!NOTE]
> Supabase Realtime works on **tables**, not views. If you need to monitor a view, subscribe to the underlying source tables (e.g., `facts` + `todos`).
