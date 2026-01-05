#!/bin/bash
# Control Plane Quick Start - Copy/Paste Commands for VM Deployment

# ============================================
# STEP 1: Install Dependencies on VM
# ============================================
pip3 install fastapi uvicorn pydantic pyyaml python-dotenv

# ============================================
# STEP 2: Set Environment Variables
# ============================================
export CONTROL_PLANE_TOKEN="$(openssl rand -hex 32)"
export CONTROL_PLANE_HOST="127.0.0.1"
export CONTROL_PLANE_PORT="8787"
export RUNTIME_CONFIG_PATH="runtime/config.yaml"
export LOG_FILE_PATH="logs/ai_quant.log"

# Save token for later use
echo "CONTROL_PLANE_TOKEN=$CONTROL_PLANE_TOKEN" >> ~/.ai_quant_env
chmod 600 ~/.ai_quant_env

# ============================================
# STEP 3: Verify Installation
# ============================================
./scripts/verify_control_plane.sh

# ============================================
# STEP 4: Start Control Plane (Background)
# ============================================
nohup ./scripts/run_control_plane.sh > logs/control_plane.log 2>&1 &
echo "Control Plane PID: $!"

# Wait for startup
sleep 3

# Test health
curl http://127.0.0.1:8787/health

# ============================================
# STEP 5: Start Runner (Separate Terminal)
# ============================================
# In another tmux/screen session:
TRADING_MODE=paper \
PAPER_EXECUTION_ENABLED=false \
PAPER_ALLOW_OANDA_NETWORK=true \
python3 -m runner_src.runner.main

# ============================================
# STEP 6: Access Dashboard (SSH Tunnel)
# ============================================
# On your LOCAL machine:
ssh -L 8787:127.0.0.1:8787 user@vm-hostname

# Then open browser: http://localhost:8787/

# ============================================
# VERIFICATION COMMANDS
# ============================================

# Check API is running
curl http://127.0.0.1:8787/health

# Get status
curl http://127.0.0.1:8787/api/status | jq

# Get config (no secrets)
curl http://127.0.0.1:8787/api/config | jq

# List strategies
curl http://127.0.0.1:8787/api/strategies | jq

# Activate strategy (requires token)
source ~/.ai_quant_env
curl -X POST http://127.0.0.1:8787/api/strategy/activate \
  -H "Authorization: Bearer $CONTROL_PLANE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"strategy_key": "gold", "scope": "global"}'

# Update config (requires token)
curl -X POST http://127.0.0.1:8787/api/config \
  -H "Authorization: Bearer $CONTROL_PLANE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scan_interval_seconds": 60}'

# Test signals-only safety
MAX_ITERATIONS=1 TRADING_MODE=paper PAPER_EXECUTION_ENABLED=false \
python3 -m runner_src.runner.main 2>&1 | \
grep -i "Execution disabled\|signals-only" && echo "✅ SAFE" || echo "❌ CHECK LOGS"

# Verify no secrets in config
grep -i "OANDA_API_KEY\|password\|secret" runtime/config.yaml && echo "❌ BAD" || echo "✅ OK"

# ============================================
# MONITORING COMMANDS
# ============================================

# Watch control plane logs
tail -f logs/control_plane.log

# Watch runner logs
tail -f logs/ai_quant.log

# Check processes
ps aux | grep -E "control_plane|runner"

# ============================================
# SYSTEMD SERVICE (OPTIONAL)
# ============================================

# Create systemd service file
sudo tee /etc/systemd/system/ai-quant-control-plane.service <<'EOF'
[Unit]
Description=AI_QUANT Control Plane API
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/ai_quant
EnvironmentFile=/home/YOUR_USER/.ai_quant_env
Environment="CONTROL_PLANE_HOST=127.0.0.1"
Environment="CONTROL_PLANE_PORT=8787"
ExecStart=/usr/bin/python3 -m src.control_plane.api
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ai-quant-control-plane
sudo systemctl start ai-quant-control-plane
sudo systemctl status ai-quant-control-plane

# View logs
sudo journalctl -u ai-quant-control-plane -f

# ============================================
# TROUBLESHOOTING
# ============================================

# If dashboard not loading:
# 1. Check API is running
curl http://127.0.0.1:8787/health

# 2. Check browser console for errors

# 3. Verify dashboard file exists
ls -lh dashboard/control_plane.html

# If config changes not applied:
# 1. Check runner logs for hot-reload message
grep "Runtime config changed" logs/ai_quant.log

# 2. Verify config file is valid YAML
python3 -c "import yaml; yaml.safe_load(open('runtime/config.yaml'))"

# 3. Check config mtime
stat runtime/config.yaml

# If strategies not appearing:
# 1. Test strategy registry
python3 -c "from src.control_plane.strategy_registry import STRATEGIES; print(list(STRATEGIES.keys()))"

# 2. Check API response
curl http://127.0.0.1:8787/api/strategies | jq '.strategies[].key'

# ============================================
# STOP/RESTART COMMANDS
# ============================================

# Stop control plane (if started with nohup)
pkill -f "python3 -m src.control_plane.api"

# Stop runner
pkill -f "python3 -m runner_src.runner.main"

# Or if using systemd:
sudo systemctl stop ai-quant-control-plane

# Restart:
./scripts/run_control_plane.sh
# or
sudo systemctl restart ai-quant-control-plane
