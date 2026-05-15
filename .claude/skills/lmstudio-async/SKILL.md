---
name: lmstudio-async
description: Route high-token, async, background tasks to LM Studio local Qwen model instead of Anthropic API — cost-free, speed-irrelevant workloads only.
---

> [!IMPORTANT]
> **Cross-Platform Skill**: This skill is shared across Claude Code, OpenClaw, Gemini, and Codex.
> Before executing, check the "Platform Blocks" below. If your current platform is missing, add a block detailing how your platform should execute it.

# lmstudio-async — Local Qwen via LM Studio for Background Tasks

Use LM Studio's locally-running Qwen model for any task that is:
- **High token count** (large context, bulk processing, long outputs)
- **Async / background** (spawned via `Bash run_in_background`, subagent, or cron)
- **Speed-irrelevant** (no user waiting on the result in real time)
- **Cost-sensitive** (avoid burning Anthropic API credits on non-critical work)

**Do NOT use for:** user-facing responses, anything requiring Claude's reasoning depth, tool use with complex chaining, or safety-critical decisions.

---

## LM Studio Config

| Key | Value |
|---|---|
| **OpenAI-compat** (multi-turn, preferred) | `POST http://localhost:1234/v1/chat/completions` |
| **Claude-compat** (Anthropic Messages API) | `POST http://localhost:1234/v1/messages` |
| **Native** (single-shot only) | `POST http://localhost:1234/api/v1/chat` |
| List models | `GET http://localhost:1234/v1/models` |
| Generation model | `qwen/qwen3.5-9b` (best available 8B-class Qwen for generation) |
| Embedding model | `text-embedding-hf_qwen_qwen3-embedding-8b` (do not use for generation) |

### API formats at a glance

```bash
# OpenAI-compat — use for multi-turn chat and scripts (messages array = proper history)
POST /v1/chat/completions
{"model":"...", "messages":[{"role":"system","content":"..."},{"role":"user","content":"..."}], "max_tokens":4096}
→ data["choices"][0]["message"]["content"]

# Claude-compat — use when code already targets Anthropic SDK format
POST /v1/messages
{"model":"...", "system":"...", "messages":[{"role":"user","content":"..."}], "max_tokens":4096}
headers: x-api-key: lm-studio, anthropic-version: 2023-06-01
→ data["content"][0]["text"]

# Native — simpler, single-shot only (no real history support)
POST /api/v1/chat
{"model":"...", "system_prompt":"...", "input":"...", "max_tokens":4096}
→ data["output"][0]["content"]   (data["output"] is a list of {type, content})
```

> **Note:** `text-embedding-hf_qwen_qwen3-embedding-8b` is embedding-only. For text generation, always use `qwen/qwen3.5-9b`.

---

## Trigger Conditions (use this skill when ALL are true)

1. The task will run in background / async (not blocking the user)
2. Token count is high (>4K input or >2K expected output)
3. Speed is not paramount (minutes-to-finish is acceptable)
4. No Claude-specific tools, tool_use blocks, or safety reasoning needed
5. LM Studio is running (`curl -s http://localhost:1234/v1/models` returns 200)

---

## Agentic Executor (model → code → run → open browser)

The model only generates text — it cannot execute commands itself. Use `lm-exec.py` to close that loop:

```bash
# Ask model to create something, auto-extract code, write files, open HTML in browser
python3 ~/clawd/scripts/lm-exec.py "create a hello world with unique images, open in my browser"

# Use a specific model
python3 ~/clawd/scripts/lm-exec.py --model "qwen3-space.agent.claude.uncensored-4b.gguf:2" "make a snake game"

# Preview what would be extracted without executing
python3 ~/clawd/scripts/lm-exec.py --dry-run "write a script that lists my files"
```

**What `lm-exec.py` does:**
1. Calls the model via `/api/v1/chat`
2. Extracts fenced code blocks by language tag (`html`, `python`, `bash`, `js`)
3. Writes each block to `~/clawd/data/lm-exec-TIMESTAMP/`
4. Executes: opens HTML in browser, runs bash/python/node directly
5. Saves raw response to `response.md` in the same directory

---

## Python Pattern (preferred — uses shared venv)

```python
#!/usr/bin/env python3
# Uses ~/clawd/venv/ — activate before running or call directly
import openai, sys

client = openai.OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio",
)

def lm_complete(prompt: str, system: str = "You are a helpful assistant.", max_tokens: int = 4096) -> str:
    resp = client.chat.completions.create(
        model="qwen/qwen3.5-9b",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content

if __name__ == "__main__":
    prompt = sys.stdin.read() if not sys.argv[1:] else " ".join(sys.argv[1:])
    print(lm_complete(prompt))
```

Save to `~/clawd/scripts/lm-complete.py` for reuse.

---

## Bash One-Liners (curl)

```bash
# OpenAI-compat (preferred — proper history, standard format)
LM_PROMPT="Summarize this in 3 bullets: ..."
curl -s http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"qwen/qwen3.5-9b\",\"messages\":[{\"role\":\"user\",\"content\":\"$LM_PROMPT\"}],\"max_tokens\":-1}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Claude-compat (Anthropic Messages API format)
curl -s http://localhost:1234/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: lm-studio" \
  -H "anthropic-version: 2023-06-01" \
  -d "{\"model\":\"qwen/qwen3.5-9b\",\"messages\":[{\"role\":\"user\",\"content\":\"$LM_PROMPT\"}],\"max_tokens\":-1}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['content'][0]['text'])"

# Native (single-shot, simpler payload)
curl -s http://localhost:1234/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"qwen/qwen3.5-9b\",\"system_prompt\":\"You are helpful.\",\"input\":\"$LM_PROMPT\",\"max_tokens\":-1}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(next(o['content'] for o in d['output'] if o['type']=='message'))"
```

---

## Background Subagent Pattern (Claude Code)

When spawning a background task that qualifies:

```
Bash(run_in_background=true):
  ~/clawd/venv/bin/python3 ~/clawd/scripts/lm-complete.py < input.txt > output.txt
```

Or use the `mcp__mcp-openai__openai_chat` tool with:
- `base_url`: `http://localhost:1234/v1`
- `api_key`: `lm-studio`
- `model`: `qwen/qwen3.5-9b`

---

## Health Check Before Use

Always verify LM Studio is running before routing:

```bash
curl -s http://localhost:1234/v1/models | python3 -c "
import sys, json
d = json.load(sys.stdin)
ids = [m['id'] for m in d.get('data', [])]
print('OK' if 'qwen/qwen3.5-9b' in ids else 'MODEL NOT LOADED — switch to Anthropic')
"
```

If LM Studio is down or the model isn't loaded, fall back to the Anthropic API transparently — never block or error.

---

## If you are Claude Code / OpenClaw

- Use `Bash(run_in_background=true)` to fire the script without blocking
- Use `~/clawd/venv/bin/python3` explicitly (not bare `python3`) to hit the shared venv
- Write output to `~/clawd/data/<task>-output.txt` (never `/tmp/`)
- Log completion to Turso via `todo done <id>` when the background task finishes

## If you are Gemini (Antigravity)

- Use `run_command` with `WaitMsBeforeAsync: 0` for fire-and-forget
- Same curl pattern works — Gemini has no venv constraint

## If you are Codex / OpenClaw (non-Claude)

- Use `exec` with `async: true`
- Same Python/curl pattern applies
