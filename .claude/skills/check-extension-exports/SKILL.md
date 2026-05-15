---
name: check-extension-exports
description: Find extension-scraped pages, HTML captures, and session data written by the lkup.info browser extension into Supabase raw tables.
---

# /check-extension-exports — Find Extension-Scraped Data in lkup Supabase

Find pages, HTML captures, and session data that the lkup.info browser extension auto-imported into Supabase's raw schema.

## Tables to check (raw schema)

| Table | What it stores | Key fields |
|-------|---------------|------------|
| `raw.cert_scrapes` | Raw HTML + JSON from grader cert pages, and tagged sessions | `url`, `html`, `user_note`, `scraper`, `extension_version` |
| `raw.page_captures` | Full page HTML captured by extension autoscope | `url`, `hostname`, `html`, `scope_data`, `capture_type` |
| `raw.harvested_urls` | Every URL discovered by extension | `url`, `url_type`, `found_by`, `status` |
| `raw.scan_events` | Barcode scan events with session/metadata | `session_id`, `raw_barcode`, `source`, `metadata` |

## Service role key

```bash
SRK=$(grep LKUP_SUPABASE_SERVICE_ROLE_KEY ~/github/ammonfife/lkup.info/.env | cut -d'"' -f2)
```

## How to search

### By URL pattern (e.g. find claude.ai sessions)
```bash
SRK=$(grep LKUP_SUPABASE_SERVICE_ROLE_KEY ~/github/ammonfife/lkup.info/.env | cut -d'"' -f2)

curl -s "https://vsotvatntzlrzrhemayh.supabase.co/rest/v1/cert_scrapes?select=id,url,user_note,scraper,scraped_at&url=like.%25PATTERN%25&limit=20" \
  -H "apikey: $SRK" -H "Authorization: Bearer $SRK" -H "Accept-Profile: raw"
```

### By user_note tag (e.g. 'claudecodesession')
```bash
curl -s "https://vsotvatntzlrzrhemayh.supabase.co/rest/v1/cert_scrapes?select=id,url,html,user_note,scraped_at&user_note=eq.TAG&limit=10" \
  -H "apikey: $SRK" -H "Authorization: Bearer $SRK" -H "Accept-Profile: raw"
```

### By hostname in page_captures
```bash
curl -s "https://vsotvatntzlrzrhemayh.supabase.co/rest/v1/page_captures?select=id,url,hostname,capture_type,captured_at&hostname=like.%25HOSTNAME%25&limit=20" \
  -H "apikey: $SRK" -H "Authorization: Bearer $SRK" -H "Accept-Profile: raw"
```

### Get HTML content and extract conversation/intent
```bash
curl -s "https://vsotvatntzlrzrhemayh.supabase.co/rest/v1/cert_scrapes?select=html&user_note=eq.claudecodesession&limit=1" \
  -H "apikey: $SRK" -H "Authorization: Bearer $SRK" -H "Accept-Profile: raw" | python3 -c "
import json,sys,re
d=json.loads(sys.stdin.read())
html=d[0]['html']
# Extract large text blocks (conversation content)
blocks=re.findall(r'>([^<]{100,})<', html)
for b in blocks[:20]:
    print(b[:400])
    print('---')
"
```

## Tagged sessions

The extension marks special captures with `user_note`. Known tags:
- `claudecodesession` — a shared Claude Code session page was tagged and saved

## When running this skill

1. Get SRK from `.env` or `bigmac-secrets get SUPABASE_SERVICE_ROLE_KEY`
2. Query the relevant table using `Accept-Profile: raw` header
3. Filter by URL pattern, hostname, or user_note tag
4. If HTML is present, extract conversation using the regex pattern above
5. The second session `01BuW9rTCajWy2d45GuV4gSe` was NOT captured — only `01JoL2fenAdwAXC9z8kKXE3v`

## Full table count check
```bash
for table in cert_scrapes page_captures harvested_urls scan_events; do
  count=$(curl -s "https://vsotvatntzlrzrhemayh.supabase.co/rest/v1/$table?select=id" \
    -H "apikey: $SRK" -H "Authorization: Bearer $SRK" -H "Accept-Profile: raw" \
    -H "Prefer: count=exact" -I 2>/dev/null | grep -i content-range | grep -oP '\d+$')
  echo "raw.$table: $count rows"
done
```
