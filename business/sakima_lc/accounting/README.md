# Sakima LC Accounting System

**Open-source accounting for Whatnot earnings using hledger**

## Overview

This directory contains the complete accounting records for Sakima LC's Whatnot collectibles business.

**PRIMARY DATA SOURCE**: Transaction ledger (complete history with 2,200 transactions)
**SUPPLEMENTAL**: Weekly earnings statements (16 files with fee details)

See [DATA_SOURCE_COMPARISON.md](DATA_SOURCE_COMPARISON.md) for detailed analysis.

### Financial Summary (July 14 - November 9, 2025)

**FROM TRANSACTION LEDGER (Primary Source)**:

**Income Statement**:
- **Total Revenue**: $122,931.51
  - Sales: $119,087.66
  - Other: $3,843.85
- **Total Expenses**: $1,188.19
  - Giveaways: $511.15
  - Marketing: $431.91 (show promotions)
  - Adjustments: $245.13
- **Net Income**: $121,743.32

**Cash Flow**:
- **Payouts to Bank**: $119,227.17
- **Current Whatnot Balance**: $2,516.15
- **Cash in Bank**: $119,227.17
- **Total Assets**: $121,743.32 ✅

**Transaction Volume**:
- 2,200 transactions (ledger)
- 1,975 transactions (statements - supplemental)

**Note**: The ledger shows NET revenue (after Whatnot takes fees). For detailed fee breakdown, see earnings statements or run `python3 whatnot_to_hledger.py` for statement analysis.

## Directory Structure

```
sakima_lc/accounting/
├── import/              # Original CSV files from Whatnot
├── journals/            # hledger journal files (double-entry format)
├── reports/             # Generated financial reports
├── whatnot_to_hledger.py  # Import script
└── README.md           # This file
```

## Quick Start

### View Reports

**Balance Sheet (PRIMARY - from ledger):**
```bash
hledger -f journals/whatnot_ledger.journal balance
```

**Income Statement (PRIMARY - from ledger):**
```bash
hledger -f journals/whatnot_ledger.journal incomestatement
```

**Fee Analysis (from earnings statements):**
```bash
hledger -f journals/whatnot_earnings.journal balance Expenses:Fees
```

**Monthly Revenue Breakdown:**
```bash
hledger -f journals/whatnot_earnings.journal register Revenue --monthly
```

**Cash Flow (Whatnot Account Balance):**
```bash
hledger -f journals/whatnot_earnings.journal balance Assets:Whatnot
```

### Re-import Data

If you add new CSV files to `import/` directory:

```bash
python3 whatnot_to_hledger.py
```

## Chart of Accounts

**Assets:**
- `Assets:Whatnot:Pending` - Earnings pending in Whatnot account
- `Assets:Checking` - Bank account (after payouts)

**Revenue:**
- `Revenue:Sales` - Product sales
- `Revenue:Tips` - Customer tips
- `Revenue:Other` - Other income/adjustments

**Expenses:**
- `Expenses:Fees` - Whatnot commission and processing fees
- `Expenses:Giveaways` - Cost of giveaway items

**Equity:**
- `Equity:Opening` - Opening balance

## Advanced Queries

**Top 10 sales by amount:**
```bash
hledger -f journals/whatnot_earnings.journal register Revenue:Sales -w 200 | sort -k5 -n | tail -10
```

**Total fees paid:**
```bash
hledger -f journals/whatnot_earnings.journal balance Expenses:Fees
```

**Daily transaction count:**
```bash
hledger -f journals/whatnot_earnings.journal register --daily | wc -l
```

**Average transaction value:**
```bash
# Revenue / transaction count
# $121,683.81 / 1,975 = $61.61 average sale
```

## Export to Other Formats

**CSV Export (for Excel/Google Sheets):**
```bash
hledger -f journals/whatnot_earnings.journal print -O csv > reports/transactions.csv
```

**JSON Export:**
```bash
hledger -f journals/whatnot_earnings.journal print -O json > reports/transactions.json
```

**QuickBooks-compatible (future):**
- Use hledger-to-quickbooks conversion tool (TBD)
- Or export CSV and import into QuickBooks Online

## Notes

- All amounts in USD
- Transactions dated by completion date (when payment was processed)
- Comments include order IDs, SKUs, and fee breakdowns for audit trail
- Giveaways are expensed when shipped (negative earnings)
- System uses double-entry bookkeeping (all transactions balance to $0)

## Tax Preparation

For tax purposes, the key numbers are:

- **Gross Revenue**: $121,683.81
- **Deductible Expenses**: $14,824.03
- **Net Profit**: $106,859.78

See journals/whatnot_earnings.journal for complete transaction-level detail.

---

**Generated**: 2025-11-09
**Edited by**: Assignment Assistant
**Period Covered**: July 14, 2025 - October 28, 2025
