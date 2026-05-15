---
name: session-archive
description: Bundle all artifacts from any Claude/OpenClaw session into a dated archive directory. Triggers on "save session", "archive session", "export session", "save all session files", "package session", "bundle session artifacts", "save session files", "archive my session", "collect session artifacts", "--all --session --subagents" flags.
type: workflow
---

> [!IMPORTANT]
> **Cross-Platform Skill**: This skill is shared across Claude Code, OpenClaw, Gemini, and Codex.
> Before executing, check the "Platform Blocks" below. If your current platform is missing, or if a command fails due to your unique toolset, **UPDATE THIS SKILL** by adding an `If you are [Platform]...` block detailing how your platform should execute it.

### If you are Claude (Claude Code / OpenClaw)
- Use `Bash` for all shell operations.
- Use `Read` and `Write` tools for file I/O where appropriate.
- You can run the helper script directly: `bash ~/clawd/scripts/session-archive.sh [args]`
- For Turso queries, use the HTTP pipeline via `curl` or `turso db shell`.

### If you are Gemini (Antigravity / Google)
- Use `run_command` for shell operations.
- Translate `Bash` calls to `run_command` equivalents.
- The helper script at `~/clawd/scripts/session-archive.sh` is the fastest path.

### If you are Codex / Grok
- Use your terminal execution pipeline.
- Run `bash ~/clawd/scripts/session-archive.sh [args]` directly.

---

# session-archive — Session Artifact Bundler

Collect and bundle **all useful artifacts** from any session type into a dated archive directory at:
```
~/clawd/data/session-archives/{session-id}-{YYYY-MM-DD}/
```

Supports session types: **cli**, **cloud**, **cowork**, **desktop**, **dispatch**, **dcloud**, **openclaw**, **chat**.

---

## Invocation

```
session-archive [session-id] [--type cli|cloud|cowork|desktop|dispatch|dcloud|openclaw|chat]
                [--all] [--session] [--subagents] [--tmp] [--files] [--scripts]
                [--plans] [--memory] [--turso] [--git] [--network] [--history]
```

- If no `session-id` given, auto-detect current session.
- `--all` implies every flag below it.
- Flags can be combined freely.

### Flags reference

| Flag | What it collects |
|---|---|
| `--all` | Everything |
| `--session` | JSONL transcript + clean text extract |
| `--subagents` | Subagent JSONL files spawned during session |
| `--tmp` | /tmp artifacts — runs tmp-rescue.sh then sweeps rescued-from-tmp/ |
| `--files` | Files created/modified during session |
| `--scripts` | .sh, .py, .js, .ts, .mjs files touched |
| `--plans` | Plan/task .md files (matching plan/task/todo/PLAN/immutable-* in name) |
| `--memory` | Memory files written during session |
| `--turso` | Facts, todos, policies, sessions written to Turso in session window |
| `--git` | Git commits made across all repos during session time window |
| `--network` | Captured network log from capture-cloud-session |
| `--history` | Claude Code input history from `~/.claude/history.jsonl` filtered to session ID + time window |

---

## Session type → transcript location

```
cli:       ~/.claude/projects/-Users-benfife/{session-id}.jsonl
           ~/.claude/projects/*/{session-id}.jsonl  (search all projects)
subagents: ~/.claude/projects/-Users-benfife/{parent-id}/subagents/*.jsonl
cloud:     Run /capture-cloud-session skill first OR check:
           ~/clawd/data/session-{id}-transcript.txt
cowork:    ~/Library/Application Support/Claude/local-agent-mode-sessions/shared/{id}/
desktop:   ~/Library/Application Support/Claude/claude-code-sessions/{profile}/{id}.jsonl
openclaw:  ~/.openclaw/agents/{agent}/sessions/{id}.jsonl
dispatch:  ~/.claude/projects/-Users-benfife/{id}.jsonl  (same as cli)
dcloud:    ~/clawd/data/session-{id}-*.json  (captured events)
chat:      ~/clawd/data/session-{id}-transcript.txt  (if captured via scope)
```

---

## Archive structure

```
~/clawd/data/session-archives/{session-id}-{YYYY-MM-DD}/
├── README.md                        # session summary: type, time range, counts
├── transcript/
│   ├── {session-id}.jsonl           # raw JSONL
│   └── {session-id}-clean.txt       # conversation turns (user+assistant only)
├── subagents/
│   └── {subagent-id}.jsonl
├── files/                           # files created/modified (path-flattened)
│   └── {relative-path-flattened}    # e.g. github-ammonfife-lkup-src-pages-Coins.tsx
├── scripts/                         # .sh/.py/.js/.ts/.mjs touched
│   └── {script-name}
├── plans/                           # plan .md files
│   └── {plan-name}.md
├── memory/                          # memory files touched
│   └── {memory-file}.md
├── git/
│   └── commits.txt                  # git log --oneline per repo, session window
├── turso/
│   ├── facts.json
│   ├── todos.json
│   └── sessions.json
└── network/                         # if --network
    ├── events-page1.json
    └── transcript.txt
```

---

## Step-by-step agent instructions

### Step 0: Parse arguments

```
session-archive [session-id] [--type TYPE] [--all] [flag...]
```

- If no `session-id`, detect from `~/.claude/current-session-id` or most recent JSONL:
  ```bash
  ls -t ~/.claude/projects/-Users-benfife/*.jsonl 2>/dev/null | head -1
  ```
- If `--all` is set, enable every flag.
- If no flags at all, default to `--session --subagents --git --turso`.

### Step 1: Find and load transcript

Search these paths in order, first match wins:

```bash
# CLI / dispatch
find ~/.claude/projects -name "${SESSION_ID}.jsonl" 2>/dev/null | head -1

# Desktop / cowork
find "$HOME/Library/Application Support/Claude" -name "${SESSION_ID}.jsonl" 2>/dev/null | head -1

# OpenClaw
find ~/.openclaw/agents -name "${SESSION_ID}.jsonl" 2>/dev/null | head -1

# Cloud / chat (pre-captured text)
ls ~/clawd/data/session-${SESSION_ID}-transcript.txt 2>/dev/null
ls ~/clawd/data/session-${SESSION_ID}-*.json 2>/dev/null
```

Extract `SESSION_START` and `SESSION_END` from JSONL first/last `timestamp` fields:

```python
import json
lines = [l for l in open(jsonl_path) if l.strip()]
def get_ts(entry):
    return entry.get('timestamp') or entry.get('created_at') or ''
first = json.loads(lines[0])
last  = json.loads(lines[-1])
SESSION_START = get_ts(first)
SESSION_END   = get_ts(last)
```

For missing timestamps, use file mtime as `SESSION_END` and mtime minus `(file_size_bytes / 200)` seconds as `SESSION_START` heuristic.

### Step 2: Extract clean transcript

For JSONL sessions, write `transcript/{session-id}-clean.txt`:

```python
import json, textwrap

def extract_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                t = block.get('type','')
                if t == 'text':
                    parts.append(block.get('text',''))
                elif t == 'tool_use':
                    parts.append(f"[tool_use: {block.get('name','')}]")
                elif t == 'tool_result':
                    rc = block.get('content','')
                    parts.append(f"[tool_result: {str(rc)[:200]}]")
        return '\n'.join(parts)
    return str(content)

with open(clean_path, 'w') as out:
    for line in open(jsonl_path):
        e = json.loads(line)
        if e.get('type') not in ('user', 'assistant'):
            continue
        msg = e.get('message', {})
        role = msg.get('role', e.get('type',''))
        content = extract_content(msg.get('content', ''))
        if not content.strip():
            continue
        out.write(f"\n{'='*60}\n[{role.upper()}]\n{'='*60}\n{content}\n")
```

### Step 3: Find subagents (if --subagents)

```bash
# Subagents alongside parent in a subagents/ subdir
find ~/.claude/projects -path "*/${SESSION_ID}/subagents/*.jsonl" 2>/dev/null

# Subagents in top-level project dir named subagent-* or sub-session-*
find ~/.claude/projects -name "subagent-*.jsonl" -newer /tmp/.sa-start 2>/dev/null
find ~/.claude/projects -name "sub-session-*.jsonl" -newer /tmp/.sa-start 2>/dev/null
```

Copy each found file into `archive/subagents/`.

### Step 4: /tmp sweep (if --tmp)

```bash
~/clawd/scripts/hooks/tmp-rescue.sh 2>/dev/null || true

# Find rescued files newer than session start (use a touch marker)
touch -d "$SESSION_START" /tmp/.sa-start-marker 2>/dev/null || true
find ~/clawd/data/rescued-from-tmp -newer /tmp/.sa-start-marker -type f 2>/dev/null \
  | while read f; do
      cp "$f" "$ARCHIVE_DIR/files/tmp-rescued-$(basename $f)"
    done
```

### Step 5: Files modified during session (if --files or --scripts or --plans or --memory)

Create time-boundary marker files:
```bash
python3 -c "
import os, time
from datetime import datetime, timezone
for ts, path in [('$SESSION_START', '/tmp/.sa-start'), ('$SESSION_END', '/tmp/.sa-end')]:
    if ts:
        dt = datetime.fromisoformat(ts.replace('Z','+00:00'))
        os.utime(path, (dt.timestamp(), dt.timestamp()))
    else:
        open(path,'w').close()
" 2>/dev/null || touch /tmp/.sa-start /tmp/.sa-end
```

Find files by mtime:
```bash
find ~/github ~/clawd ~/.claude -newer /tmp/.sa-start -not -newer /tmp/.sa-end \
  -type f \
  -not -path "*/node_modules/*" \
  -not -path "*/.git/*" \
  -not -path "*/\.*" \
  2>/dev/null | head -200
```

For --scripts: filter to `.sh .py .js .ts .mjs .rb .go .rs` extensions.
For --plans: filter to files where `basename` matches `plan|task|todo|PLAN|immutable-|PLAN-`.
For --memory: filter to `memory/` paths or files matching `feedback_*|project_*|MEMORY.md|today.md`.

Copy matched files into the appropriate archive subdir, flattening paths:
```python
def flatten_path(src_path, home):
    rel = src_path.replace(home, '').lstrip('/')
    return rel.replace('/', '-')
```

### Step 6: Git commits in session window (if --git)

```bash
REPOS=$(find ~/github ~/clawd -maxdepth 4 -name ".git" -type d 2>/dev/null | sed 's|/.git$||' | sort -u)
for repo in $REPOS; do
    COMMITS=$(git -C "$repo" log --oneline \
        --after="$SESSION_START" --before="$SESSION_END" 2>/dev/null)
    if [ -n "$COMMITS" ]; then
        RNAME=$(basename "$repo")
        echo "=== $RNAME ===" >> "$ARCHIVE_DIR/git/commits.txt"
        echo "$COMMITS" >> "$ARCHIVE_DIR/git/commits.txt"
        echo "" >> "$ARCHIVE_DIR/git/commits.txt"
    fi
done
```

### Step 7: Turso artifacts (if --turso)

```bash
TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w 2>/dev/null)
TURSO_URL="https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline"

for TABLE in facts todos sessions; do
    curl -s "$TURSO_URL" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"requests\":[{\"type\":\"execute\",\"stmt\":{
            \"sql\":\"SELECT * FROM ${TABLE} WHERE created_at > ? AND created_at < ? LIMIT 200\",
            \"args\":[
              {\"type\":\"text\",\"value\":\"${SESSION_START}\"},
              {\"type\":\"text\",\"value\":\"${SESSION_END}\"}
            ]
          }}]}" \
      > "$ARCHIVE_DIR/turso/${TABLE}.json" 2>/dev/null
done
```

### Step 8: Network artifacts (if --network)

```bash
# Check for pre-captured cloud session data
find ~/clawd/data -name "session-${SESSION_ID}*" -o -name "session-events-*.json" \
  -newer /tmp/.sa-start -not -newer /tmp/.sa-end 2>/dev/null \
  | while read f; do
      cp "$f" "$ARCHIVE_DIR/network/"
    done
```

### Step 8b: Claude Code input history (if --history)

`~/.claude/history.jsonl` has 10,000+ entries, each timestamped with session ID:
```json
{"display":"git status","pastedContents":{},"timestamp":1778372618000,"project":"/path","sessionId":"uuid"}
```

Filter to this session and time window:

```python
import json, os

SESSION_ID = "<session_id>"
HIST_PATH = os.path.expanduser("~/.claude/history.jsonl")
ARCHIVE_HIST = f"{ARCHIVE_DIR}/history"
os.makedirs(ARCHIVE_HIST, exist_ok=True)

# Convert SESSION_START/END ISO to ms epoch for comparison
from datetime import datetime, timezone
start_ms = int(datetime.fromisoformat(SESSION_START.replace('Z','+00:00')).timestamp() * 1000)
end_ms   = int(datetime.fromisoformat(SESSION_END.replace('Z','+00:00')).timestamp() * 1000)

entries = []
with open(HIST_PATH) as f:
    for line in f:
        try:
            e = json.loads(line)
            ts = e.get('timestamp', 0)
            sid = e.get('sessionId', '')
            # Match by session ID OR by time window (catches renamed/compacted sessions)
            if sid == SESSION_ID or (start_ms <= ts <= end_ms):
                entries.append(e)
        except: pass

# Write readable history
with open(f"{ARCHIVE_HIST}/input-history.txt", 'w') as f:
    for e in entries:
        ts = datetime.fromtimestamp(e['timestamp']/1000, tz=timezone.utc).strftime('%H:%M:%S')
        f.write(f"[{ts}] {e.get('display','').strip()}\n")

# Write raw JSONL slice
with open(f"{ARCHIVE_HIST}/input-history.jsonl", 'w') as f:
    for e in entries:
        f.write(json.dumps(e) + '\n')

print(f"History: {len(entries)} entries → {ARCHIVE_HIST}/input-history.txt")
```

This captures every prompt, slash command, and multi-line input typed into Claude Code during the session — the "what the user typed" complement to the tool call "what Claude ran."

---

### Step 9: Write README.md

```markdown
# Session Archive: {session-id}

**Type:** cli | cloud | cowork | desktop | dispatch | dcloud | openclaw | chat
**Date:** YYYY-MM-DD
**Time range:** {SESSION_START} → {SESSION_END}
**Duration:** X hours Y minutes
**Archive path:** ~/clawd/data/session-archives/{session-id}-{YYYY-MM-DD}/

## Contents

| Artifact | Count |
|---|---|
| Transcript lines | N |
| Conversation turns | N |
| Subagent files | N |
| Files modified | N (across M repos) |
| Scripts | N |
| Plans | N |
| Memory files | N |
| Git commits | N (across M repos) |
| Turso facts | N |
| Turso todos | N |
| Turso sessions | N |
| /tmp rescued | N |
| Network events | N |

## Key topics (from first 3 user messages)

1. {first user message, truncated to 120 chars}
2. {second user message, truncated to 120 chars}
3. {third user message, truncated to 120 chars}

## Generated by

`session-archive` skill — BigMac BigMac {date}
```

### Step 10: Register archive in Turso

Write a fact so future agents can find this archive:

```bash
TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w 2>/dev/null)
FACT_CONTENT="session-archive: session ${SESSION_ID} archived to ~/clawd/data/session-archives/${SESSION_ID}-${TODAY}/ on ${TODAY}. Type: ${SESSION_TYPE}. Range: ${SESSION_START} to ${SESSION_END}."

curl -s "https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"requests\":[{\"type\":\"execute\",\"stmt\":{
        \"sql\":\"INSERT INTO facts (content, tags, agent_id, created_at) VALUES (?, ?, 'Claude', datetime('now'))\",
        \"args\":[
          {\"type\":\"text\",\"value\":\"${FACT_CONTENT}\"},
          {\"type\":\"text\",\"value\":\"session-archive,sessions\"}
        ]
      }}]}" > /dev/null 2>&1
```

### Step 11: Print summary table

Output to terminal:
```
Archive created: ~/clawd/data/session-archives/{session-id}-{YYYY-MM-DD}/
Session type:    cli
Time range:      2026-05-09T14:23:00Z → 2026-05-09T18:45:00Z (4h 22m)
──────────────────────────────────────────
  transcript/    1 file  (19,199 lines JSONL + clean.txt)
  subagents/     3 files
  files/         47 files
  scripts/       8 files
  git/           commits.txt (12 commits, 3 repos)
  turso/         facts.json (5), todos.json (3), sessions.json (1)
  memory/        4 files
──────────────────────────────────────────
Turso fact registered. Archive is findable via knowledge-search.
```

---

## Quick CLI usage (via helper script)

```bash
# Archive current session, everything
session-archive.sh --all

# Archive a specific session, transcripts + git only
session-archive.sh abc123def --session --git

# Archive a cloud session (must run capture-cloud-session first)
session-archive.sh 01YQDU3 --type cloud --all
```

---

## Helper script (canonical location: ~/clawd/scripts/session-archive.sh)

The full helper script is embedded below and also lives at `~/clawd/scripts/session-archive.sh`. The skill steps above are what the agent follows interactively; this script automates the same flow for CLI use.

```bash
#!/usr/bin/env bash
# session-archive.sh — Archive all artifacts from any BigMac session type
# Usage: session-archive.sh [session-id] [--type TYPE] [--all] [flag...]
# Canonical location: ~/clawd/scripts/session-archive.sh
# See: ~/.claude/skills/session-archive/SKILL.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE_ROOT="${HOME}/clawd/data/session-archives"
TODAY=$(date +%Y-%m-%d)
TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w 2>/dev/null || echo "")
TURSO_URL="https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline"

# ── Defaults ──────────────────────────────────────────────────────────────────
SESSION_ID=""
SESSION_TYPE="cli"
DO_SESSION=0 DO_SUBAGENTS=0 DO_TMP=0 DO_FILES=0
DO_SCRIPTS=0 DO_PLANS=0 DO_MEMORY=0 DO_TURSO=0 DO_GIT=0 DO_NETWORK=0

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --all)       DO_SESSION=1; DO_SUBAGENTS=1; DO_TMP=1; DO_FILES=1
                     DO_SCRIPTS=1; DO_PLANS=1; DO_MEMORY=1; DO_TURSO=1
                     DO_GIT=1; DO_NETWORK=1 ;;
        --session)   DO_SESSION=1 ;;
        --subagents) DO_SUBAGENTS=1 ;;
        --tmp)       DO_TMP=1 ;;
        --files)     DO_FILES=1 ;;
        --scripts)   DO_SCRIPTS=1 ;;
        --plans)     DO_PLANS=1 ;;
        --memory)    DO_MEMORY=1 ;;
        --turso)     DO_TURSO=1 ;;
        --git)       DO_GIT=1 ;;
        --network)   DO_NETWORK=1 ;;
        --type)      SESSION_TYPE="$2"; shift ;;
        --type=*)    SESSION_TYPE="${1#--type=}" ;;
        -*)          echo "Unknown flag: $1" >&2; exit 1 ;;
        *)           SESSION_ID="$1" ;;
    esac
    shift
done

# Default flags if none set
if [[ $((DO_SESSION+DO_SUBAGENTS+DO_TMP+DO_FILES+DO_SCRIPTS+DO_PLANS+DO_MEMORY+DO_TURSO+DO_GIT+DO_NETWORK)) -eq 0 ]]; then
    DO_SESSION=1; DO_SUBAGENTS=1; DO_GIT=1; DO_TURSO=1
fi

# ── Auto-detect session ID ────────────────────────────────────────────────────
if [[ -z "$SESSION_ID" ]]; then
    if [[ -f "${HOME}/.claude/current-session-id" ]]; then
        SESSION_ID=$(cat "${HOME}/.claude/current-session-id")
    else
        LATEST=$(ls -t "${HOME}/.claude/projects/-Users-benfife/"*.jsonl 2>/dev/null | head -1)
        if [[ -n "$LATEST" ]]; then
            SESSION_ID=$(basename "$LATEST" .jsonl)
        fi
    fi
fi

if [[ -z "$SESSION_ID" ]]; then
    echo "ERROR: Could not detect session ID. Pass one explicitly." >&2
    exit 1
fi

echo "Session ID: $SESSION_ID"
echo "Type: $SESSION_TYPE"

# ── Create archive directory ──────────────────────────────────────────────────
ARCHIVE_DIR="${ARCHIVE_ROOT}/${SESSION_ID}-${TODAY}"
mkdir -p "$ARCHIVE_DIR"/{transcript,subagents,files,scripts,plans,memory,git,turso,network}
echo "Archive dir: $ARCHIVE_DIR"

# ── Find transcript ───────────────────────────────────────────────────────────
JSONL_PATH=""
for candidate in \
    "${HOME}/.claude/projects/-Users-benfife/${SESSION_ID}.jsonl" \
    "${HOME}/.claude/projects/"*"/${SESSION_ID}.jsonl" \
    "${HOME}/Library/Application Support/Claude/claude-code-sessions/"*"/${SESSION_ID}.jsonl" \
    "${HOME}/Library/Application Support/Claude/local-agent-mode-sessions/shared/${SESSION_ID}/"*.jsonl \
    "${HOME}/.openclaw/agents/"*"/sessions/${SESSION_ID}.jsonl"; do
    for f in $candidate; do
        if [[ -f "$f" ]]; then
            JSONL_PATH="$f"
            break 2
        fi
    done
done

SESSION_START=""
SESSION_END=""

if [[ -n "$JSONL_PATH" ]]; then
    echo "Transcript: $JSONL_PATH"
    # Extract timestamps via Python
    read SESSION_START SESSION_END < <(python3 - "$JSONL_PATH" <<'PYEOF'
import json, sys
lines = [l for l in open(sys.argv[1]) if l.strip()]
def ts(e):
    return e.get('timestamp') or e.get('created_at') or ''
try:
    s = ts(json.loads(lines[0]))
    e = ts(json.loads(lines[-1]))
    # walk forward for first real timestamp
    for l in lines[:20]:
        t = ts(json.loads(l))
        if t:
            s = t
            break
    # walk backward for last real timestamp
    for l in reversed(lines[-20:]):
        t = ts(json.loads(l))
        if t:
            e = t
            break
    print(s, e)
except Exception as ex:
    print('', '')
PYEOF
    )
    echo "Session start: $SESSION_START"
    echo "Session end:   $SESSION_END"
else
    echo "WARNING: No JSONL transcript found for session $SESSION_ID"
    # Use "now" as end, 2 hours ago as start (fallback)
    SESSION_END=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    SESSION_START=$(date -u -v-2H +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d "-2 hours" +"%Y-%m-%dT%H:%M:%SZ")
fi

# Create time-boundary marker files for find -newer
python3 - "$SESSION_START" "$SESSION_END" <<'PYEOF' 2>/dev/null || true
import sys, os
from datetime import datetime, timezone
for arg, path in zip(sys.argv[1:], ['/tmp/.sa-start', '/tmp/.sa-end']):
    if arg:
        try:
            dt = datetime.fromisoformat(arg.replace('Z','+00:00'))
            os.utime(path, (dt.timestamp(), dt.timestamp()))
        except Exception:
            open(path, 'w').close()
    else:
        open(path, 'w').close()
PYEOF

# ── Step: Copy transcript (--session) ────────────────────────────────────────
TRANSCRIPT_LINES=0
CLEAN_TURNS=0

if [[ $DO_SESSION -eq 1 && -n "$JSONL_PATH" ]]; then
    cp "$JSONL_PATH" "$ARCHIVE_DIR/transcript/${SESSION_ID}.jsonl"
    TRANSCRIPT_LINES=$(wc -l < "$JSONL_PATH")

    # Extract clean conversation
    python3 - "$JSONL_PATH" "$ARCHIVE_DIR/transcript/${SESSION_ID}-clean.txt" <<'PYEOF'
import json, sys

def extract_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                parts.append(str(block))
                continue
            t = block.get('type', '')
            if t == 'text':
                parts.append(block.get('text', ''))
            elif t == 'tool_use':
                parts.append(f"[tool: {block.get('name','')} input={str(block.get('input',''))[:100]}]")
            elif t == 'tool_result':
                rc = block.get('content', '')
                parts.append(f"[tool_result: {str(rc)[:300]}]")
        return '\n'.join(p for p in parts if p)
    return str(content)

turns = 0
with open(sys.argv[2], 'w') as out:
    for line in open(sys.argv[1]):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get('type') not in ('user', 'assistant'):
            continue
        msg = e.get('message', {})
        role = msg.get('role', e.get('type', ''))
        content = extract_content(msg.get('content', ''))
        if not content.strip():
            continue
        ts = e.get('timestamp', '')
        out.write(f"\n{'='*60}\n[{role.upper()}] {ts}\n{'='*60}\n{content}\n")
        turns += 1
print(turns)
PYEOF
    CLEAN_TURNS=$(cat /tmp/.sa-clean-turns 2>/dev/null || echo "?")
    echo "  transcript: $TRANSCRIPT_LINES lines"

    # Check for cloud/network transcript
    for alt in \
        "${HOME}/clawd/data/session-${SESSION_ID}-transcript.txt" \
        "${HOME}/clawd/data/session-${SESSION_ID}-clean.txt"; do
        if [[ -f "$alt" ]]; then
            cp "$alt" "$ARCHIVE_DIR/transcript/"
        fi
    done
fi

# ── Step: Subagents (--subagents) ────────────────────────────────────────────
SUBAGENT_COUNT=0
if [[ $DO_SUBAGENTS -eq 1 ]]; then
    # Look in parent-session's subagents dir
    for sub in "${HOME}/.claude/projects/-Users-benfife/${SESSION_ID}/subagents/"*.jsonl \
               "${HOME}/.claude/projects/"*"/${SESSION_ID}/subagents/"*.jsonl; do
        if [[ -f "$sub" ]]; then
            cp "$sub" "$ARCHIVE_DIR/subagents/"
            (( SUBAGENT_COUNT++ )) || true
        fi
    done
    # Also find recent subagent-* files
    find "${HOME}/.claude/projects" -name "subagent-*.jsonl" -newer /tmp/.sa-start \
        ! -newer /tmp/.sa-end 2>/dev/null | while read f; do
        cp "$f" "$ARCHIVE_DIR/subagents/" 2>/dev/null || true
        (( SUBAGENT_COUNT++ )) || true
    done
    [[ $SUBAGENT_COUNT -gt 0 ]] && echo "  subagents: $SUBAGENT_COUNT files"
fi

# ── Step: /tmp rescue (--tmp) ─────────────────────────────────────────────────
TMP_COUNT=0
if [[ $DO_TMP -eq 1 ]]; then
    bash "${HOME}/clawd/scripts/hooks/tmp-rescue.sh" 2>/dev/null || true
    find "${HOME}/clawd/data/rescued-from-tmp" -newer /tmp/.sa-start \
        ! -newer /tmp/.sa-end -type f 2>/dev/null | while read f; do
        FNAME="tmp-rescued-$(basename "$f")"
        cp "$f" "$ARCHIVE_DIR/files/$FNAME" 2>/dev/null || true
        (( TMP_COUNT++ )) || true
    done
    [[ $TMP_COUNT -gt 0 ]] && echo "  tmp rescued: $TMP_COUNT files"
fi

# ── Step: Files / scripts / plans / memory ────────────────────────────────────
FILES_COUNT=0 SCRIPTS_COUNT=0 PLANS_COUNT=0 MEMORY_COUNT=0

if [[ $((DO_FILES+DO_SCRIPTS+DO_PLANS+DO_MEMORY)) -gt 0 ]]; then
    # Gather candidates from mtime window
    mapfile -t CANDIDATES < <(
        find "${HOME}/github" "${HOME}/clawd" "${HOME}/.claude" \
            -newer /tmp/.sa-start ! -newer /tmp/.sa-end -type f \
            ! -path "*/node_modules/*" ! -path "*/.git/*" \
            ! -path "*/\.*_versions/*" ! -name "*.pyc" \
            2>/dev/null | head -500
    )

    for f in "${CANDIDATES[@]}"; do
        BASE=$(basename "$f")
        EXT="${f##*.}"
        FLAT=$(echo "$f" | sed "s|${HOME}/||" | tr '/' '-')

        # --files: everything
        if [[ $DO_FILES -eq 1 && ! -d "$f" ]]; then
            cp "$f" "$ARCHIVE_DIR/files/$FLAT" 2>/dev/null || true
            (( FILES_COUNT++ )) || true
        fi

        # --scripts
        if [[ $DO_SCRIPTS -eq 1 ]] && echo "$EXT" | grep -qE "^(sh|py|js|ts|mjs|rb|go|rs)$"; then
            cp "$f" "$ARCHIVE_DIR/scripts/$BASE" 2>/dev/null || true
            (( SCRIPTS_COUNT++ )) || true
        fi

        # --plans
        if [[ $DO_PLANS -eq 1 ]] && echo "$BASE" | grep -qiE "^(plan|task|todo|PLAN|immutable-|PLAN-)"; then
            cp "$f" "$ARCHIVE_DIR/plans/$BASE" 2>/dev/null || true
            (( PLANS_COUNT++ )) || true
        fi

        # --memory
        if [[ $DO_MEMORY -eq 1 ]] && ( echo "$f" | grep -q "/memory/" || echo "$BASE" | grep -qE "^(feedback_|project_|MEMORY\.md|today\.md|yesterday\.md)" ); then
            cp "$f" "$ARCHIVE_DIR/memory/$BASE" 2>/dev/null || true
            (( MEMORY_COUNT++ )) || true
        fi
    done

    [[ $FILES_COUNT -gt 0 ]]   && echo "  files: $FILES_COUNT"
    [[ $SCRIPTS_COUNT -gt 0 ]] && echo "  scripts: $SCRIPTS_COUNT"
    [[ $PLANS_COUNT -gt 0 ]]   && echo "  plans: $PLANS_COUNT"
    [[ $MEMORY_COUNT -gt 0 ]]  && echo "  memory: $MEMORY_COUNT files"
fi

# ── Step: Git commits (--git) ─────────────────────────────────────────────────
GIT_COMMITS=0 GIT_REPOS=0

if [[ $DO_GIT -eq 1 ]]; then
    REPOS=$(find "${HOME}/github" "${HOME}/clawd" -maxdepth 4 -name ".git" -type d \
        2>/dev/null | sed 's|/.git$||' | sort -u)
    for repo in $REPOS; do
        if [[ -z "$SESSION_START" ]]; then continue; fi
        COMMITS=$(git -C "$repo" log --oneline \
            --after="$SESSION_START" --before="${SESSION_END:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}" \
            2>/dev/null || true)
        if [[ -n "$COMMITS" ]]; then
            RNAME=$(basename "$repo")
            {
                echo "=== $RNAME ==="
                echo "$COMMITS"
                echo ""
            } >> "$ARCHIVE_DIR/git/commits.txt"
            GIT_COMMITS=$(( GIT_COMMITS + $(echo "$COMMITS" | wc -l) ))
            (( GIT_REPOS++ )) || true
        fi
    done
    [[ $GIT_COMMITS -gt 0 ]] && echo "  git: $GIT_COMMITS commits across $GIT_REPOS repos"
fi

# ── Step: Turso artifacts (--turso) ──────────────────────────────────────────
TURSO_FACTS=0 TURSO_TODOS=0 TURSO_SESSIONS=0

if [[ $DO_TURSO -eq 1 && -n "$TOKEN" && -n "$SESSION_START" ]]; then
    for TABLE in facts todos sessions; do
        RESP=$(curl -s "$TURSO_URL" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"requests\":[{\"type\":\"execute\",\"stmt\":{
                    \"sql\":\"SELECT * FROM ${TABLE} WHERE created_at > ? AND created_at < ? LIMIT 200\",
                    \"args\":[
                        {\"type\":\"text\",\"value\":\"${SESSION_START}\"},
                        {\"type\":\"text\",\"value\":\"${SESSION_END:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}\"}
                    ]
                }}]}" 2>/dev/null || echo '{}')
        echo "$RESP" > "$ARCHIVE_DIR/turso/${TABLE}.json"
        COUNT=$(echo "$RESP" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    rows=d['results'][0]['response']['result']['rows']
    print(len(rows))
except: print(0)" 2>/dev/null || echo 0)
        case $TABLE in
            facts)    TURSO_FACTS=$COUNT ;;
            todos)    TURSO_TODOS=$COUNT ;;
            sessions) TURSO_SESSIONS=$COUNT ;;
        esac
    done
    echo "  turso: facts=$TURSO_FACTS todos=$TURSO_TODOS sessions=$TURSO_SESSIONS"
fi

# ── Step: Network artifacts (--network) ───────────────────────────────────────
NETWORK_COUNT=0
if [[ $DO_NETWORK -eq 1 ]]; then
    find "${HOME}/clawd/data" -name "session-${SESSION_ID}*" \
        -o -name "session-events-*.json" -newer /tmp/.sa-start ! -newer /tmp/.sa-end \
        2>/dev/null | while read f; do
        cp "$f" "$ARCHIVE_DIR/network/" 2>/dev/null || true
        (( NETWORK_COUNT++ )) || true
    done
    [[ $NETWORK_COUNT -gt 0 ]] && echo "  network: $NETWORK_COUNT files"
fi

# ── Step: Write README.md ─────────────────────────────────────────────────────
# Extract first 3 user messages for "key topics"
TOPICS=""
if [[ -n "$JSONL_PATH" ]]; then
    TOPICS=$(python3 - "$JSONL_PATH" <<'PYEOF' 2>/dev/null
import json, sys
n = 0
for line in open(sys.argv[1]):
    try:
        e = json.loads(line)
    except Exception:
        continue
    if e.get('type') != 'user':
        continue
    msg = e.get('message', {})
    if msg.get('role') != 'user':
        continue
    content = msg.get('content', '')
    if isinstance(content, list):
        content = ' '.join(b.get('text','') for b in content if isinstance(b,dict) and b.get('type')=='text')
    content = content.strip()
    if not content or content.startswith('<'):
        continue
    n += 1
    print(f"{n}. {content[:120]}")
    if n >= 3:
        break
PYEOF
    )
fi

# Calculate duration
DURATION_STR="unknown"
if [[ -n "$SESSION_START" && -n "$SESSION_END" ]]; then
    DURATION_STR=$(python3 - "$SESSION_START" "$SESSION_END" <<'PYEOF' 2>/dev/null
import sys
from datetime import datetime, timezone
try:
    fmt = lambda s: datetime.fromisoformat(s.replace('Z','+00:00'))
    s, e = fmt(sys.argv[1]), fmt(sys.argv[2])
    secs = int((e - s).total_seconds())
    h, m = divmod(secs // 60, 60)
    print(f"{h}h {m}m" if h else f"{m}m")
except Exception as ex:
    print('?')
PYEOF
    )
fi

cat > "$ARCHIVE_DIR/README.md" <<READMEEOF
# Session Archive: ${SESSION_ID}

**Type:** ${SESSION_TYPE}
**Date:** ${TODAY}
**Time range:** ${SESSION_START} → ${SESSION_END}
**Duration:** ${DURATION_STR}
**Archive path:** ${ARCHIVE_DIR}

## Contents

| Artifact | Count |
|---|---|
| Transcript lines | ${TRANSCRIPT_LINES} |
| Subagent files | ${SUBAGENT_COUNT} |
| Files modified | ${FILES_COUNT} |
| Scripts | ${SCRIPTS_COUNT} |
| Plans | ${PLANS_COUNT} |
| Memory files | ${MEMORY_COUNT} |
| Git commits | ${GIT_COMMITS} (${GIT_REPOS} repos) |
| Turso facts | ${TURSO_FACTS} |
| Turso todos | ${TURSO_TODOS} |
| Turso sessions | ${TURSO_SESSIONS} |
| /tmp rescued | ${TMP_COUNT} |
| Network files | ${NETWORK_COUNT} |

## Key topics (from first 3 user messages)

${TOPICS:-"(no user messages found)"}

## Generated by

\`session-archive\` skill — BigMac — ${TODAY}
READMEEOF

echo "  README.md written"

# ── Step: Register in Turso ───────────────────────────────────────────────────
if [[ -n "$TOKEN" ]]; then
    FACT_CONTENT="session-archive: session ${SESSION_ID} archived to ${ARCHIVE_DIR} on ${TODAY}. Type: ${SESSION_TYPE}. Range: ${SESSION_START} to ${SESSION_END}. Commits: ${GIT_COMMITS}. Turso facts: ${TURSO_FACTS}."
    curl -s "$TURSO_URL" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"requests\":[{\"type\":\"execute\",\"stmt\":{
                \"sql\":\"INSERT INTO facts (content, tags, agent_id, created_at) VALUES (?, 'session-archive,sessions', 'Claude', datetime('now'))\",
                \"args\":[{\"type\":\"text\",\"value\":\"$(echo "$FACT_CONTENT" | sed "s/'/\\''/g")\"}]
            }}]}" > /dev/null 2>&1 || true
    echo "  Turso fact registered"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Archive: $ARCHIVE_DIR"
echo "Type:    $SESSION_TYPE | Duration: $DURATION_STR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
du -sh "$ARCHIVE_DIR" 2>/dev/null | awk '{print "Total size: "$1}'
```

## Related skills

- `/session-upload` — upload the archive to Cloudflare R2 `bigmac-sessions` bucket for cross-machine access
