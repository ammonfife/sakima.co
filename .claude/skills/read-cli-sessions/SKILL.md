---
name: read-cli-sessions
description: Read and monitor Claude Code CLI session transcripts from JSONL files. Use this skill whenever you need to see what a CLI session is doing, read its history, find a specific session by topic, or communicate with CLI agents. Triggers on any mention of CLI sessions, session transcripts, JSONL session files, checking on agents, monitoring sessions, or inter-session communication. Also use when asked to find what a CLI agent did, replay a session, or extract decisions/actions from past sessions.
---

# /read-cli-sessions

Read, search, and monitor Claude Code CLI session JSONL transcript files from Cowork or any agent context.

## Why this exists

Claude Code CLI sessions write their full conversation transcripts to JSONL files on disk. Each line is a JSON object representing a user message, assistant response, tool call, or system event. This skill gives any agent (especially Cowork, which runs outside the CLI session infrastructure) the ability to read those transcripts, find specific sessions, monitor active work, and extract useful context.

## Session file locations

```
~/.claude/projects/-Users-benfife/*.jsonl          # CLI sessions rooted at ~/
~/.claude/projects/-Users-benfife-github-*/*.jsonl  # CLI sessions in specific repos
```

Each session is a single `.jsonl` file named by its session UUID (e.g., `a95bf0e6-a74f-4753-b45e-57e3fc9b6109.jsonl`).

## JSONL line format

Each line is a JSON object. Key fields:

| Field | Description |
|-------|-------------|
| `type` | `user`, `assistant`, `system` |
| `message.role` | `user` or `assistant` |
| `message.content` | Text or array of content blocks (text, tool_use, tool_result) |
| `sessionId` | UUID matching the filename |
| `timestamp` | ISO 8601 |
| `uuid` | Unique message ID |
| `parentUuid` | Threading — which message this responds to |
| `cwd` | Working directory at time of message |
| `version` | Claude CLI version |
| `subtype` | For system messages: `stop_hook_summary`, etc. |

Assistant messages also have:
- `message.model` — model ID (e.g., `claude-opus-4-6`)
- `message.usage` — token counts (input, output, cache)
- `message.stop_reason` — `end_turn`, `tool_use`, etc.

Tool use appears as content blocks within `message.content`:
```json
{"type": "tool_use", "id": "toolu_...", "name": "Bash", "input": {"command": "..."}}
{"type": "tool_result", "tool_use_id": "toolu_...", "content": "..."}
```

## How to read sessions

### Find sessions by recency
```bash
ls -lt ~/.claude/projects/-Users-benfife/*.jsonl | head -5
```

### Read the tail of an active session (last N lines)
Use Desktop Commander `read_file` with negative offset:
```
read_file(path: "~/.claude/projects/-Users-benfife/<uuid>.jsonl", offset: -20)
```
Or use the Read tool (Cowork file tools) — count total lines first, then read with offset near the end.

### Search across sessions for a topic
```bash
grep -l "lkup" ~/.claude/projects/-Users-benfife/*.jsonl
grep -l "barcode" ~/.claude/projects/-Users-benfife/*.jsonl
```

### Extract just user messages from a session
```bash
grep '"type":"user"' <file>.jsonl | jq -r '.message.content' | head -20
```

### Extract assistant text responses
```bash
grep '"type":"assistant"' <file>.jsonl | jq -r '.message.content[] | select(.type=="text") | .text' 2>/dev/null | tail -20
```

### Get session metadata (model, version, start time)
```bash
head -3 <file>.jsonl | jq '{type, sessionId: .sessionId, version: .version, model: .message.model, timestamp}'
```

## Cowork ↔ CLI communication

Cowork and CLI sessions share the filesystem at `/Users/benfife/`. Communication channels:

1. **File drop**: Write to `~/cowork-inbox.md` (CLI reads) or `~/cli-outbox.md` (Cowork reads)
2. **JSONL reading**: Cowork reads CLI session transcripts directly from the JSONL files
3. **Turso memory**: Both sides read/write via `claude-sync push/pull` and shared memory files
4. **Terminal typing**: Cowork can type into Terminal windows via osascript

### Typing into a CLI session's Terminal window
```applescript
tell application "Terminal"
    repeat with w in windows
        if name of w contains "<search-term>" then
            do script "<message>" in selected tab of w
            return
        end if
    end repeat
end tell
```
This sends text as if typed — the CLI agent sees it as user input on its next turn.

## Cowork session list (via session_info MCP)

Cowork can also see sessions managed by the desktop app via `list_sessions` / `read_transcript`. These are separate from CLI Terminal sessions.

## Active session reference (update as discovered)

- `a95bf0e6-a74f-4753-b45e-57e3fc9b6109.jsonl` — Main lkup.info work session (16.6MB, Opus)
- `8adc09a0-*.jsonl` — Companion parallel session (134MB)

## CLI skills accessible from Cowork

All CLI skills live at `/Users/benfife/.claude/skills/` and are readable by Cowork via Desktop Commander or the Read tool:

| Skill | Path | Purpose |
|-------|------|---------|
| work-on-lkup | `~/.claude/skills/work-on-lkup/SKILL.md` | Meta-skill for lkup.info — architecture, DO-NOTs, gaps |
| price-coins | `~/.claude/skills/price-coins/SKILL.md` | Canonical pricing workflow |
| lift-module | `~/.claude/skills/lift-module/SKILL.md` | Python → TypeScript porting |
| audit-parity | `~/.claude/skills/audit-parity/SKILL.md` | Python ↔ TS parity audit |
| fix-stubs | `~/.claude/skills/fix-stubs/SKILL.md` | Phase 0 stub wiring |
| plan-validator | `~/.claude/skills/plan-validator/SKILL.md` | lkup-plan.json validation |
| lovable-deploy | `~/.claude/skills/lovable-deploy/SKILL.md` | Lovable publish automation |
| graphify | `~/.claude/skills/graphify/SKILL.md` | Knowledge graph builder |
| lift-and-constrain | `~/.claude/skills/lift-and-constrain/SKILL.md` | Inventory → nuance → test → canonical impl |
| lkup-plan-editor | `~/.claude/skills/lkup-plan-editor/SKILL.md` | Edit lkup-plan.json |
| resync-agents | `~/.claude/skills/resync-agents/SKILL.md` | Full BIGMAC agent resync |
| consolidate | `~/.claude/skills/consolidate/SKILL.md` | Phase-by-phase consolidation |
| use-e2b | `~/.claude/skills/use-e2b/SKILL.md` | E2B sandbox operations |
| desktop-control | `~/.claude/skills/desktop-control/SKILL.md` | Mac desktop automation |

To use a CLI skill from Cowork: read its SKILL.md via `Read` tool or Desktop Commander `read_file`, then follow its instructions using Cowork's available tools.

## Tips

- JSONL files can be huge (134MB+). Always use `tail`, `grep`, or offset-based reads — never load a full file into context.
- Active sessions write continuously. The tail of the file is the freshest content.
- `jq` is your friend for parsing. Chain `grep` to filter line types first, then pipe to `jq`.
- Session names (like "lkup.info bash session") are set in-memory by the CLI `/session-name` command and don't appear in the JSONL — search by content/topic instead.
