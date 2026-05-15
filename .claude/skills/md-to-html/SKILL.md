---
name: md-to-html
description: Convert one or more Markdown files to styled, professional HTML and open in browser. Same directory, .html extension, dark-blue #2c3e8c accent, white card on grey background, proper table/code styling. Multi-file runs include a cross-nav bar. Call via python3 or invoke the skill.
---

# /md-to-html — Markdown to Styled HTML

Convert `.md` files to clean, professional HTML and open in the default browser. Output lands alongside the source file (same directory, `.html` extension).

## Invocation

When user says "make viewable HTML versions", "open in browser", "convert to HTML", or similar:

```bash
python3 ~/.claude/skills/md-to-html/md_to_html.py file1.md [file2.md ...]
```

Multiple files: all get a shared cross-nav bar linking between them.

## What the script does

1. Auto-installs `markdown` pip package if missing
2. Converts using `markdown` extensions: `tables` + `fenced_code`
3. Writes sibling `.html` in same directory as source
4. Injects cross-nav bar when converting multiple files together
5. Opens all output files in default browser via `open` (macOS) or `xdg-open` (Linux)

## Style summary

| Property | Value |
|---|---|
| Background | `#f0f2f5` (light grey) |
| Card | White, `border-radius: 10px`, drop shadow |
| Max width | 860px centered |
| Header accent | `#2c3e8c` (dark blue) |
| Table header | `#2c3e8c` white text |
| Table stripe | `#f5f7ff` even rows |
| Code inline | `#eef0f8` bg, `#2d2d8a` text |
| Code block | `#1a1a2e` dark bg, light text |
| Print | nav hidden, no shadow |

## Script location

`~/.claude/skills/md-to-html/md_to_html.py`

---

## Platform notes

**Claude Code / OpenClaw (macOS):**
```bash
python3 ~/.claude/skills/md-to-html/md_to_html.py /path/to/file.md
```

**Gemini / Antigravity:**
Use `run_command` with the same invocation. `open` is macOS-native; substitute `xdg-open` on Linux.

**Codex / Grok:**
Call via terminal execution pipeline. If `open` unavailable, print paths for manual opening.

**Fallback (no pip):**
```bash
~/clawd/venv/bin/pip install markdown -q
~/clawd/venv/bin/python3 ~/.claude/skills/md-to-html/md_to_html.py file.md
```

---

## When to use this skill

- Any time the user asks to view markdown files in the browser
- Any time you've generated `.md` audit/report files and want to present them cleanly
- Any time you need to share analysis with a non-technical audience
- After generating multi-file report sets (audit directories, analysis packages)
