---
name: bigmac-secrets
description: Store and retrieve secrets (API keys, tokens) in shared Turso vault. Global across all agents.
homepage: https://turso.tech/
metadata: {"moltbot":{"emoji":"🔐","requires":{"bins":["secrets"]}}}
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


# bigmac-secrets - Shared Secrets Vault

Store and retrieve secrets (API keys, tokens, credentials) in Turso database. Shared globally.

## Commands

```bash
# Set a secret
secrets set <key> <value>
secrets set google_ai_api_key "AIza..."

# Get a secret
secrets get <key>
API_KEY=$(secrets get google_ai_api_key)

# Or via macOS Keychain directly (if secrets CLI fails)
TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w)

# List all secret keys
secrets list

# Export all secrets (JSON)
secrets export
```

## Current Secrets (53 in vault)

Run `secrets list` for full inventory. Key categories:

**AI APIs:**
- `anthropic` — Claude API key
- `openai` — OpenAI API key
- `openai_organization` — OpenAI org ID
- `google_ai_api_key` — Google Gemini API
- `grok` — Grok API key
- `perplexity` — Perplexity API key

**Meta/Facebook:**
- `app_id`, `app_secret`, `access_token`
- `instagram_*` — Multiple Instagram accounts

**Google Services:**
- GCP, Gmail, Google Ads, GA4

**Payments:**
- Stripe (3 keys), Shopify (2 keys)

**Infrastructure:**
- E2B, Upstash Redis (2 keys), Cloudflare

## Usage Examples

```bash
# Use in scripts
API_KEY=$(secrets get google_ai_api_key)
curl "https://api.example.com" -H "Authorization: Bearer $API_KEY"

# Python
import subprocess
api_key = subprocess.check_output(["secrets", "get", "openai"]).decode().strip()
```

## Security

- **Global access** — All agents can read all secrets
- **No versioning** — Updates overwrite immediately
- **Turso ACLs** — Protected by Turso token (keychain)
- **Never log secrets** — Don't print to console
- **Never commit secrets** — Don't write to git

## New Machine Setup

```bash
# Set Turso token first
security add-generic-password -a "bigmac" -s "turso-bigmac-token" -w "TOKEN" -U

# Pull workspace
bigmac-sync pull

# Secrets are now accessible
secrets list
```

## Notes

- CLI located at: `/Users/benfife/clawd/scripts/bigmac-secrets`
- Database: Turso `secrets` table
- Master key is Turso token (unlocks all 53 secrets)
- Shared globally across all agents and machines
