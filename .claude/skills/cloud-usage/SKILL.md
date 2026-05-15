---
name: cloud-usage
description: Query billing/usage APIs for all 13 cloud providers (~$615/mo total) and produce a unified cost report sorted by cost descending with annual projections. Trigger with /cloud-usage.
metadata:
  {
    "openclaw":
      {
        "emoji": "💰",
        "os": ["darwin"],
        "requires":
          {
            "bins":
              ["gcloud", "gh", "curl", "python3", "jq", "security"],
          },
      },
  }
---

# Cloud Usage Report V2

## Overview

Queries all 13 BIGMAC cloud providers for billing and usage data, producing a unified JSON report at `~/cloud-usage-report.json` plus a pretty-printed stdout summary sorted by cost descending with annual projections.

## Quick Start

```bash
# Full report (all 13 providers)
bash {baseDir}/scripts/cloud-usage.sh

# Single provider
bash {baseDir}/scripts/cloud-usage.sh --provider gcp
bash {baseDir}/scripts/cloud-usage.sh --provider cloudflare
bash {baseDir}/scripts/cloud-usage.sh --provider supabase
bash {baseDir}/scripts/cloud-usage.sh --provider e2b
bash {baseDir}/scripts/cloud-usage.sh --provider turso
bash {baseDir}/scripts/cloud-usage.sh --provider github
bash {baseDir}/scripts/cloud-usage.sh --provider Codex
bash {baseDir}/scripts/cloud-usage.sh --provider openai
bash {baseDir}/scripts/cloud-usage.sh --provider lovable
bash {baseDir}/scripts/cloud-usage.sh --provider surge
bash {baseDir}/scripts/cloud-usage.sh --provider godaddy
bash {baseDir}/scripts/cloud-usage.sh --provider workspace
bash {baseDir}/scripts/cloud-usage.sh --provider upstash
```

## Providers (13 total, ~$615/mo)

| Provider | Account/Project | Monthly Cost | API Method |
|---|---|---|---|
| GCP | 9 projects on billing 01DF3E-B36319-1B1ACA | ~$200/mo (variable) | gcloud billing budgets, Cloud Run list, Compute, SQL |
| Codex Max | Anthropic subscription | ~$200/mo | Fixed line item |
| Cloudflare | 187de0c1d881a4a2254008f31d8e93d4 | $5/mo Workers Paid | GraphQL analytics (workers, D1, R2) |
| Supabase | vsotvatntzlrzrhemayh (lkup.info) | $25/mo Pro | REST API (projects list) |
| GoDaddy | 16 domains | ~$31/mo ($377/yr) | Fixed line item |
| OpenAI | API + ChatGPT Plus | ~$20/mo | Fixed line item |
| Lovable | lovable.dev subscription | ~$20/mo | Fixed line item |
| Google Workspace | 2 users | ~$14/mo | Fixed line item |
| E2B | team via API key | Usage-based | REST API (running sandboxes) |
| Surge | SMS service | ~$10/mo | Fixed line item |
| Turso | ammonfife org | Free tier | DB row count via libsql |
| GitHub | ammonfife repos | Free tier | gh CLI (actions, cache) |
| Upstash | Redis (phone-home only) | Free tier | Fixed line item |

### GCP Projects (9 linked to billing account)

1. `heimdall-8675309` -- primary (Cloud Run, SQL, Scheduler, Secrets)
2. `ammon-ai` -- Gemini API spend (~$270/mo BIGMAC_OPENCLAW key, now disabled)
3. `mailduringshutdown` -- VMs (stopped)
4. `basecase-analytics` -- legacy
5. `runsignup-data` -- legacy
6. `heimdall-277921` -- legacy
7. `monitoring-dev` -- dev
8. `prod2-svc` -- production services
9. `pr-846b` -- PR environment

## Output

- **JSON:** `~/cloud-usage-report.json` (machine-readable, all providers)
- **stdout:** Pretty-printed summary table sorted by cost descending + annual projection

## Credential Sources

All credentials are pulled automatically at runtime:
- GCP: `gcloud` ADC (application default credentials)
- Cloudflare: `gcloud secrets versions access latest --secret=cloudflare_api_token --project=heimdall-8675309`
- Supabase: `security find-generic-password -s supabase-access-token -w`
- E2B: `security find-generic-password -s E2B_API_KEY -a benfife -w`
- Turso: `security find-generic-password -s turso-bigmac-token -a bigmac -w`
- GitHub: `gh` CLI (already authenticated)

## Verification URLs

Each subscription provider includes a `manual_verification_url` in the JSON output for manual cost verification:
- GCP: https://console.cloud.google.com/billing/01DF3E-B36319-1B1ACA
- Cloudflare: https://dash.cloudflare.com/187de0c1d881a4a2254008f31d8e93d4
- Supabase: https://supabase.com/dashboard/org/default/billing
- E2B: https://e2b.dev/dashboard
- Codex: https://console.anthropic.com/settings/billing
- OpenAI: https://platform.openai.com/settings/organization/billing/overview
- Lovable: https://lovable.dev/settings/billing
- GoDaddy: https://account.godaddy.com/billing
- Google Workspace: https://admin.google.com/ac/billing
- Surge: https://app.surgeapp.co/billing
- Upstash: https://console.upstash.com/billing

## Notes

- GCP billing export to BigQuery is dead (last data Nov 2025). Cost estimates derived from active resource inventory + known pricing.
- Turso platform API rejects the DB token. Usage estimated from local DB stats.
- E2B does not expose a billing/usage API. Running sandbox count is the best proxy.
- Supabase billing API is not publicly documented. Fixed cost ($25/mo Pro) is reported.
- GCP is the largest variable cost -- Gemini API spend on ammon-ai was ~$270/mo before openclaw was disabled 2026-04-08.
