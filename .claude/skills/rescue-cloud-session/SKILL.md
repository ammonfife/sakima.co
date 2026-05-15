---
name: rescue-cloud-session
description: Rescue uncommitted/unstaged work from any cloud AI session (Devin, Codex, Claude cloud, mog) cut off by quota/usage limits. Finds unstaged changes, pushes them, captures session transcript.
---

# /rescue-cloud-session

Use when an AI cloud session (Devin, Codex, Claude cloud) hit its usage limit mid-work.

## Codex sessions (most common)

```bash
cd ~/github/ammonfife/<repo>
git log --oneline -5       # check "auto: sync" commits captured work
git push origin <branch>   # push if ahead of origin
# If hooks didn't fire: git add -A && git commit -m "rescue: Codex session" && git push
```

Auto-sync hooks fire on every commit — if Codex committed but didn't push, just push.

## Devin.ai sessions

**Auth requires BOTH headers** (most common failure mode):
- `Authorization: Bearer auth1_{token}` — from browser `localStorage.auth1_session.token`
- `x-cog-org-id: {org_id}` — from `localStorage` key starting with `post-auth-v3-*`

```bash
TOKEN="auth1_lalp5z6renz4..."   # from BigMac Scope capture or Playwright
ORG="org-8cf13fc3b..."

# Get all session events (NDJSON, each line is {"result":[...]})
curl -H "Authorization: Bearer $TOKEN" -H "x-cog-org-id: $ORG" \
  "https://app.devin.ai/api/events/devin-{id}/stream?order=asc" \
  > ~/clawd/data/devin-sessions/{id}/events-raw.json

# Get terminal content (via Playwright Shell tab presigned Azure Blob URLs)
# Navigate to session → browser_network_requests --filter "terminal_contents"
# Fetch each .bin file, decode: TextDecoder('utf-8') + strip ANSI escapes

# Get uncommitted file diffs
curl -H "Authorization: Bearer $TOKEN" -H "x-cog-org-id: $ORG" \
  "https://app.devin.ai/api/ide/devin-{id}/file_diffs"
```

Git commits from Devin are already on origin — check `git log origin/prod..HEAD`.
Resume in Devin UI when quota resets (daily: midnight PT).

## Claude cloud sessions

```bash
/capture-cloud-session https://claude.ai/code/session_{id}
```
Decrypts Desktop cookies, fetches events API, saves to `~/clawd/data/`.

## Prevention

```bash
# Ensure auto-sync hook is wired in any repo:
git config core.hooksPath .githooks
# Pre-push hook regenerates knowledge snapshots and creates "auto: sync" commits
```
