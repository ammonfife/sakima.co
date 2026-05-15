---
name: ledgestone-alias
description: Generate, persist to Turso, and route @ledgestonehome.com aliases for signups, verification, and account recovery. Use when any service needs a fresh email address.
user-invocable: true
version: 2.0.0
---

# LEDGESTONE ALIAS GENERATOR

Version: 1.0.0

This skill defines the standard workflow for autonomous agents that need a unique @ledgestonehome.com catch-all alias for a new signup, login, verification, or future routing path.

## Purpose

Use this skill whenever a service needs a fresh alias and the agent should not ask the user for a new email address.

The goal is to make alias selection deterministic, service-aware, unique, and recoverable later through ledgestone-email-router.

## Core rules

1. Generate one alias per service unless there is a documented reason to reuse an existing alias.
2. Make the alias service-aware so it is easy to recognize later.
3. Ensure the alias is globally unique.
4. Persist every created alias immediately for later login, verification, and routing.
5. Register or update the alias in ledgestone-email-router so mail can be delivered to the right downstream workflow.
6. Do not ask the user to invent a new email unless the service explicitly rejects the generated alias format and no valid fallback exists.

## Alias format

Preferred format:
service-slug-uuid@ledgestonehome.com

Rules:
- service-slug should be short, lowercase, and ASCII-only.
- Use hyphens, not spaces or punctuation.
- Keep the service slug stable across time for the same service.
- uuid should be a fresh collision-resistant token.
- If a service imposes length limits, shorten the slug before shortening uniqueness.
- If a service rejects hyphens or long local parts, derive the closest acceptable variant while preserving service identity and uniqueness.

Examples:
- fiverr-2f3a9c1e@ledgestonehome.com
- upwork-7d1b8a44@ledgestonehome.com
- freelancer-b41c0d9a@ledgestonehome.com

## Alias generation procedure

When a new alias is needed:

1. Identify the service name and normalize it into a service slug.
2. Check whether an alias already exists for that service and signup context.
3. If an alias exists, reuse it for continuity.
4. If no alias exists, generate a new alias using the preferred format.
5. Validate that the alias is unique in the local alias registry before use.
6. Store the alias and its metadata immediately.
7. Pass the alias to the signup or verification flow.

## Persistence requirements

Every alias must be persisted with enough metadata to restore context later.

Minimum fields:
- service_name
- service_slug
- alias_email
- generated_at
- purpose (signup, verification, login recovery, support, routing)
- status (active, retired, blocked)
- notes
- router_key or routing reference if available

Persistence backend: **Turso** (canonical, cross-agent, cross-session)

```bash
# Store alias
bigmac-secrets set "alias:<service_slug>:<uuid_suffix>" "<full_alias_email>"

# Or use Turso facts for richer metadata
bigmac-facts add "ledgestone alias: <service_slug> → <alias_email>" \
  --tags ledgestone,alias,<service_slug>
```

Persistence behavior:
- Save the alias to Turso BEFORE submitting it to any external form.
- Mark the alias as active once the service accepts it.
- Mark the alias as blocked if the service rejects it.
- Retain the history of prior aliases for the same service.
- Never overwrite a prior alias without preserving the record.
- All aliases MUST be in Turso — never only in local files or memory.

## ledgestone-email-router integration

For each new alias, update the email router so incoming mail can be mapped to the correct service workflow.

Router responsibilities:
- Recognize the alias as belonging to the service.
- Route inbound mail to the right login, verification, or support path.
- Preserve a lookup from alias to service and account context.
- Allow future agents to resolve the alias without guessing.

Required router update behavior:
- Create or refresh a router entry whenever a new alias is generated.
- Include the service name, alias, and current purpose.
- Keep the router mapping synchronized with the persisted alias record.
- If router registration fails, do not discard the alias; persist the failure and retry later.

## Standard request flow

Agents should follow this flow instead of asking the user for a new email manually:

1. Detect that a new signup or account recovery needs an email address.
2. Resolve whether a reusable service alias already exists.
3. If not, generate a new service-aware alias.
4. Persist the alias.
5. Register it with ledgestone-email-router.
6. Use the alias in the signup or login flow.
7. Record any verification code or response path against the same alias.
8. Reuse the alias for future login, password reset, or support interactions for that service.

## Failure handling

If the preferred alias is rejected:
- Try a shorter service slug.
- Try a simplified but still unique local part.
- Preserve the rejection reason in the alias record.
- Stop only after no valid alias format remains.

If the router cannot be updated immediately:
- Continue only if the alias itself is still usable.
- Mark the router sync as pending.
- Ensure the next agent can pick up the unsynced mapping.

## SMS Verification Policy

When a service requires phone verification alongside the email alias:

1. **Use frictionless SMS providers** (Twilio, TextBelt, or similar) — do NOT use Ben's personal number (+18019390533) as the signup number
2. **Forwarding TO Ben's number is OK** — for read-back via Messages DB or BlueBubbles
3. **Reading verification codes locally**: Messages.app SQLite DB at `~/Library/Messages/chat.db` or via `/imsg` skill
4. **Reading verification codes from cloud**: BlueBubbles API via `/bluebubbles` skill
5. Store the phone number used alongside the alias in Turso: `bigmac-secrets set "sms:<service_slug>" "<phone_number>"`

## Operational notes

- Prefer deterministic naming over ad hoc improvisation.
- Never invent a new human inbox when a catch-all alias is appropriate.
- Keep aliases service-scoped so login, routing, and verification remain easy to trace.
- Treat the alias registry and router mapping as the source of truth for future sign-in recovery.
- ALL aliases and phone numbers MUST be persisted to Turso immediately on creation.

## Output expectations

When using this skill, report:
- the service name
- the exact alias used
- whether it was newly generated or reused
- persistence status
- router sync status
- any rejection or fallback used
---
name: ledgestone-email-router
description: Route catch-all emails forwarded from any @ledgestonehome.com alias to the correct service-specific agent, webhook, or Supabase Edge Function.
metadata:
  author: Ben Fife
  version: "0.1.0"
  scope: email-routing
---

# Ledgestone email router

Use this skill when processing mail that arrives through the ledgestonehome.com catch-all and is forwarded to a.benfife@gmail.com.

## Goal

Extract the intended recipient alias from the incoming message, infer the service from that alias, and route the message payload to the correct downstream handler.

## Inputs to inspect

Prefer the first trustworthy recipient source in this order:
1. Envelope-To / Delivered-To
2. X-Original-To
3. To / Cc headers
4. Any alias embedded in the forwarded body

Normalize the alias before routing:
- lowercase the local-part
- trim whitespace
- preserve dots and hyphens in the alias
- ignore plus-tags only if they are clearly delivery tags, not part of the service alias
- require the domain to be ledgestonehome.com

## Routing contract

Always build a structured payload with:
- messageId
- from
- originalRecipients
- matchedAlias
- subject
- receivedAt
- textBody
- htmlBody
- attachments
- headers
- routingReason
- destinationType
- destinationTarget

Preserve the raw message details so downstream agents or functions can reprocess the email without losing context.

## Routing table

Use the recipient local-part to choose the handler.

| Alias pattern | Destination type | Example destination |
| --- | --- | --- |
| fiverr@ledgestonehome.com | agent or webhook | Fiverr workflow handler |
| upwork@ledgestonehome.com | agent or webhook | Upwork workflow handler |
| supabase@ledgestonehome.com | Supabase Edge Function | ledgestone-email-supabase-router |
| github@ledgestonehome.com | agent or webhook | GitHub workflow handler |
| billing@ledgestonehome.com | agent | finance / billing triage |
| support@ledgestonehome.com | agent | support triage |
| anything else | default triage | generic inbox router |

If multiple ledgestonehome.com recipients are present, route to the most specific service alias. If no service alias matches, send to the default triage handler.

## Recommended downstream behavior

### Fiverr / Upwork
Route to the service-specific agent or webhook that can:
- summarize the message
- preserve attachments
- decide whether a reply, manual review, or task creation is needed

### Supabase
Route to a dedicated Edge Function that can:
- parse the alias
- fan out to internal workflows
- call Supabase APIs or background jobs as needed

### Default triage
If the alias is unknown, send the email to a generic routing agent with the full payload and the unmatched alias.

## Failure handling

If alias extraction fails:
- keep the message in default triage
- include a clear routingReason explaining which header sources were missing or conflicting
- do not drop attachments or body content

If downstream delivery fails:
- log the failure reason
- preserve the payload for retry
- do not silently reroute to a different service unless that fallback is explicitly configured

## Implementation notes for a code version

A dedicated edge function should:
1. accept the forwarded Gmail payload
2. extract the ledgestonehome.com alias from headers
3. normalize and classify the alias
4. dispatch to the configured agent, webhook, or edge function URL
5. return a compact routing result with the chosen destination and reason

Suggested environment variables:
- LEDGESTONE_DEFAULT_WEBHOOK_URL
- LEDGESTONE_FIVERR_WEBHOOK_URL
- LEDGESTONE_UPWORK_WEBHOOK_URL
- LEDGESTONE_GITHUB_WEBHOOK_URL
- LEDGESTONE_SUPABASE_FUNCTION_URL
- LEDGESTONE_ROUTER_HMAC_SECRET

Suggested dispatch format:

```ts
export type RoutedEmail = {
  messageId: string
  from?: string
  subject?: string
  matchedAlias: string
  destinationType: 'agent' | 'webhook' | 'edge_function'
  destinationTarget: string
  reason: string
}
```

Keep the router deterministic. Do not infer a destination from the email body unless the recipient alias is missing.
