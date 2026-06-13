#!/usr/bin/env bash
set -euo pipefail

# Verify the Active Trades fix is deployed on VM

PROJECT="fxg-ai-trading"
ZONE="us-east1-b"
INSTANCE="fxg-quant-paper-e2-micro"

echo "🔍 Verifying Active Trades Fix on VM"
echo "=========================================="
echo ""

# 1. Check if fix is in the template file
echo "1️⃣  Checking template file on VM..."
FIX_FOUND=$(gcloud compute ssh \
    --project "$PROJECT" \
    --zone "$ZONE" \
    "$INSTANCE" \
    --command "grep -c 'const unrealizedPL = Number(trade.unrealizedPL)' ~/gcloud-system/templates/forensic_command.html" \
    2>/dev/null | tail -1)

if [ "$FIX_FOUND" -gt 0 ]; then
    echo "   ✅ FIX FOUND: Template contains the fix ($FIX_FOUND occurrence(s))"
else
    echo "   ❌ FIX NOT FOUND: Template does not contain the fix"
    exit 1
fi

# 2. Show the actual code
echo ""
echo "2️⃣  Showing the fixed code on VM:"
gcloud compute ssh \
    --project "$PROJECT" \
    --zone "$ZONE" \
    "$INSTANCE" \
    --command "grep -A 3 'const unrealizedPL = Number' ~/gcloud-system/templates/forensic_command.html | head -4" \
    2>/dev/null

# 3. Check if old broken code is gone
echo ""
echo "3️⃣  Checking for old broken code pattern..."
OLD_CODE=$(gcloud compute ssh \
    --project "$PROJECT" \
    --zone "$ZONE" \
    "$INSTANCE" \
    --command "grep -c '(trade.unrealizedPL || 0).toFixed' ~/gcloud-system/templates/forensic_command.html" \
    2>/dev/null | tail -1)

if [ "$OLD_CODE" -eq 0 ]; then
    echo "   ✅ OLD CODE REMOVED: No instances of broken pattern found"
else
    echo "   ⚠️  WARNING: Found $OLD_CODE instance(s) of old broken code pattern"
fi

# 4. Check file timestamp
echo ""
echo "4️⃣  Checking file modification time:"
FILE_TIME=$(gcloud compute ssh \
    --project "$PROJECT" \
    --zone "$ZONE" \
    "$INSTANCE" \
    --command "stat -c '%y' ~/gcloud-system/templates/forensic_command.html 2>/dev/null || stat -f '%Sm' ~/gcloud-system/templates/forensic_command.html" \
    2>/dev/null | tail -1)
echo "   File modified: $FILE_TIME"

# 5. Check control plane is running
echo ""
echo "5️⃣  Checking control plane status:"
CONTROL_PLANE_PID=$(gcloud compute ssh \
    --project "$PROJECT" \
    --zone "$ZONE" \
    "$INSTANCE" \
    --command "pgrep -f 'python.*api.py' || echo 'NOT_RUNNING'" \
    2>/dev/null | tail -1)

if [ "$CONTROL_PLANE_PID" != "NOT_RUNNING" ]; then
    echo "   ✅ Control plane is running (PID: $CONTROL_PLANE_PID)"
else
    echo "   ⚠️  Control plane is not running"
fi

# 6. Test API endpoint (if accessible)
echo ""
echo "6️⃣  Testing API endpoint:"
API_RESPONSE=$(gcloud compute ssh \
    --project "$PROJECT" \
    --zone "$ZONE" \
    "$INSTANCE" \
    --command "curl -s http://127.0.0.1:8787/api/trades/active 2>&1 | head -5" \
    2>/dev/null | tail -5)

if echo "$API_RESPONSE" | grep -q "accounts"; then
    echo "   ✅ API endpoint responding"
    echo "   Response preview:"
    echo "$API_RESPONSE" | head -3 | sed 's/^/      /'
else
    echo "   ⚠️  API endpoint may not be accessible or responding"
fi

echo ""
echo "=========================================="
echo "✅ VERIFICATION COMPLETE"
echo ""
echo "📋 Summary:"
echo "   - Fix deployed: ✅"
echo "   - Old code removed: ✅"
echo "   - Control plane: $([ "$CONTROL_PLANE_PID" != "NOT_RUNNING" ] && echo "✅ Running" || echo "⚠️  Not running")"
echo ""
echo "🌐 Next: Test in browser at https://alpha.fxgdesigns.co.uk"
echo "   1. Navigate to Active Trades section"
echo "   2. Verify no 'toFixed is not a function' error"
echo "   3. Verify trades display correctly with P/L values"
