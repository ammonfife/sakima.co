---
name: test-lkup
description: Full E2E test suite for lkup.info — all input types (numeric barcode, URL barcode, manual cert, photo upload), all surfaces (web, extension, Edge Functions, CF Workers, desktop scanner, OBS, SMS), all graders (NGC/PCGS/CAC/ANACS/ICG/SEGS/GONGBO/CNGC/WPT/CSIS), all pipeline stages (scan→enrich→price→collections→listings). Every failure = instant Turso todo + root-cause screenshot. Nothing is a stub.
user-invocable: true
---

@~/.claude/skills/lkup-shared-context/CONTEXT.md

### Platform notes
- **Claude Code / OpenClaw:** `Bash run_in_background`, `str_replace_editor`
- **Gemini:** `multi_replace_file_content`, `run_command` with `WaitMsBeforeAsync`
- **Codex / Grok:** native file-edit + terminal APIs

# /test-lkup — Full E2E Test Suite for lkup.info

## Testing Policy (non-negotiable)

> **Every error found during testing must be instantly fixed or filed as a Turso todo.**
> Nothing in lkup.info is a stub. Nothing is "future integration." If it doesn't work, the test found a bug — fix it or file it.

```bash
todo add "describe the failure" --tags=lkup,test --assign=claude --priority=p1
```

**HTTP 200 ≠ working.** Always verify actual response body content and Supabase row state.  
**Screenshot ≠ passing.** A screenshot of a spinner or blank state is a failure.  
**"Previously worked" ≠ still works.** Re-verify every flow on every run.

---

## When to Run

- After any lkup.info deploy (Lovable publish)
- After any Edge Function change
- After any extension version bump
- After any schema migration
- After any CF Worker deploy
- Before declaring a feature "done" — screenshot proof required

---

## Pre-Run Checklist

### 1. Sync knowledge files (do this first — agents need current schema context)

```bash
cd ~/github/ammonfife/lkup.info

# Refresh lkup_knowledge.md (Turso facts + policies + todos → markdown)
node scripts/snapshot-lkup-knowledge.mjs

# Refresh SCHEMA_DICTIONARY.md (DB → markdown, report undocumented columns)
python3 scripts/sync-column-dictionary.py --check --export
```

Then READ the relevant sections before testing:
- **`lkup_knowledge.md`** — what the system currently knows: schema state, enrichment pipeline status, todos. Read the `certs`, `grader_data`, `pricing_consensus` sections before barcode/enrichment tests.
- **`docs/SCHEMA_DICTIONARY.md`** — column semantics and UUID linkage. Read the table section for any table you'll be querying or asserting against. Tells you which columns are canonical vs. derived vs. deprecated.

Both files are auto-refreshed on every `git push` via `.githooks/pre-push`. If the repo is fresh and you haven't pushed recently, refresh manually above.

### 2. Refresh test fixtures

```bash
# Append new valid barcodes/certs from Supabase (validity-gated, append-only)
python3 test/scripts/update-fixtures.py --apply

# Download fresh slab images for upload tests
python3 test/scripts/refresh-test-images.py --from-catalog --count 30
```

---

## Input Types — All Must Be Tested

Every run exercises at least one input of each type. Rotate through `test/fixtures/known-good-barcodes.json` to avoid cache hits.

### Type A — Numeric Barcode (physical scanner output)

| Grader | Format | Example | Source |
|--------|--------|---------|--------|
| NGC | 20-digit GS1 | `40806369008665933283` | known-good-barcodes.json NGC.verified |
| PCGS | 16-digit | `0071186128235924` | known-good-barcodes.json PCGS.verified |
| PCGS | 22-digit | `1000084000064046637738` | known-good-barcodes.json PCGS |
| CAC | 24-digit | `000104116600000746187045` | known-good-barcodes.json CAC |
| ANACS | 20-digit GS1 | `02225564047288301000` | known-good-barcodes.json ANACS |
| ANACS | 10-digit | `2000601600` | known-good-barcodes.json ANACS |
| ICG | 18-digit | `482474694145340308` | known-good-barcodes.json ICG |
| SEGS | 20-digit | `53719115450247036081` | known-good-barcodes.json SEGS |

### Type B — URL Barcode (QR code on international slab)

| Grader | URL pattern | Source |
|--------|-------------|--------|
| GONGBO | `https://m.gongbocoins.com/k/…` | known-good-barcodes.json GONGBO |
| CNGC | `http://www.cngccoin.com/pro/…` | known-good-barcodes.json CNGC |
| WPT | `http://z.wpt.la/…` | known-good-barcodes.json WPT |
| CSIS | `https://www.csis.vip/Product/…` | known-good-barcodes.json CSIS |

### Type C — Manual Cert Entry (grader + cert number, no barcode)

Use `known-good-certs.json` entries where `desc` is populated (real enrichment confirmed).

### Type D — Photo Upload (slab image)

- **With visible barcode label:** system detects barcode → full enrichment pipeline
- **Raw coin photo (no slab):** AI vision fallback → coin identification + estimated grade

```bash
# Real slab photos from Supabase cert_photos/listing_comps:
test/fixtures/images/                  # populated by refresh-test-images.py

# Sample slab reference images (AI vision only — NOT real cert barcodes):
test/fixtures/static-coin-images.json  # sampleslabs.com
```

### Type E — Desktop Scanner Input

Verify `desktop/unified/interfaces/gui/desktop_scanner.py` correctly processes USB/BT barcode → Supabase write → enrichment trigger → label print.

---

## Test Surfaces

### Surface 1 — Web App (lkup.info)

E2B desktop sandbox, Chrome via CDP. 5 ICP personas, each with unique certs.

```
abenfife.ben@gmail.com       / LkupTest2026!ben       (power dealer / admin)
abenfife.marcus@gmail.com    / LkupTest2026!marcus    (weekend Whatnot dealer)
abenfife.dave@gmail.com      / LkupTest2026!dave      (show booth dealer)
abenfife.jess@gmail.com      / LkupTest2026!jess      (eBay flipper)
abenfife.patricia@gmail.com  / LkupTest2026!patricia  (hobbyist collector)
```

### Surface 2 — Browser Extension (lkup_helper)

Always bump manifest version before loading — Chrome caches by version.

```bash
node extension/scripts/bump-version.js patch
git add extension/manifest.json && git commit -m "test: bump extension version"
```

Load in E2B Chrome via `--load-extension=<path>`.

### Surface 3 — Edge Functions (direct HTTP)

```bash
EDGE_BASE="https://vsotvatntzlrzrhemayh.supabase.co/functions/v1"
ANON=$(security find-generic-password -s supabase_lkup_anon_key -w)

curl -sS -X POST "$EDGE_BASE/scan" \
  -H "Authorization: Bearer $ANON" \
  -H "Content-Type: application/json" \
  -d '{"barcode":"40806369008665933283"}' | python3 -m json.tool
```

### Surface 4 — Cloudflare Workers (direct HTTP)

```bash
curl -X POST https://lkup-api.sakima-api.workers.dev/api/parse \
  -d '{"title":"1881-S Morgan Dollar MS65 PCGS"}'
```

### Surface 5 — Desktop Scanner

```bash
cd ~/github/ammonfife/lkup.info/desktop/unified
python3 interfaces/gui/desktop_scanner.py --test-mode --barcode "40806369008665933283"
```

---

## Full Test Matrix

### Group 1 — Authentication

| # | Input | Expected | Verify in Supabase |
|---|-------|----------|--------------------|
| 1.1 | Sign in (email + password) | Redirects to /dashboard | `auth.users` session alive |
| 1.2 | Session persistence (refresh page) | Still logged in | — |
| 1.3 | Admin user role check | Admin nav visible | `user_roles.role = 'admin'` |
| 1.4 | Non-admin user | No admin nav | — |
| 1.5 | Sign out | Redirects to /login | Session invalidated |

### Group 2 — Barcode Scan → Enrichment Pipeline

For every grader: submit barcode → `certs` row created → enrichment fields populated.

| # | Input | Pipeline fired | Key output fields |
|---|-------|----------------|-------------------|
| 2.1 | NGC 20-digit | scan EF → enqueue-enrichment → certlookup + CCG-OPS + CPG | `description`, `grade`, `grader_data` rows, `pricing_consensus` |
| 2.2 | PCGS 16-digit | scan EF → GetCoinFactsByCertNo | `description`, `pcgs_number`, `grade` |
| 2.3 | PCGS 22-digit | Same as 2.2 | Same |
| 2.4 | CAC 24-digit | scan EF → CAC certlookup | `description`, `grade` |
| 2.5 | ANACS 20-digit GS1 | scan EF → ANACS portal | `service=ANACS`, `cert_number` correct |
| 2.6 | ANACS 10-digit | Same | Same |
| 2.7 | ICG 18-digit | scan EF → ICG portal | `service=ICG`, enrichment fields |
| 2.8 | SEGS 20-digit | scan EF → barcode parse | `cert_number` = LAST 8 digits (not last 10) |
| 2.9 | GONGBO URL barcode | scan EF → gongbo-enrich EF | `service=GONGBO`, `grader_data` row |
| 2.10 | CNGC URL barcode | scan EF | `service=CNGC` |
| 2.11 | WPT URL barcode | scan EF | `service=WPT` |
| 2.12 | CSIS URL barcode | scan EF | `service=CSIS` |

**Enrichment completeness check (run after each 2.x):**
```bash
SVC=$(security find-generic-password -s supabase_lkup_service_role_key -w)
curl -s "${SUPA_URL}/rest/v1/certs?raw_barcode=eq.<barcode>&select=service,cert_number,description,grade,enrichment_attempted_at" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" | python3 -c "
import json,sys
r = json.load(sys.stdin)
assert r, 'FAIL: no certs row'
assert r[0].get('description'), f'FAIL: description null — cert={r[0].get(\"cert_number\")}'
assert r[0].get('enrichment_attempted_at'), 'FAIL: enrichment never attempted'
print('PASS:', r[0]['service'], r[0]['cert_number'], 'grade='+str(r[0]['grade']))
"
```

### Group 3 — Manual Cert Entry

| # | Input | Expected | Verify |
|---|-------|----------|--------|
| 3.1 | NGC cert + service | Coin page loads, enrichment fires | Same as 2.1 |
| 3.2 | PCGS cert | Coin page loads | Same as 2.2 |
| 3.3 | Invalid cert number | Error state shown (not blank, not crash) | No phantom `certs` row |

### Group 4 — Photo Upload

| # | Input | Expected path | Verify |
|---|-------|---------------|--------|
| 4.1 | Slab photo with clear barcode | Barcode detected → full enrichment | `barcode_cert_xref` row created |
| 4.2 | Slab photo, barcode unreadable | AI vision fallback → coin identified | `cert_photos` row, `coin_id` populated |
| 4.3 | Raw coin photo (no slab) | AI vision → coin type + estimated grade | `cert_photos` row, no `certs` row |
| 4.4 | Multiple photos (batch) | All processed | N rows in `cert_photos` |
| 4.5 | Non-coin image | Graceful error shown | No phantom rows |

### Group 5 — Pricing Pipeline

| # | What to verify | Expected | Query |
|---|----------------|----------|-------|
| 5.1 | PCGS price guide | `certs.price_guide` not null after enrichment | `SELECT price_guide FROM certs WHERE ...` |
| 5.2 | NGC CPG pricing | `pricing_consensus` row exists | `SELECT * FROM pricing_consensus WHERE cert_id=...` |
| 5.3 | Greysheet CPG | `grader_data` row with source=cpg | `SELECT * FROM grader_data WHERE ...` |
| 5.4 | eBay comp pricing | `listing_comps` row present | `SELECT count(*) FROM listing_comps` |
| 5.5 | Whatnot comp pricing | `listing_comps` row present | Same |
| 5.6 | Melt value | Not null for silver/gold coins | `SELECT agwoz, fineness FROM certs WHERE ...` |
| 5.7 | Price visible on coin page | `/coin/<uid>` price field populated | Screenshot: price not blank |

### Group 6 — Collections

| # | Flow | Expected | Verify |
|---|------|----------|--------|
| 6.1 | Create new collection | Visible in list | `SELECT * FROM collections WHERE user_id=...` |
| 6.2 | Scan to collection (`?collection=slug`) | Cert added | `collections.cert_ids` updated |
| 6.3 | Batch scan (`?batch=true`) | Multiple certs added | Cert count incremented |
| 6.4 | View collection contents | Certs listed with descriptions | Screenshot: populated list |
| 6.5 | Remove cert from collection | Cert gone | `cert_ids` array updated |

### Group 7 — Inventory

| # | Flow | Expected | Verify |
|---|------|----------|--------|
| 7.1 | `/inventory` page loads | Items visible (not blank, not spinner) | Screenshot: items with prices |
| 7.2 | Margin applied correctly | Price = guide × dealer margin | `dealer_settings` row applied |
| 7.3 | Filter by grader | Only that grader's coins | — |
| 7.4 | Filter by collection | Only collection's coins | — |

### Group 8 — Listings (eBay / Whatnot)

| # | Flow | Expected | Verify |
|---|------|----------|--------|
| 8.1 | Talking points generation | Non-empty response with coin facts | `draft_listings` row created |
| 8.2 | eBay listing draft | Draft visible in inventory | `draft_listings.status=draft` |
| 8.3 | eBay listing publish | Published | `ebay_listing_xref` row created |
| 8.4 | eBay sold webhook | Inventory item marked sold | `sold_archive` row created |

### Group 9 — Browser Extension (lkup_helper)

Must run in E2B desktop. Bump manifest version before every test run.

| # | Surface URL | Input | Expected | Verify in Supabase |
|---|-------------|-------|----------|--------------------|
| 9.1 | ngccoin.com cert page | Open cert page | Auto-scrape fires | `grader_data` + `certs` row |
| 9.2 | pcgs.com cert page | Open cert page | Auto-scrape fires | `grader_data` + `certs` row |
| 9.3 | cacgrading.com cert page | Open cert page | Auto-scrape fires | `certs.service=CAC` |
| 9.4 | anacs.org cert page | Open cert page | Auto-scrape fires | `certs.service=ANACS` |
| 9.5 | icgcoin.com cert page | Open cert page | Auto-scrape fires | `certs.service=ICG` |
| 9.6 | Whatnot listing page | Any Whatnot lot | Price overlay visible | — |
| 9.7 | eBay listing page | Any eBay lot | Price overlay visible | — |
| 9.8 | Whatnot live show | Join active show | Hot-label panel available | — |
| 9.9 | Admin popup → Scope ON | Enable scope recording | Network calls captured | `network_scope` rows written |
| 9.10 | Null-safe guard | Cert with null fields | No null overwrites on existing rows | Existing non-null values unchanged after re-scan |

### Group 10 — Edge Functions (direct HTTP)

| # | EF | Method | Sample payload | Expected response |
|---|---|--------|----------------|-------------------|
| 10.1 | `scan` | POST | `{"barcode":"40806369008665933283"}` | cert_id + coin_current data |
| 10.2 | `enqueue-enrichment` | POST | `{"cert_id":"NGC-8665933283"}` | Enrichment triggered, returns job_id |
| 10.3 | `price-guide` | POST | `{"cert_id":"...","service":"PCGS"}` | Price object |
| 10.4 | `coin-action` | POST | `{"action":"collection","cert_id":"...","collection_slug":"..."}` | Cert added to collection |
| 10.5 | `obs-state` | GET | — | Current OBS overlay state JSON |
| 10.6 | `obs-state` | POST | `{"cert_id":"...","action":"show"}` | OBS state updated |
| 10.7 | `listing-draft` | POST | `{"cert_id":"..."}` | Draft listing created |
| 10.8 | `ingest-scope` | POST | Scope payload | Rows written to `network_scope` |
| 10.9 | `parse-page-captures` | POST | HTML payload | Structured data extracted |
| 10.10 | `gongbo-enrich` | POST | `{"cert_id":"...","url":"https://m.gongbocoins.com/k/..."}` | GONGBO data written to `grader_data` |
| 10.11 | `sms-inbound` | POST | `{"from":"+1...","body":"40806369008665933283"}` | Scan triggered, SMS response queued |
| 10.12 | `lot-scan` | POST | `{"barcode":"...","lot_id":"..."}` | Lot scan recorded |
| 10.13 | `coin-id-bridge` | POST | `{"cert_id":"..."}` | coin_id resolved |
| 10.14 | `resolve-uuid` | POST | `{"barcode":"..."}` | lkup_uuid returned |
| 10.15 | `flags` | GET | — | Feature flags JSON |
| 10.16 | `coin-id-hygiene` | POST | `{"cert_id":"..."}` | Hygiene check result |
| 10.17 | `learn-selectors` | POST | Selector payload | Selectors updated |
| 10.18 | `mirror-image` | POST | `{"cert_id":"...","image_url":"..."}` | Image mirrored to R2 |

### Group 11 — Cloudflare Workers

| # | Worker | Test | Expected |
|---|--------|------|----------|
| 11.1 | `lkup-api` /api/parse | POST coin title | Returns `{grader, cert, grade}` parsed |
| 11.2 | `greysheet-scraper` | GET ?gsid=<id> | Price data JSON, not empty |
| 11.3 | `whatnot-comp-scraper` | GET ?query=<coin> | Sold comps array |
| 11.4 | `coin-vision` | POST image | AI identification result |
| 11.5 | `e2b-pool-lb` /health | GET | `{"status":"ok"}` with live pool count |
| 11.6 | `e2b-pool-lb` /pool/claim/desktop | POST (body: empty) | `{"status":"claimed","sandbox_id":"..."}` — NOT `GET /pool/desktop` (that returns 403) |

### Group 12 — OBS Overlay

| # | Flow | Expected | Verify |
|---|------|----------|--------|
| 12.1 | Load /obs page | Overlay HTML renders | Screenshot: overlay visible (not blank) |
| 12.2 | POST coin to obs-state | Overlay updates | Screenshot: coin info displayed |
| 12.3 | Reload overlay page | Shows last coin | obs-state GET returns last coin |

### Group 13 — Settings

| # | Setting | Input | Expected | Verify |
|---|---------|-------|----------|--------|
| 13.1 | Dealer margin (4 fields) | Change + save | Values persisted | `dealer_settings` row updated |
| 13.2 | Profile display name | Update + save | Saved | `dealers` row updated |
| 13.3 | eBay account status | View settings | Shows connected/disconnected | `dealer_platform_accounts` |

### Group 14 — Desktop Scanner

| # | Test | Input | Expected |
|---|------|-------|----------|
| 14.1 | Barcode scan (all graders) | USB/BT barcode string | `certs` row created, enrichment fires |
| 14.2 | Camera scan | Camera frame with slab | Same |
| 14.3 | Label print | Scanned cert | Label printed |
| 14.4 | Session analytics | Scan 5 certs | Session summary updates |
| 14.5 | Hot-label webhook | Whatnot win | Label prints automatically |

```bash
cd ~/github/ammonfife/lkup.info/desktop/unified
python3 interfaces/gui/desktop_scanner.py \
  --test-mode \
  --barcode "40806369008665933283"
# Verify: certs row created in Supabase, enrichment triggered
```

---

## Qualitative Output Verification

Tests must check that outputs **make sense**, not just that they exist. Never assume — always inspect.

### Screenshot Analysis (correct method — avoids Claude vision errors)

DO NOT pass screenshots directly to Claude in large batches or as base64 blobs. Use the `Read` tool on saved PNG files, which triggers Claude's vision on the file path. One image per check.

```python
# Save screenshot to disk first
screenshot_path = f"test/e2b-icp-tests/results/screenshots/{icp}-{test_name}.png"
page.screenshot(path=screenshot_path)

# In Claude session: verify visually by reading the file
# Read(file_path=screenshot_path)  ← triggers vision, no size errors
```

**What to look for in screenshots — qualitative checks:**

| Screen | PASS looks like | FAIL looks like |
|--------|-----------------|-----------------|
| Coin page after scan | Coin title visible, grade shown, price > $0, description 10+ words | Spinner, "Loading...", blank fields, generic error, price = $0 |
| Collection list | 1+ collection names, cert count > 0 | "No collections", empty state, mismatched count |
| Inventory | Items with coin names + prices | Blank rows, placeholder text, all prices $0 |
| Auth | User email visible in nav or profile | Login form, 401 screen |
| Extension scrape | Extension popup shows cert data | Empty popup, "Not found", console errors |

### Qualitative DB Field Checks

Beyond "not null" — check that values make sense:

```python
def qualitative_check_cert(row, barcode_input):
    """Fail if the returned data is internally inconsistent."""
    service = row.get("service", "")
    cert = row.get("cert_number", "")
    grade = row.get("grade", "")
    desc = row.get("description", "")

    # Service must match what the barcode implied
    assert service in {"NGC","PCGS","CAC","ANACS","ICG","SEGS","GONGBO","CNGC","WPT","CSIS"}, \
        f"FAIL: unknown service '{service}'"

    # Cert number must not be empty or suspiciously short
    assert len(cert) >= 5, f"FAIL: cert_number suspiciously short: '{cert}'"

    # Description must look like a real coin description
    assert len(desc) >= 10, f"FAIL: description too short: '{desc}'"
    assert not desc.lower().startswith("error"), f"FAIL: description is an error: '{desc}'"

    # Grade must be plausible (MS60-70, PR, SP, AU, EF, VF, etc.) or GENUINE
    if grade:
        assert any(g in grade.upper() for g in ["MS","PR","SP","AU","EF","VF","XF","F","VG","G","AG","GENUINE","BU"]), \
            f"FAIL: grade doesn't look like a coin grade: '{grade}'"

    # Price guide — if present, must be positive
    price = row.get("price_guide")
    if price is not None:
        assert float(price) > 0, f"FAIL: price_guide is 0 or negative: {price}"

    print(f"PASS qualitative: {service} {cert} {grade} '{desc[:40]}'")
```

### Domino Chain Verification (complete trigger trace)

For every barcode scan, verify the FULL downstream chain fired — not just the first step.

```
Barcode input
  ↓
  [1] scan EF called → certs row created
  ↓
  [2] enqueue-enrichment EF called → grader_data rows written (PCGS/NGC/ICG API response)
  ↓
  [3] price-guide EF called → pricing_consensus row written
  ↓
  [4] barcode_cert_xref row created (if new barcode)
  ↓
  [5] coin_current view reflects updated data
  ↓
  [6] UI coin page shows populated description + price (not spinner)
```

**Full chain verification script:**

```bash
SVC=$(security find-generic-password -s supabase_lkup_service_role_key -w)
SUPA="https://vsotvatntzlrzrhemayh.supabase.co"
B="40806369008665933283"  # replace with actual barcode

# [1] certs row
C=$(curl -s "$SUPA/rest/v1/certs?raw_barcode=eq.$B&select=id,service,cert_number,description,grade,enrichment_attempted_at" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC")
echo "=== [1] certs ===" && echo "$C" | python3 -m json.tool

# [2] grader_data rows (enrichment)
CID=$(echo "$C" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r[0]['id'] if r else '')")
echo "=== [2] grader_data ===" && \
  curl -s "$SUPA/rest/v1/grader_data?cert_id=eq.$CID&select=source,fetched_at,price_guide" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" | python3 -m json.tool

# [3] pricing_consensus
echo "=== [3] pricing_consensus ===" && \
  curl -s "$SUPA/rest/v1/pricing_consensus?cert_id=eq.$CID&select=*" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" | python3 -m json.tool

# [4] barcode_cert_xref
echo "=== [4] barcode_cert_xref ===" && \
  curl -s "$SUPA/rest/v1/barcode_cert_xref?barcode=eq.$B&select=barcode,service,cert_from_barcode,confirmed" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" | python3 -m json.tool

# If ANY step returns [] or null → file Turso todo immediately
# todo add "domino chain broken at step N: barcode=$B" --tags=lkup,test,p1 --priority=p1
```

**Cross-join sanity check (are joined columns consistent?):**

```bash
# Verify barcode_cert_xref.cert_from_barcode matches certs.cert_number
# Verify certs.service matches grader_data source prefix
# Verify pricing_consensus.cert_id matches certs.id
curl -s "$SUPA/rest/v1/certs?raw_barcode=eq.$B&select=id,service,cert_number" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" | python3 -c "
import json, sys
rows = json.load(sys.stdin)
if not rows: print('FAIL: no cert row'); exit(1)
r = rows[0]
print(f'cert_id={r[\"id\"]} service={r[\"service\"]} cert_number={r[\"cert_number\"]}')
# Now check grader_data source matches service
import urllib.request
req = urllib.request.Request(
    f'$SUPA/rest/v1/grader_data?cert_id=eq.{r[\"id\"]}',
    headers={'apikey': '$SVC', 'Authorization': 'Bearer \$SVC'}
)
gd = json.loads(urllib.request.urlopen(req).read())
for g in gd:
    src = g.get('source','')
    svc = r['service']
    consistent = svc.lower() in src.lower() or src.lower() in svc.lower()
    print(f'grader_data source={src} vs service={svc}: {\"OK\" if consistent else \"MISMATCH\"}')
"
```

### When Any Step Fails

```bash
# Immediate Turso todo — do not skip, do not defer
todo add "test: domino chain broken — <describe what failed> — barcode=<b>" \
  --tags=lkup,test,p1 --assign=claude --priority=p1

# Fix the root cause in the same session
# Re-run the full chain verification after fix
# Screenshot the passing state
```

---

## Output Verification Protocol

For every test, verify at BOTH the UI layer and the DB layer.

### UI verification (Playwright)
```python
page.wait_for_selector(".coin-description:not(:empty)", timeout=30000)
screenshot = page.screenshot()
# FAIL if: .coin-description empty, spinner visible, error state shown
```

### DB verification (Supabase REST)
```bash
SVC=$(security find-generic-password -s supabase_lkup_service_role_key -w)
SUPA_URL="https://vsotvatntzlrzrhemayh.supabase.co"
curl -s "${SUPA_URL}/rest/v1/certs?raw_barcode=eq.<barcode>&select=*" \
  -H "apikey: $SVC" -H "Authorization: Bearer $SVC" | python3 -c "
import json,sys
r=json.load(sys.stdin)
assert r, 'FAIL: no certs row'
assert r[0].get('description'), 'FAIL: description null'
assert r[0].get('enrichment_attempted_at'), 'FAIL: enrichment never attempted'
print('PASS:', r[0]['service'], r[0]['cert_number'])
"
```

---

## Error Handling Protocol

```
1. Screenshot the failure state immediately
2. Query Supabase to see what was/wasn't written
3. Check EF logs in Supabase dashboard
4. File Turso todo: todo add "test failure: <surface> <flow> — <what broke>" --tags=lkup,test,p1 --priority=p1
5. Fix root cause in same session
6. Re-run failing test to confirm fix
7. Screenshot passing state
```

Never mark passing based on HTTP 200 alone. Never skip a failure as "pre-existing."

---

## How to Run

### Full suite (5 ICPs, web + extension)
```bash
cd ~/github/ammonfife/lkup.info/test/e2b-icp-tests
SUPABASE_ANON_KEY=$(security find-generic-password -s supabase_lkup_anon_key -w) \
SUPABASE_SVC_KEY=$(security find-generic-password -s supabase_lkup_service_role_key -w) \
node run-icp-test.js all
```

### E2B Desktop — Correct Setup (READ THIS BEFORE ANYTHING ELSE)

Agents have previously failed here on three mistakes. Know them before you start:

| Mistake | What happens | Fix |
|---|---|---|
| `urllib.request.urlopen(pool_url)` | HTTP 403 from Cloudflare | Use `subprocess.run(["curl", "-sf", "-X", "POST", url])` — curl bypasses bot-UA block |
| `GET /pool/desktop` | HTTP 403 | Must be `POST /pool/claim/desktop` |
| `connect_over_cdp("localhost:9222")` from local Mac | ECONNREFUSED | CDP is internal to sandbox — run Playwright script inside via `sbx.commands.run()` |
| `DISPLAY=:99` in xdotool/scrot | "Can't open X display" | Display is `:0` — always `DISPLAY=:0` |
| `sbx.screenshot()` crashes | `scrot: Can't open X display` | Use `DISPLAY=:0 scrot /tmp/s.png` + base64 until v3.3.5 template is built |
| `sbx.files.read("/tmp/s.png")` returns str | Can't write_bytes | Use `base64 /tmp/s.png` → decode in Python (never print base64 to stdout — 20K tokens/image) |

```python
import base64, time
from pathlib import Path
from e2b_desktop import Sandbox
from e2b.sandbox.commands.command_handle import CommandExitException
import subprocess

POOL_LB = "https://e2b-pool-lb.sakima-api.workers.dev"
E2B_KEY = subprocess.run(["bigmac-secrets", "get", "e2b_api_key"], capture_output=True, text=True).stdout.strip()
OUT = Path("~/clawd/data/test-lkup").expanduser()
OUT.mkdir(parents=True, exist_ok=True)

import subprocess, json

# ── 1. CLAIM ──────────────────────────────────────────────────────
# POST /pool/claim/desktop — NOT GET /pool/desktop
# Must use curl — Python urllib gets 403 from Cloudflare (bot UA blocked). curl works.
result = subprocess.run(
    ["curl", "-sf", "-X", "POST", f"{POOL_LB}/pool/claim/desktop"],
    capture_output=True, text=True, timeout=15
)
sandbox_meta = json.loads(result.stdout)
SBX_ID = sandbox_meta["sandbox_id"]
VNC_URL = f"https://8080-{SBX_ID}.e2b.app/vnc.html?autoconnect=true&resize=scale"
print(f"VNC (open this in browser): {VNC_URL}")

# ── 2. CONNECT SDK ────────────────────────────────────────────────
sbx = Sandbox.connect(SBX_ID, api_key=E2B_KEY)

def run(cmd, timeout=20):
    try:
        r = sbx.commands.run(cmd, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), 0
    except CommandExitException as e:
        return "", str(e)[:200], 1

def see(label):
    """Screenshot → save locally → use Read tool to inspect (not base64 to context)."""
    run(f"DISPLAY=:0 scrot /tmp/{label}.png")
    b64, _, rc = run(f"base64 /tmp/{label}.png", timeout=15)
    if b64 and rc == 0:
        png = base64.b64decode(b64)  # never print b64 — 20K tokens/image
        path = OUT / f"{label}.png"
        path.write_bytes(png)
        # Use Read tool on path to see it: Read(str(path))
        return path

# ── 3. WAIT FOR DESKTOP ───────────────────────────────────────────
for _ in range(15):
    out, _, _ = run("DISPLAY=:0 pgrep -x xfce4-panel && echo READY || echo LOADING")
    if "READY" in out:
        break
    time.sleep(3)

# ── 4. PLAYWRIGHT — runs INSIDE sandbox (not from local Mac) ──────
# localhost:9222 is only accessible from inside. Upload script → execute → download results.
def browser_test(playwright_code, timeout=60):
    """Run Playwright inside sandbox. Returns stdout lines."""
    sbx.files.write("/tmp/_pw.py", playwright_code)
    out, err, rc = run("python3 /tmp/_pw.py", timeout=timeout)
    return out, err, rc

# ── 5. RELEASE (try/finally — ALWAYS release) ────────────────────
# Wrap everything in try/finally:
# try:
#     ... all test groups ...
# finally:
#     subprocess.run(["curl", "-sf", "-X", "POST",
#         f"{POOL_LB}/pool/release/{SBX_ID}"], timeout=10)
```

### Sample: run a Playwright web test inside the sandbox

```python
result, err, rc = browser_test(f"""
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://lkup.info", wait_until="domcontentloaded", timeout=25000)
    page.wait_for_timeout(1500)
    print("TITLE:" + page.title())
    page.screenshot(path="/tmp/lkup_home.png")
    browser.close()
print("DONE")
""")
print(result)   # "TITLE:lkup.info — Real-time coin pricing & cert lookup"
see("lkup_home")  # downloads screenshot, use Read tool to verify
```

### Edge Functions only (no browser)
```bash
python3 test/scripts/test-edge-functions.py --group 10
```

### Single ICP
```bash
node test/e2b-icp-tests/run-icp-test.js ben
```

---

## Pre-Test Cleanup

```bash
python3 test/scripts/cleanup-test-certs.py --backup --delete
```

Clears (FK order): `pricing_consensus` → `grader_data` → `barcode_cert_xref` →
`cert_photos` → `coin_xref` → `ebay_listing_xref` → `marketplace_listings` →
`draft_listings` → `inventory` → `sold_archive` → `coin_id_review_queue` → `certs`

Backups: `test/e2b-icp-tests/backup-<table>.json`

---

## Fixtures

| File | What it is | Real certs? | Use for |
|---|---|---|---|
| `test/fixtures/known-good-barcodes.json` | 172+ real barcode strings, 10 graders | ✅ | Types A, B |
| `test/fixtures/known-good-certs.json` | 299+ enriched cert numbers | ✅ | Type C |
| `test/fixtures/static-coin-images.json` | 300+ sampleslabs.com reference images | ❌ sample only | AI vision |
| `test/fixtures/images/` | Real slab photos from Supabase | Mixed | Photo upload |
| `test/e2b-icp-tests/test-matrix.json` | ICP credentials + verified certs | ✅ | All web tests |

Keep fixtures live (append-only, validity-gated):
```bash
python3 test/scripts/update-fixtures.py --apply --commit
```

---

## ICP Personas

| ICP | Email | Focus |
|-----|-------|-------|
| ben | abenfife.ben@gmail.com | Power dealer — all flows, admin |
| marcus | abenfife.marcus@gmail.com | Whatnot dealer — scan speed, mobile |
| dave | abenfife.dave@gmail.com | Show booth — labels, offline |
| jess | abenfife.jess@gmail.com | eBay flipper — margins, comps, listing |
| patricia | abenfife.patricia@gmail.com | Hobbyist — simplicity, free tier |

---

## Forward Compatibility — Adding New Tests

When a new surface, grader, or EF is added:

1. Add a row to the relevant group in this matrix
2. Add barcode/cert entries to fixtures via `update-fixtures.py` (add grader to `KNOWN_GRADERS`)
3. For new graders: add to Group 2 barcode table + `static-coin-images.json`
4. For new EFs: add a row to Group 10 with sample payload + expected fields
5. For new CF Workers: add a row to Group 11
6. For new surfaces: add a new Group (15+) following the same input/expected/verify pattern

No test group requires a specific runner — any group can be exercised independently via
the E2B sandbox + CDP pattern above.
