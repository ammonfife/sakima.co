---
name: bigmac-policies
description: Track policies, rules, guidelines, and standards with tags, agent tracking, date validity, and supersession chains. Identical schema to facts.
homepage: https://turso.tech/
metadata: { "moltbot": { "emoji": "📋", "requires": { "bins": ["policies"] } } }
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


# bigmac-policies - Policies, Rules & Guidelines

Track organizational policies, operational guidelines, standards, and rules that govern behavior and decisions.

## Schema

Identical to facts/assumptions/opinions table structure:

- Multi-tagging (many-to-many)
- Agent tracking (created_by, updated_by, tag added_by)
- Date validity (as_of_date, inactive_date, valid_until)
- Supersession chains (bidirectional: supersedes ↔ superseded_by)
- Full audit history
- Active/inactive status

## Quick Start

```bash
# Add policy
policies add operational "Always verify tracking before launch" --tags genomic,marketing,mandatory

# List policies
policies list

# Search policies
policies search "tracking"

# Tag/untag
policies tag 123 genomic mandatory urgent
policies untag 123 inbox

# Show details
policies show 123

# Update policy (supersede old one)
policies add operational "Verify tracking AND creative approval" \
  --tags genomic,marketing,mandatory --supersedes 123
```

## Use Cases

### Marketing Policies

```bash
policies add operational "Require 2x ROAS minimum for paid media" \
  --tags genomic,marketing,performance

policies add operational "Test incrementally before scaling" \
  --tags genomic,marketing,best-practice

policies add operational "Never launch without conversion tracking" \
  --tags genomic,marketing,mandatory
```

### Operational Guidelines

```bash
policies add operational "Daily budget pacing checks required" \
  --tags genomic,operations,daily

policies add operational "Weekly performance reviews for all clients" \
  --tags genomic,operations,weekly

policies add operational "Monthly strategy alignment meetings" \
  --tags genomic,operations,monthly
```

### Compliance & Standards

```bash
policies add operational "GDPR consent required for EU audiences" \
  --tags genomic,compliance,legal,mandatory

policies add operational "Privacy-first targeting only" \
  --tags genomic,compliance,privacy

policies add operational "Brand safety filters on all display campaigns" \
  --tags genomic,compliance,brand-safety
```

### Client-Specific Policies

```bash
policies add operational "Client X: Approval required for all creative" \
  --tags genomic-client-x,approval,mandatory

policies add operational "Client Y: Monthly reports by 5th of month" \
  --tags genomic-client-y,reporting,deadline
```

## Policy vs Fact vs Assumption vs Opinion

### Facts 📚

Objective, verifiable, data-backed:

- "ROAS was 3x in Q1 2026"
- "Email deliverability improved 14%"

### Assumptions 🤔

Testable hypotheses, working beliefs:

- "Customers prefer simple interfaces"
- "Email timing affects open rates"

### Opinions 💭

Subjective theories, paradigms:

- "Multi-channel is key to growth"
- "Brand awareness drives long-term value"

### Policies 📋

Rules, guidelines, standards that govern:

- "Always verify tracking before launch" (mandatory)
- "Require 2x ROAS minimum" (performance standard)
- "GDPR consent required for EU" (compliance)

## Tag Taxonomy

### Domain Tags

Same as facts: `private`, `genomic`, `genomic-client-X`, `sakima`, etc.

### Lifecycle Tags

- `inbox` — Needs tagging
- `draft` — Policy being developed
- `active` — Currently enforced
- `under-review` — Being reconsidered
- `superseded` — Replaced by newer policy
- `deprecated` — No longer enforced

### Type Tags

- `mandatory` — Must be followed
- `recommended` — Best practice
- `guideline` — Suggested approach
- `standard` — Quality/performance standard
- `rule` — Strict rule
- `best-practice` — Recommended approach

### Enforcement Tags

- `compliance` — Legal/regulatory requirement
- `legal` — Legal constraint
- `brand-safety` — Brand protection
- `privacy` — Privacy protection
- `security` — Security requirement

### Frequency Tags

- `daily` — Daily requirement
- `weekly` — Weekly requirement
- `monthly` — Monthly requirement
- `quarterly` — Quarterly requirement
- `on-launch` — Required at campaign launch
- `on-change` — Required when changing

## Time-Limited Policies

```bash
# Temporary policy (e.g., holiday season rules)
policies add operational "Black Friday: No budget caps Nov 20-27" \
  --tags genomic,seasonal,temporary \
  --as-of 2026-11-20 \
  --valid-until 2026-11-27

# Policy expires automatically
policies auto-expire
```

## Policy Updates

```bash
# Original policy
policies add operational "Max $10K daily budget per client" \
  --tags genomic,budget,limit --as-of 2026-01-15

# Update policy (market conditions changed)
policies add operational "Max $25K daily budget per client" \
  --tags genomic,budget,limit --as-of 2026-03-01 --supersedes 123

# View policy evolution
policies chain 123
```

## Compliance Tracking

```bash
# List all compliance policies
policies list --tags compliance

# List all mandatory policies
policies list --tags mandatory

# Find client-specific policies
policies list --tags genomic-client-acme

# Policies expiring soon (need renewal/review)
policies list --expiring-days 30
```

## Commands

Same as facts CLI:

```bash
policies add <category> "text" --tags tag1,tag2 --as-of YYYY-MM-DD --valid-until YYYY-MM-DD
policies list [--tags X] [--all] [--agent X]
policies search "query" [--tags X]
policies tag <id> tag1 tag2
policies untag <id> tag1
policies show <id>
policies chain <id>
policies deactivate <id>
policies tags
policies auto-expire
policies rm <id>
```

## Integration

### Policy → Fact Pipeline

When a policy becomes a verified practice:

```bash
# Policy (rule to follow)
policies add operational "Require 2x ROAS minimum" \
  --tags genomic,marketing,standard

# After consistent achievement, convert to fact
facts add operational "Team consistently achieves 2x+ ROAS (2026)" \
  --tags genomic,marketing,validated
```

### Policy Enforcement via Assumptions

```bash
# Policy
policies add operational "Test creative before scaling" \
  --tags genomic,marketing,best-practice

# Underlying assumption
assumptions add operational "Tested creative outperforms untested" \
  --tags genomic,marketing,hypothesis

# Validate assumption to justify policy
facts add operational "A/B tests show 45% higher CTR for tested creative" \
  --tags genomic,marketing,validated
```

## Notes

- CLI: `/Users/benfife/clawd/scripts/bigmac-policies`
- Database: Turso `policies`, `policies_tags`, `policies_edits`, `policies_tag_changes`
- Schema: Identical to facts/assumptions/opinions
- Shared globally across all agents
- Use for rules and guidelines that govern operations
