# Dashboard Development Environment

Complete guide for safely developing and testing the dashboard without affecting production.

---

## 🎯 Quick Start

### Option 1: Mock API (Safest - No VM Required)

```bash
# 1. Start mock API server
python scripts/mock_api_server.py

# 2. Open dashboard in browser
open http://127.0.0.1:8787

# 3. Run Playwright tests
npm test
```

### Option 2: Live VM via Tunnel (Bypasses Google Security)

```bash
# 1. Start development tunnel (bypasses Cloudflare/Google security)
./scripts/dev_tunnel_alpha.sh

# 2. In another terminal, open dashboard
open http://127.0.0.1:28787

# 3. Run Playwright tests
DASHBOARD_URL=http://127.0.0.1:28787 npm test
```

---

## 📁 Project Structure

```
dashboard/               # Static assets
templates/               # Dashboard HTML templates
  ├── forensic_command.html  # Active template (served by API)
  └── ...
tests/dashboard/         # Playwright E2E tests
scripts/
  ├── dev_tunnel_alpha.sh      # Development tunnel (no security)
  ├── mock_api_server.py       # Mock API for safe development
  └── wire_dashboard_template.sh  # Wire in new templates
playwright.config.js     # Playwright configuration
```

---

## 🔧 Development Workflow

### 1. Wire In New Dashboard Template

```bash
# Development mode (symlink, easy to change)
./scripts/wire_dashboard_template.sh my_dashboard.html dev

# Production mode (copy, permanent)
./scripts/wire_dashboard_template.sh my_dashboard.html prod
```

**Template Location:**
- Active template: `templates/forensic_command.html`
- This is what the API serves at `/` endpoint

### 2. Develop with Mock API

**Benefits:**
- ✅ No VM required
- ✅ Fast iteration
- ✅ No risk to live system
- ✅ Predictable test data

```bash
# Terminal 1: Start mock API
python scripts/mock_api_server.py

# Terminal 2: Edit template
code templates/forensic_command.html

# Browser: Auto-reload (or refresh)
# http://127.0.0.1:8787
```

**Mock API Endpoints:**
- All dashboard endpoints are available with realistic mock data
- See `scripts/mock_api_server.py` for full endpoint list

### 3. Test with Playwright

```bash
# Install Playwright browsers (first time only)
npm run pw:install

# Run all tests
npm test

# Run against live VM
DASHBOARD_URL=http://127.0.0.1:28787 npm test

# Run with UI mode (see browser)
npx playwright test --ui

# Debug single test
npx playwright test dashboard.spec.js --debug
```

### 4. Test Against Live VM

**Setup:**
1. Ensure VM is running
2. Start development tunnel: `./scripts/dev_tunnel_alpha.sh`
3. Dashboard available at: `http://127.0.0.1:28787`

**Tunnel Details:**
- Bypasses Google Cloud security (Cloudflare Access, IAP)
- Direct SSH port forwarding
- Safe for development (VM still secured, just local access)

---

## 🌐 API Endpoints Reference

All endpoints support both mock and live modes:

### System Status
- `GET /api/status` - Main status
- `GET /api/truth/status` - Status with truth envelope
- `GET /health` - Health check

### Market Data
- `GET /api/market/overview` - Market overview
- `GET /api/market/prices` - Detailed prices
- `GET /api/news` - News items

### Trading
- `GET /api/trades/active` - Active trades
- `GET /api/trades/pending` - Pending orders
- `GET /api/positions` - Current positions

### Strategies
- `GET /api/strategies` - All strategies
- `GET /api/strategies/overview` - Strategy overview
- `POST /api/strategy/activate` - Activate/deactivate

### Performance
- `GET /api/performance/summary` - Performance summary
- `GET /api/performance/strategies` - By strategy
- `GET /api/performance/accounts` - By account

**Full API documentation:**
- Mock API: `http://127.0.0.1:8787/docs`
- Live API: `http://127.0.0.1:28787/docs` (via tunnel)

---

## 🧪 Testing Strategy

### Mock Mode (Recommended for Development)

```bash
# Start mock API
python scripts/mock_api_server.py

# Run tests
npm test
```

**Use when:**
- Developing new dashboard features
- Testing UI changes
- Fast iteration cycles
- No VM access needed

### Live Mode (Pre-Production Testing)

```bash
# 1. Start tunnel
./scripts/dev_tunnel_alpha.sh

# 2. Run tests against live VM
DASHBOARD_URL=http://127.0.0.1:28787 npm test
```

**Use when:**
- Verifying integration with real data
- Pre-deployment validation
- Testing real-time features

---

## 🔒 Security Notes

### Development Tunnel
- **Bypasses Google Security**: Uses direct SSH port forwarding
- **Local Only**: Accessible only from your Mac (`127.0.0.1`)
- **VM Still Secured**: VM firewall and internal security unchanged
- **Safe for Development**: No production exposure

### Mock API
- **No Security**: Mock API has no authentication
- **Local Only**: Binds to `127.0.0.1` (localhost only)
- **Development Only**: Never deploy mock API to production

### Production
- Production dashboard uses Cloudflare Access + IAP
- Full security enabled
- Separate from development environment

---

## 📝 Adding New Endpoints to Mock API

Edit `scripts/mock_api_server.py`:

```python
@app.get("/api/my/new/endpoint")
async def my_endpoint():
    return {
        "data": {
            # Your mock data here
        },
        "complete": True,
        "warnings": [],
        "ts_utc": datetime.now(timezone.utc).isoformat(),
    }
```

---

## 🚀 Deployment Workflow

### 1. Develop & Test Locally

```bash
# Use mock API for development
python scripts/mock_api_server.py
# ... develop dashboard ...
npm test
```

### 2. Test Against Live VM

```bash
# Test with real data
./scripts/dev_tunnel_alpha.sh
# ... verify dashboard works with real API ...
```

### 3. Deploy to Production

```bash
# Wire template in production mode
./scripts/wire_dashboard_template.sh my_dashboard.html prod

# Deploy to VM
./scripts/push_repo_to_vm.sh

# Verify on VM
# (SSH to VM and restart API service)
```

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :28787

# Kill it
kill <PID>

# Or use different port in tunnel script
```

### Tunnel Connection Failed

```bash
# Check VM is running
gcloud compute instances list --project fxg-ai-trading

# Test SSH access
gcloud compute ssh fxg-quant-paper-e2-micro --zone us-east1-b --project fxg-ai-trading
```

### Playwright Tests Fail

```bash
# Ensure tunnel is running (for live tests)
# Ensure mock API is running (for mock tests)

# Check browser installation
npm run pw:install

# Run with headed browser to see what's happening
npx playwright test --headed
```

### Dashboard Not Loading

1. **Check API is running:**
   ```bash
   curl http://127.0.0.1:8787/health  # Mock
   curl http://127.0.0.1:28787/health  # Live (via tunnel)
   ```

2. **Check template exists:**
   ```bash
   ls -la templates/forensic_command.html
   ```

3. **Check browser console** for JavaScript errors

---

## 📚 Additional Resources

- **API Documentation**: `DASHBOARD_API_AND_ENDPOINTS_OVERVIEW.md`
- **Full API Docs**: `http://127.0.0.1:8787/docs` (Swagger UI)
- **Playwright Docs**: https://playwright.dev

---

## ✅ Checklist for New Dashboard Template

- [ ] Template file created
- [ ] Wired in with `wire_dashboard_template.sh`
- [ ] Tested with mock API
- [ ] Tested with Playwright (mock mode)
- [ ] Tested against live VM (via tunnel)
- [ ] Tested with Playwright (live mode)
- [ ] Verified all API endpoints work
- [ ] Verified error handling (empty data, network errors)
- [ ] Deployed to production (production mode)

---

**Last Updated:** January 2026
