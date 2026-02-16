# Whatnot Data Source Comparison

## Summary: Use LEDGER as Primary Source

The **transaction ledger** is the source of truth for Sakima LC accounting. The weekly earnings statements provide additional fee detail but are less complete.

## Data Source Comparison

### Transaction Ledger (PRIMARY)
**File**: `0e2b8bd2-573c-4405-bd98-0dc8a2dd015a.csv`
**Format**: Complete transaction-by-transaction history
**Transactions**: 2,200
**Date Range**: July 14, 2025 - November 9, 2025

**Financial Summary**:
- **Total Revenue**: $122,931.51
  - Sales: $119,087.66
  - Other: $3,843.85
- **Total Expenses**: $1,188.19
  - Giveaways: $511.15
  - Marketing: $431.91
  - Adjustments: $245.13
- **Net Income**: $121,743.32
- **Payouts to Bank**: $119,227.17
- **Current Whatnot Balance**: $2,516.15

**Advantages**:
✅ Complete transaction history (every sale, payout, adjustment)
✅ Includes PAYOUT records (money moved to bank account)
✅ Shows actual account balance over time
✅ Source of truth from Whatnot platform
✅ Can track cash flow (in and out)

**Limitations**:
❌ Shows NET amounts (after fees) - no fee breakdown
❌ No buyer information
❌ No SKU tracking
❌ Less detail on individual transactions

---

### Weekly Earnings Statements (SUPPLEMENTAL)
**Files**: 16 CSV files (e.g., `october_27_november_2_2025_earnings.csv`)
**Format**: Weekly summaries with detailed breakdowns
**Transactions**: 1,975
**Date Range**: July 14, 2025 - October 28, 2025

**Financial Summary**:
- **Total Revenue**: $121,683.81
  - Sales: $121,239.99
  - Tips: $523.00
  - Other: -$79.18
- **Total Expenses**: $14,824.03
  - Whatnot Fees: $14,360.62 (11.8% rate)
  - Giveaways: $463.41
- **Net Income**: $106,859.78
- **Apparent Whatnot Balance**: $106,859.78

**Advantages**:
✅ Detailed FEE BREAKDOWNS (commission, processing, tax)
✅ Buyer names and locations
✅ SKU tracking
✅ Livestream information
✅ Item descriptions

**Limitations**:
❌ NO payout tracking (doesn't show money leaving Whatnot)
❌ Weekly summaries (not complete transaction history)
❌ Missing some transaction types
❌ Balance doesn't match reality (ignores payouts)

---

## Why the Numbers Differ

**Revenue Difference**:
- Ledger: $122,931.51
- Statements: $121,683.81
- **Difference**: $1,247.70

Reasons:
1. Different time periods (ledger includes Nov 3-9, statements end Oct 28)
2. "Other" revenue categorized differently
3. Ledger is more complete

**Net Income Explanation**:
- Ledger shows: $121,743.32 earned, $119,227.17 paid out = $2,516.15 in account ✅
- Statements show: $106,859.78 but ignore $119K in payouts ❌

The statements show GROSS revenue minus fees but **don't track payouts**, so the "balance" is fictional.

---

## Recommended Approach

### Primary Accounting: Use Ledger
- Import ledger for accurate balance sheet and cash flow
- Run: `hledger -f journals/whatnot_ledger.journal balance`
- Shows real account balances (Whatnot $2,516, Checking $119,227)

### Fee Analysis: Use Statements (when needed)
- Import statements to analyze fee structure
- Useful for understanding Whatnot's commission rates
- Can identify fee trends over time

### Reconciliation
Both sources should reconcile if you:
1. Add back the $14,360.62 in fees (from statements) to ledger revenue
2. Account for the $119,227.17 in payouts (from ledger)

Formula:
```
Ledger Net ($121,743) ≈ Statement Gross Revenue ($121,240) - Fees ($14,361) + Other Adjustments
```

---

## Action Items

- [x] Import transaction ledger (PRIMARY)
- [x] Import weekly statements (SUPPLEMENTAL)
- [ ] Keep ledger updated with future exports
- [ ] Use statements for fee analysis as needed
- [ ] Reconcile monthly to verify accuracy

---

**Date**: 2025-11-09
**Conclusion**: The transaction ledger is the authoritative source for Sakima LC accounting. Use it for all financial reporting and balance tracking.
