# Whatnot Accounting Automation Guide

## Quick Start

### 1. Update Sales Data (Semi-Automated)

Download new transaction ledger from Whatnot, then run:
```bash
cd sakima_lc/accounting
./sync_whatnot_data.sh
```

The script will:
- Find the latest CSV in Downloads
- Import into hledger
- Generate reports
- Commit to git
- Send notification

### 2. Import Purchase History (COGS)

For Whatnot buyer order exports:
```bash
python3 import_purchases.py ~/Downloads/order_history.csv
```

To scan all purchase files in Downloads:
```bash
python3 import_purchases.py --scan-downloads
```

### 3. View Complete P&L (with COGS)

Combine sales and purchases:
```bash
# Include both journals
hledger -f journals/whatnot_ledger.journal -f journals/purchases.journal incomestatement
```

## Manual Download Steps

**Whatnot doesn't have a public API**, so downloads are manual:

### Sales/Earnings Ledger
1. Go to Whatnot app/website
2. Navigate to: Seller Dashboard → Earnings → Transaction History
3. Click "Download" or "Export"
4. Save CSV to Downloads folder
5. Run `./sync_whatnot_data.sh`

### Purchase History (for COGS)
1. Go to Whatnot app/website
2. Navigate to: Profile → Orders → Purchase History
3. Click "Download" or "Export All"
4. Save CSV to Downloads folder
5. Run `python3 import_purchases.py --scan-downloads`

## Automation Options

### Option 1: Manual Trigger (Recommended)
Run sync script after each download:
```bash
./sync_whatnot_data.sh
```

### Option 2: Scheduled Check (Semi-Automated)
Run daily to check for new files in Downloads:

**macOS (launchd)**:
```bash
# Create ~/Library/LaunchAgents/com.sakima.whatnot-sync.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sakima.whatnot-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/benfife/github/ammonfife/GitHubGitHub/sakima_lc/accounting/sync_whatnot_data.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</dict>
</plist>

# Load it
launchctl load ~/Library/LaunchAgents/com.sakima.whatnot-sync.plist
```

**Linux (cron)**:
```bash
# Run daily at 9am
0 9 * * * /path/to/sakima_lc/accounting/sync_whatnot_data.sh
```

### Option 3: Browser Automation (Advanced)
Use Selenium/Playwright to auto-download from Whatnot (requires login handling, not included).

## CSV Format Support

### Sales Data (Auto-Detected)
- **Transaction Ledger**: UUID-named CSV (e.g., `0e2b8bd2-573c-4405-bd98-0dc8a2dd015a.csv`)
  - Columns: Date, Amount, Listing ID, Order ID, Message, Status, Transaction Type
- **Weekly Earnings**: `*_earnings.csv` files
  - Columns: TRANSACTION_TYPE, BUYER_PAID, COMMISSION_FEE, etc.

### Purchase Data (Auto-Detected)
- **Whatnot Orders**: Order Date, Total, Seller, Item, Order ID
- **Manual Tracking**: Date, Cost, Item, Seller, Notes
- **Generic CSV**: Any CSV with date + amount columns

## File Structure

```
sakima_lc/accounting/
├── import/                      # Raw CSV files
│   ├── 0e2b8bd2-...-*.csv      # Transaction ledger (sales)
│   └── *_earnings.csv           # Weekly earnings (sales)
├── journals/                    # hledger journals
│   ├── whatnot_ledger.journal  # Sales (PRIMARY)
│   ├── whatnot_earnings.journal # Sales with fees (supplemental)
│   └── purchases.journal        # COGS (run import_purchases.py)
├── reports/                     # Auto-generated reports
│   ├── balance_sheet_*.txt
│   └── income_statement_*.txt
├── sync_whatnot_data.sh        # Automation script
├── import_purchases.py          # COGS import
└── sync.log                     # Activity log
```

## Troubleshooting

**Script says "No new data found"**
- Check Downloads folder for CSV files
- Make sure files are less than 7 days old
- Or manually specify file path

**Purchase import fails**
- Check CSV format with `head -5 file.csv`
- Use `--output` to specify different journal file
- Check for valid date and amount columns

**Journal validation error**
- Run `hledger -f journals/whatnot_ledger.journal check`
- Look for unbalanced transactions
- Check sync.log for errors

## Next Steps

1. **Download latest data from Whatnot** (manual step)
2. **Run sync script**: `./sync_whatnot_data.sh`
3. **Import purchases** (if you have COGS data): `python3 import_purchases.py --scan-downloads`
4. **View complete financials**: `hledger -f journals/whatnot_ledger.journal -f journals/purchases.journal balance`

For questions, see [README.md](README.md) or [DATA_SOURCE_COMPARISON.md](DATA_SOURCE_COMPARISON.md).

---
**Last Updated**: 2025-11-10
**Status**: Production ready (manual downloads required)
