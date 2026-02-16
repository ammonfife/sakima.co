#!/usr/bin/env python3
"""
Import Whatnot purchase history (COGS) into hledger format.

Tracks inventory purchases to calculate true profit margins.
Handles both Whatnot buyer account exports and manual purchase records.

Usage:
    python3 import_purchases.py <purchases.csv>
    python3 import_purchases.py --scan-downloads
"""

import csv
import sys
import argparse
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional
import glob

def parse_whatnot_purchase_date(date_str: str) -> Optional[str]:
    """Convert Whatnot purchase datetime to hledger date format."""
    if not date_str or date_str.strip() == '':
        return None

    # Try multiple date formats
    formats = [
        "%b %d, %Y, %I:%M:%S %p",  # Nov 9, 2025, 7:27:37 PM
        "%Y-%m-%d %H:%M:%S",        # 2025-11-09 19:27:37
        "%m/%d/%Y",                 # 11/09/2025
        "%Y-%m-%d",                 # 2025-11-09
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y/%m/%d")
        except ValueError:
            continue

    print(f"Warning: Could not parse date '{date_str}'", file=sys.stderr)
    return None

def parse_amount(amount_str: str) -> Decimal:
    """Parse amount string with various formats."""
    if not amount_str or amount_str.strip() == '':
        return Decimal('0')
    # Remove $, commas, whitespace, and handle negative
    clean = amount_str.replace('$', '').replace(',', '').strip()
    return Decimal(clean)

def detect_csv_format(file_path: Path) -> str:
    """Detect the format of the purchase CSV file."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        header = f.readline().strip()

    # Whatnot buyer order history format
    if 'Order Date' in header and 'Total' in header:
        return 'whatnot_orders'

    # Manual tracking format
    elif 'Date' in header and 'Item' in header and 'Cost' in header:
        return 'manual'

    # Generic CSV with common columns
    elif 'date' in header.lower() and 'amount' in header.lower():
        return 'generic'

    return 'unknown'

def import_whatnot_orders(file_path: Path) -> List[str]:
    """Import from Whatnot buyer order history CSV."""
    entries = []
    count = 0

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            date = parse_whatnot_purchase_date(row.get('Order Date', ''))
            if not date:
                continue

            # Extract purchase details
            total = parse_amount(row.get('Total', '0'))
            seller = row.get('Seller', 'Unknown')
            item = row.get('Item', row.get('Title', 'Purchase'))
            order_id = row.get('Order ID', '')

            if total <= 0:
                continue

            desc = f"Purchase: {item[:50]}"
            if seller != 'Unknown':
                desc += f" from {seller}"

            entries.append(f"{date} * {desc}")
            if order_id:
                entries.append(f"    ; order_id: {order_id}")
            entries.append(f"    ; seller: {seller}")
            entries.append(f"    Assets:Inventory                    ${total}")
            entries.append(f"    Liabilities:CreditCard")
            entries.append("")

            count += 1

    print(f"Imported {count} purchases from Whatnot orders")
    return entries

def import_manual_purchases(file_path: Path) -> List[str]:
    """Import from manual purchase tracking CSV."""
    entries = []
    count = 0

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            date = parse_whatnot_purchase_date(row.get('Date', ''))
            if not date:
                continue

            cost = parse_amount(row.get('Cost', '0'))
            item = row.get('Item', 'Purchase')
            seller = row.get('Seller', row.get('Source', ''))
            notes = row.get('Notes', '')

            if cost <= 0:
                continue

            desc = f"Purchase: {item[:50]}"

            entries.append(f"{date} * {desc}")
            if seller:
                entries.append(f"    ; seller: {seller}")
            if notes:
                entries.append(f"    ; notes: {notes[:80]}")
            entries.append(f"    Assets:Inventory                    ${cost}")
            entries.append(f"    Liabilities:CreditCard")
            entries.append("")

            count += 1

    print(f"Imported {count} manual purchase records")
    return entries

def import_generic_csv(file_path: Path) -> List[str]:
    """Import from generic CSV with date and amount columns."""
    entries = []
    count = 0

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = [h.lower() for h in reader.fieldnames]

        # Find date column
        date_col = None
        for col in ['date', 'purchase date', 'order date', 'transaction date']:
            if col in headers:
                date_col = reader.fieldnames[headers.index(col)]
                break

        # Find amount column
        amount_col = None
        for col in ['amount', 'total', 'cost', 'price']:
            if col in headers:
                amount_col = reader.fieldnames[headers.index(col)]
                break

        # Find description column
        desc_col = None
        for col in ['description', 'item', 'title', 'product']:
            if col in headers:
                desc_col = reader.fieldnames[headers.index(col)]
                break

        if not date_col or not amount_col:
            print(f"Error: Could not find date and amount columns in {file_path}", file=sys.stderr)
            return []

        for row in reader:
            date = parse_whatnot_purchase_date(row.get(date_col, ''))
            if not date:
                continue

            amount = parse_amount(row.get(amount_col, '0'))
            if amount <= 0:
                continue

            desc = "Purchase"
            if desc_col and row.get(desc_col):
                desc = f"Purchase: {row[desc_col][:50]}"

            entries.append(f"{date} * {desc}")
            entries.append(f"    Assets:Inventory                    ${amount}")
            entries.append(f"    Liabilities:CreditCard")
            entries.append("")

            count += 1

    print(f"Imported {count} generic purchase records")
    return entries

def main():
    parser = argparse.ArgumentParser(description='Import Whatnot purchase history for COGS tracking')
    parser.add_argument('csv_file', nargs='?', help='Path to purchase CSV file')
    parser.add_argument('--scan-downloads', action='store_true', help='Scan Downloads folder for purchase files')
    parser.add_argument('--output', default='sakima_lc/accounting/journals/purchases.journal', help='Output journal file')

    args = parser.parse_args()

    output_file = Path(args.output)
    all_entries = []

    # Add header
    all_entries.append("; Whatnot Purchase History (COGS)")
    all_entries.append(f"; Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    all_entries.append("")
    all_entries.append("; Account declarations")
    all_entries.append("account Assets:Inventory")
    all_entries.append("account Liabilities:CreditCard")
    all_entries.append("account Equity:Opening")
    all_entries.append("")
    all_entries.append("; Opening balance")
    all_entries.append("2025/07/01 * Opening Balance")
    all_entries.append("    Assets:Inventory                    $0.00")
    all_entries.append("    Equity:Opening                      $0.00")
    all_entries.append("")

    files_to_import = []

    if args.scan_downloads:
        # Scan Downloads for purchase files
        download_dir = Path.home() / "Downloads"
        patterns = [
            "*purchase*.csv",
            "*order*.csv",
            "*inventory*.csv",
            "*COGS*.csv"
        ]

        for pattern in patterns:
            files_to_import.extend(download_dir.glob(pattern))

        if not files_to_import:
            print("No purchase files found in Downloads")
            return 1

    elif args.csv_file:
        files_to_import = [Path(args.csv_file)]

    else:
        parser.print_help()
        return 1

    # Import each file
    for file_path in files_to_import:
        if not file_path.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            continue

        print(f"\nProcessing: {file_path.name}")

        csv_format = detect_csv_format(file_path)
        print(f"Detected format: {csv_format}")

        if csv_format == 'whatnot_orders':
            entries = import_whatnot_orders(file_path)
        elif csv_format == 'manual':
            entries = import_manual_purchases(file_path)
        elif csv_format == 'generic':
            entries = import_generic_csv(file_path)
        else:
            print(f"Warning: Unknown CSV format, skipping {file_path.name}")
            continue

        all_entries.extend(entries)

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_entries))

    print(f"\n✓ Purchase journal created: {output_file}")
    print(f"\nView inventory: hledger -f {output_file} balance Assets:Inventory")
    print(f"Total COGS: hledger -f {output_file} register Assets:Inventory")

    return 0

if __name__ == '__main__':
    sys.exit(main())
