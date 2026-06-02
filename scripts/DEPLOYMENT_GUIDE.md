# FXG Startup System Deployment Guide

This guide covers the deployment and usage of the comprehensive FXG startup health system.

## 🎯 Overview

The FXG startup system consists of three main components:

1. **FXG Startup Script** (`scripts/fxg_startup.sh`) - Comprehensive health checker and auto-remediation
2. **Windows Pull Signals Fix** (`scripts/windows/pull_signals.ps1`) - Fixed PowerShell script with corrected threshold  
3. **PM2 Watchdog Service** (`scripts/fxg-watchdog.js`) - Continuous monitoring with Telegram alerts

## 📋 Components Overview

### 1. FXG Startup Health Script

**File**: `scripts/fxg_startup.sh`

**What it checks**:
- ✅ EA heartbeat age (threshold: 120s)
- ✅ Signal file size (threshold: 1000 bytes)
- ✅ Windows pull loop status (via sidecar/SSH)
- ✅ Preflight gate status
- ✅ ALPHA services (`ai-quant-control-plane`, `ai-quant-runner`)
- ✅ Automatic remediation where possible
- ✅ Telegram alerts with exact fix commands

### 2. Windows PowerShell Fix

**File**: `scripts/windows/pull_signals.ps1`

**Key changes**:
- 🔧 **FIXED**: Changed file size threshold from 1000 bytes to 100 bytes
- ✅ Enhanced error handling and logging
- ✅ Added health checks and connectivity tests
- ✅ Improved service loop with periodic health monitoring

### 3. PM2 Watchdog Service

**Files**:
- `scripts/fxg-watchdog.js` - Main watchdog service
- `scripts/ecosystem.config.js` - PM2 configuration
- `scripts/setup_fxg_watchdog.sh` - Installation script

**Features**:
- ⏱️ Runs every 60 seconds
- 📱 Telegram alerts with exact fix commands
- 🔄 Auto-restart on failure
- 📊 Comprehensive logging
- 🎯 No silent failures - all issues are reported immediately

## 🚀 Deployment Instructions

### Step 1: Deploy to ALPHA VM

**Copy scripts to ALPHA VM**:
```bash
# Copy the entire scripts directory to ALPHA
gcloud compute scp --tunnel-through-iap --zone us-central1-a \
  --recurse ./scripts/ \
  fxg-paper-e2-small-main-2026:/opt/ai-quant/scripts/ \
  --project fxg-ai-trading
```

**Make scripts executable on ALPHA**:
```bash
gcloud compute ssh --tunnel-through-iap --zone us-central1-a \
  fxg-paper-e2-small-main-2026 --project fxg-ai-trading \
  --command="chmod +x /opt/ai-quant/scripts/*.sh /opt/ai-quant/scripts/*.js"
```

### Step 2: Deploy Windows PowerShell Fix

**Run the deployment script**:
```bash
./scripts/deploy_windows_pull_signals.sh
```

This will:
- Backup existing `pull_signals.ps1`
- Deploy the fixed version with 100-byte threshold
- Restart the FXG service if it exists
- Verify deployment

### Step 3: Install PM2 Watchdog Service

**On ALPHA VM**:
```bash
# SSH into ALPHA
gcloud compute ssh --tunnel-through-iap --zone us-central1-a \
  fxg-paper-e2-small-main-2026 --project fxg-ai-trading

# Run the setup script
sudo /opt/ai-quant/scripts/setup_fxg_watchdog.sh
```

This will:
- Install Node.js and PM2 if needed
- Configure PM2 startup
- Start the watchdog service
- Save PM2 configuration

### Step 4: Test the Startup Script

**Run the startup script**:
```bash
# On ALPHA VM
sudo /opt/ai-quant/scripts/fxg_startup.sh
```

**Expected output**:
```
=== Service Health Check ===
✅ Service ai-quant-control-plane is running
✅ Service ai-quant-runner is running

=== EA Heartbeat Check ===
✅ EA heartbeat is fresh: 45s old

=== Signal File Check ===
✅ Signal file size OK: 2847 bytes

=== Pull Loop Check ===
✅ Pull loop status OK

=== Preflight Check ===
✅ Preflight status: PASS

=== Final Status Summary ===
✅ All systems healthy - no issues found
```

## 📱 Telegram Alerts

The system will send Telegram alerts for:

- 🚨 **CRITICAL**: Service down, preflight blocked, EA heartbeat stale
- ⚠️ **WARNING**: Small signal files, pull loop unreachable
- ✅ **SUCCESS**: System startup complete, all healthy

Each alert includes:
- Clear problem description
- **Exact fix command** to resolve the issue
- Context about impact on trading

## 🔧 Operation Commands

### PM2 Watchdog Management

```bash
# View real-time logs
pm2 logs fxg-watchdog

# Restart the watchdog
pm2 restart fxg-watchdog

# Stop the watchdog
pm2 stop fxg-watchdog

# Check status
pm2 status fxg-watchdog

# Monitor dashboard
pm2 monit
```

### Manual Health Checks

```bash
# Run complete startup health check
sudo /opt/ai-quant/scripts/fxg_startup.sh

# Check individual components
systemctl status ai-quant-control-plane
curl -s http://127.0.0.1:8787/api/mt5/preflight | python3 -m json.tool
tail -f /home/aiquant/gcloud-system/logs/signals_ftmo_demo2.jsonl
```

### Windows PowerShell Management

```bash
# Check Windows service status
gcloud compute ssh --tunnel-through-iap --zone us-central1-a \
  fxg-windows-vm-instance --project fxg-ai-trading \
  --command="powershell -Command 'Get-Service FXGPullSignals'"

# View pull signals log
gcloud compute ssh --tunnel-through-iap --zone us-central1-a \
  fxg-windows-vm-instance --project fxg-ai-trading \
  --command="powershell -Command 'Get-Content C:\\FXG\\logs\\pull_signals.log -Tail 20'"
```

## 📊 Monitoring and Logs

### Log Locations

**ALPHA VM**:
- Startup script: `/opt/ai-quant/logs/fxg_startup.log`
- Watchdog main: `/opt/ai-quant/logs/fxg-watchdog.log`
- Watchdog errors: `/opt/ai-quant/logs/fxg-watchdog-error.log`

**Windows VM**:
- Pull signals: `C:\FXG\logs\pull_signals.log`

### Health Check Schedule

- **Startup Script**: Run manually or via cron
- **PM2 Watchdog**: Every 60 seconds automatically
- **Telegram Alerts**: Immediate on any failure

## 🚨 Troubleshooting

### Common Issues

**1. Preflight BLOCKED**
```bash
# Check preflight details
curl -s http://127.0.0.1:8787/api/mt5/preflight | python3 -m json.tool

# Restart services
sudo systemctl restart ai-quant-control-plane ai-quant-runner
```

**2. EA Heartbeat Stale**
```bash
# Sync telemetry
gcloud compute scp --tunnel-through-iap --zone us-central1-a \
  fxg-windows-vm-instance:/FXG/telemetry/latest.json \
  /tmp/ea_heartbeat_sync.json --project fxg-ai-trading
```

**3. Windows Pull Loop Errors**
```bash
# Connect to Windows and restart service
gcloud compute ssh --tunnel-through-iap --zone us-central1-a \
  fxg-windows-vm-instance --project fxg-ai-trading
# Then: powershell -Command 'Restart-Service FXGPullSignals'
```

**4. PM2 Watchdog Not Starting**
```bash
# Check Node.js installation
node --version

# Reinstall PM2
npm install -g pm2

# Check script syntax
node --check /opt/ai-quant/scripts/fxg-watchdog.js
```

## ⚙️ Configuration

### Environment Variables

Set these on ALPHA VM for optimal operation:

```bash
export MT5_SIDECAR_BASE_URL="http://192.168.1.100:8080"
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### Customization

**Modify thresholds in the startup script**:
```bash
# Edit /opt/ai-quant/scripts/fxg_startup.sh
HEARTBEAT_THRESHOLD=120  # seconds
SIGNAL_SIZE_THRESHOLD=1000  # bytes
```

**Adjust watchdog frequency**:
```bash
# Edit /opt/ai-quant/scripts/fxg-watchdog.js
checkIntervalMs: 60 * 1000  # 60 seconds
```

## ✅ Success Indicators

When everything is working correctly:

1. **Startup script** reports "All systems healthy"
2. **PM2 status** shows watchdog running
3. **Telegram** receives periodic health confirmations
4. **Preflight** consistently returns PASS
5. **Services** remain active without restarts

## 🔄 Maintenance

### Daily Tasks
- Review Telegram alerts for any overnight issues
- Check PM2 watchdog status: `pm2 status fxg-watchdog`

### Weekly Tasks  
- Review startup script logs for patterns
- Verify Windows PowerShell script is running smoothly
- Test manual startup script execution

### Monthly Tasks
- Update Node.js and PM2 if needed
- Review and adjust alert thresholds based on observed patterns
- Test disaster recovery procedures

---

## 📞 Support

For issues with this system:

1. Check logs in `/opt/ai-quant/logs/`
2. Run manual health check: `sudo /opt/ai-quant/scripts/fxg_startup.sh`
3. Review Telegram alerts for specific fix commands
4. Check PM2 watchdog status: `pm2 logs fxg-watchdog`

**Remember: No silent failures - if you're not getting Telegram alerts, the watchdog itself may need attention.**