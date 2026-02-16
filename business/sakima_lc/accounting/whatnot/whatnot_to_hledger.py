#!/usr/bin/env python3
"""
Import Whatnot earnings CSV files into hledger journal format.
Converts Whatnot transaction data into double-entry bookkeeping format.
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional
import glob

def parse_whatnot_date(date_str: str) -> Optional[str]:
    """Convert Whatnot datetime to hledger date format."""
    if not date_str or date_str.strip() == '':
        return None
    try:
        # Format: "2025-10-28 06:06:52" -> "2025/10/28"
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y/%m/%d")
    except ValueError:
        return None

def format_amount(amount: str) -> Decimal:
    """Convert string amount to Decimal."""
    if not amount or amount.strip() == '':
        return Decimal('0')
    return Decimal(amount)

def create_journal_entry(row: Dict[str, str]) -> List[str]:
    """Create hledger journal entry from Whatnot CSV row."""
    entries = []

    # Use transaction completed date, fallback to order placed date
    date_str = row['TRANSACTION_COMPLETED_AT_UTC'] or row['ORDER_PLACED_AT_UTC']
    date = parse_whatnot_date(date_str)
    if not date:
        return []  # Skip entries without dates

    trans_type = row['TRANSACTION_TYPE']
    trans_amount = format_amount(row['TRANSACTION_AMOUNT'])

    # Skip zero-amount transactions
    if trans_amount == 0:
        return []

    # Create transaction description
    listing_title = row['LISTING_TITLE'].replace('"', "'") if row['LISTING_TITLE'] else 'Unknown'
    buyer = row['BUYER_NAME'] or 'Unknown'
    order_id = row['ORDER_ID']

    if trans_type == 'TIP':
        # Tips are pure revenue
        desc = f"Tip from {buyer}"
        entries.append(f"{date} * {desc}")
        if row['LEDGER_TRANSACTION_ID']:
            entries.append(f"    ; transaction_id: {row['LEDGER_TRANSACTION_ID']}")
        entries.append(f"    Assets:Whatnot:Pending              ${trans_amount}")
        entries.append(f"    Revenue:Tips                       ${-trans_amount}")
        entries.append("")

    elif trans_type == 'ORDER_EARNINGS':
        # Sales with fees broken out
        buyer_paid = format_amount(row['BUYER_PAID'])
        commission = format_amount(row['COMMISSION_FEE'])
        processing = format_amount(row['PAYMENT_PROCESSING_FEE'])
        shipping = format_amount(row['SHIPPING_FEE'])

        if trans_amount < 0:
            # Giveaway cost (expense)
            desc = f"Giveaway: {listing_title[:40]}"
            entries.append(f"{date} * {desc}")
            if order_id:
                entries.append(f"    ; order_id: {order_id}")
            entries.append(f"    Expenses:Giveaways                  ${-trans_amount}")
            entries.append(f"    Assets:Whatnot:Pending              ${trans_amount}")
            entries.append("")
        else:
            # Regular sale
            # Calculate total fees (difference between buyer paid and net received)
            total_fees = buyer_paid - trans_amount if buyer_paid > 0 else Decimal('0')

            desc = f"Sale: {listing_title[:40]} - {buyer}"
            entries.append(f"{date} * {desc}")
            if order_id:
                entries.append(f"    ; order_id: {order_id}")
            if row['SKU']:
                entries.append(f"    ; sku: {row['SKU']}")
            if commission > 0:
                entries.append(f"    ; commission_fee: ${commission}")
            if processing > 0:
                entries.append(f"    ; processing_fee: ${processing}")

            # Simplified accounting: Net amount received and total revenue
            if buyer_paid > 0:
                entries.append(f"    Assets:Whatnot:Pending              ${trans_amount}")
                entries.append(f"    Expenses:Fees                        ${total_fees}")
                entries.append(f"    Revenue:Sales")
            else:
                # If no buyer_paid amount, just record net
                entries.append(f"    Assets:Whatnot:Pending              ${trans_amount}")
                entries.append(f"    Revenue:Sales")
            entries.append("")

    elif trans_type == 'PAYOUT':
        # Payout to bank account
        desc = "Payout to bank"
        entries.append(f"{date} * {desc}")
        if row['LEDGER_TRANSACTION_ID']:
            entries.append(f"    ; transaction_id: {row['LEDGER_TRANSACTION_ID']}")
        entries.append(f"    Assets:Checking                     ${trans_amount}")
        entries.append(f"    Assets:Whatnot:Pending              ${-trans_amount}")
        entries.append("")

    elif trans_type == 'REFUND':
        # Refunds reduce revenue
        desc = f"Refund: {listing_title[:40]}"
        entries.append(f"{date} * {desc}")
        if order_id:
            entries.append(f"    ; order_id: {order_id}")
        entries.append(f"    Assets:Whatnot:Pending              ${trans_amount}")
        entries.append(f"    Revenue:Sales                       ${-trans_amount}")
        entries.append("")
    else:
        # Other transaction types
        desc = f"{trans_type}: {row['TRANSACTION_MESSAGE'][:50]}"
        entries.append(f"{date} * {desc}")
        if row['LEDGER_TRANSACTION_ID']:
            entries.append(f"    ; transaction_id: {row['LEDGER_TRANSACTION_ID']}")
        entries.append(f"    Assets:Whatnot:Pending              ${trans_amount}")
        entries.append(f"    Revenue:Other                       ${-trans_amount}")
        entries.append("")

    return entries

def main():
    import_dir = Path("sakima_lc/accounting/import")
    output_file = Path("sakima_lc/accounting/journals/whatnot_earnings.journal")

    # Find all earnings CSV files
    csv_files = sorted(import_dir.glob("*_earnings.csv"))

    if not csv_files:
        print("No earnings CSV files found in import directory")
        return 1

    print(f"Found {len(csv_files)} earnings files to import")

    all_entries = []
    transaction_count = 0

    # Add header
    all_entries.append("; Whatnot Earnings Import")
    all_entries.append(f"; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    all_entries.append(f"; Source files: {len(csv_files)}")
    all_entries.append("")
    all_entries.append("; Account declarations")
    all_entries.append("account Assets:Whatnot:Pending")
    all_entries.append("account Assets:Checking")
    all_entries.append("account Revenue:Sales")
    all_entries.append("account Revenue:Tips")
    all_entries.append("account Revenue:Other")
    all_entries.append("account Expenses:Fees")
    all_entries.append("account Expenses:Giveaways")
    all_entries.append("account Equity:Opening")
    all_entries.append("")
    all_entries.append("; Opening balance")
    all_entries.append("2025/07/14 * Opening Balance")
    all_entries.append("    Assets:Whatnot:Pending              $0.00")
    all_entries.append("    Equity:Opening                      $0.00")
    all_entries.append("")

    # Process each CSV file
    for csv_file in csv_files:
        print(f"Processing {csv_file.name}...")

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries = create_journal_entry(row)
                if entries:
                    all_entries.extend(entries)
                    transaction_count += 1

    # Write journal file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_entries))

    print(f"\nImport complete!")
    print(f"Transactions imported: {transaction_count}")
    print(f"Journal file: {output_file}")
    print(f"\nVerify with: hledger -f {output_file} balance")
    print(f"View income: hledger -f {output_file} incomestatement")

    return 0

if __name__ == '__main__':
    sys.exit(main())
