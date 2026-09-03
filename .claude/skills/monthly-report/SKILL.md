---
name: monthly-report
description: Generate the monthly client performance report for Avalara Capital (extensible to other Genomic clients). Blended Google Ads + LinkedIn, May-format HTML with prose, penny-verified against three API query shapes, delivered as a Gmail draft via copy-paste from the rendered page. Never sends. Encodes the 2026-04-08 50%-underreporting incident and the 2026-09-03 format/delivery corrections.
---

# /monthly-report

Generate the monthly performance report for Avalara Capital. Execute all steps
without pausing unless a sanity check fails. **Never send email autonomously —
this skill produces drafts only.**

## Default client: Avalara Capital

- Client folder: `/Users/benfife/github/ammonfife/genomic/Clients/avalara-capital/`
- Recipient: Kyle Ivins `<kyle.ivins@avalara.com>`
- Google Ads customer: `7404128201` (Avalara - Embedded Finance)
- LinkedIn ad account: `507797315`
- Ground truth: `data/july-august-2026-ground-truth.json` (rename per cycle)
- LinkedIn rollup: `data/linkedin-monthly-rollup.json` (built from
  `data/linkedin-daily-normalized.csv`)

---

## THE FORMAT — read this before writing anything

There are four report shapes on disk. Only one is the client deliverable.

| File pattern | What it is | Send it? |
|---|---|---|
| `<MONTH>_COMBINED_REPORT.html` | **The deliverable.** Clone of `sent-archive/MAY_2026_REPORT_SENT.html` | **YES** |
| `<MONTH>_2026_MONTH_END_REPORT.html` | tables-only, by-campaign, from `build_month_end_email.py` | no |
| `<MONTH>_2026_REPORT.html` | ~44 KB variant in a Cowork outputs dir | no |
| `AVALARA_WEEKLY_REPORT_*.xlsx` | weekly workbook | no |

**Verify the format against what was actually sent, not against what is on
disk.** Search Gmail: `in:sent to:kyle.ivins@avalara.com subject:report`. The
May report (sent 2026-06-10) is the canonical structure:

1. `<h1>` title + subtitle line
2. **Headline** insight block (prose paragraph)
3. Section **1** — `<Month> Performance`: 4 hero tiles + benchmark table
4. Section **2** — `Month-over-Month: <Prior> → <Month>`: delta table +
   narrative paragraph + channel detail table
5. Section **3** — `2026 Year-to-Date (Jan – <Month>)`: 4 YTD tiles + monthly
   trajectory table
6. **Key Takeaways** — bullets

Builder: `scripts/build_combined_report.py`. CSS: `scripts/may_report.css`
(extracted verbatim from the sent May report).

### Content rules (learned 2026-09-03, each one from a correction)

- **Blend Google Ads + LinkedIn.** Google-only understates badly: July was
  $8,431.55 Google vs **$11,236.92 blended**; YTD $34,747.16 vs **$40,747.16**.
  Subtitle reads `Google Ads + LinkedIn | Full Account`.
- **Channels are Search / Video & Display / LinkedIn / Blended.** Video&Display
  groups `DISPLAY + VIDEO + DEMAND_GEN`. Google-as-a-whole is also acceptable.
  Never break out individual campaigns — no sent email ever has.
- **No IDs.** No customer ID, no LinkedIn account ID, no campaign IDs.
- **Month is the finest date granularity.** Never "July 18" or "August 19" —
  write "mid-month", "in July", "during the month". Scan the output for
  `Month DD`, ISO and slash date patterns before shipping.
- **No source footer.** No "Source: Google Ads API full-account pull,
  customer …, Period YYYY-MM-DD to YYYY-MM-DD".
- **Prose: yes. Advice: no.** Keep the Headline paragraph, the MoM narrative
  and Key Takeaways. Cut: next steps, strategy changes, an Outlook section,
  anything alarming or blunt.
- **Banned phrases** (scan before shipping): `next step`, `recommend`,
  `we should`, `outlook`, `action needed`, `collapse`, `starved`, `root cause`,
  `suppressed`, `overshot`, and the whole attribution caveat family —
  `pending`, `attribution`, `Salesforce`, `Adobe`, `generic Avalara`,
  `validation`, `outstanding`. Ben rejected each of these by name.
- **Framing that was approved:** spend running hot early in a month followed by
  tightened price targets is described as a deliberate action we took, not a
  defect we discovered. Keep every report internally consistent with that.

---

## Step 0 — Freshness gate (MANDATORY)

The 2026-04-08 incident: the puller was in single-campaign mode and understated
March by 50%. See `HOW_MARCH_REPORT_WENT_WRONG_2026-04-08.md`.

```bash
cd /Users/benfife/github/ammonfife/genomic/Clients/avalara-capital/scripts
grep -n 'CAMPAIGN_ID = "[0-9]\|campaign\.id = ' fetch_performance_data.py
grep -n 'CAMPAIGN_ID = "[0-9]' monitor_tracking.py check_conversion_details.py update_budget.py
```

Matches are only acceptable inside a `HISTORICAL NOTE` docstring. Anything else
— **STOP** and re-apply commit `420fe4c`. `update_budget.py` is on the write
path and must never run in single-campaign mode.

## Step 1 — Pin the month explicitly

**Never derive the window from an MTD cutoff.** On 2026-09-03 a
`MTD_END = today - 1` cutoff silently pulled Sep 1–2 into the August figure
($530.81 instead of $478.70). Hard-code both ends:

```python
("august_2026",          "2026-08-01", "2026-08-31"),   # complete month
("september_2026_mtd",   "2026-09-01", MTD_END.isoformat()),
("ytd_through_august_2026", "2026-01-01", "2026-08-31"),
```

If the month just closed, report it as complete. Check the real date with
`date.today()` — a long session can roll past midnight or a month boundary.

## Step 2 — Pull ground truth (full account, full precision)

Puller: `scripts/fetch_july_august_2026-08-27.py` (rename per cycle). Rules:

- `WHERE campaign.status != 'REMOVED'` — **never** `WHERE campaign.id = X`.
- **Do not round conversions.** Store the raw float; format only at display.
  Rounding to 1dp gave July 160.70 instead of 160.68; rounding to 2dp still gave
  CAC $69.93 instead of $69.94. Both are visible to the client.
- **Pull YTD from the API per reporting month** (`ytd_through_<month>_2026`).
  Summing rounded monthly values drifts a cent.
- Emit `by_channel` per period (SEARCH / DISPLAY / VIDEO / DEMAND_GEN) and
  `by_campaign` for internal use only.
- LinkedIn: `scripts/_li_monthly.py` rolls
  `data/linkedin-daily-normalized.csv` into `data/linkedin-monthly-rollup.json`.
  **Check its last date** — it has trailed the month end (through Aug 27 for an
  Aug 31 close). Note any gap in the closing summary.

## Step 3 — Ground-truth JSON

Canonical for every downstream step. Include `source`, `customer_id`, `scope`,
`periods{}` with derived cac/cpc/ctr/conv_rate, `by_channel`, `by_campaign`,
and `cross_check`.

## Step 4 — Sanity assertions (MANDATORY)

1. ≥2 campaigns with delivery in the report month.
2. Prior month matches the prior cycle's ground-truth JSON.
3. No period silently zero.

Failing any of these blocks generation. Do not "fix" a number by hand.

## Step 5 — Cross-check with three independent query shapes

The old step asked Ben for a Google Ads UI CSV. **Three API shapes are faster
and self-verifying** — campaign-level vs customer-level vs ad-level:

```python
FROM campaign  WHERE campaign.status != 'REMOVED'   # primary
FROM customer                                        # account rollup
FROM ad_group_ad                                     # summed from ad grain
```

All three must agree to `$0.0000` and `0.0000` conversions. Compare **raw**
values — comparing already-rounded ones produced a false MISMATCH on a $0.004
delta. A UI CSV export remains a valid extra check; the `" -- "` summary row
must be excluded or totals double.

## Step 6 — Build the report

```bash
python3 scripts/build_combined_report.py     # writes <MONTH>_COMBINED_REPORT.html
```

Then scan the output:

```bash
# no day-level dates, no IDs, no banned phrases, no leftover template braces
grep -nE '(January|February|…|December|Jan|Feb|…|Dec)[[:space:]]+[0-9]{1,2}\b' <MONTH>_COMBINED_REPORT.html
grep -nE '7404128201|507797315|\{[a-z_]+\}' <MONTH>_COMBINED_REPORT.html
```

## Step 7 — Email body HTML

```bash
python3 scripts/inline_email_html.py    # <MONTH>_EMAIL_BODY.html
```

Inlines the class-based CSS. Two Gmail-sanitizer traps this handles:

- **Gmail strips `background:` from CSS.** Purple `#667eea` table headers with
  white text became **white-on-white and invisible**. The converter falls back
  to dark text on a light `bgcolor` attribute so it reads either way.
- The right-align regex must capture *up to but not including* the closing
  quote. Capturing the quote produces `style="…";text-align:right"` — a broken
  attribute. Same bug bit a "compress the CSS" pass that ate the `;` separator
  and produced `#ecf0f1text-align:right`. **Assert** after any string surgery:

```python
assert "ecf0f1text" not in h and '";text-align' not in h
```

## Step 8 — Gmail draft: COPY-PASTE, not the API

**This is the only reliable path, and Ben has insisted on it.** Writing HTML
through `create_draft` works but loses backgrounds to the sanitizer. Pasting
from the rendered page carries Chrome's *computed* styles, so the purple
headers survive (`rgb(102, 126, 234)` confirmed in the compose DOM).

Procedure per month:

1. Create an empty draft via API to get a stable draft id and set
   subject + recipient:
   `create_draft(to=[kyle], subject="Avalara Capital: <Month> Report", htmlBody="<div>&nbsp;</div>")`
2. Open the rendered `<MONTH>_COMBINED_REPORT.html` in a Chrome tab.
   `⌘A`, `⌘C` via System Events.
3. Open the draft: `https://mail.google.com/mail/u/4/#drafts?compose=<messageId>`
   in **its own window**.
4. **Scroll the compose body into view and confirm it.** This is the whole
   failure mode: the body renders ~8,400 px tall and sat at `rect.top = -6115`,
   so `⌘A`/`⌘V` never reached the editor — the paste **appended**, and June and
   July ended up with three stacked copies. Verify `rect.top > 0` and
   `document.activeElement === body` before pasting.
5. Focus the body, `selectNodeContents`, then `⌘V`.
6. **Verify the result** — do not assume:

```js
var d=document.querySelector('div[aria-label="Message Body"]');
var t=d.innerText.replace(/\s+/g,' ').trim();
// titles must be 1, takeaways must be 1
(t.match(/Performance Report/g)||[]).length
(t.match(/Key Takeaways/g)||[]).length
getComputedStyle(d.querySelectorAll('th')[0]).backgroundColor  // want rgb(102,126,234)
```

7. Read the draft back with `get_draft` and confirm subject, recipient and a
   single copy.

Gmail's AppleScript `execute javascript` needs "Allow JavaScript from Apple
Events" enabled in Chrome's Develop menu.

**Hard rule: this skill never sends.** Ends at "draft created". Ben sends.

## Step 9 — Open for review

Open each `<MONTH>_COMBINED_REPORT.html` in one window, tabs not windows,
unless Ben asks otherwise.

## Step 10 — Commit

The genomic repo has an autocommit hook; it often lands the work before a manual
`git commit` runs ("nothing to commit, working tree clean" is normal). Check
`git log --oneline -3` and confirm the files are in a commit either way. Keep
prior report HTML as `.backup-<date>`.

## Step 11 — Log to Turso

Facts + a captains_log entry via the HTTP pipeline
(`scripts/log_to_turso.py`). Todos for anything queued for Ben.

## Step 12 — Closing summary

Report: file paths, draft ids, spend/conv/CAC per month and YTD, any sanity
check that failed, and any data gap (for example LinkedIn trailing the month
end). No next-steps list as a substitute for finished work.

---

## Hard rules

1. **Never** `WHERE campaign.id = X`. Full account, filter after.
2. **Never** send email. Drafts only.
3. **Never** generate a report if a sanity check fails.
4. **Never** trust one source — three API query shapes must agree.
5. **Never** reuse prior-month narrative without re-validating every number.
6. **Never** delete a backup.
7. **Never** round conversions before computing CAC.
8. **Never** let an MTD cutoff define a completed month.
9. **Never** rely on CSS `background:` in an email — Gmail strips it.
10. **Never** paste into a Gmail compose without confirming the body is
    on-screen and focused, then verifying the copy count afterward.

## Reference artifacts

- `sent-archive/MAY_2026_REPORT_SENT.html` — canonical format
- `HOW_MARCH_REPORT_WENT_WRONG_2026-04-08.md` — why Steps 0/4/5 exist
- `scripts/build_combined_report.py` — deliverable builder
- `scripts/inline_email_html.py` — Gmail-safe inliner
- `scripts/fetch_july_august_2026-08-27.py` — full-account puller + cross-check
- `scripts/_li_monthly.py` — LinkedIn monthly rollup
- `scripts/build_month_end_email.py` — tables-only variant (NOT the deliverable)
- Commit `420fe4c` — the single-campaign fix

## 2026-09 cycle, for continuity

| Month | Spend | Conversions | CAC |
|---|---|---|---|
| June | $8,749.08 | 110.00 | $79.54 |
| July | $11,236.92 | 160.68 | $69.94 |
| August | $532.21 | 23.00 | $23.14 |
| YTD Jan–Aug | $40,747.15 | 598.30 | $68.10 |

June, July and August 2026 were all sent on 2026-09-03 (May had been the last
report sent, on 2026-06-10 — always check for a backlog rather than assuming
only the latest month is due).
