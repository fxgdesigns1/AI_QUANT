#!/bin/bash
set -e

PROJECT_ID=ai-quant-trading
INSTANCE=ai-quant-trading-vm

echo "🚀 Starting AI Agent Deployment to $PROJECT_ID"
echo "================================================"

# Set project
echo "📋 Setting project..."
gcloud config set project "$PROJECT_ID" --quiet

# Enable Compute API
echo "🔧 Enabling Compute API..."
gcloud services enable compute.googleapis.com --quiet || true

# Check quotas first
echo "📊 Checking quotas..."
echo "Required: 1 VM (f1-micro), 10GB disk, 1 IP, 2 firewall rules"
echo "Current usage:"
echo "VMs: $(gcloud compute instances list --format='value(name)' | wc -l)"
echo "Disks: $(gcloud compute disks list --format='value(name)' | wc -l)"
echo "IPs: $(gcloud compute addresses list --format='value(name)' | wc -l)"

# Try to create VM in europe-west2 zones
echo "🖥️  Creating VM (f1-micro)..."
CREATED=0
for Z in europe-west2-a europe-west2-b europe-west2-c; do
    echo "   Trying $Z..."
    if gcloud compute instances create "$INSTANCE" \
        --zone="$Z" \
        --machine-type=f1-micro \
        --image-family=debian-12 \
        --image-project=debian-cloud \
        --tags=http-server \
        --boot-disk-size=10GB \
        --quiet; then
        ZONE="$Z"
        CREATED=1
        echo "✅ Created $INSTANCE in $ZONE (f1-micro)"
        break
    fi
done

if [ "$CREATED" != "1" ]; then
    echo "❌ No f1-micro capacity in europe-west2"
    echo "Try again later or contact support"
    exit 1
fi

# Create firewall rules
echo "🔥 Setting up firewall..."
gcloud compute firewall-rules describe allow-8080-8081 >/dev/null 2>&1 || \
gcloud compute firewall-rules create allow-8080-8081 \
    --allow=tcp:8080,tcp:8081 \
    --source-ranges=0.0.0.0/0 \
    --description="Trading system ports" \
    --quiet

# Install dependencies
echo "📦 Installing dependencies..."
gcloud compute ssh "$INSTANCE" --zone="$ZONE" --command '
    sudo mkdir -p /opt/quant_system_clean && \
    sudo chown $USER:$USER /opt/quant_system_clean && \
    sudo apt-get update -y && \
    sudo apt-get install -y python3 python3-pip
'

# Upload code
echo "📤 Uploading code..."
gcloud compute scp --recurse /Users/mac/quant_system_clean/* "$INSTANCE":/opt/quant_system_clean/ --zone="$ZONE"

# Install and start agent service
echo "🤖 Installing agent service..."
gcloud compute ssh "$INSTANCE" --zone="$ZONE" --command '
    set -e
    sudo cp /opt/quant_system_clean/google-cloud-trading-system/systemd/agent-controller.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable agent-controller
    sudo systemctl restart agent-controller
    sleep 3
    echo "Checking agent status..."
    curl -s http://127.0.0.1:8081/api/agent_metrics || true
    journalctl -u agent-controller -n 20 --no-pager || true
'

# Get external IP
IP="$(gcloud compute instances describe "$INSTANCE" --zone="$ZONE" --format='value(networkInterfaces[0].accessConfigs[0].natIP)')"

echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================"
echo "Trading system: http://$IP:8080"
echo "Agent metrics:  http://$IP:8081/api/agent_metrics"
echo "SSH access:     gcloud compute ssh $INSTANCE --zone=$ZONE"
echo ""
echo "📱 Telegram alerts are enabled for:"
echo "   - Agent starts/stops"
echo "   - Anomalies and errors"
echo "   - Daily briefs (6 AM & 9:30 PM London time)"
echo ""
echo "🔧 Agent features:"
echo "   - 24/7 intelligent supervision"
echo "   - Risk guardrails (10% exposure cap, max 5 positions)"
echo "   - London time scheduling (8 AM - 5 PM)"
echo "   - Demo account only (101-004-30719775-008)"
echo ""
echo "✅ Your AI trading agent is now running!"

