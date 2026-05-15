---
name: monthly-report
description: Generate a monthly performance report for Avalara Capital (and extensible to other Genomic clients) using the full-account Google Ads puller. Builds a single combined report with three non-redundant sections (Month standalone, Month-over-Month, Year-to-Date), cross-checks numbers against a Google Ads UI CSV export, and leaves the email in DRAFT state for Ben to review and send. Codifies the procedure learned the hard way on 2026-04-08 when a 50% underreporting error almost reached Kyle Ivins.
user-invocable: true
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


# /monthly-report

Generate the monthly performance report for Avalara Capital. Execute all steps without pausing unless a sanity check fails. **Never send email autonomously — this skill produces drafts only.**

## Default client: Avalara Capital

The default run assumes Avalara Capital. If the user invokes `/monthly-report <client>`, substitute the client folder path accordingly.

- Client folder: `/Users/benfife/github/ammonfife/genomic/Clients/avalara-capital/`
- Recipient: Kyle Ivins `<kyle.ivins@avalara.com>`
- Customer ID: `7404128201` (Avalara - Embedded Finance)
- Ground-truth file: `data/march-2026-ground-truth.json` (rename by month as you go: `data/<month>-<year>-ground-truth.json`)
- Canonical puller: `scripts/fetch_performance_data.py` (must be the full-account version — see Step 0)

## Step 0 — Freshness gate (MANDATORY)

**Before touching anything, confirm the data puller is not in "single-campaign" mode.** This bug caused March 2026 to understate by 50%. See `Clients/avalara-capital/HOW_MARCH_REPORT_WENT_WRONG_2026-04-08.md` for the full root cause.

```bash
grep -n "CAMPAIGN_ID = \"[0-9]\|campaign\.id = {CAMPAIGN_ID}" \
  /Users/benfife/github/ammonfife/genomic/Clients/avalara-capital/scripts/fetch_performance_data.py
```

If **either** pattern matches outside the HISTORICAL NOTE docstring, **STOP**. Re-apply the fix from commit `420fe4c`:
- Delete the `CAMPAIGN_ID = "..."` line
- Replace every `WHERE campaign.id = {CAMPAIGN_ID}` with `WHERE campaign.status != "REMOVED"`

Do the same grep on the three sibling scripts that historically carried the same bug:
```bash
grep -n "CAMPAIGN_ID = \"[0-9]" \
  /Users/benfife/github/ammonfife/genomic/Clients/avalara-capital/scripts/monitor_tracking.py \
  /Users/benfife/github/ammonfife/genomic/Clients/avalara-capital/scripts/check_conversion_details.py \
  /Users/benfife/github/ammonfife/genomic/Clients/avalara-capital/scripts/update_budget.py
```

If any match, flag to the user before proceeding — `update_budget.py` in particular is on the write path and must not run in single-campaign mode.

## Step 1 — Determine the reporting month

The "monthly report" is always the **most recently completed full month**. Examples:
- Run on April 8 → report covers March
- Run on May 2 → report covers April

In code:
```python
from datetime import date
today = date.today()
first_of_this_month = today.replace(day=1)
last_of_last_month = first_of_this_month - timedelta(days=1)
month_start = last_of_last_month.replace(day=1)
month_end = last_of_last_month
```

Store as `REPORT_MONTH = "2026-03"` etc. for filename templating.

## Step 2 — Pull ground truth from Google Ads API

Use the FIXED `fetch_performance_data.py` OR run a direct Python query. For a fresh, skill-scoped pull that doesn't depend on the client script:

```python
from google.ads.googleads.client import GoogleAdsClient
from collections import defaultdict
import json

AUTH = "/Users/benfife/github/ammonfife/genomic/Clients/avalara-capital/auth/google-ads.json"
CID  = "7404128201"  # Avalara - Embedded Finance

client = GoogleAdsClient.load_from_dict(json.load(open(AUTH)))
ga = client.get_service("GoogleAdsService")

def period_totals(start, end):
    q = f"""
        SELECT metrics.impressions, metrics.clicks, metrics.cost_micros,
               metrics.conversions, campaign.id, campaign.name, campaign.advertising_channel_type
        FROM campaign
        WHERE segments.date BETWEEN '{start}' AND '{end}'
          AND campaign.status != 'REMOVED'
    """
    t = {'cost':0.0, 'conv':0.0, 'clicks':0, 'imp':0}
    by_camp = defaultdict(lambda: {'cost':0,'conv':0,'name':'','type':''})
    for row in ga.search(customer_id=CID, query=q):
        m = row.metrics
        c = row.campaign
        t['cost'] += m.cost_micros / 1_000_000
        t['conv'] += m.conversions
        t['clicks'] += m.clicks
        t['imp'] += m.impressions
        by_camp[c.id]['cost'] += m.cost_micros / 1_000_000
        by_camp[c.id]['conv'] += m.conversions
        by_camp[c.id]['name'] = c.name
        by_camp[c.id]['type'] = c.advertising_channel_type.name
    return t, dict(by_camp)

# Pull the three periods the report needs
jan = period_totals('2026-01-01', '2026-01-31')
feb = period_totals('2026-02-01', '2026-02-28')
mar = period_totals('2026-03-01', '2026-03-31')   # ← the report month
ytd = period_totals('2026-01-01', '2026-03-31')
```

Always pull at least:
- The report month
- The prior month (for MoM comparison)
- Every prior month of the current year (for YTD rollup)

## Step 3 — Write the ground-truth JSON

Save the raw numbers to `data/<month>-<year>-ground-truth.json` with this schema (matches the 2026-03 version in the repo):

```json
{
  "source": "Google Ads API, live pull YYYY-MM-DD",
  "customer_id": "7404128201",
  "scope": "FULL ACCOUNT (all non-removed campaigns)",
  "campaigns_included": [ {"id": "...", "name": "...", "type": "...", "status": "..."} ],
  "periods": {
    "january_2026": { "date_range": "...", "cost": N, "conversions": N, "clicks": N, "impressions": N, "cac": N, "cpc": N, "ctr_pct": N },
    "february_2026": { ... },
    "<report_month>_2026": { ..., "by_campaign": [ {"id":"...","name":"...","cost":N,"conversions":N} ] },
    "ytd_through_<report_month>_2026": { ... }
  },
  "mom_deltas_<report_month>_vs_<prior_month>": { ... }
}
```

This file is the **canonical truth** for all downstream consumers. Every subsequent step reads from it.

## Step 4 — Sanity-check count assertions (MANDATORY)

Before generating HTML, verify:

1. **Campaign count check** — at least 2 active campaigns pulled for the report month. If fewer, the query is filtering silently.
2. **Cross-month continuity** — the prior month in this pull must match the prior month in the prior report's ground-truth JSON (if one exists). Diff them.
3. **Zero-check** — no period should have cost=0 or conversions=0 unless the campaigns literally didn't run. If the script returns nothing, the query is wrong.

```python
if len(mar[1]) < 2:
    raise SystemExit(f"FAIL: only {len(mar[1])} campaigns seen — expected 2+. Check query scope.")
```

Failing any assertion blocks report generation. Do NOT silently "fix" the number.

## Step 5 — Ask the user for a Google Ads CSV cross-check

Before generating HTML, **ask the user to export a Campaign report CSV from the Google Ads UI** covering the same month (and ideally including the MoM comparison against the prior month). The expected path is `~/Downloads/Campaign report.csv` but the user may provide another path.

Parse the CSV and compare every line:

```python
import csv
with open(csv_path) as f:
    # Google Ads UI exports prepend 2 header lines ("Campaign report", date range)
    lines = f.readlines()
reader = csv.DictReader(lines[2:])
totals = {'cost':0, 'conv':0}
for row in reader:
    name = row.get('Campaign','')
    if not name or name.startswith('Total'): continue
    if name.strip() == '--':           # Google Ads embeds a Total row with name ' -- '
        continue                       # — skipping prevents a double-count
    totals['cost'] += float(row['Cost'].replace(',',''))
    totals['conv'] += float(row['Conversions'])
```

**Both totals must match the API pull to the penny.** Any mismatch > $0.01 or > 0.01 conversions blocks report generation. If the user pushes back, re-verify against a fresh API pull before overriding.

**Important CSV gotcha:** Google Ads embeds a summary row whose Campaign name is `" -- "` (two dashes). Always exclude it when summing — summing everything double-counts to ~2× the real total.

## Step 6 — Generate the combined report HTML

Write a single file: `<CLIENT>/<MONTH>_COMBINED_REPORT.html`. Three sections, non-redundant:

1. **Headline insight block** — 1 paragraph at the top summarizing the month's story (conversions trajectory, CAC direction, spend change, any campaign inventory change). Frame from ground truth, not prior reports.
2. **Section 1 — `<Month>` <Year> Performance** — current-month standalone metrics (conversions, spend, CAC, CTR) as hero tiles; then a benchmark table (CPC, impressions, clicks, conv rate). **Do not** repeat the hero-tile numbers in the table.
3. **Section 2 — Month-over-Month (`<PriorMonth>` → `<Month>`)** — just the delta table. Each row: metric / prior / current / change%. Do not repeat the current-month hero tiles.
4. **Section 3 — `<Year>` Year-to-Date** — YTD hero tiles + a monthly trajectory table (one row per month in the current year, ending with the report month). Include an `Active Campaigns` column to make scope-change events visible.
5. **Key Takeaways + Next Month Outlook** — bullet list, anchor each bullet to a specific number from the ground-truth JSON.

**Styling:** clone the CSS block from the prior month's combined report (`MARCH_COMBINED_REPORT.html`). Do not reinvent it. The `.metric`, `.status-good`, `.status-warn`, `.highlight`, `.insight` classes must stay.

**Narrative rules:**
- Lead with the direction (up/down) and magnitude (%).
- Explain any counter-intuitive signal inline. Example: "blended CTR dropped because the Display layer contributes high-volume low-CTR impressions by design."
- Never write "despite lower spend" unless spend actually dropped.
- Back every number with a `data/<month>-ground-truth.json` citation (comment in the HTML, not visible to the reader).

## Step 7 — Generate the email draft HTML

Create `<CLIENT>/<MONTH>_EMAIL_DRAFT.html` — same narrative, tighter. Use the Feb sent body as a structural template (stored in `sent-archive/` from the 2026-04-08 correction). Data cells only — do not redesign.

## Step 8 — Save as Gmail draft, do NOT send

Use the drafts-only path in `scripts/send_campaign_update_email.py` (already rewritten 2026-04-08 to create drafts only). The send function is named `create_march_draft` in the March version — rename or parameterize by month for each run.

**Hard rule: this skill never sends email.** All outbound ends at "Gmail draft created." Ben reviews and sends manually.

## Step 9 — Open reports in the user's browser

```bash
open <CLIENT>/<MONTH>_COMBINED_REPORT.html \
     <CLIENT>/<MONTH>_MOM_REPORT.html \
     <CLIENT>/<MONTH>_EMAIL_DRAFT.html \
     <CLIENT>/<MONTH>_YTD_REPORT.html
```

The combined report is the primary deliverable; the individual files are optional artifacts for historical parallel with the earlier report family. If you skip the individual files for a given month, note it in the commit message.

## Step 10 — Commit

```bash
cd /Users/benfife/github/ammonfife/genomic
git add \
  Clients/<client>/data/<month>-<year>-ground-truth.json \
  Clients/<client>/data/performance_60days.csv \
  Clients/<client>/<MONTH>_COMBINED_REPORT.html \
  Clients/<client>/<MONTH>_EMAIL_DRAFT.html
git commit -m "$(cat <<'EOF'
feat(<client>): <month> <year> monthly report — full-account pull

Headline: <one sentence — direction, magnitude, CAC>.
Ground truth: data/<month>-<year>-ground-truth.json.
Cross-checked against Google Ads UI CSV export: ✓ match to the penny.
Campaigns included: N (X Search + Y Display).

Draft saved to Gmail for Ben's review. Not sent.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

## Step 11 — Log to Turso

Insert a memory row marking the run. Use the HTTP pipeline API (the `turso` CLI may not be authenticated):

```bash
source ~/.moltbot/turso-bigmac.env
URL=$(echo "$TURSO_DATABASE_URL" | sed 's|libsql://|https://|')/v2/pipeline
TODAY=$(date -u +%Y-%m-%d)
python3 - <<'PY'
import json, urllib.request, os, subprocess
URL = subprocess.check_output(['bash','-c','source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_DATABASE_URL" | sed "s|libsql://|https://|"']).decode() + "/v2/pipeline"
TOKEN = subprocess.check_output(['bash','-c','source ~/.moltbot/turso-bigmac.env && echo -n "$TURSO_AUTH_TOKEN"']).decode()
content = "Ran /monthly-report for <client> covering <month> <year>. Ground truth saved. Draft created. Not sent."
body = {"requests":[{"type":"execute","stmt":{
  "sql":"INSERT INTO memory (agent_id, date, content, tags, created_by, created_by_platform) VALUES (?, ?, ?, ?, ?, ?)",
  "args":[
    {"type":"text","value":"Claude"},
    {"type":"text","value":"<today>"},
    {"type":"text","value":content},
    {"type":"text","value":"monthly-report,<client>,<month>-<year>"},
    {"type":"text","value":"Claude"},
    {"type":"text","value":"darwin"}
  ]}}]}
req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json"})
print(urllib.request.urlopen(req,timeout=20).read().decode()[:200])
PY
```

## Step 12 — Final report to user

Output a concise summary:
- Combined report path
- Draft saved: yes / no (reason)
- Numbers: spend / conv / CAC for the month, vs prior
- Any campaigns added or removed
- Any sanity check that failed

## Hard rules (never violate)

1. **Never query with `WHERE campaign.id = X`.** Always full-account. Filter post-query if needed.
2. **Never send email autonomously.** Drafts only, always.
3. **Never generate a report if any sanity check fails.** Stop, ask Ben, fix the data.
4. **Never trust a single source.** API pull + Google Ads UI CSV cross-check are both mandatory before send.
5. **Never reuse narrative language from a prior month** without re-validating every number referenced. Chloe's March draft carried forward the Feb "efficiency improving" narrative against wrong March numbers and almost shipped "volume dipped" when reality was "nearly doubled."
6. **Never delete a backup.** The prior month's report files stay on disk as `.backup` so future audits can diff.

## Known working artifacts from the 2026-04-08 run (reference)

- `MARCH_COMBINED_REPORT.html` — exemplar combined format
- `data/march-2026-ground-truth.json` — exemplar ground-truth schema
- `HOW_MARCH_REPORT_WENT_WRONG_2026-04-08.md` — why every one of these rules exists
- `sent-archive/` — the actual Feb emailed bodies extracted from Mail.app, structural templates for future months
- Commit `420fe4c` in genomic repo — the corrected fetch_performance_data.py + all the above

## Extending to other clients

To support a second client (e.g. a hypothetical "acme-corp"):

1. Ensure `Clients/acme-corp/auth/google-ads.json` exists
2. Update the `CUSTOMER_ID` at the top of Step 2
3. Update the default recipient
4. All other steps transfer unchanged

The skill is written around Avalara Capital because that's the only live client as of 2026-04-08. Parameterize by client when a second one ships.
