# 🚀 ENABLE TRADING NOW - QUICK GUIDE

## ⚡ FASTEST METHOD: Use API Trigger (30 seconds)

Your system has a built-in API endpoint to enable trading immediately:

```bash
curl -X POST "https://ai-quant-trading.uc.r.appspot.com/api/enable-trading?token=${SCAN_TRIGGER_TOKEN}"
```

This will:
- ✅ Disable weekend mode
- ✅ Enable signal generation
- ✅ Start executing trades immediately
- ✅ No deployment needed

---

## 🌐 METHOD 2: Google Cloud Console (5 minutes)

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/appengine/settings/environmentvariables?project=ai-quant-trading

2. **Update Environment Variables**
   - Find: `WEEKEND_MODE` → Change to `false`
   - Find: `TRADING_DISABLED` → Change to `false`
   - Find: `SIGNAL_GENERATION` → Change to `enabled`

3. **Save Changes**
   - Click "Save" at the bottom
   - System will restart automatically (2-3 minutes)

---

## 💻 METHOD 3: Local Command (Already Done)

The `app.yaml` file has been updated locally with:
```yaml
WEEKEND_MODE: "false"
TRADING_DISABLED: "false"
SIGNAL_GENERATION: "enabled"
```

**To deploy** (when cloud build is working):
```bash
cd /Users/mac/quant_system_clean/google-cloud-trading-system
gcloud app deploy --quiet
```

---

## ✅ VERIFY TRADING IS ENABLED

After enabling, check the logs:

```bash
# Method 1: Check via API
curl https://ai-quant-trading.uc.r.appspot.com/api/system/status

# Method 2: Check Google Cloud Logs
gcloud app logs tail --service=default

# Method 3: Visit Dashboard
# https://ai-quant-trading.uc.r.appspot.com
```

You should see:
- ✅ "TRADING ACTIVE" instead of "WEEKEND MODE"
- ✅ Live market data streaming
- ✅ Signals being generated
- ✅ Orders being placed

---

## 📊 CURRENT SYSTEM STATUS

**Active Strategies:**
- Account 006: Group 3 High Win Rate (AUD/USD)
- Account 007: Group 2 Zero Drawdown (EUR/USD)  
- Account 008: Group 1 High Frequency (Multi-Portfolio)
- Account 011: Momentum Trading

**Total Portfolio:** $423,831.27

---

## 🚨 RECOMMENDED: Use API Trigger

**Run this command NOW to enable trading:**

```bash
curl -X POST "https://ai-quant-trading.uc.r.appspot.com/api/enable-trading?token=${SCAN_TRIGGER_TOKEN}"
```

This is the **fastest and safest** method - takes effect immediately without deployment!





