---
name: model-change
description: "Full model switcher with all available aliases. Use instead of /model when you want to see the complete list: sonnet, sonnet[1m], opus, opus[1m], opusplan, opusplan[1m], haiku, claude-opus-4-7, and explicit version pins. Invoke with /model-change."
---

# /model-change — Full Model Switcher

Present the user with a numbered list of ALL available model aliases, let them pick, then switch using the built-in /model command.

## Available Models

| # | Alias | Resolves to | Best for |
|---|---|---|---|
| 1 | `sonnet[1m]` | claude-sonnet-4-6 (1M ctx) | **Default** — everyday coding, large codebases |
| 2 | `opus[1m]` | claude-opus-4-6 (1M ctx) | Hard problems, architecture, reasoning |
| 3 | `opusplan[1m]` | Opus for planning + Sonnet[1m] for execution | Planning-heavy sessions needing 1M context |
| 4 | `opusplan` | Opus for planning + Sonnet for execution | Planning-heavy sessions, normal context |
| 5 | `sonnet` | claude-sonnet-4-6 | Sonnet without 1M (faster startup) |
| 6 | `opus` | claude-opus-4-6 | Opus without 1M |
| 7 | `claude-opus-4-7` | claude-opus-4-7 (no 1M yet) | Latest Opus, normal context |
| 8 | `haiku` | claude-haiku-4-5 | Fastest, cheapest, quick answers |
| 9 | `claude-sonnet-4-6[1m]` | explicit version pin | Pin to exact Sonnet version |
| 10 | `claude-opus-4-6[1m]` | explicit version pin | Pin to exact Opus 4.6 version |
| 11 | `claude-haiku-4-5` | explicit version pin | Pin to exact Haiku version |

## Instructions

Use AskUserQuestion for a two-step interactive picker — do NOT show a text table.

### Step 1 — Pick tier (4 options)

```
question: "Which model tier?"
header: "Tier"
options:
  - label: "Sonnet"       description: "Everyday coding · fast · default"
  - label: "Opus"         description: "Hard problems · architecture · reasoning"
  - label: "Opusplan"     description: "Opus for planning + Sonnet for execution"
  - label: "Haiku"        description: "Fastest · cheapest · quick answers"
```

### Step 2 — Pick variant based on tier

**If Sonnet:**
```
options:
  - label: "sonnet[1m]"            description: "1M context · recommended"
  - label: "sonnet"                description: "200K context · faster startup"
  - label: "claude-sonnet-4-6[1m]" description: "Explicit version pin"
```

**If Opus:**
```
options:
  - label: "opus[1m]"            description: "1M context · Opus 4.6"
  - label: "opus"                description: "200K context · Opus 4.6"
  - label: "claude-opus-4-7"     description: "Latest Opus · no 1M yet"
  - label: "claude-opus-4-6[1m]" description: "Explicit version pin"
```

**If Opusplan:**
```
options:
  - label: "opusplan[1m]" description: "Opus planning + Sonnet[1m] execution · 1M ctx"
  - label: "opusplan"     description: "Opus planning + Sonnet execution · 200K ctx"
```

**If Haiku:**
```
options:
  - label: "haiku"            description: "Haiku 4.5 · alias"
  - label: "claude-haiku-4-5" description: "Explicit version pin"
```

### Step 3 — Output the switch command

After the user picks, display:

> **Type in the prompt to switch:**
> `/model <chosen-alias>`

Skills cannot invoke built-in CLI commands — the user must type it. To also persist across sessions, write `"model": "<alias>"` to `~/.claude/settings.json`.
