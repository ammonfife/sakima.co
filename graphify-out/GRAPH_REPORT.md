# Graph Report - /Users/benfife/github/ammonfife/sakima.co  (2026-04-08)

## Corpus Check
- Corpus is ~10,132 words - fits in a single context window. You may not need a graph.

## Summary
- 137 nodes · 188 edges · 19 communities detected
- Extraction: 64% EXTRACTED · 36% INFERRED · 0% AMBIGUOUS · INFERRED: 68 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `fetch()` - 9 edges
2. `jsonResponse()` - 8 edges
3. `surgeRequest()` - 7 edges
4. `errorResponse()` - 7 edges
5. `Coin Cert Lookup (PCGS/NGC)` - 7 edges
6. `main()` - 6 edges
7. `Cloudflare Worker (sakima-api)` - 6 edges
8. `handle_cert()` - 5 edges
9. `parse_whatnot_purchase_date()` - 5 edges
10. `parse_amount()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `Whatnot profile scraper (E2B sandbox)` --semantically_similar_to--> `Whatnot transaction ledger -> hledger`  [INFERRED] [semantically similar]
  README.md → business/sakima_lc/accounting/whatnot/ledger_to_hledger.py
- `Coin Cert Lookup (PCGS/NGC)` --semantically_similar_to--> `Cloudflare Worker (sakima-api)`  [INFERRED] [semantically similar]
  sms-api/handlers/cert.py → worker/src/index.ts
- `Turso purchases table (Whatnot buyer history)` --semantically_similar_to--> `COGS / purchase-history import`  [INFERRED] [semantically similar]
  worker/src/turso.ts → business/sakima_lc/accounting/import_purchases.py
- `Whatnot profile scraper (E2B sandbox)` --shares_data_with--> `Turso sakima_shows table`  [EXTRACTED]
  README.md → scripts/sync_to_turso.py
- `eBay Browse API listing fetch` --shares_data_with--> `Turso sakima_items table (eBay listings)`  [EXTRACTED]
  README.md → scripts/sync_to_turso.py

## Hyperedges (group relationships)
- **Coin cert lookup triad (Turso -> PCGS -> NGC)** — concept_cert_lookup, concept_turso_inventory_coins, concept_pcgs_api, concept_ngc_api [EXTRACTED 1.00]
- **Whatnot data pipelines (scrape shows, ledger, earnings, COGS)** — concept_whatnot_scraper, concept_whatnot_ledger_import, concept_whatnot_earnings_import, concept_cogs_import [INFERRED 0.80]
- **Two SMS stacks (Python FastAPI + Cloudflare Worker) both on Surge** — concept_surge_sms_service, concept_sms_router, concept_cf_worker [INFERRED 0.85]

## Communities

### Community 0 - "Core Concepts & Cross-Cutting"
Cohesion: 0.11
Nodes (22): BID price flow (buy price), Coin Cert Lookup (PCGS/NGC), Cloudflare Worker (sakima-api), COGS / purchase-history import, Turso form_submissions table, Golden Ticket multi-step SMS flow, hledger double-entry journals, JWT signing for Surge admin (+14 more)

### Community 1 - "Purchase/COGS Import (Python)"
Cohesion: 0.25
Nodes (13): detect_csv_format(), import_generic_csv(), import_manual_purchases(), import_whatnot_orders(), main(), parse_amount(), parse_whatnot_purchase_date(), Import from manual purchase tracking CSV. (+5 more)

### Community 2 - "Turso Sync Script (shows/items)"
Cohesion: 0.23
Nodes (13): create_tables(), get_turso_token(), get_turso_url(), main(), Upsert shows from shows.json into Turso., Upsert items from listings.json into Turso., Get Turso HTTP URL from env., Get Turso token from env or macOS keychain. (+5 more)

### Community 3 - "Cloudflare Worker API"
Cohesion: 0.44
Nodes (12): corsHeaders(), corsResponse(), errorResponse(), fetch(), formatE164(), handleAdminToken(), handleOffer(), handleSignup() (+4 more)

### Community 4 - "Coin Cert Lookup (PCGS/NGC)"
Cohesion: 0.27
Nodes (9): handle_cert(), _lookup_ngc(), _lookup_pcgs(), CERT <number> handler — looks up coin cert via: 1. Sakima Turso inventory (coins, Handle CERT <number> — return coin name, grade, value., Execute a read query against Turso via HTTP pipeline., Query PCGS public cert verification endpoint., Query NGC public cert verification endpoint. (+1 more)

### Community 5 - "Whatnot Ledger → hledger"
Cohesion: 0.43
Nodes (7): create_ledger_entry(), main(), parse_amount(), parse_whatnot_ledger_date(), Convert Whatnot ledger datetime to hledger date format., Parse amount string with $ sign and commas., Create hledger journal entry from Whatnot ledger row.

### Community 6 - "Whatnot Earnings → hledger"
Cohesion: 0.36
Nodes (7): create_journal_entry(), format_amount(), main(), parse_whatnot_date(), Convert Whatnot datetime to hledger date format., Convert string amount to Decimal., Create hledger journal entry from Whatnot CSV row.

### Community 7 - "Surge SMS Client"
Cohesion: 0.46
Nodes (7): createContact(), createUser(), listContacts(), listPhoneNumbers(), sendMessage(), surgeRequest(), updateContact()

### Community 8 - "SMS-API FastAPI Entry"
Cohesion: 0.4
Nodes (4): Send reply via Surge.app REST API., Surge.app inbound SMS webhook.     Surge posts form-encoded or JSON — handles bo, send_sms_reply(), sms_webhook()

### Community 9 - "BID Handler + Redis Cache"
Cohesion: 0.47
Nodes (5): handle_bid(), BID <cert> handler — return our current buy/bid price for a coin. Checks Turso i, Return bid/buy price for a cert., _redis_get(), _redis_set()

### Community 10 - "SMS Keyword Router"
Cohesion: 0.5
Nodes (3): Message router — parses inbound SMS body and dispatches to correct handler. Fuzz, Return reply string for inbound SMS body., route_message()

### Community 11 - "PRICE Handler"
Cohesion: 0.5
Nodes (3): handle_price(), PRICE <cert> handler — return pricing info for a cert. Delegates cert lookup the, Return price guide info for a cert number.

### Community 12 - "JWT Signer (Admin)"
Cohesion: 1.0
Nodes (3): base64urlEncode(), signJWT(), textToBase64url()

### Community 13 - "Turso Worker Client"
Cohesion: 0.5
Nodes (0): 

### Community 14 - "HOURS Handler"
Cohesion: 0.67
Nodes (1): HOURS handler — return Sakima business hours. Edit HOURS_TEXT to update without

### Community 15 - "Default Handler"
Cohesion: 0.67
Nodes (1): Default/fallback handler — unknown commands.

### Community 16 - "HELP Handler"
Cohesion: 0.67
Nodes (1): HELP handler — list available SMS commands.

### Community 17 - "eBay Listings Feed"
Cohesion: 1.0
Nodes (2): eBay Browse API listing fetch, Turso sakima_items table (eBay listings)

### Community 18 - "Handlers Package Init"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **44 isolated node(s):** `Send reply via Surge.app REST API.`, `Surge.app inbound SMS webhook.     Surge posts form-encoded or JSON — handles bo`, `HOURS handler — return Sakima business hours. Edit HOURS_TEXT to update without`, `BID <cert> handler — return our current buy/bid price for a coin. Checks Turso i`, `Return bid/buy price for a cert.` (+39 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `eBay Listings Feed`** (2 nodes): `eBay Browse API listing fetch`, `Turso sakima_items table (eBay listings)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Handlers Package Init`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Are the 8 inferred relationships involving `fetch()` (e.g. with `corsResponse()` and `jsonResponse()`) actually correct?**
  _`fetch()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `jsonResponse()` (e.g. with `corsHeaders()` and `errorResponse()`) actually correct?**
  _`jsonResponse()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `surgeRequest()` (e.g. with `createContact()` and `listContacts()`) actually correct?**
  _`surgeRequest()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `errorResponse()` (e.g. with `jsonResponse()` and `handleSignup()`) actually correct?**
  _`errorResponse()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Send reply via Surge.app REST API.`, `Surge.app inbound SMS webhook.     Surge posts form-encoded or JSON — handles bo`, `HOURS handler — return Sakima business hours. Edit HOURS_TEXT to update without` to the rest of the system?**
  _44 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Core Concepts & Cross-Cutting` be split into smaller, more focused modules?**
  _Cohesion score 0.11 - nodes in this community are weakly interconnected._