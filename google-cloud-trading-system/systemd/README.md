Install on your GCE VM (f1-micro) to run alongside your current system.

1) Copy repo to /opt and install service

   sudo mkdir -p /opt && sudo chown $USER:$USER /opt
   sudo rsync -a --delete /Users/mac/quant_system_clean/ /opt/quant_system_clean/
   sudo cp /opt/quant_system_clean/google-cloud-trading-system/systemd/agent-controller.service /etc/systemd/system/

2) Set environment (demo account, Telegram if desired)

   sudo systemctl daemon-reload
   sudo systemctl enable agent-controller
   sudo systemctl start agent-controller

The service runs dashboard at PORT=8081 so it won’t clash with your existing 8080 app.

Check logs:

   journalctl -u agent-controller -f



