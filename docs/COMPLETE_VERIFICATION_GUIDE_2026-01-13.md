# ✅ COMPLETE VERIFICATION GUIDE
**Date:** 2026-01-13  
**Status:** All code deployed - Ready for verification

---

## 🎯 WHAT'S BEEN DONE

### ✅ Code Deployed
1. **3 New API Endpoints** (`src/control_plane/api.py`)
   - `/api/performance/strategies?days=30`
   - `/api/performance/accounts?days=30`
   - `/api/performance/ai-evaluation?days=30`

2. **Performance Tab Overhaul** (`templates/forensic_command.html`)
   - Individual strategy/account metrics
   - AI evaluation summary
   - Period selector, view toggle, sorting, filtering

3. **Countdown Feature** (`templates/forensic_command.html`)
   - Added to News tab
   - Updates every second

4. **Structural Scanner Fix** (`templates/forensic_command.html`)
   - Fixed frontend to display real data

---

## 🚀 VERIFICATION STEPS

### Step 1: Restart API on VM

**Option A: If you're already SSH'd into the VM:**
```bash
cd ~/gcloud-system
bash scripts/complete_restart_and_verify.sh
```

**Option B: Manual restart:**
```bash
cd ~/gcloud-system
pkill -f 'uvicorn.*api:app'
sleep 2
nohup python3 -m uvicorn src.control_plane.api:app --host 0.0.0.0 --port 8000 > /tmp/api.log 2>&1 &
sleep 3
pgrep -f 'uvicorn.*api:app'  # Should show PID
tail -20 /tmp/api.log  # Check for errors
```

### Step 2: Set Up SSH Tunnel (from local machine)

```bash
gcloud compute ssh fxg-quant-paper-e2-micro \
  --zone=us-east1-b \
  --tunnel-through-iap \
  -- -L 8787:127.0.0.1:8000
```

**Keep this terminal open!** The tunnel will forward `localhost:8787` to the VM's port 8000.

### Step 3: Test Endpoints

**Option A: Using Python script:**
```bash
python3 scripts/test_endpoints_once_connected.py
```

**Option B: Manual curl tests:**
```bash
# New endpoints
curl http://localhost:8787/api/performance/strategies?days=30
curl http://localhost:8787/api/performance/accounts?days=30
curl http://localhost:8787/api/performance/ai-evaluation?days=30

# Existing endpoints
curl http://localhost:8787/api/v1/scanner/structural
curl http://localhost:8787/api/v1/outlook/daily
curl http://localhost:8787/api/status
```

### Step 4: Run Playwright Audit

```bash
python3 scripts/comprehensive_playwright_audit.py
```

This will:
- Test all navigation tabs
- Test all API endpoints
- Verify Structural Scanner shows real data
- Verify Market Outlook shows real scenarios
- Test Performance tab
- Test Countdown feature
- Check for console errors
- Generate JSON report

### Step 5: Browser Verification

1. Open browser: `http://localhost:8787`
2. Navigate to **Performance** tab
   - Verify individual strategy/account cards appear
   - Verify AI evaluation summary shows
   - Test period selector (7/30/90/365 days)
   - Test view toggle (Strategies/Accounts/Both)
   - Test sorting options
   - Test search/filter

3. Navigate to **News** tab
   - Verify countdown timer appears (`#newsTimer`)
   - Verify upcoming news section appears (`#upcomingNews`)
   - Verify countdown updates every second

4. Navigate to **Structural Scanner** tab
   - Verify real data (not "UNDEFINED")
   - Verify different scores/regimes for different instruments
   - Verify no dummy data

5. Navigate to **Market Outlook** tab
   - Verify real scenarios appear
   - Verify probabilities vary
   - Verify no empty scenarios

---

## 📋 VERIFICATION CHECKLIST

- [ ] API service restarted on VM
- [ ] SSH tunnel established (localhost:8787 → VM:8000)
- [ ] All 3 new performance endpoints return 200
- [ ] Structural Scanner endpoint returns 200
- [ ] Market Outlook endpoint returns 200
- [ ] Status endpoint returns 200
- [ ] Playwright audit passes
- [ ] Performance tab displays individual metrics
- [ ] Countdown feature visible in News tab
- [ ] Structural Scanner shows real data (not UNDEFINED)
- [ ] Market Outlook shows real scenarios
- [ ] No console errors in browser

---

## 🛠️ TROUBLESHOOTING

### SSH Connection Failing
- Check: `gcloud auth list` (ensure you're authenticated)
- Try: `gcloud compute ssh fxg-quant-paper-e2-micro --zone=us-east1-b --tunnel-through-iap --troubleshoot`

### Endpoints Return 404
- **Cause:** API service not restarted
- **Fix:** Restart API (Step 1)

### Endpoints Return Connection Refused
- **Cause:** SSH tunnel not active
- **Fix:** Set up tunnel (Step 2)

### Performance Tab Shows "Loading..."
- **Cause:** New endpoints not working
- **Fix:** Verify endpoints return 200 (Step 3)

### Countdown Not Visible
- **Cause:** Browser cache or HTML not loaded
- **Fix:** Hard refresh (Cmd+Shift+R) or clear cache

### Structural Scanner Shows "UNDEFINED"
- **Cause:** Frontend not parsing API response correctly
- **Fix:** Check browser console for errors, verify API returns correct format

---

## ✅ SUCCESS CRITERIA

**All of these must pass:**
1. ✅ All new endpoints return 200
2. ✅ Performance tab shows individual strategy/account cards
3. ✅ AI evaluation summary appears
4. ✅ Countdown timer visible and updating
5. ✅ Structural Scanner shows real data (varying scores/regimes)
6. ✅ Market Outlook shows real scenarios
7. ✅ Playwright audit reports no critical failures
8. ✅ No console errors in browser

---

## 📊 FILES CREATED

**Scripts:**
- `scripts/complete_restart_and_verify.sh` - Restart API and verify (run on VM)
- `scripts/connect_and_verify.sh` - Automated connection and verification (run locally)
- `scripts/test_endpoints_once_connected.py` - Python endpoint tester
- `scripts/comprehensive_playwright_audit.py` - Full browser audit
- `scripts/verify_all_endpoints.sh` - Bash endpoint tester
- `scripts/restart_api.sh` - Simple API restart script

**Documentation:**
- `docs/ALL_WORK_COMPLETE_VERIFICATION_2026-01-13.md`
- `docs/FINAL_WORK_REPORT_2026-01-13.json`
- `docs/COMPLETE_VERIFICATION_GUIDE_2026-01-13.md` (this file)

---

## 🎯 NEXT STEPS

1. **Restart API** (Step 1)
2. **Set up tunnel** (Step 2)
3. **Test endpoints** (Step 3)
4. **Run audit** (Step 4)
5. **Browser verify** (Step 5)

**Status:** ✅ All code ready - ⚠️ Awaiting API restart and verification
