---
name: lift-module
description: Port a Python module from auction_tools/ to TypeScript in lkup.info — Phase 1 of consolidation
---

# Lift Module

Port Python business logic from `~/github/ammonfife/auction_tools/` to TypeScript in this repo, reusable across all surfaces (web, desktop, extension, mobile).

## Source of Truth

Read `lkup-plan.json` → `consolidation.phases[1]` for the module map.

## Modules

| Module | Source (auction_tools/) | Target (lkup.info/) |
|--------|------------------------|---------------------|
| Barcode parser | `lkup_info_site/cloud_run/libs/barcode_parser/` | `shared/barcode-parser/` |
| Pricing engine | `production/scanners/unified/enrichment/price_fetcher.py` + `item_valuator.py` | `shared/pricing/` |
| Coin title parser | `collection_enrichment/coin_xref_enrichment.py` | `shared/coin-parser/` |
| Label generator | desktop_scanner.py label sections | `shared/labels/` |

## Process

1. Read the Python source completely
2. Create TypeScript module with equivalent exports
3. Port all constants and edge cases
4. Write tests matching Python behavior (same inputs/outputs)
5. Validate parity — run both against same inputs
6. Update `lkup-plan.json` Phase 1 module status

## Constraints

- Do NOT modify any Python file in auction_tools/
- Server stays authoritative for scan resolution
- Test parity required — every Python test case needs a matching TS test

## Bigmac Turso

After completing each module port:
```bash
# Record the port as a fact
facts add operational "Phase 1: [module] ported Python→TS, [N] tests passing, parity verified" --tags lkup,consolidation,phase1,agent:Codex,agent:bob

# Record any discoveries during the port
facts add operational "[module]: [discovery about edge case or behavior]" --tags lkup,barcode|pricing|coin-parser|labels,agent:Codex

bigmac-sync push
```

### Tag Conventions
- **Project:** `lkup`, `consolidation`, `sakima`
- **Agents:** `agent:bob`, `agent:Codex`
- **Domain:** `barcode`, `pricing`, `coin-parser`, `labels`, `enrichment`, `desktop`, `extension`
- **Status:** `status:verified`, `status:inbox`
