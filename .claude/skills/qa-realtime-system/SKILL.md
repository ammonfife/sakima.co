---
name: qa-realtime-system
description: Procedures for verifying the health and performance of the BigMac Realtime notification mesh.
---

# QA: BigMac Realtime System

Use this skill to verify that `bigmac-realtime-agent` is correctly bridging Turso, Supabase, and local filesystem events.

## 1. Health Check Procedure

### Step A: Process Verification
Ensure the agent is running and has the correct project/session context.
```bash
ps aux | grep bigmac-realtime-agent | grep -v grep
```

### Step B: Connection Test
Verify the agent can connect to the BigMac Supabase instance.
```bash
# Trigger a test fact
bigmac-facts add operational "Realtime Health Check" --tags lkup,qa,test

# Check if the background agent caught it (inspect latest log/output)
# For Gemini: command_status(CommandId: "<PID>")
```

### Step C: Multi-Platform Inbox Check
Verify filesystem watch triggers for cross-platform messaging.
```bash
echo "QA Test Message" > ~/.gemini/tmp/benfife/.inbox
# The agent should batch this, clear the file, and exit with JSON
```

## 2. Authentication & Connectivity

### Project URL
- **BigMac Production:** `https://ppiqawxxqdajzqdxhgmo.supabase.co`
- **LKUP Production:** `https://vsotvatntzlrzrhemayh.supabase.co`

### Credentials Source
The agent automatically attempts to retrieve keys from the macOS keychain in this order:
1. `bigmac_supabase_service_role_key` (Primary for notification mesh)
2. `supabase_lkup_service_role_key` (Primary for lkup.info data)
3. `bigmac_supabase_anon_key`
4. `supabase_lkup_anon_key`

**Manual retrieval:**
```bash
security find-generic-password -s bigmac_supabase_service_role_key -w
```

## 3. Data Schema (Supabase Realtime)

The following tables are Realtime-enabled and mirrored from Turso.

### `facts` (Durable Knowledge)
| Column | Type | Example |
| :--- | :--- | :--- |
| `id` | int8 | `817` |
| `category` | text | `operational` |
| `content` | text | `reference.greysheet_prices: 19K+ rows...` |
| `tags` | jsonb | `["lkup", "pricing"]` |
| `agent` | text | `claude_2` |

### `todos` (Task Management)
| Column | Type | Example |
| :--- | :--- | :--- |
| `id` | int8 | `3746` |
| `title` | text | `Assign canonical group lkup_uuid` |
| `status` | text | `pending` |
| `assigned_agent`| text | `gemini` |
| `tags` | jsonb | `["lkup", "p0"]` |

### `messages` (Inter-Agent Comms)
| Column | Type | Example |
| :--- | :--- | :--- |
| `id` | uuid | `f40e7b8a-...` |
| `from_agent` | text | `poke` |
| `to_agent` | text | `gemini` |
| `content` | text | `Numismedia metadata update complete` |

### `session_inbox` (Session-Specific Pushes)
Used for direct "wake up" calls to a specific CLI instance.
- `session_id`: The target UUID.
- `content`: The prompt or notification.

## 4. Troubleshooting

### 401 Unauthorized
- **Cause:** Service role key expired or project ID mismatch.
- **Fix:** Update the keychain entry or check if `BIGMAC_SUPABASE_URL` is set to the correct project.

### No Events Received
- **Cause:** Incorrect `project_tag` provided (filtering too strictly).
- **Fix:** Run without a project tag to see the global firehose:
  `bigmac-realtime-agent $SID $AGENT "" 60`

### Agent Stalled
- **Cause:** Synced blocking call.
- **Fix:** Ensure it is run via `run_command` (Gemini) or `run_in_background: true` (Claude).
