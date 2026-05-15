---
name: bigmac-facts
description: Tag-based fact management with full history, agent tracking, and date validity. Supports supersession chains and lifecycle management.
homepage: https://turso.tech/
metadata: { "moltbot": { "emoji": "📚", "requires": { "bins": ["facts"] } } }
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


# bigmac-facts - Tag-Based Knowledge System

Store and search knowledge with tags, date validity, agent tracking, and full history.

## Quick Start

```bash
# Add a fact
facts add operational "ROAS target 3x" --tags genomic,marketing --as-of 2026-02-06

# List facts (defaults to your agent's active facts)
facts list

# Search facts
facts search "ROAS"

# Show detailed info
facts show 123

# Tag/untag facts
facts tag 123 urgent
facts untag 123 inbox
```

## Core Commands

### Add Facts

```bash
# Basic (defaults to today, tags as 'inbox')
facts add operational "New fact"

# With tags and date
facts add operational "ROAS target 3x" --tags genomic,marketing --as-of 2026-02-06

# With expiration date
facts add operational "20% promo" --tags genomic-client-acme --valid-until 2026-03-31

# Supersede old fact
facts add operational "Updated ROAS 3.5x" --tags genomic --supersedes 123
```

### List & Search

```bash
# List (defaults to current agent's active facts, newest first)
facts list
facts list --tags inbox                    # Facts needing tagging
facts list --tags genomic                  # Genomic facts
facts list --all                           # All agents, all facts
facts list --inactive-only                 # Only superseded/deactivated facts
facts list --stale-days 90                 # Facts older than 90 days
facts list --expiring-days 30              # Expiring in next 30 days

# Search (defaults to current agent's active facts)
facts search "ROAS"
facts search "ROAS" --tags genomic         # Search within tags
facts search "ROAS" --all                  # Search all agents
facts search "ROAS" --exclude-tags deprecated,proven-false
facts search "client" --valid-on 2026-01-15  # What was valid on date?
```

### Tagging

```bash
# Add tags
facts tag 123 genomic marketing urgent

# Remove tags
facts untag 123 inbox urgent

# List all tags in use
facts tags
```

### Fact Details

```bash
# Show full details
facts show 123

# Show supersession chain
facts chain 123

# Deactivate (mark inactive)
facts deactivate 123
```

### Maintenance

```bash
# Auto-expire facts past valid_until date
facts auto-expire

# Remove a fact (permanent)
facts rm 123
```

## Tag Taxonomy

### Domain Tags

- `private` — Personal/confidential
- `genomic` — Genomic Digital company-wide
- `genomic-client-{name}` — Client-specific (e.g., `genomic-client-acme`)
- `sakima` — Sakima LC (coin/auction business)
- `basecase-archived` — Base Case reference/templates
- `incubator-{project}` — AI experiments (e.g., `incubator-auctions`)
- `system` — BIGMAC/OpenClaw infrastructure
- `machine` — Local computer/filesystem
- `family` — Family-related
- `marketing` — General marketing knowledge
- `development` — Technical/coding
- `shared` — Shared across all contexts

### Lifecycle Tags

- `inbox` — Needs tagging (default for untagged facts)
- `archived` — Historical reference only
- `template` — Reusable patterns
- `urgent` — Needs immediate attention
- `review` — Needs verification/update
- `deprecated` — Outdated, replaced
- `proven-false` — Fact was wrong
- `no-longer-applicable` — Was true, circumstances changed
- `superseded` — Auto-added when fact is superseded

### Location Tags

- `repo-{name}` — Related repository (e.g., `repo-genomic`, `repo-openclaw`)
- `folder-{name}` — Related directory (e.g., `folder-workknowledge`)

## Agent Isolation

Facts are automatically tagged with the creating agent based on your current directory:

```bash
# From Chloe's workspace
cd /Users/benfife/clawd/agents/chloe
facts add operational "Client fact"   # created_by='chloe'

# From main workspace
cd /Users/benfife/clawd
facts add user_prefs "Personal fact"  # created_by='main'

# Search defaults to current agent
facts list                             # Shows only your agent's facts
facts list --all                       # Shows all agents
facts list --agent chloe               # Shows only Chloe's facts
```

## Date Validity

Facts have three date fields:

### `as_of_date` (Start Date - Required)

When the fact became valid/true. Defaults to today.

### `inactive_date` (End Date - Auto-set)

When the fact became inactive. Set automatically when superseded or deactivated.

### `valid_until` (Expiration - Optional)

Explicit expiration date. Only set when you KNOW the fact expires (never guessed).

```bash
# Fact with start date
facts add operational "Policy change" --as-of 2026-01-15

# Fact with known expiration
facts add operational "Limited promo" --valid-until 2026-03-31

# Query by date
facts search "policy" --valid-on 2026-01-20   # What was valid then?
facts list --expiring-days 30                  # Expiring soon
facts auto-expire                               # Expire past valid_until
```

## Supersession Chains

Track how facts evolve over time:

```bash
# Original fact
facts add operational "ROAS target 2x" --tags genomic

# Supersede with new fact
facts add operational "ROAS target 3x" --tags genomic --supersedes 100
# → Fact #100 marked inactive, superseded_by=150
# → Fact #150 is now active

# View evolution
facts chain 100
# Fact #100: ROAS target 2x [SUPERSEDED]
#   ↓ superseded by #150 on 2026-02-06
# Fact #150: ROAS target 3x [ACTIVE]
```

## Full History & Audit

Every change is tracked:

```bash
facts show 123
# Displays:
# - Full fact details
# - All tags and who added them
# - Date validity ranges
# - Creation/update agent & timestamps
# - Supersession info
# - Edit history (if fact text was changed)
```

## Workflow Examples

### Tagging Inbox Facts

```bash
# See untagged facts
facts list --tags inbox

# Tag them properly
facts tag 45 genomic marketing
facts untag 45 inbox
```

### Client Campaign Evolution

```bash
# Initial strategy
facts add operational "Client X: Focus on Google Search" \
  --tags genomic-client-x,marketing --as-of 2026-01-15

# Strategy changes
facts add operational "Client X: Switch to Performance Max" \
  --tags genomic-client-x,marketing --supersedes 100 --as-of 2026-02-01

# View evolution
facts chain 100
```

### Mark Facts as Outdated

```bash
# Deprecated (replaced by new approach)
facts tag 67 deprecated
facts add operational "New approach: ..." --tags genomic

# Proven false
facts tag 89 proven-false
facts add operational "Correction: ..." --tags genomic

# Search excluding bad facts (default behavior)
facts search "ROAS"  # Auto-excludes deprecated/proven-false
```

## Default Behavior

- **Active only** — Inactive facts excluded unless `--all` or `--inactive-only`
- **Current agent** — Your agent's facts only unless `--all` or `--agent X`
- **Newest first** — Descending sort by ID (use `--asc` to reverse)
- **No bad facts** — `deprecated`, `proven-false`, `no-longer-applicable` excluded by default

## Categories

Facts must have a category:

- `user_info` — User information
- `user_prefs` — User preferences
- `system` — System configuration
- `operational` — Operational knowledge (most common)

## Notes

- CLI: `/Users/benfibe/clawd/scripts/bigmac-facts`
- Database: Turso `facts`, `fact_tags`, `fact_edits`, `fact_tag_changes` tables
- Agent detection: Auto-detects from current directory
- Shared globally across all agents
- Full audit trail of all changes
