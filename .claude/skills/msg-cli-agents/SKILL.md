---
name: msg-cli-agents
description: Send messages to Claude Code CLI sessions via the .inbox file system (preferred) or Terminal osascript (fallback). Includes session ID signing and self-consumption guard. Use for inter-session coordination, task handoffs, and cross-agent communication.
user-invocable: true
---

# /msg-cli-agents

Send messages to other Claude Code CLI sessions. Two delivery methods: file-based inbox (preferred) and Terminal osascript (fallback).

## Method 1: Inbox file (preferred)

Messages go to `~/.claude/projects/-Users-benfife/.inbox`. All CLI sessions sharing this project directory will see them.

### How to send

```bash
# Get your session ID for signing
MYSESS=$(cat ~/.claude/sessions/$(ps -o ppid= -p $PPID 2>/dev/null | tr -d ' ').json 2>/dev/null | python3 -c 'import sys,json;print(json.load(sys.stdin).get("sessionId","unknown"))' 2>/dev/null)

# Send (append, don't overwrite — multiple messages may queue)
echo "[Session $MYSESS → <target>] <message>" >> ~/.claude/projects/-Users-benfife/.inbox
```

### How delivery works

1. **FileChanged hook** fires on `.inbox` write → `asyncRewake` wakes idle sessions
2. **PreToolUse hook** reads `.inbox` on every tool call
3. **Self-consumption guard**: if message contains the reader's own session ID, it's skipped
4. Consumed messages archived to `.read`, file deleted

### Message format

```
[Session <sender-id> → <target>] <body>
```

Target can be: a session ID prefix (e.g. `ce2788a9`), an agent name (e.g. `lance`), or `ALL OTHER SESSIONS`.

### Structured handoffs

```
[Session abc123 → def456] Task handoff: Fix CAC enrichment
Context: CAC URL changed from coins.cacg.us to cacgrading.com/cert/
Files touched: supabase/functions/scan/index.ts:1847
What's needed: Test with CAC cert 411660000074, verify enrichment returns description
```

## Method 2: Terminal osascript (fallback)

Direct keystroke injection into Terminal windows. Use when inbox method isn't sufficient (e.g., need to trigger immediate action in a mid-turn session).

### Find target session

```applescript
tell application "Terminal"
    set windowNames to {}
    repeat with w in windows
        set end of windowNames to (name of w as text)
    end repeat
    return windowNames
end tell
```

### Send message

```applescript
tell application "Terminal"
    repeat with w in windows
        if name of w contains "<keyword>" then
            do script "<your message>" in selected tab of w
            return "sent"
        end if
    end repeat
    return "window not found"
end tell
```

## Finding active sessions

```bash
# List active CLI sessions with PIDs
for f in ~/.claude/sessions/*.json; do
  PID=$(python3 -c "import json;print(json.load(open('$f'))['pid'])" 2>/dev/null)
  ps -p $PID -o pid= >/dev/null 2>&1 && cat "$f" | python3 -c "
import sys,json;d=json.load(sys.stdin);print(f'{d[\"sessionId\"][:8]} PID={d[\"pid\"]} cwd={d[\"cwd\"]}')"
done
```

## Timing

- **Inbox method**: Message persists until consumed. FileChanged hook rewakes idle sessions within seconds. Active sessions see it on next tool call.
- **osascript method**: Immediate if session is at input prompt. Queued if mid-turn. Lost if session is in a subprocess.

## Gotchas

- **Self-consumption**: Always include your session ID in the message body. The inbox hook skips messages containing the reader's own session ID.
- **Multiple concurrent sessions**: All sessions sharing `~/.claude/projects/-Users-benfife/` see the same `.inbox`. First non-self session to read it consumes it.
- **Gateway down**: `bigmac-msg` requires openclaw gateway (disabled since 2026-04-08). Use inbox method instead.
- **Quotes in osascript**: Escape double quotes or use single quotes in message body.
- **Long messages**: Terminal paste buffer ~4000 chars. For longer content, write to a temp file and reference it.
