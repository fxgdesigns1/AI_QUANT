#!/bin/bash
# fix_dashboard_tunnel.sh
# Comprehensive dashboard fix: verify VM service, set up tunnel, test with Playwright
#
# This script:
# 1. Checks if control plane API is running on VM
# 2. Sets up/verifies Cloudflare tunnel
# 3. Tests dashboard accessibility
# 4. Runs Playwright verification

set -euo pipefail

VM="fxg-quant-paper-e2-micro"
ZONE="us-east1-b"
PROJECT="fxg-ai-trading"
REMOTE_PORT="8787"
DOMAIN="alpha.fxgdesigns.co.uk"
LOCAL_PORT="28787"
DASHBOARD_URL="http://127.0.0.1:${LOCAL_PORT}"

echo "=== DASHBOARD FIX & TUNNEL SETUP ==="
echo "VM: $VM"
echo "Domain: $DOMAIN"
echo "Remote Port: $REMOTE_PORT"
echo "Local Tunnel Port: $LOCAL_PORT"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Step 1: Check if control plane is running on VM
echo "=== STEP 1: Checking Control Plane on VM ==="
echo "Checking if service is running on VM port $REMOTE_PORT..."

# Check via SSH if service is running
if gcloud compute ssh "$VM" \
    --zone "$ZONE" \
    --project "$PROJECT" \
    --tunnel-through-iap \
    --command "curl -sf --max-time 3 http://127.0.0.1:$REMOTE_PORT/health > /dev/null 2>&1 && echo 'RUNNING' || echo 'NOT_RUNNING'" 2>/dev/null | grep -q "RUNNING"; then
    print_status 0 "Control plane API is running on VM"
else
    print_status 1 "Control plane API is NOT running on VM"
    echo ""
    echo "⚠️  Attempting to start control plane on VM..."
    
    # Try to start the service
    gcloud compute ssh "$VM" \
        --zone "$ZONE" \
        --project "$PROJECT" \
        --tunnel-through-iap \
        --command "cd ~/gcloud-system 2>/dev/null || cd ~/gcloud_clean_room 2>/dev/null || cd ~ && \
            if [ -f scripts/start_control_plane_clean.sh ]; then \
                nohup bash scripts/start_control_plane_clean.sh > /tmp/control_plane_start.log 2>&1 & \
                sleep 5 && \
                curl -sf --max-time 3 http://127.0.0.1:$REMOTE_PORT/health > /dev/null 2>&1 && echo 'STARTED' || echo 'FAILED' \
            else \
                echo 'NO_SCRIPT' \
            fi" 2>/dev/null || echo "FAILED"
    
    # Wait and check again
    echo "Waiting 10 seconds for service to start..."
    sleep 10
    
    if gcloud compute ssh "$VM" \
        --zone "$ZONE" \
        --project "$PROJECT" \
        --tunnel-through-iap \
        --command "curl -sf --max-time 3 http://127.0.0.1:$REMOTE_PORT/health > /dev/null 2>&1 && echo 'RUNNING' || echo 'NOT_RUNNING'" 2>/dev/null | grep -q "RUNNING"; then
        print_status 0 "Control plane API started successfully"
    else
        print_status 1 "Failed to start control plane API"
        echo ""
        echo "📋 Manual steps required:"
        echo "1. SSH to VM: gcloud compute ssh $VM --zone $ZONE --project $PROJECT"
        echo "2. Navigate to project directory"
        echo "3. Run: bash scripts/start_control_plane_clean.sh"
        echo ""
        exit 1
    fi
fi

# Step 2: Set up local IAP tunnel (for immediate access)
echo ""
echo "=== STEP 2: Setting up Local IAP Tunnel ==="

# Kill existing tunnel if running
if lsof -i ":$LOCAL_PORT" >/dev/null 2>&1; then
    PID=$(lsof -t -i ":$LOCAL_PORT")
    echo "⚠️  Port $LOCAL_PORT is already in use (PID: $PID)"
    read -p "Kill existing tunnel and create new one? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill "$PID" 2>/dev/null || true
        sleep 2
    else
        echo "Using existing tunnel..."
        TUNNEL_EXISTS=true
    fi
else
    TUNNEL_EXISTS=false
fi

# Start tunnel if needed
if [ "${TUNNEL_EXISTS:-false}" = false ]; then
    echo "🚇 Starting IAP tunnel..."
    gcloud compute ssh "$VM" \
        --zone "$ZONE" \
        --project "$PROJECT" \
        --tunnel-through-iap \
        -- -N -L "$LOCAL_PORT:127.0.0.1:$REMOTE_PORT" > /tmp/tunnel.log 2>&1 &
    TUNNEL_PID=$!
    
    echo "   Tunnel PID: $TUNNEL_PID"
    echo "   Waiting for tunnel to establish..."
    sleep 5
    
    # Verify tunnel
    MAX_RETRIES=10
    RETRY_COUNT=0
    TUNNEL_WORKING=false
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -sf --max-time 3 "$DASHBOARD_URL/health" >/dev/null 2>&1; then
            TUNNEL_WORKING=true
            break
        else
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                echo "   Waiting for tunnel... (attempt $RETRY_COUNT/$MAX_RETRIES)"
                sleep 2
            fi
        fi
    done
    
    if [ "$TUNNEL_WORKING" = true ]; then
        print_status 0 "Local IAP tunnel is working"
        echo "   Dashboard accessible at: $DASHBOARD_URL"
    else
        print_status 1 "Local IAP tunnel failed to connect"
        echo "   Check /tmp/tunnel.log for details"
        exit 1
    fi
else
    # Verify existing tunnel
    if curl -sf --max-time 3 "$DASHBOARD_URL/health" >/dev/null 2>&1; then
        print_status 0 "Existing tunnel is working"
    else
        print_status 1 "Existing tunnel is not working"
        echo "   Please restart the tunnel manually"
        exit 1
    fi
fi

# Step 3: Test dashboard accessibility
echo ""
echo "=== STEP 3: Testing Dashboard Accessibility ==="

# Test health endpoint
if curl -sf --max-time 5 "$DASHBOARD_URL/health" >/dev/null 2>&1; then
    print_status 0 "Health endpoint accessible"
    HEALTH_RESPONSE=$(curl -sf --max-time 5 "$DASHBOARD_URL/health" 2>/dev/null || echo "{}")
    echo "   Response: $HEALTH_RESPONSE"
else
    print_status 1 "Health endpoint not accessible"
fi

# Test status endpoint
if curl -sf --max-time 5 "$DASHBOARD_URL/api/status" >/dev/null 2>&1; then
    print_status 0 "Status endpoint accessible"
    STATUS_RESPONSE=$(curl -sf --max-time 5 "$DASHBOARD_URL/api/status" 2>/dev/null | python3 -m json.tool 2>/dev/null | head -10 || echo "Unable to parse")
    echo "   Status preview:"
    echo "$STATUS_RESPONSE"
else
    print_status 1 "Status endpoint not accessible"
fi

# Test root endpoint (dashboard)
if curl -sf --max-time 5 "$DASHBOARD_URL/" >/dev/null 2>&1; then
    print_status 0 "Dashboard root accessible"
    ROOT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$DASHBOARD_URL/" 2>/dev/null || echo "000")
    echo "   HTTP Status: $ROOT_STATUS"
else
    print_status 1 "Dashboard root not accessible"
fi

# Step 4: Cloudflare Tunnel Setup (for public domain)
echo ""
echo "=== STEP 4: Cloudflare Tunnel Setup (for $DOMAIN) ==="
echo "⚠️  This requires Cloudflare tunnel to be configured on the VM"
echo "   Checking if cloudflared is installed on VM..."

CLOUDFLARED_INSTALLED=$(gcloud compute ssh "$VM" \
    --zone "$ZONE" \
    --project "$PROJECT" \
    --tunnel-through-iap \
    --command "command -v cloudflared >/dev/null 2>&1 && echo 'YES' || echo 'NO'" 2>/dev/null || echo "NO")

if [ "$CLOUDFLARED_INSTALLED" = "YES" ]; then
    print_status 0 "cloudflared is installed on VM"
    
    # Check if tunnel service is running
    TUNNEL_RUNNING=$(gcloud compute ssh "$VM" \
        --zone "$ZONE" \
        --project "$PROJECT" \
        --tunnel-through-iap \
        --command "sudo systemctl is-active cloudflared >/dev/null 2>&1 && echo 'YES' || echo 'NO'" 2>/dev/null || echo "NO")
    
    if [ "$TUNNEL_RUNNING" = "YES" ]; then
        print_status 0 "Cloudflare tunnel service is running"
        
        # Test domain accessibility
        echo "   Testing domain: $DOMAIN"
        DOMAIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://$DOMAIN/health" 2>/dev/null || echo "000")
        
        if [ "$DOMAIN_STATUS" = "200" ]; then
            print_status 0 "Domain $DOMAIN is accessible"
        else
            print_status 1 "Domain $DOMAIN returned status: $DOMAIN_STATUS"
            echo "   This may indicate:"
            echo "   - DNS not configured correctly"
            echo "   - Tunnel not routing to correct hostname"
            echo "   - Cloudflare Access blocking requests"
        fi
    else
        print_status 1 "Cloudflare tunnel service is NOT running"
        echo "   To start: sudo systemctl start cloudflared"
        echo "   To enable: sudo systemctl enable cloudflared"
    fi
else
    print_status 1 "cloudflared is NOT installed on VM"
    echo ""
    echo "📋 To set up Cloudflare tunnel:"
    echo "1. SSH to VM: gcloud compute ssh $VM --zone $ZONE --project $PROJECT"
    echo "2. Follow: docs/TUNNEL_SETUP_RUNBOOK.md"
    echo "   Or run: bash scripts/setup_auth_free_tunnel.sh"
fi

# Step 5: Playwright Verification
echo ""
echo "=== STEP 5: Playwright Verification ==="

# Check if Playwright is available
if command -v npx &> /dev/null; then
    print_status 0 "npx is available"
    
    # Check if Playwright test file exists
    if [ -f "tests/dashboard/dashboard_truth.spec.ts" ] || [ -f "src/verification/playwright_dashboard_full.spec.ts" ]; then
        TEST_FILE=""
        if [ -f "tests/dashboard/dashboard_truth.spec.ts" ]; then
            TEST_FILE="tests/dashboard/dashboard_truth.spec.ts"
        elif [ -f "src/verification/playwright_dashboard_full.spec.ts" ]; then
            TEST_FILE="src/verification/playwright_dashboard_full.spec.ts"
        fi
        
        echo "   Running Playwright test: $TEST_FILE"
        echo "   Dashboard URL: $DASHBOARD_URL"
        
        export DASHBOARD_URL="$DASHBOARD_URL"
        export CONTROL_PLANE_TOKEN="${CONTROL_PLANE_TOKEN:-}"
        
        # Run Playwright test
        if npx playwright test "$TEST_FILE" --headed 2>&1 | tee /tmp/playwright_test.log; then
            print_status 0 "Playwright tests passed"
        else
            print_status 1 "Playwright tests had issues"
            echo "   Check /tmp/playwright_test.log for details"
        fi
    else
        echo -e "${YELLOW}⚠️  Playwright test file not found${NC}"
        echo "   Creating a simple verification test..."
        
        # Create a simple Playwright test
        mkdir -p tests/dashboard
        cat > tests/dashboard/dashboard_verification.spec.ts << 'EOF'
import { test, expect } from '@playwright/test';

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://127.0.0.1:28787';

test('Dashboard is accessible', async ({ page }) => {
  await page.goto(DASHBOARD_URL);
  
  // Check that we don't get a 404
  await expect(page).not.toHaveURL(/.*404.*/);
  
  // Check for common dashboard elements or API response
  const response = await page.goto(`${DASHBOARD_URL}/api/status`);
  expect(response?.status()).toBe(200);
  
  const status = await response?.json();
  expect(status).toHaveProperty('mode');
  expect(status).toHaveProperty('execution_enabled');
});

test('Dashboard health endpoint works', async ({ request }) => {
  const response = await request.get(`${DASHBOARD_URL}/health`);
  expect(response.status()).toBe(200);
});

test('Dashboard status endpoint returns valid data', async ({ request }) => {
  const response = await request.get(`${DASHBOARD_URL}/api/status`);
  expect(response.status()).toBe(200);
  
  const data = await response.json();
  expect(data).toHaveProperty('mode');
  expect(data).toHaveProperty('execution_enabled');
  expect(data).toHaveProperty('accounts_loaded');
});
EOF
        
        echo "   Created test file: tests/dashboard/dashboard_verification.spec.ts"
        echo "   Running test..."
        
        export DASHBOARD_URL="$DASHBOARD_URL"
        if npx playwright test tests/dashboard/dashboard_verification.spec.ts --headed 2>&1 | tee /tmp/playwright_test.log; then
            print_status 0 "Playwright verification tests passed"
        else
            print_status 1 "Playwright verification tests failed"
            echo "   Check /tmp/playwright_test.log for details"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  npx not found. Skipping Playwright tests${NC}"
    echo "   Install with: npm install"
fi

# Summary
echo ""
echo "=== SUMMARY ==="
echo ""
print_status 0 "Local dashboard accessible at: $DASHBOARD_URL"
echo ""
if [ "${TUNNEL_PID:-}" != "" ]; then
    echo "📋 Tunnel Information:"
    echo "   PID: $TUNNEL_PID"
    echo "   To stop: kill $TUNNEL_PID"
    echo "   Logs: /tmp/tunnel.log"
    echo ""
fi

echo "📋 Next Steps:"
echo "1. Open dashboard: $DASHBOARD_URL"
echo "2. For public access, ensure Cloudflare tunnel is configured on VM"
echo "3. Domain $DOMAIN should route through Cloudflare tunnel"
echo ""

# Open browser
if command -v open &> /dev/null; then
    echo "🌐 Opening dashboard in browser..."
    open "$DASHBOARD_URL"
fi

echo ""
echo "✅ Dashboard fix complete!"
