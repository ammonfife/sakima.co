---
name: agent-reach
description: Read live internet content (arbitrary web pages, RSS/Atom, YouTube transcripts, GitHub, Bilibili, V2EX) into clean Markdown for an agent, without per-platform scraping code. Use when a task needs the actual rendered content of a URL — including client-rendered SPAs, since the default web channel executes JS via a headless-browser-backed reader. Also covers Twitter/X, Reddit, Facebook, Instagram, Xiaohongshu, LinkedIn, and podcast transcription once those channels are configured with login/cookies (`agent-reach doctor` shows current channel status).
user-invocable: true
---

# agent-reach — read the internet into Markdown

Wraps `yt-dlp`, `feedparser`, Jina Reader, `gh`, `bili-cli`/Bilibili search API, and (once configured)
per-platform authenticated readers behind one CLI. Source: https://github.com/Panniantong/Agent-Reach
(NOT the same-named PyPI package by Jean Galea — that is a different, unrelated project; do not
`pip install agent-reach` from PyPI, it installs the wrong tool. Install from source, see below.)

## Install (already done on this machine, 2026-08-21)

```bash
git clone --depth 1 https://github.com/Panniantong/Agent-Reach.git ~/.local/opt/Agent-Reach
cd ~/.local/opt/Agent-Reach
pip3 install --user -e .
```

`~/.local/bin` is already on `$PATH` (`.zprofile`/`.bash_profile`), so `agent-reach` resolves in any
new shell on this machine. If a session reports `command not found`, check `pip3 show agent-reach` —
`Home-page` must read `github.com/Panniantong/Agent-Reach`; if it reads `github.com/jgalea/agent-reach`
you have the wrong package installed and must `pip3 uninstall -y agent-reach` then reinstall from
source as above.

## When to use

- Pulling the rendered content of a specific URL (marketing page, docs page, GitHub README) as clean
  Markdown instead of raw HTML.
- Verifying what a deployed page ACTUALLY renders (client-rendered React/Vue SPA included — the
  underlying Jina Reader backend runs a headless browser and waits for JS execution, so post-hydration
  UI text comes back, not an empty `<div id="root">`).
- RSS/Atom monitoring, YouTube transcript pulls, GitHub code/repo search (needs `gh` CLI authenticated),
  Bilibili search.
- NOT for: driving a UI (click/type/login), asserting test outcomes, anything needing JS execution
  results beyond static rendered text, or any platform not yet configured (see `doctor` output).

## Quick check

```bash
agent-reach doctor      # shows which of the 15 channels are usable right now, and how to unlock more
agent-reach --version
```

## Reading a URL (generic web channel, always available, zero config)

There is no `agent-reach read <url>` top-level CLI subcommand — the tool ships as importable channel
modules an agent calls directly (this is a skill/library, not a full standalone CLI product):

```python
import sys; sys.path.insert(0, "/Users/benfife/.local/opt/Agent-Reach")
from agent_reach.channels.web import WebChannel

ch = WebChannel()
content = ch.read("https://example.com")   # returns full page as Markdown (str)
```

Other channels live at `agent_reach/channels/{rss,youtube,github,bilibili,v2ex,twitter,reddit,...}.py`
— same `.read(...)` pattern, gated by `doctor` status.

## Unlocking more channels

Login-gated platforms (Twitter, Reddit, LinkedIn, Facebook, Instagram, Xiaohongshu) store
cookies/tokens in `~/.agent-reach/config.yaml` (chmod 600), populated interactively — tell the agent
"帮我装 <platform>" (or just ask it to configure that channel) and it walks you through login.

- GitHub: needs `gh` CLI installed + `gh auth login`.
- YouTube: needs a JS runtime configured for `yt-dlp` — `doctor` prints the exact one-liner if missing.
- Full-web semantic search: needs `mcporter` + Exa MCP —
  `mcporter config add exa https://mcp.exa.ai/mcp --scope home`.

## Making this available to the whole BigMac mesh

This file lives in `~/.claude/skills/agent-reach/`, one of the three `bigmac-skills` sync sources
(alongside `~/.openclaw/skills/` and `~/clawd/skills/`). Run `bigmac-skills push` (or `bigmac-skills
sync`) after any edit here so every Claude Code / OpenClaw / Gemini / Codex / Grok instance picks it
up on their next `bigmac-skills pull`. See `~/.claude/skills/bigmac-sync-skills/SKILL.md`.

## Known gotcha (hit 2026-08-21)

`pip install agent-reach` on PyPI resolves to a DIFFERENT project (`jgalea/agent-reach`, CLI verbs
`{list,install,remove,doctor,get,skill,cache}` — note NO `setup`/`configure`/`transcribe`/`watch`).
Always verify `pip3 show agent-reach` → Home-page before trusting a fresh install; prefer installing
from the git source directly (above) to avoid the ambiguity entirely.
