---
name: claude-view
description: "View and inspect Claude Code session JSONL files. Use when the user wants to look at past Claude Code sessions, transcripts, or replay a conversation."
---

# claude-view

View Claude Code session transcripts stored as JSONL files under `~/.claude/projects/`.

## Usage

Each session is a directory under `~/.claude/projects/<project-slug>/<session-uuid>/`. The transcript lives in JSONL form — one JSON object per turn.

```bash
# List sessions for current project
ls -lht ~/.claude/projects/-Users-benfife*/sessions/ | head

# Read a session
cat ~/.claude/projects/<slug>/<session>.jsonl | jq -s '.[] | {ts:.timestamp, role:.message.role, text:.message.content[0].text}'
```

## Notes
- Session JSONL is append-only; latest turn is at the bottom.
- Tool results live in `tool-results/<id>.txt` adjacent to the JSONL.
