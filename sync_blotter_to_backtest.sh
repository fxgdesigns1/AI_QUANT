#!/bin/bash
# Sync Live Trading Blotter to Backtesting System
# Copies latest blotter data for backtesting parity validation

set -e

echo "=========================================="
echo "Syncing Blotter to Backtesting System"
echo "=========================================="

# Configuration
LOCAL_BASE="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system"
BLOTTER_SOURCE="$LOCAL_BASE/Sync folder MAC TO PC/DESKTOP_HANDOFF_PACKAGE/google-cloud-trading-system/data"
BACKTEST_BASE="$LOCAL_BASE/../DEEP_BACKTESTING"  # Adjust path if needed

# Check if backtesting directory exists
if [ ! -d "$BACKTEST_BASE" ]; then
    echo "⚠️  Backtesting directory not found at: $BACKTEST_BASE"
    echo "📝 Creating local sync directory instead..."
    SYNC_DIR="$LOCAL_BASE/backtest_blotter_sync"
    mkdir -p "$SYNC_DIR"
else
    SYNC_DIR="$BACKTEST_BASE/data/live_blotter"
    mkdir -p "$SYNC_DIR"
fi

echo ""
echo "Step 1: Copying blotter files..."
echo "   Source: $BLOTTER_SOURCE"
echo "   Destination: $SYNC_DIR"

# Copy all blotter files
FILES=(
    "live_trade_blotter.json"
    "live_trade_blotter_trades.csv"
    "live_trade_blotter_trades.json"
    "all_accounts_blotter.json"
    "combined_blotter_101_accounts.csv"
)

# Copy individual account blotters
for file in "$BLOTTER_SOURCE"/blotter_*.csv; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        cp "$file" "$SYNC_DIR/$filename"
        echo "   ✅ Copied: $filename"
    fi
done

# Copy main blotter files
for file in "${FILES[@]}"; do
    if [ -f "$BLOTTER_SOURCE/$file" ]; then
        cp "$BLOTTER_SOURCE/$file" "$SYNC_DIR/$file"
        echo "   ✅ Copied: $file"
    else
        echo "   ⚠️  File not found: $file"
    fi
done

echo ""
echo "Step 2: Creating sync manifest..."
MANIFEST_FILE="$SYNC_DIR/sync_manifest.json"
cat > "$MANIFEST_FILE" << EOF
{
  "sync_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "timezone": "Europe/London",
  "source": "google-cloud-trading-system",
  "destination": "backtesting_system",
  "files_synced": [
$(for file in "${FILES[@]}"; do
    if [ -f "$BLOTTER_SOURCE/$file" ]; then
        echo "    \"$file\","
    fi
done | sed '$ s/,$//')
  ],
  "account_blotters": [
$(for file in "$BLOTTER_SOURCE"/blotter_*.csv; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo "    \"$filename\","
    fi
done | sed '$ s/,$//')
  ],
  "notes": [
    "Paper-trading only. All accounts isolated per user directive.",
    "Blotter data synced for backtesting parity validation.",
    "Use this data to ensure live trading matches backtest expectations."
  ]
}
EOF

echo "   ✅ Created manifest: sync_manifest.json"

echo ""
echo "Step 3: Creating summary report..."
SUMMARY_FILE="$SYNC_DIR/blotter_summary.txt"
cat > "$SUMMARY_FILE" << EOF
========================================
Live Trading Blotter Summary
========================================
Sync Date: $(date)
Source: Google Cloud Trading System
Destination: Backtesting System

Files Synced:
$(ls -lh "$SYNC_DIR" | grep -v "^total" | awk '{print "  " $9 " (" $5 ")"}')

Account Coverage:
$(for file in "$SYNC_DIR"/blotter_*.csv; do
    if [ -f "$file" ]; then
        filename=$(basename "$file" .csv)
        account_id=$(echo "$filename" | sed 's/blotter_//')
        line_count=$(wc -l < "$file" | tr -d ' ')
        echo "  Account $account_id: $line_count trades"
    fi
done)

========================================
EOF

echo "   ✅ Created summary: blotter_summary.txt"

echo ""
echo "=========================================="
echo "✅ Blotter Sync Complete!"
echo "=========================================="
echo ""
echo "Synced to: $SYNC_DIR"
echo ""
echo "Files available for backtesting:"
ls -1 "$SYNC_DIR" | head -10
echo ""
echo "Next steps:"
echo "1. Review sync manifest: $MANIFEST_FILE"
echo "2. Use blotter data in backtesting system for parity validation"
echo "3. Compare live performance with backtest expectations"
echo ""

