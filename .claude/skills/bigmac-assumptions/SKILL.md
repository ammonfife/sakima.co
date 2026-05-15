---
name: bigmac-assumptions
description: Track working assumptions with tags, agent tracking, date validity, and supersession chains. Identical schema to facts.
homepage: https://turso.tech/
metadata: { "moltbot": { "emoji": "🤔", "requires": { "bins": ["assumptions"] } } }
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


# bigmac-assumptions - Assumptions Tracker

Track working assumptions that underlie strategies, decisions, and operations. Assumptions can be tested, validated, or invalidated over time.

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
# Add assumption
assumptions add operational "Customers prefer simple UX" --tags genomic,ux,marketing

# List assumptions
assumptions list

# Search assumptions
assumptions search "customers"

# Tag/untag
assumptions tag 123 genomic urgent
assumptions untag 123 inbox

# Show details
assumptions show 123

# Mark as invalidated
assumptions tag 123 invalidated proven-false
assumptions deactivate 123
```

## Use Cases

### Marketing Assumptions

```bash
assumptions add operational "Email open rates correlate with send time" \
  --tags genomic,marketing,email --as-of 2026-02-06

assumptions add operational "Video ads outperform static" \
  --tags genomic,marketing,creative
```

### Product Assumptions

```bash
assumptions add operational "Users want dark mode" \
  --tags product,ux

assumptions add operational "Mobile-first design is essential" \
  --tags product,ux,development
```

### Business Assumptions

```bash
assumptions add operational "Multi-channel approach reduces CAC" \
  --tags genomic,marketing,strategy
```

## Testing & Validation

### Validate Assumption

```bash
# Mark as validated
assumptions tag 123 validated
assumptions add operational "Confirmed: Email timing matters (A/B test)" \
  --tags genomic,marketing,validated --supersedes 123
```

### Invalidate Assumption

```bash
# Mark as invalidated
assumptions tag 123 invalidated proven-false
assumptions deactivate 123

# Document what replaced it
assumptions add operational "New finding: Subject line matters more than timing" \
  --tags genomic,marketing,validated --supersedes 123
```

## Tag Taxonomy

### Domain Tags

Same as facts: `private`, `genomic`, `genomic-client-X`, `sakima`, etc.

### Lifecycle Tags

- `inbox` — Needs tagging
- `untested` — Assumption not yet validated
- `testing` — Currently running tests
- `validated` — Confirmed by data/testing
- `invalidated` — Proven false
- `superseded` — Replaced by new assumption
- `deprecated` — No longer relevant

### Type Tags

- `hypothesis` — Testable assumption
- `constraint` — Business/technical constraint
- `belief` — Working belief (less testable)

## Commands

Same as facts CLI:

```bash
assumptions add <category> "text" --tags tag1,tag2 --as-of YYYY-MM-DD
assumptions list [--tags X] [--all] [--agent X]
assumptions search "query" [--tags X]
assumptions tag <id> tag1 tag2
assumptions untag <id> tag1
assumptions show <id>
assumptions chain <id>
assumptions deactivate <id>
assumptions tags
assumptions rm <id>
```

## Integration with Facts

Assumptions should be tested and converted to facts when validated:

```bash
# Start with assumption
assumptions add operational "ROAS target 3x is achievable" \
  --tags genomic,marketing,hypothesis --as-of 2026-01-15

# Test it (run campaigns)

# If validated, convert to fact
facts add operational "ROAS target 3x (validated Q1 2026)" \
  --tags genomic,marketing,validated --as-of 2026-02-06

# Mark assumption as validated
assumptions tag 123 validated superseded
```

## Notes

- CLI: `/Users/benfife/clawd/scripts/bigmac-assumptions`
- Database: Turso `assumptions`, `assumptions_tags`, `assumptions_edits`, `assumptions_tag_changes`
- Schema: Identical to facts
- Shared globally across all agents
