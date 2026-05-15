---
name: bigmac-todo
description: Manage todos in shared Turso database with assignment, filtering, and completion tracking.
homepage: https://turso.tech/
metadata: {"moltbot":{"emoji":"✅","requires":{"bins":["todo"]}}}
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


# bigmac-todo - Shared Todo Management

Manage todos in Turso database. Shared across all BIGMAC agents.

## Commands

```bash
# Add a new todo
todo add "Task description"
todo add "Task description" --assign steve

# List todos
todo list                  # All open todos
todo list --mine          # Assigned to current agent
todo list --agent steve   # Assigned to Steve
todo list --all           # Include completed

# Complete a todo
todo done <id>

# Assign/unassign
todo assign <id> <agent>
todo unassign <id>
```

## Examples

```bash
# Create todos
todo add "Review Gemini API integration"
todo add "Test E2B sandbox spawning" --assign garcia
todo add "Update MEMORY.md with findings"

# Check your assignments
todo list --mine

# Check what Steve is working on
todo list --agent steve

# Complete a task
todo done 42
```

## Todo Fields

- `id` — Auto-incremented unique ID
- `text` — Task description
- `assigned_to` — Agent name (optional)
- `completed` — 0 (open) or 1 (done)
- `created_at` — Timestamp
- `completed_at` — Timestamp (when marked done)

## Coordination

Use for:
- Delegating tasks between agents
- Tracking work across the system
- Coordinating multi-agent workflows
- Avoiding duplicate work

Don't use for:
- Personal notes (use `memory/*.md`)
- Ephemeral reminders (use `HEARTBEAT.md`)
- Private tasks (use local files)

## Notes

- CLI located at: `/Users/benfife/clawd/scripts/bigmac-todo`
- Database: Turso `todos` table
- Shared globally across all agents
- Auto-detects current agent from directory
