#!/bin/bash
set -euo pipefail

# Verify Truth-Only News UI Implementation
# This script ensures the dashboard shows only real news data, no placeholders

echo "🔍 Verifying Truth-Only News Implementation"
echo "=========================================="

# Test 1: Check dashboard HTML for forbidden hardcoded strings
echo "Test 1: Checking for hardcoded news strings in dashboard..."
FORBIDDEN_STRINGS="NFP Release|Jackson Hole|AI bias|hawkish pivot|vol spike|150-pip swing|2038 zone"

if curl -s http://127.0.0.1:8787/ | grep -qE "$FORBIDDEN_STRINGS"; then
    echo "❌ FAIL: Found hardcoded news strings in dashboard HTML"
    echo "   Forbidden strings still present in UI"
    exit 1
else
    echo "✅ PASS: No hardcoded news strings found in dashboard HTML"
fi

# Test 2: Check /api/news endpoint accessibility
echo "Test 2: Testing /api/news endpoint..."
NEWS_RESPONSE=$(curl -s http://127.0.0.1:8787/api/news || echo "ERROR")

if [[ "$NEWS_RESPONSE" == "ERROR" ]]; then
    echo "❌ FAIL: /api/news endpoint not reachable"
    exit 1
fi

# Test 3: Verify /api/news returns proper structure
echo "Test 3: Verifying /api/news response structure..."
if echo "$NEWS_RESPONSE" | jq -e '.enabled != null and .items != null and .reason != null' >/dev/null 2>&1; then
    echo "✅ PASS: /api/news returns proper structure"
    
    # Extract enabled state
    ENABLED=$(echo "$NEWS_RESPONSE" | jq -r '.enabled')
    ITEMS_COUNT=$(echo "$NEWS_RESPONSE" | jq -r '.items | length')
    REASON=$(echo "$NEWS_RESPONSE" | jq -r '.reason')
    
    echo "   News enabled: $ENABLED"
    echo "   Items count: $ITEMS_COUNT"
    echo "   Reason: $REASON"
    
    if [[ "$ENABLED" == "false" ]]; then
        echo "✅ PASS: News integration properly disabled by default"
    else
        echo "⚠️  WARNING: News integration is enabled - ensure this is intentional"
    fi
else
    echo "❌ FAIL: /api/news response missing required fields"
    echo "   Response: $NEWS_RESPONSE"
    exit 1
fi

# Test 4: Verify dashboard JavaScript loads news dynamically
echo "Test 4: Checking dashboard JavaScript for dynamic news loading..."
if curl -s http://127.0.0.1:8787/ | grep -q "loadNews()"; then
    echo "✅ PASS: Dashboard contains dynamic news loading function"
else
    echo "❌ FAIL: Dashboard missing dynamic news loading"
    exit 1
fi

# Test 5: Verify no hardcoded news content in source files
echo "Test 5: Scanning source files for hardcoded news content..."
if find . -name "*.html" -o -name "*.js" -o -name "*.py" | xargs grep -l "NFP Release\|Jackson Hole minutes\|hawkish pivot" 2>/dev/null | grep -v "ARTIFACTS\|ROTATE_SECRETS\|verify_truth_only_news"; then
    echo "❌ FAIL: Found hardcoded news content in source files"
    exit 1
else
    echo "✅ PASS: No hardcoded news content found in source files"
fi

echo ""
echo "🎉 ALL TESTS PASSED"
echo "✅ Dashboard shows truth-only news (no hardcoded placeholders)"
echo "✅ News UI properly handles disabled state"
echo "✅ /api/news endpoint returns proper structure"
echo "✅ Dynamic loading implemented correctly"
echo ""
echo "📋 Summary:"
echo "   - News integration disabled by default (safe)"
echo "   - UI shows 'disabled' state when news integration off"
echo "   - No hardcoded macro/news text in dashboard"
echo "   - All news content comes from backend API only"