#!/bin/bash
# Automated Whatnot Data Sync
# Updates accounting system with latest transaction data
#
# Run manually: ./sync_whatnot_data.sh
# Or schedule with cron/launchd (see automation_setup.sh)

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
DOWNLOAD_DIR="$HOME/Downloads"
IMPORT_DIR="$SCRIPT_DIR/import"
JOURNALS_DIR="$SCRIPT_DIR/journals"
REPORTS_DIR="$SCRIPT_DIR/reports"
LEDGER_FILE="$JOURNALS_DIR/whatnot_ledger.journal"
LOG_FILE="$SCRIPT_DIR/sync.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log "=== Whatnot Data Sync Started ==="

# Step 1: Check for new ledger file in Downloads
log "Checking for new transaction ledger in Downloads..."

# Look for Whatnot ledger exports (UUID pattern)
LATEST_LEDGER=$(find "$DOWNLOAD_DIR" -name "*-*-*-*-*.csv" -type f -mtime -7 | head -1)

if [ -z "$LATEST_LEDGER" ]; then
    warn "No recent ledger file found in Downloads (last 7 days)"
    warn "Manual download needed from Whatnot:"
    warn "  1. Go to Whatnot > Seller Dashboard > Earnings"
    warn "  2. Click 'Download Transaction History'"
    warn "  3. Save to Downloads folder"
    warn "  4. Re-run this script"
    echo ""
    log "Checking for weekly earnings statements instead..."

    # Check for weekly earnings files
    NEW_STATEMENTS=$(find "$DOWNLOAD_DIR" -name "*_earnings.csv" -type f -mtime -7)

    if [ -n "$NEW_STATEMENTS" ]; then
        log "Found new weekly earnings statements"
        echo "$NEW_STATEMENTS" | while read statement; do
            FILENAME=$(basename "$statement")
            if [ ! -f "$IMPORT_DIR/$FILENAME" ]; then
                log "  Importing: $FILENAME"
                cp "$statement" "$IMPORT_DIR/"
            else
                log "  Skipping (already imported): $FILENAME"
            fi
        done

        log "Re-running earnings statement import..."
        python3 whatnot_to_hledger.py
    else
        warn "No new earnings statements found either"
        log "Sync complete (no new data to import)"
        exit 0
    fi
else
    LEDGER_NAME=$(basename "$LATEST_LEDGER")
    log "Found ledger: $LEDGER_NAME"

    # Check if already imported
    EXISTING_LEDGER=$(find "$IMPORT_DIR" -name "*-*-*-*-*.csv" -type f | head -1)

    if [ -n "$EXISTING_LEDGER" ]; then
        EXISTING_SIZE=$(stat -f%z "$EXISTING_LEDGER" 2>/dev/null || stat -c%s "$EXISTING_LEDGER")
        NEW_SIZE=$(stat -f%z "$LATEST_LEDGER" 2>/dev/null || stat -c%s "$LATEST_LEDGER")

        if [ "$EXISTING_SIZE" -eq "$NEW_SIZE" ]; then
            log "Ledger unchanged (same size), skipping import"
            exit 0
        fi

        log "New ledger is different size (old: $EXISTING_SIZE, new: $NEW_SIZE)"
        log "Backing up old ledger..."
        mv "$EXISTING_LEDGER" "$IMPORT_DIR/backup_$(date +%Y%m%d_%H%M%S)_$(basename "$EXISTING_LEDGER")"
    fi

    log "Copying ledger to import directory..."
    cp "$LATEST_LEDGER" "$IMPORT_DIR/"

    # Step 2: Update ledger file path in script
    log "Updating ledger import script..."
    LEDGER_IMPORT_SCRIPT="$SCRIPT_DIR/ledger_to_hledger.py"

    # Update the hardcoded path in the script
    sed -i.bak "s|ledger_file = Path(\".*\\.csv\")|ledger_file = Path(\"$IMPORT_DIR/$LEDGER_NAME\")|" "$LEDGER_IMPORT_SCRIPT"

    # Step 3: Run import
    log "Running ledger import..."
    python3 "$LEDGER_IMPORT_SCRIPT"

    if [ $? -ne 0 ]; then
        error "Ledger import failed!"
        exit 1
    fi
fi

# Step 4: Verify journal integrity
log "Verifying journal integrity..."
hledger -f "$LEDGER_FILE" balance > /dev/null 2>&1

if [ $? -ne 0 ]; then
    error "Journal validation failed! Check $LEDGER_FILE for errors"
    exit 1
fi

log "Journal validated successfully"

# Step 5: Generate reports
log "Generating financial reports..."

mkdir -p "$REPORTS_DIR"

hledger -f "$LEDGER_FILE" balance > "$REPORTS_DIR/balance_sheet_$(date +%Y%m%d).txt"
hledger -f "$LEDGER_FILE" incomestatement > "$REPORTS_DIR/income_statement_$(date +%Y%m%d).txt"
hledger -f "$LEDGER_FILE" register Assets:Whatnot -H | tail -1 > "$REPORTS_DIR/current_balance_$(date +%Y%m%d).txt"

# Step 6: Get summary stats
CURRENT_BALANCE=$(hledger -f "$LEDGER_FILE" balance Assets:Whatnot:Pending -N)
BANK_BALANCE=$(hledger -f "$LEDGER_FILE" balance Assets:Checking -N)
NET_INCOME=$(hledger -f "$LEDGER_FILE" incomestatement | grep "Net:" | awk '{print $2}')

log "=== Sync Summary ==="
log "Current Whatnot Balance: $CURRENT_BALANCE"
log "Bank Balance (from payouts): $BANK_BALANCE"
log "Total Net Income: $NET_INCOME"

# Step 7: Commit to git (optional)
if command -v git &> /dev/null; then
    if [ -n "$(git status --porcelain sakima_lc/accounting/)" ]; then
        log "Committing changes to git..."
        git add sakima_lc/accounting/
        git commit -m "chore: Automated Whatnot data sync - $(date +%Y-%m-%d)" \
                   -m "Updated accounting records with latest transactions" \
                   -m "Balance: $CURRENT_BALANCE (Whatnot) + $BANK_BALANCE (Bank)" \
                   -m "Edited by: Automated Sync, $(date -u +%Y-%m-%dT%H:%M:%SZ)" || true
    else
        log "No changes to commit"
    fi
fi

# Step 8: Send notification (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "display notification \"Balance: $CURRENT_BALANCE\" with title \"Whatnot Sync Complete\" subtitle \"Net Income: $NET_INCOME\" sound name \"Glass\"" 2>/dev/null || true
fi

log "=== Sync Complete ==="

# Cleanup old reports (keep last 30 days)
find "$REPORTS_DIR" -name "*_*.txt" -type f -mtime +30 -delete 2>/dev/null || true

exit 0
