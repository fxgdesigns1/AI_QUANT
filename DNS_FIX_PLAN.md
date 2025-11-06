# DNS RESOLUTION FIX PLAN - CLOUD DEPLOYMENT

## 🔍 PROBLEM VERIFIED

**Issue**: Oanda client connects to `194.168.4.100:443` instead of Oanda API
**Root Cause**: DNS pre-resolution code incorrectly parses `nslookup` output

### Evidence:
```bash
$ nslookup api-fxpractice.oanda.com
Server:    194.168.4.100    # ← This is the DNS SERVER, not the resolved IP
Address:   194.168.4.100#53

Non-authoritative answer:
Name:      api-fxpractice.oanda.com
Address:   104.18.34.254    # ← This is the ACTUAL IP
Address:   172.64.153.2      # ← This is the ACTUAL IP
```

**Current Code Bug** (lines 204-208):
```python
match = re.search(r'Address:\s*(\d+\.\d+\.\d+\.\d+)', result.stdout)
```
This regex matches the FIRST "Address:" which is the DNS server IP, not the resolved IPs.

## 🎯 FIX PLAN

### Phase 1: Fix DNS Resolution (Cloud-Safe)
1. **Fix regex to parse actual resolved IPs** (not DNS server)
2. **Add cloud environment detection** - disable IP substitution in cloud
3. **Use proper DNS resolution** - let platform handle it in cloud

### Phase 2: Cloud Deployment Optimization
1. **Remove IP substitution in cloud** - Google Cloud handles DNS properly
2. **Keep Host header logic** for edge cases
3. **Add environment detection** for local vs cloud

### Phase 3: Testing & Validation
1. Test locally with fix
2. Verify Oanda API connection works
3. Deploy to cloud and verify
4. Monitor for connection issues

## 📋 IMPLEMENTATION STEPS

### Step 1: Fix DNS Parsing Logic
- Parse "Non-authoritative answer" section only
- Extract all resolved IPs, use first valid one
- Skip DNS server IP (194.168.4.100)

### Step 2: Add Cloud Environment Detection
- Check if running on Google App Engine
- Disable IP substitution in cloud (let platform handle DNS)
- Keep hostname-based URLs in cloud

### Step 3: Fallback Strategy
- If DNS pre-resolution fails, use hostname (standard behavior)
- Add proper error handling
- Log warnings for debugging

## 🔧 TECHNICAL DETAILS

### Current Code Location:
`google-cloud-trading-system/src/core/oanda_client.py` lines 194-220

### Changes Required:
1. Fix regex pattern to match resolved IPs (not DNS server)
2. Add `_is_cloud_environment()` detection
3. Skip IP substitution in cloud environments
4. Improve error handling and logging

### Cloud Detection Method:
```python
def _is_cloud_environment():
    return (
        os.getenv('GAE_ENV') or  # Google App Engine
        os.getenv('GAE_INSTANCE') or  # Google App Engine instance
        os.getenv('GOOGLE_CLOUD_PROJECT')  # GCP project
    )
```

## ✅ EXPECTED OUTCOME

After fix:
- ✅ Oanda API connects successfully
- ✅ No more `194.168.4.100` connection errors
- ✅ Trades can execute properly
- ✅ Works in both local and cloud environments
- ✅ Proper DNS resolution in all scenarios

