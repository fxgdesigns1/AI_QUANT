# DNS Fix Commands for alpha.fxgdesigns.co.uk

## M1: Confirmed ✅
- **194.168.4.100** (primary ISP DNS): Returns **NXDOMAIN** (failure)
- **194.168.8.100** (secondary ISP DNS): Returns A records (works when queried directly)
- **1.1.1.1** (Cloudflare DNS): Returns A records ✅
- **8.8.8.8** (Google DNS): Returns A records ✅
- **Mac default resolver**: Fails (likely due to negative cache from 194.168.4.100)

## M2: Fix Mac DNS Globally

Run these commands in your terminal:

```bash
# 1. Set Wi-Fi DNS to public resolvers
sudo networksetup -setdnsservers "Wi-Fi" 1.1.1.1 8.8.8.8

# 2. Flush DNS caches
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# 3. Wait a moment for changes to take effect
sleep 2

# 4. Verify DNS configuration
scutil --dns | grep -E "nameserver\[[0-9]+\]" | head -n 40

# 5. Test DNS resolution
dig alpha.fxgdesigns.co.uk +short

# Expected output: Should return A records (104.21.85.244 and 172.67.212.141)

# 6. Test HTTPS endpoint
curl -I https://alpha.fxgdesigns.co.uk | head -n 30

# Expected output: HTTP/2 302 redirect to Cloudflare Access login
```

### Rollback (if needed)
If you need to revert to DHCP-provided DNS:
```bash
sudo networksetup -setdnsservers "Wi-Fi" Empty
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

## M3: Alternative - Per-Domain Override (if M2 fails/is blocked)

If global DNS changes are blocked by VPN/MDM/router, use per-domain override:

```bash
# 1. Create resolver override directory
sudo mkdir -p /etc/resolver

# 2. Create domain-specific resolver config
printf "nameserver 1.1.1.1\nnameserver 8.8.8.8\n" | sudo tee /etc/resolver/fxgdesigns.co.uk >/dev/null

# 3. Flush DNS caches
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# 4. Verify resolver config
scutil --dns | sed -n '1,220p' | grep -E "fxgdesigns|resolver|nameserver" || true

# 5. Test DNS resolution
dig alpha.fxgdesigns.co.uk +short

# 6. Test HTTPS endpoint
curl -I https://alpha.fxgdesigns.co.uk | head -n 30
```

### Rollback (if needed)
```bash
sudo rm -f /etc/resolver/fxgdesigns.co.uk
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

## M4: VM Origin Health ✅

**Status: PASS**

- cloudflared service: **active**
- Health endpoint: `{"status":"ok","timestamp":1768180921.6869094}`
- Tunnel connections: Multiple registered connections (QUIC protocol)
- Configuration: alpha.fxgdesigns.co.uk → http://127.0.0.1:8787 ✅

## M5: Public End-to-End Verification

After completing M2 or M3, verify end-to-end:

```bash
# Test without explicit resolver
curl -I https://alpha.fxgdesigns.co.uk | head -n 30

# Expected: HTTP/2 302 redirect to Cloudflare Access login
# Location header should point to fxg1.cloudflareaccess.com

# Optional: Test with explicit resolver as control
curl -I --resolve alpha.fxgdesigns.co.uk:443:104.21.85.244 https://alpha.fxgdesigns.co.uk | head -n 30
```

---

## Summary

- **M1**: ✅ Confirmed ISP DNS failure (194.168.4.100 returns NXDOMAIN)
- **M2**: ⏳ **ACTION REQUIRED** - Run sudo commands above to fix Mac DNS
- **M3**: ⏳ Alternative if M2 is blocked
- **M4**: ✅ VM origin health verified (cloudflared active, health OK, tunnel registered)
- **M5**: ⏳ Waiting for DNS fix completion
