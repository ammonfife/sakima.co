---
name: lovable-deploy
description: Deploy lkup.info via Lovable.dev — uses E2B desktop sandbox to click the publish button
---

# Lovable Deploy

Lovable.dev has no public deploy API. Production deploys require clicking the "Deploy"/"Publish" button in the Lovable UI. This skill automates that via an E2B desktop sandbox.

## When to Use

After pushing commits to `ammonfife/lkup.info` main branch. Lovable auto-fetches but does NOT auto-deploy.

## Process

1. **Get desktop sandbox**: `sbx ls | grep desktop` (ignore pool-managed ones). Create if needed: `sbx new bigmac-desktop-v3-0-0`
2. **Open browser** to `https://lovable.dev/projects/198cfbd3-f2a7-4365-ae7a-94cc5c555bd9`
3. **Login if needed** — GitHub OAuth, credentials from secrets vault (`bigmac-secrets`)
4. **Verify changes synced** — preview should show latest commit
5. **Click Deploy/Publish button** — typically top-right area
6. **Wait for build** — 30-90 seconds
7. **Verify**: `curl -s -o /dev/null -w '%{http_code}' https://lkup.info` → 200

## Notes

- `git push` alone does NOT deploy — button click required
- No public Lovable API for automated deploys (confirmed 2026-03-23)
- Published URLs: `https://look-up-now.lovable.app` and `https://lkup.info`

## Bigmac Turso

After successful deploy:
```bash
facts add operational "lkup.info deployed: [commit hash or brief description of what shipped]" --tags lkup,deploy,agent:Codex,agent:bob
bigmac-sync push
```

## Bigmac Turso Integration

After a successful Lovable deploy, record it.

### Facts
```bash
facts add operational "lkup.info deployed to Lovable — [commit range or feature summary]" --tags lkup,deploy,agent:bob,agent:Codex
```

### Sync
```bash
bigmac-sync push
```

### Tag Conventions
- **Project:** `lkup`, `sakima`
- **Agents:** `agent:bob`, `agent:Codex`
- **Domain:** `deploy`, `lovable`
- **Status:** `status:verified`
