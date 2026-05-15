---
name: bigmac-opinions
description: Track opinions, theories, and paradigms with tags, agent tracking, date validity, and supersession chains. Identical schema to facts.
homepage: https://turso.tech/
metadata: { "moltbot": { "emoji": "💭", "requires": { "bins": ["opinions"] } } }
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


# bigmac-opinions - Opinions, Theories & Paradigms

Track subjective opinions, working theories, mental models, and paradigm shifts. Separate from facts (objective) and assumptions (testable).

## Schema

Identical to facts table structure:

- Multi-tagging (many-to-many)
- Agent tracking (created_by, updated_by, tag added_by)
- Date validity (as_of_date, inactive_date, valid_until)
- Supersession chains (bidirectional: supersedes ↔ superseded_by)
- Full audit history
- Active/inactive status

## Quick Start

```bash
# Add opinion
opinions add operational "Multi-channel is key to growth" --tags genomic,marketing,theory

# List opinions
opinions list

# Search opinions
opinions search "growth"

# Tag/untag
opinions tag 123 paradigm genomic
opinions untag 123 inbox

# Show details
opinions show 123

# Update when thinking evolves
opinions add operational "Integrated attribution is the real key" \
  --tags genomic,marketing,paradigm --supersedes 123
```

## Use Cases

### Marketing Theories

```bash
opinions add operational "Brand awareness drives long-term revenue" \
  --tags genomic,marketing,theory

opinions add operational "Performance Max is superior to Search" \
  --tags genomic,marketing,platform-opinion
```

### Strategic Opinions

```bash
opinions add operational "AI will disrupt paid media in 2026" \
  --tags marketing,prediction,ai

opinions add operational "Privacy-first targeting is the future" \
  --tags genomic,marketing,paradigm
```

### Mental Models

```bash
opinions add operational "Customer journey is non-linear" \
  --tags genomic,marketing,mental-model

opinions add operational "Data beats intuition every time" \
  --tags genomic,philosophy,mental-model
```

## Opinion vs Fact vs Assumption

### Facts

Objective, verifiable, data-backed:

- "ROAS was 3x in Q1 2026"
- "Email deliverability improved 14%"
- "Client X uses Google Ads"

### Assumptions

Testable hypotheses, working beliefs:

- "Customers prefer simple interfaces" (testable)
- "Email timing affects open rates" (testable)
- "Video ads outperform static" (testable)

### Opinions

Subjective interpretations, theories, paradigms:

- "Multi-channel is key to growth" (strategic opinion)
- "Brand awareness drives long-term value" (theory)
- "Privacy-first is the future" (prediction/paradigm)

## Tag Taxonomy

### Domain Tags

Same as facts: `private`, `genomic`, `genomic-client-X`, `sakima`, etc.

### Lifecycle Tags

- `inbox` — Needs tagging
- `working-theory` — Current thinking
- `evolving` — Opinion in flux
- `confident` — High confidence
- `speculative` — Low confidence
- `superseded` — Thinking has changed
- `deprecated` — No longer hold this view

### Type Tags

- `theory` — Explanatory framework
- `paradigm` — Mental model/worldview
- `prediction` — Future-oriented opinion
- `principle` — Guiding principle
- `philosophy` — Core belief
- `mental-model` — How things work
- `strategy` — Strategic opinion
- `platform-opinion` — Opinion about tools/platforms

## Tracking Paradigm Shifts

```bash
# Old thinking (2025)
opinions add operational "Google Search is the core channel" \
  --tags genomic,marketing,paradigm --as-of 2025-01-15

# Paradigm shift (2026)
opinions add operational "Multi-platform orchestration is the new core" \
  --tags genomic,marketing,paradigm,shift --supersedes 123 --as-of 2026-02-06

# View evolution
opinions chain 123
```

## Confidence Tracking

Use confidence field (0.0-1.0):

```bash
# High confidence
opinions add operational "Privacy regulations will tighten" \
  --tags marketing,prediction --confidence 0.9

# Speculative
opinions add operational "Quantum computing will disrupt ads" \
  --tags marketing,prediction,speculative --confidence 0.3
```

## Commands

Same as facts CLI:

```bash
opinions add <category> "text" --tags tag1,tag2 --as-of YYYY-MM-DD
opinions list [--tags X] [--all] [--agent X]
opinions search "query" [--tags X]
opinions tag <id> tag1 tag2
opinions untag <id> tag1
opinions show <id>
opinions chain <id>
opinions deactivate <id>
opinions tags
opinions rm <id>
```

## Integration

### Opinion → Assumption → Fact Pipeline

```bash
# 1. Start with opinion/theory
opinions add operational "Multi-channel reduces CAC" \
  --tags genomic,marketing,theory

# 2. Convert to testable assumption
assumptions add operational "Multi-channel reduces CAC by 20%" \
  --tags genomic,marketing,hypothesis

# 3. Test it (run campaigns)

# 4. If validated, promote to fact
facts add operational "Multi-channel reduced CAC 23% (Q1 2026)" \
  --tags genomic,marketing,validated
```

## Notes

- CLI: `/Users/benfife/clawd/scripts/bigmac-opinions`
- Database: Turso `opinions`, `opinions_tags`, `opinions_edits`, `opinions_tag_changes`
- Schema: Identical to facts and assumptions
- Shared globally across all agents
- Use for subjective thinking, not objective data
