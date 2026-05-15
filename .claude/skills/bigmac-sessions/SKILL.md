---
name: bigmac-sessions
description: Track all chat sessions with metadata and links to knowledge items (facts/assumptions/opinions/policies) referenced or created.
homepage: https://turso.tech/
metadata: { "moltbot": { "emoji": "💬", "requires": { "bins": ["sessions"] } } }
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


# bigmac-sessions - Session Tracking & Knowledge Audit

Track all chat sessions with complete metadata and links to knowledge items referenced or created during the conversation.

## Schema

**Main table:** `sessions`

- `session_key` — Unique session identifier
- `agent_id` — Which agent handled the session
- `user_id`, `channel`, `channel_id` — User/channel info
- `status` — active, closed, abandoned, needs_review
- `title`, `summary` — Session description
- `started_at`, `ended_at`, `last_activity_at` — Timestamps
- `message_count` — Number of messages
- `created_by`, `closed_by` — Agent tracking
- `tags`, `metadata` — Additional context

**Link tables:** (session ↔ knowledge)

- `session_facts`
- `session_assumptions`
- `session_opinions`
- `session_policies`

Each link tracks:

- Which knowledge item (fact_id, assumption_id, etc.)
- Action: `referenced`, `created`, `updated`, `superseded`
- Message ID (optional)
- Timestamp

## Quick Start

```bash
# Start a session
sessions start sess_12345 --agent main --channel telegram --title "Campaign planning"

# Update session (heartbeat)
sessions update sess_12345 --inc-messages

# Link knowledge items
sessions link sess_12345 fact 123 created
sessions link sess_12345 assumption 45 referenced
sessions link sess_12345 policy 67 referenced

# Close session
sessions close sess_12345 --summary "Created 3 facts, discussed ROAS strategy"

# List sessions
sessions list

# Show session details
sessions show sess_12345
```

## Workflow

### 1. Session Start

When a new conversation starts:

```bash
sessions start <session-key> \
  --agent main \
  --user ben \
  --channel telegram \
  --channel-id 123456 \
  --title "Campaign planning discussion"
```

### 2. During Session

Track activity and link knowledge:

```bash
# After each message
sessions update <session-key> --inc-messages

# When referencing existing knowledge
sessions link <session-key> fact 123 referenced
sessions link <session-key> policy 45 referenced

# When creating new knowledge
sessions link <session-key> fact 456 created
sessions link <session-key> assumption 78 created

# Update title/summary as understanding evolves
sessions update <session-key> --title "ROAS optimization strategy"
```

### 3. Session Close

Proper session closure:

```bash
sessions close <session-key> \
  --summary "Discussed Q1 2026 campaign strategy. Created 3 facts about ROAS targets, referenced 2 policies on tracking requirements. Decision: Launch PMax campaign with 3x ROAS target."
```

## Abandoned Sessions

Find sessions that weren't properly closed:

```bash
# Find sessions idle >24 hours
sessions abandoned --hours 24

# Mark them for review
sessions abandoned --hours 48 --mark-review

# List sessions needing review
sessions list --status needs_review
```

### Review Workflow

```bash
# Show abandoned session
sessions show sess_old_123

# Review the session (look at knowledge links, context)
# Decide: close it or mark abandoned

# Close with summary
sessions close sess_old_123 \
  --summary "Session ended without explicit close. Created 2 facts about client requirements."

# Or mark as abandoned
sessions update sess_old_123 --status abandoned
```

## Listing & Filtering

```bash
# List your sessions
sessions list

# List all agents' sessions
sessions list --all

# List specific agent
sessions list --agent chloe

# Filter by status
sessions list --status active
sessions list --status needs_review

# Filter by channel
sessions list --channel telegram

# Limit results
sessions list --limit 10
```

## Session Details

```bash
sessions show <session-key>
```

Shows:

- All metadata (agent, user, channel, status, times, message count)
- Summary
- All linked knowledge items:
  - Facts (with action: referenced/created/updated)
  - Assumptions
  - Opinions
  - Policies

## Knowledge Traceability

**Forward tracing:** "Which sessions used this fact?"

```sql
SELECT s.session_key, s.title, sf.action
FROM sessions s
JOIN session_facts sf ON s.id = sf.session_id
WHERE sf.fact_id = 123;
```

**Backward tracing:** "What knowledge was created in this session?"

```bash
sessions show <session-key>
# Shows all created/referenced knowledge
```

## Integration Example

```bash
# Session starts
sessions start current_session --agent main --channel webchat

# During conversation, agent creates a fact
facts add operational "Client X prefers Google Ads" --tags genomic-client-x
# → Fact #123 created

# Link it to session
sessions link current_session fact 123 created

# Later, agent references a policy
sessions link current_session policy 45 referenced

# Session ends
sessions close current_session \
  --summary "Client onboarding: documented platform preference, reviewed tracking policies"
```

## Automated Cleanup

Schedule via cron:

```bash
# Daily: Mark abandoned sessions (idle >48h)
sessions abandoned --hours 48 --mark-review

# Weekly: Review and close sessions
# (Manual or via agent review workflow)
```

## Commands

```bash
# Start
sessions start <key> [--agent X] [--user X] [--channel X] [--channel-id X] [--title X] [--tags X]

# Update
sessions update <key> [--title X] [--summary X] [--status X] [--inc-messages]

# Link knowledge
sessions link <key> <type> <id> <action> [--message-id X]
  Types: fact, assumption, opinion, policy
  Actions: referenced, created, updated, superseded

# Close
sessions close <key> [--summary "X"]

# List
sessions list [--agent X] [--status X] [--channel X] [--limit N] [--all]

# Show
sessions show <key>

# Abandoned
sessions abandoned [--hours N] [--mark-review]
```

## Status Values

- `active` — Session in progress
- `closed` — Properly closed with summary
- `abandoned` — Ended without explicit close
- `needs_review` — Flagged for agent review

## Use Cases

### Audit Trail

- "What knowledge did we create during client onboarding?"
- "Which sessions referenced this policy?"
- "What was discussed in the Feb 5 planning session?"

### Knowledge Provenance

- "Where did this fact come from?" → Check session links
- "Who created this assumption?" → Check created_by + session

### Session Recovery

- Agent goes offline mid-conversation
- Sessions system tracks what was discussed
- Agent can resume by reviewing session details

### Quality Review

- Periodic review of sessions needing closure
- Ensure proper documentation
- Identify patterns (which sessions create most knowledge?)

## Notes

- CLI: `/Users/benfife/clawd/scripts/bigmac-sessions`
- Database: Turso `sessions` + 4 link tables
- Shared globally across all agents
- Use for complete session audit trail
- Links are protected by foreign keys (can't delete knowledge while linked)
