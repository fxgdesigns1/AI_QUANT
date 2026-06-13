#!/bin/bash
# fix_cloudflare_tunnel_domain.sh
# Fixes Cloudflare tunnel to use alpha.fxgdesigns.co.uk domain
# Also ensures React build is on VM

set -euo pipefail

VM="fxg-quant-paper-e2-micro"
ZONE="us-east1-b"
PROJECT="fxg-ai-trading"
DOMAIN="alpha.fxgdesigns.co.uk"
SERVICE_PORT="8787"
CONFIG_FILE="/etc/cloudflared/config.yml"

echo "=== FIXING CLOUDFLARE TUNNEL FOR $DOMAIN ==="
echo ""

# Colors
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

# Step 1: Check current tunnel config
echo "=== STEP 1: Checking Current Tunnel Config ==="
CURRENT_CONFIG=$(gcloud compute ssh "$VM" \
    --zone "$ZONE" \
    --project "$PROJECT" \
    --tunnel-through-iap \
    --command "sudo cat $CONFIG_FILE 2>/dev/null || echo 'NOT_FOUND'" 2>/dev/null || echo "ERROR")

if [ "$CURRENT_CONFIG" = "NOT_FOUND" ] || [ "$CURRENT_CONFIG" = "ERROR" ]; then
    print_status 1 "Tunnel config not found or error reading"
    echo "   Config file: $CONFIG_FILE"
    echo ""
    echo "📋 You need to set up the tunnel first. Run on VM:"
    echo "   bash scripts/setup_auth_free_tunnel.sh"
    echo "   OR follow: docs/TUNNEL_SETUP_RUNBOOK.md"
    exit 1
else
    echo "Current config:"
    echo "$CURRENT_CONFIG" | head -20
    echo ""
    
    # Check if domain is already configured
    if echo "$CURRENT_CONFIG" | grep -q "$DOMAIN"; then
        print_status 0 "Domain $DOMAIN is already in config"
    else
        print_status 1 "Domain $DOMAIN is NOT in config"
        echo ""
        echo "⚠️  Need to update tunnel config to include $DOMAIN"
        echo ""
        echo "📋 To fix this, SSH to VM and run:"
        echo ""
        echo "   gcloud compute ssh $VM --zone $ZONE --project $PROJECT"
        echo ""
        echo "   Then on VM:"
        echo "   sudo nano $CONFIG_FILE"
        echo ""
        echo "   Update ingress to include:"
        echo "   ingress:"
        echo "     - hostname: $DOMAIN"
        echo "       service: http://127.0.0.1:$SERVICE_PORT"
        echo "     - hostname: alpha-dashboard.fxg.internal"
        echo "       service: http://127.0.0.1:$SERVICE_PORT"
        echo "     - service: http_status:404"
        echo ""
        echo "   Then restart:"
        echo "   sudo systemctl restart cloudflared"
        echo ""
        echo "   And route DNS:"
        echo "   cloudflared tunnel route dns fxg-alpha-dashboard $DOMAIN"
        echo ""
        exit 1
    fi
fi

# Step 2: Check if React build exists on VM
echo ""
echo "=== STEP 2: Checking React Build on VM ==="
REACT_BUILD_PATH="frontend/fxg-dashboard/dist"
REACT_EXISTS=$(gcloud compute ssh "$VM" \
    --zone "$ZONE" \
    --project "$PROJECT" \
    --tunnel-through-iap \
    --command "cd ~/gcloud-system 2>/dev/null || cd ~/gcloud_clean_room 2>/dev/null || cd ~ && \
        if [ -d $REACT_BUILD_PATH ] && [ -f $REACT_BUILD_PATH/index.html ]; then \
            echo 'EXISTS'; \
        else \
            echo 'NOT_FOUND'; \
        fi" 2>/dev/null || echo "ERROR")

if [ "$REACT_EXISTS" = "EXISTS" ]; then
    print_status 0 "React build exists on VM"
else
    print_status 1 "React build NOT found on VM"
    echo ""
    echo "📋 Deploying React build to VM..."
    
    # Check if local build exists
    LOCAL_BUILD="/Users/mac/Library/CloudStorage/GoogleDrive-fxgdesigns1@gmail.com/My Drive/AI Trading/Gcloud system/frontend/fxg-dashboard/dist"
    if [ -d "$LOCAL_BUILD" ] && [ -f "$LOCAL_BUILD/index.html" ]; then
        echo "   Local build found, deploying..."
        
        # Create a tarball and copy to VM
        cd "$(dirname "$LOCAL_BUILD")"
        tar czf /tmp/react_build.tar.gz dist/
        
        # Copy to VM
        gcloud compute scp \
            --zone "$ZONE" \
            --project "$PROJECT" \
            /tmp/react_build.tar.gz \
            "$VM:/tmp/react_build.tar.gz" \
            --tunnel-through-iap
        
        # Extract on VM
        gcloud compute ssh "$VM" \
            --zone "$ZONE" \
            --project "$PROJECT" \
            --tunnel-through-iap \
            --command "cd ~/gcloud-system 2>/dev/null || cd ~/gcloud_clean_room 2>/dev/null || cd ~ && \
                mkdir -p frontend/fxg-dashboard && \
                tar xzf /tmp/react_build.tar.gz -C frontend/fxg-dashboard && \
                rm /tmp/react_build.tar.gz && \
                echo 'DEPLOYED' || echo 'FAILED'" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            print_status 0 "React build deployed to VM"
        else
            print_status 1 "Failed to deploy React build"
            echo "   Manual steps:"
            echo "   1. Build locally: cd frontend/fxg-dashboard && npm run build"
            echo "   2. Copy to VM: gcloud compute scp --recurse dist/ $VM:~/gcloud-system/frontend/fxg-dashboard/dist"
        fi
        
        rm -f /tmp/react_build.tar.gz
    else
        print_status 1 "Local React build not found"
        echo "   Build it first:"
        echo "   cd frontend/fxg-dashboard && npm run build"
    fi
fi

# Step 3: Verify tunnel service
echo ""
echo "=== STEP 3: Verifying Tunnel Service ==="
TUNNEL_STATUS=$(gcloud compute ssh "$VM" \
    --zone "$ZONE" \
    --project "$PROJECT" \
    --tunnel-through-iap \
    --command "sudo systemctl is-active cloudflared >/dev/null 2>&1 && echo 'ACTIVE' || echo 'INACTIVE'" 2>/dev/null || echo "ERROR")

if [ "$TUNNEL_STATUS" = "ACTIVE" ]; then
    print_status 0 "Cloudflare tunnel service is running"
else
    print_status 1 "Cloudflare tunnel service is NOT running"
    echo "   Start it: sudo systemctl start cloudflared"
    echo "   Enable it: sudo systemctl enable cloudflared"
fi

# Step 4: Test domain
echo ""
echo "=== STEP 4: Testing Domain ==="
echo "Testing: https://$DOMAIN/health"
DOMAIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://$DOMAIN/health" 2>/dev/null || echo "000")

if [ "$DOMAIN_STATUS" = "200" ]; then
    print_status 0 "Domain is accessible (HTTP 200)"
elif [ "$DOMAIN_STATUS" = "302" ] || [ "$DOMAIN_STATUS" = "307" ]; then
    print_status 1 "Domain returns redirect ($DOMAIN_STATUS)"
    echo "   This likely means Cloudflare Access is blocking"
    echo "   Options:"
    echo "   1. Disable Cloudflare Access for this domain (temporary)"
    echo "   2. Add bypass rule in Cloudflare Zero Trust"
    echo "   3. Use local tunnel: bash scripts/quick_tunnel.sh"
elif [ "$DOMAIN_STATUS" = "404" ]; then
    print_status 1 "Domain returns 404"
    echo "   Tunnel may not be routing correctly"
    echo "   Check tunnel config and DNS routing"
else
    print_status 1 "Domain returned status: $DOMAIN_STATUS"
    echo "   Check tunnel logs: sudo journalctl -u cloudflared -n 50"
fi

# Summary
echo ""
echo "=== SUMMARY ==="
echo ""
echo "📋 Quick Access Options:"
echo "1. Local tunnel: bash scripts/quick_tunnel.sh"
echo "   Then open: http://127.0.0.1:28787"
echo ""
echo "2. Direct VM IP (if firewall allows):"
echo "   http://35.231.194.238:8787"
echo ""
echo "3. Fix Cloudflare Access:"
echo "   - Go to Cloudflare Dashboard → Zero Trust → Access"
echo "   - Find application for $DOMAIN"
echo "   - Add bypass rule or disable temporarily"
echo ""
