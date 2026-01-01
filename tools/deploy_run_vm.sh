#!/bin/bash
set -euo pipefail

echo "Starting deploy_run_vm.sh"

sudo cp /etc/systemd/system/ai_trading.service /etc/systemd/system/ai_trading.service.bak || true
if [ -f /tmp/ai_trading.service ]; then
  sudo mv /tmp/ai_trading.service /etc/systemd/system/ai_trading.service
  echo "Deployed ai_trading.service"
else
  echo "No /tmp/ai_trading.service found"
fi

sudo mkdir -p /opt/quant_system_clean/google-cloud-trading-system/tools
if [ -f /tmp/incremental_relax_loop.py ]; then
  sudo mv /tmp/incremental_relax_loop.py /opt/quant_system_clean/google-cloud-trading-system/tools/incremental_relax_loop.py
fi
if [ -f /tmp/force_demo_orders.py ]; then
  sudo mv /tmp/force_demo_orders.py /opt/quant_system_clean/google-cloud-trading-system/tools/force_demo_orders.py
fi

sudo chmod +x /opt/quant_system_clean/google-cloud-trading-system/tools/incremental_relax_loop.py /opt/quant_system_clean/google-cloud-trading-system/tools/force_demo_orders.py || true

sudo systemctl daemon-reload || true
sudo systemctl restart ai_trading.service || true

echo '--- SERVICE STATUS ---'
sudo systemctl status ai_trading.service --no-pager | sed -n '1,12p' || true

echo '--- LOADER JOURNAL ---'
sudo journalctl -u ai_trading.service -n 200 --no-pager | grep -iE 'Loaded Trade With Pat ORB config|Config loader candidates|Environment override' || true

echo '--- FIND CONFIGS ---'
sudo find /opt/quant_system_clean -type f -name 'trade_with_pat_orb_dual_session.yaml' -print || true

echo '--- RUN VERIFY ---'
python3 /opt/quant_system_clean/google-cloud-trading-system/verify_strategies_running.py | sed -n '1,200p' || true

echo '--- RUN INCREMENTAL LOOP ---'
python3 /opt/quant_system_clean/google-cloud-trading-system/tools/incremental_relax_loop.py | tee /tmp/incremental_relax_report.json || true

echo '--- REPORT SAVED TO /tmp/incremental_relax_report.json ---'































