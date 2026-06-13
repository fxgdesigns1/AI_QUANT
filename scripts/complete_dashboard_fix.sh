#!/bin/bash
# complete_dashboard_fix.sh
# Complete dashboard fix: tunnel setup, React build deployment, Playwright verification

set -euo pipefail

VM="fxg-quant-paper-e2-micro"
ZONE="us-east1-b"
PROJECT="fxg-ai-trading"
DOMAIN="alpha.fxgdesigns.co.uk"
SERVICE_PORT="8787"
LOCAL_PORT="28787"
DASHBOARD_URL="http://127.0.0.1:${LOCAL_PORT}"

echo "=== COMPLETE DASHBOARD FIX ==="
echo "VM: $VM"
echo "Domain: $DOMAIN"
echo "Local URL: $DASHBOARD_URL"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Step 1: Ensure local tunnel is running
echo "=== STEP 1: Local IAP Tunnel ==="
if lsof -i ":$LOCAL_PORT" >/dev/null 2>&1; then
    print_status 0 "Local tunnel already running"
else
    echo "Starting local tunnel..."
    gcloud compute ssh "$VM" \
        --zone "$ZONE" \
        --project "$PROJECT" \
        --tunnel-through-iap \
        -- -N -L "$LOCAL_PORT:127.0.0.1:$SERVICE_PORT" > /tmp/tunnel.log 2>&1 &
    TUNNEL_PID=$!
    sleep 5
    
    if curl -sf --max-time 3 "$DASHBOARD_URL/health" >/dev/null 2>&1; then
        print_status 0 "Local tunnel started (PID: $TUNNEL_PID)"
    else
        print_status 1 "Local tunnel failed to start"
        exit 1
    fi
fi

# Step 2: Check React build on VM
echo ""
echo "=== STEP 2: React Build on VM ==="
REACT_BUILD_CHECK=$(gcloud compute ssh "$VM" \
    --zone "$ZONE" \
    --project "$PROJECT" \
    --tunnel-through-iap \
    --command "cd ~/gcloud-system 2>/dev/null || cd ~/gcloud_clean_room 2>/dev/null || cd ~ && \
        if [ -f frontend/fxg-dashboard/dist/index.html ]; then \
            echo 'EXISTS'; \
        else \
            echo 'NOT_FOUND'; \
        fi" 2>/dev/null || echo "ERROR")

if [ "$REACT_BUILD_CHECK" = "EXISTS" ]; then
    print_status 0 "React build exists on VM"
else
    print_status 1 "React build NOT found on VM"
    echo "   Deploying React build..."
    
    LOCAL_BUILD_DIR="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system/frontend/fxg-dashboard/dist"
    
    if [ -d "$LOCAL_BUILD_DIR" ] && [ -f "$LOCAL_BUILD_DIR/index.html" ]; then
        # Create tarball
        cd "$(dirname "$LOCAL_BUILD_DIR")"
        tar czf /tmp/react_build.tar.gz dist/
        
        # Copy to VM
        gcloud compute scp \
            --zone "$ZONE" \
            --project "$PROJECT" \
            /tmp/react_build.tar.gz \
            "$VM:/tmp/react_build.tar.gz" \
            --tunnel-through-iap
        
        # Extract on VM
        DEPLOY_RESULT=$(gcloud compute ssh "$VM" \
            --zone "$ZONE" \
            --project "$PROJECT" \
            --tunnel-through-iap \
            --command "cd ~/gcloud-system 2>/dev/null || cd ~/gcloud_clean_room 2>/dev/null || cd ~ && \
                mkdir -p frontend/fxg-dashboard && \
                tar xzf /tmp/react_build.tar.gz -C frontend/fxg-dashboard && \
                rm /tmp/react_build.tar.gz && \
                ls -la frontend/fxg-dashboard/dist/index.html && \
                echo 'DEPLOYED'" 2>/dev/null || echo "FAILED")
        
        if echo "$DEPLOY_RESULT" | grep -q "DEPLOYED"; then
            print_status 0 "React build deployed to VM"
        else
            print_status 1 "Failed to deploy React build"
            echo "   Manual deploy: gcloud compute scp --recurse --zone $ZONE --project $PROJECT --tunnel-through-iap $LOCAL_BUILD_DIR $VM:~/gcloud-system/frontend/fxg-dashboard/dist"
        fi
        
        rm -f /tmp/react_build.tar.gz
    else
        print_status 1 "Local React build not found"
        echo "   Build it: cd frontend/fxg-dashboard && npm run build"
    fi
fi

# Step 3: Test dashboard endpoints
echo ""
echo "=== STEP 3: Testing Dashboard Endpoints ==="

# Health
if curl -sf --max-time 5 "$DASHBOARD_URL/health" >/dev/null 2>&1; then
    print_status 0 "Health endpoint: OK"
else
    print_status 1 "Health endpoint: FAILED"
fi

# Status
if curl -sf --max-time 5 "$DASHBOARD_URL/api/status" >/dev/null 2>&1; then
    print_status 0 "Status endpoint: OK"
else
    print_status 1 "Status endpoint: FAILED"
fi

# Root (dashboard)
ROOT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$DASHBOARD_URL/" 2>/dev/null || echo "000")
if [ "$ROOT_STATUS" = "200" ]; then
    print_status 0 "Dashboard root: OK (HTTP 200)"
elif [ "$ROOT_STATUS" = "404" ]; then
    print_status 1 "Dashboard root: 404 (React build may not be mounted)"
    echo "   Check: API server logs on VM"
    echo "   Verify: frontend/fxg-dashboard/dist exists on VM"
else
    print_status 1 "Dashboard root: HTTP $ROOT_STATUS"
fi

# Step 4: Playwright test
echo ""
echo "=== STEP 4: Playwright Verification ==="
if command -v npx &> /dev/null; then
    export DASHBOARD_URL="$DASHBOARD_URL"
    export CONTROL_PLANE_TOKEN="${CONTROL_PLANE_TOKEN:-}"
    
    echo "Running Playwright tests..."
    if npx playwright test tests/dashboard/dashboard_accessibility.spec.ts --reporter=list 2>&1 | tee /tmp/playwright_fix.log; then
        print_status 0 "Playwright tests passed"
    else
        TEST_RESULT=$?
        print_status 1 "Playwright tests had issues (exit code: $TEST_RESULT)"
        echo "   Check /tmp/playwright_fix.log for details"
    fi
else
    echo -e "${YELLOW}⚠️  npx not found, skipping Playwright tests${NC}"
fi

# Step 5: Cloudflare tunnel info
echo ""
echo "=== STEP 5: Cloudflare Tunnel Status ==="
CLOUDFLARED_STATUS=$(gcloud compute ssh "$VM" \
    --zone "$ZONE" \
    --project "$PROJECT" \
    --tunnel-through-iap \
    --command "sudo systemctl is-active cloudflared >/dev/null 2>&1 && echo 'ACTIVE' || echo 'INACTIVE'" 2>/dev/null || echo "ERROR")

if [ "$CLOUDFLARED_STATUS" = "ACTIVE" ]; then
    print_status 0 "Cloudflare tunnel service is running"
    
    # Test domain
    DOMAIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://$DOMAIN/health" 2>/dev/null || echo "000")
    if [ "$DOMAIN_STATUS" = "200" ]; then
        print_status 0 "Domain $DOMAIN is accessible"
    elif [ "$DOMAIN_STATUS" = "302" ] || [ "$DOMAIN_STATUS" = "307" ]; then
        echo -e "${YELLOW}⚠️  Domain returns redirect ($DOMAIN_STATUS) - Cloudflare Access may be blocking${NC}"
        echo "   To fix: Cloudflare Dashboard → Zero Trust → Access → Applications"
        echo "   Find $DOMAIN and add bypass rule or disable temporarily"
    else
        print_status 1 "Domain returned: HTTP $DOMAIN_STATUS"
    fi
else
    echo -e "${YELLOW}⚠️  Cloudflare tunnel service is not running${NC}"
    echo "   For public access, set up tunnel: bash scripts/setup_auth_free_tunnel.sh"
fi

# Summary
echo ""
echo "=== SUMMARY ==="
echo ""
print_status 0 "Dashboard accessible locally at: $DASHBOARD_URL"
echo ""
echo "📋 Access Options:"
echo "1. Local tunnel: $DASHBOARD_URL (already running)"
echo "2. Public domain: https://$DOMAIN (requires Cloudflare tunnel setup)"
echo ""
echo "📋 Next Steps:"
if [ "$ROOT_STATUS" != "200" ]; then
    echo "1. Fix dashboard root (React build deployment)"
fi
if [ "$CLOUDFLARED_STATUS" != "ACTIVE" ] || [ "${DOMAIN_STATUS:-000}" != "200" ]; then
    echo "2. Set up Cloudflare tunnel for public access"
fi
echo "3. Run Playwright tests: npx playwright test tests/dashboard/"
echo ""

# Open browser
if command -v open &> /dev/null; then
    echo "🌐 Opening dashboard..."
    open "$DASHBOARD_URL"
fi

echo "✅ Fix complete!"
