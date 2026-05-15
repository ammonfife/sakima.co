---
name: audit-parity
description: Verify feature parity between auction_tools originals and lkup.info ports during consolidation
user-invocable: true
---

# Audit Parity

After porting a module from auction_tools to lkup.info, verify the TypeScript port matches the Python original's behavior.

## Process

1. Read the Python source in `~/github/ammonfife/auction_tools/`
2. Read the TypeScript port in this repo
3. Extract test cases from Python (inline tests, known inputs/outputs)
4. Run both against same inputs, diff outputs
5. Report differences:
   - **CRITICAL** — different output for same input
   - **WARN** — missing edge case
   - **INFO** — stylistic difference, same semantics

## Key Parity Checks

- **Barcode parser**: All service prefixes, all barcode formats (8/16/18/20-digit, QR, Ser#)
- **Pricing engine**: Melt calc, margin tiers, consensus logic
- **Coin title parser**: All 40+ US series, year/denomination routing, Morgan/Peace inference
- **Label generator**: QR format, thermal printer layouts

## Output

```
PARITY REPORT: [module]
Source: [path] → Port: [path]
Tests: [N] pass / [N] fail
Verdict: READY / NOT READY for cutover
```

## Bigmac Turso

After each parity audit:
```bash
# Record result
facts add operational "Parity audit [module]: [READY|NOT READY] — [N] pass, [N] fail" --tags lkup,consolidation,parity,agent:claude,agent:bob

# If NOT READY, record blockers
facts add operational "Parity blocker [module]: [description of failure]" --tags lkup,consolidation,parity,blocker,agent:claude

bigmac-sync push
```

## Bigmac Turso Integration

After verifying parity between auction_tools original and lkup.info port, record the result.

### Facts
```bash
# After parity verified
facts add operational "Phase [N]: [module] parity verified — Python vs TS match on [N] test cases" --tags lkup,consolidation,parity,agent:claude,agent:bob

# After finding a divergence
facts add operational "[module]: TS port diverges from Python on [edge case] — fixed by [approach]" --tags lkup,consolidation,parity,agent:claude
```

### Todos
```bash
todo done <id>   # mark parity task complete
```

### Sync
```bash
bigmac-sync push
```

### Tag Conventions
- **Project:** `lkup`, `consolidation`, `sakima`
- **Agents:** `agent:bob`, `agent:claude`
- **Domain:** `barcode`, `pricing`, `coin-parser`, `labels`, `enrichment`
- **Status:** `status:verified`, `status:inbox`
