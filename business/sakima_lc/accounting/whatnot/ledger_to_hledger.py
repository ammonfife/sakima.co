#!/usr/bin/env python3
"""
Import Whatnot transaction ledger (full transaction history) into hledger format.
This is the primary import method - ledger has complete transaction-by-transaction detail.

Differences from earnings statements:
- Ledger: Complete transaction history with all individual transactions
- Statements: Weekly summaries with fee breakdowns but less complete

Use this for the most accurate account balance tracking.
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional

def parse_whatnot_ledger_date(date_str: str) -> Optional[str]:
    """Convert Whatnot ledger datetime to hledger date format."""
    if not date_str or date_str.strip() == '':
        return None
    try:
        # Format: "Nov 9, 2025, 7:27:37 PM" -> "2025/11/09"
        dt = datetime.strptime(date_str, "%b %d, %Y, %I:%M:%S %p")
        return dt.strftime("%Y/%m/%d")
    except ValueError:
        try:
            # Try alternative format without time
            dt = datetime.strptime(date_str, "%b %d, %Y")
            return dt.strftime("%Y/%m/%d")
        except ValueError:
            return None

def parse_amount(amount_str: str) -> Decimal:
    """Parse amount string with $ sign and commas."""
    if not amount_str or amount_str.strip() == '':
        return Decimal('0')
    # Remove $, commas, and whitespace
    clean = amount_str.replace('$', '').replace(',', '').strip()
    return Decimal(clean)

def create_ledger_entry(row: Dict[str, str]) -> List[str]:
    """Create hledger journal entry from Whatnot ledger row."""
    entries = []

    date = parse_whatnot_ledger_date(row['Date'])
    if not date:
        return []  # Skip entries without valid dates

    amount = parse_amount(row['Amount'])
    trans_type = row['Transaction Type']
    message = row['Message'].replace('"', "'") if row['Message'] else ''
    listing_id = row['Listing ID']
    order_id = row['Order ID']

    # Skip zero-amount transactions
    if amount == 0:
        return []

    if trans_type == 'SALES':
        if amount < 0:
            # Negative SALES = giveaway deduction
            if 'giveaway' in message.lower():
                desc = f"Giveaway deduction"
                entries.append(f"{date} * {desc}")
                if order_id:
                    entries.append(f"    ; order_id: {order_id}")
                if listing_id:
                    entries.append(f"    ; listing_id: {listing_id}")
                entries.append(f"    Expenses:Giveaways                  ${-amount}")
                entries.append(f"    Assets:Whatnot:Pending              ${amount}")
            else:
                # Other negative sales (refunds, adjustments)
                desc = message[:60] if message else "Sales adjustment"
                entries.append(f"{date} * {desc}")
                if order_id:
                    entries.append(f"    ; order_id: {order_id}")
                entries.append(f"    Expenses:Adjustments                ${-amount}")
                entries.append(f"    Assets:Whatnot:Pending              ${amount}")
        else:
            # Positive SALES = revenue
            # Extract item name from message
            if message.startswith("Earnings for selling a "):
                item = message.replace("Earnings for selling a ", "")[:50]
                desc = f"Sale: {item}"
            else:
                desc = message[:60] if message else "Sale"

            entries.append(f"{date} * {desc}")
            if order_id:
                entries.append(f"    ; order_id: {order_id}")
            if listing_id:
                entries.append(f"    ; listing_id: {listing_id}")

            # Note: Ledger shows NET amount after fees, not gross
            # So we can't break out fees - just record net revenue
            entries.append(f"    Assets:Whatnot:Pending              ${amount}")
            entries.append(f"    Revenue:Sales")

        entries.append("")

    elif trans_type == 'PAYOUT':
        # Money leaving Whatnot to bank account
        desc = "Payout to bank"
        if 'STRIPE' in message:
            desc += " (Stripe)"

        entries.append(f"{date} * {desc}")
        entries.append(f"    ; {message[:80]}")
        # Amount is negative, so we negate it for the checking account (positive cash in)
        entries.append(f"    Assets:Checking                     ${-amount}")
        entries.append(f"    Assets:Whatnot:Pending              ${amount}")
        entries.append("")

    elif trans_type == 'ADJUSTMENT':
        # Various adjustments (show promotions, reversals, etc)
        desc = message[:60] if message else "Account adjustment"

        entries.append(f"{date} * {desc}")
        if listing_id:
            entries.append(f"    ; listing_id: {listing_id}")
        if order_id:
            entries.append(f"    ; order_id: {order_id}")

        if amount < 0:
            # Negative adjustment (expense)
            if 'reversal' in message.lower() or 'reversing' in message.lower():
                # Reversal of previous sale
                entries.append(f"    Revenue:Sales                       ${amount}")
                entries.append(f"    Assets:Whatnot:Pending              ${-amount}")
            elif 'promotion' in message.lower():
                # Marketing expense
                entries.append(f"    Expenses:Marketing                  ${-amount}")
                entries.append(f"    Assets:Whatnot:Pending              ${amount}")
            else:
                # Other adjustment
                entries.append(f"    Expenses:Adjustments                ${-amount}")
                entries.append(f"    Assets:Whatnot:Pending              ${amount}")
        else:
            # Positive adjustment (income)
            entries.append(f"    Assets:Whatnot:Pending              ${amount}")
            entries.append(f"    Revenue:Other")

        entries.append("")

    else:
        # Unknown transaction type
        desc = f"{trans_type}: {message[:50]}"
        entries.append(f"{date} * {desc}")
        entries.append(f"    Assets:Whatnot:Pending              ${amount}")
        entries.append(f"    Revenue:Other")
        entries.append("")

    return entries

def main():
    ledger_file = Path("/Users/benfife/Downloads/0e2b8bd2-573c-4405-bd98-0dc8a2dd015a.csv")
    output_file = Path("sakima_lc/accounting/journals/whatnot_ledger.journal")

    if not ledger_file.exists():
        print(f"Ledger file not found: {ledger_file}")
        return 1

    print(f"Processing ledger file: {ledger_file.name}")

    all_entries = []
    transaction_count = 0
    total_sales = Decimal('0')
    total_payouts = Decimal('0')
    total_adjustments = Decimal('0')

    # Add header
    all_entries.append("; Whatnot Transaction Ledger Import")
    all_entries.append(f"; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    all_entries.append(f"; Source: {ledger_file.name}")
    all_entries.append("")
    all_entries.append("; Account declarations")
    all_entries.append("account Assets:Whatnot:Pending")
    all_entries.append("account Assets:Checking")
    all_entries.append("account Revenue:Sales")
    all_entries.append("account Revenue:Other")
    all_entries.append("account Expenses:Giveaways")
    all_entries.append("account Expenses:Marketing")
    all_entries.append("account Expenses:Adjustments")
    all_entries.append("account Equity:Opening")
    all_entries.append("")

    # Determine opening balance date (earliest transaction)
    with open(ledger_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Get earliest date
    dates = [parse_whatnot_ledger_date(row['Date']) for row in rows if parse_whatnot_ledger_date(row['Date'])]
    if dates:
        earliest_date = min(dates)
        all_entries.append(f"; Opening balance (day before first transaction)")
        all_entries.append(f"{earliest_date} * Opening Balance")
        all_entries.append("    Assets:Whatnot:Pending              $0.00")
        all_entries.append("    Equity:Opening                      $0.00")
        all_entries.append("")

    # Process transactions (reverse chronological in file, so reverse it)
    for row in reversed(rows):
        entries = create_ledger_entry(row)
        if entries:
            all_entries.extend(entries)
            transaction_count += 1

            # Track totals for summary
            amount = parse_amount(row['Amount'])
            trans_type = row['Transaction Type']
            if trans_type == 'SALES' and amount > 0:
                total_sales += amount
            elif trans_type == 'PAYOUT':
                total_payouts += amount
            elif trans_type == 'ADJUSTMENT':
                total_adjustments += amount

    # Write journal file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_entries))

    print(f"\nImport complete!")
    print(f"Transactions imported: {transaction_count:,}")
    print(f"Total sales revenue: ${total_sales:,.2f}")
    print(f"Total payouts: ${total_payouts:,.2f}")
    print(f"Total adjustments: ${total_adjustments:,.2f}")
    print(f"Journal file: {output_file}")
    print(f"\nVerify with: hledger -f {output_file} balance")
    print(f"View income: hledger -f {output_file} incomestatement")

    return 0

if __name__ == '__main__':
    sys.exit(main())
