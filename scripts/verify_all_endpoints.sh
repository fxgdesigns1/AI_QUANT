#!/bin/bash
# Comprehensive Verification Script - Run AFTER API restart
# Tests all new endpoints and provides verification report

BASE_URL="http://localhost:8787"
echo "═══════════════════════════════════════════════════════════════"
echo "COMPREHENSIVE ENDPOINT VERIFICATION"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Test new performance endpoints
echo "📊 TESTING NEW PERFORMANCE ENDPOINTS..."
echo ""

echo "1. /api/performance/strategies?days=30"
STATUS1=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/performance/strategies?days=30")
if [ "$STATUS1" = "200" ]; then
    echo "   ✅ Status: $STATUS1"
    curl -s "$BASE_URL/api/performance/strategies?days=30" | python3 -m json.tool | head -20
else
    echo "   ❌ Status: $STATUS1"
fi
echo ""

echo "2. /api/performance/accounts?days=30"
STATUS2=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/performance/accounts?days=30")
if [ "$STATUS2" = "200" ]; then
    echo "   ✅ Status: $STATUS2"
    curl -s "$BASE_URL/api/performance/accounts?days=30" | python3 -m json.tool | head -20
else
    echo "   ❌ Status: $STATUS2"
fi
echo ""

echo "3. /api/performance/ai-evaluation?days=30"
STATUS3=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/performance/ai-evaluation?days=30")
if [ "$STATUS3" = "200" ]; then
    echo "   ✅ Status: $STATUS3"
    curl -s "$BASE_URL/api/performance/ai-evaluation?days=30" | python3 -m json.tool | head -30
else
    echo "   ❌ Status: $STATUS3"
fi
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "SUMMARY"
echo "═══════════════════════════════════════════════════════════════"
if [ "$STATUS1" = "200" ] && [ "$STATUS2" = "200" ] && [ "$STATUS3" = "200" ]; then
    echo "✅ ALL NEW ENDPOINTS WORKING!"
else
    echo "❌ Some endpoints still failing"
    echo "   Strategies: $STATUS1"
    echo "   Accounts: $STATUS2"
    echo "   AI Evaluation: $STATUS3"
fi
echo "═══════════════════════════════════════════════════════════════"
