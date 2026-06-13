# TEMPORARILY DISABLE SECURITY - QUICK GUIDE

## Option 1: Access VM Directly (BYPASS CLOUDFLARE ACCESS) ✅ EASIEST

The VM has a public IP that bypasses Cloudflare Access:

**Direct URL:** `http://35.231.194.238:8787`

**OR via SSH Tunnel:**
```bash
gcloud compute ssh fxg-quant-paper-e2-micro --zone us-east1-b --project fxg-ai-trading --tunnel-through-iap -- -L 8787:127.0.0.1:8787
```
Then open: `http://localhost:8787`

---

## Option 2: Disable Cloudflare Access (Cloudflare Dashboard)

1. **Go to Cloudflare Dashboard:** https://dash.cloudflare.com
2. **Navigate to:** Zero Trust → Access → Applications
3. **Find:** `alpha.fxgdesigns.co.uk` application
4. **Options:**
   
   **A) Disable Application (Temporary):**
   - Click on the application
   - Toggle "Enabled" OFF
   - Save changes
   - **⚠️ WARNING:** This removes ALL security - anyone can access
   
   **B) Add Bypass Rule (Allows Everyone):**
   - Go to: Zero Trust → Access → Applications → `alpha.fxgdesigns.co.uk`
   - Go to: Policies tab
   - Add new policy:
     - Policy name: "Bypass All"
     - Action: Allow
     - Include: Everyone
     - Save
   - Make this policy FIRST (top priority)
   - **⚠️ WARNING:** This allows ANYONE to access
   
   **C) Add IP Allowlist (Safer):**
   - Go to: Zero Trust → Access → Policies
   - Create policy with:
     - Include: IP Address
     - Add your current IP
     - Action: Allow
   - Apply to application

---

## Option 3: SSH Port Forwarding (SECURE, NO SECURITY CHANGE)

```bash
# SSH tunnel (bypasses Cloudflare, keeps VM secure)
gcloud compute ssh fxg-quant-paper-e2-micro \
  --zone us-east1-b \
  --project fxg-ai-trading \
  --tunnel-through-iap \
  -- -L 8787:127.0.0.1:8787
```

Then access: `http://localhost:8787`

**This is the SAFEST option** - no security changes needed.

---

## ⚠️ IMPORTANT NOTES

1. **Direct IP Access:** May not work if GCP firewall blocks port 8787
   - Check firewall rules: `gcloud compute firewall-rules list --project fxg-ai-trading`
   - May need to allow port 8787

2. **Cloudflare Access Disable:**
   - **⚠️ REMEMBER TO RE-ENABLE** after testing
   - Creates security risk if left disabled

3. **SSH Tunnel (Recommended):**
   - Most secure option
   - No configuration changes needed
   - Requires SSH access

---

## ✅ RECOMMENDED: Use SSH Tunnel

**Easiest and safest:**
```bash
gcloud compute ssh fxg-quant-paper-e2-micro --zone us-east1-b --project fxg-ai-trading --tunnel-through-iap -- -L 8787:127.0.0.1:8787
```

Then open browser to: `http://localhost:8787`

**No security changes, no risk, works immediately!**
