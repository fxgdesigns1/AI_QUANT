# Dashboard Development - Quick Start

Get up and running with dashboard development in 3 minutes.

---

## 🚀 Option 1: Mock API (No VM Required)

**Best for:** Development and testing

```bash
# 1. Start mock API server
python scripts/mock_api_server.py

# 2. Open dashboard
open http://127.0.0.1:8787

# 3. Run tests (in another terminal)
npm test
```

**That's it!** The mock API provides all endpoints with realistic test data.

---

## 🌐 Option 2: Live VM via Tunnel (Bypasses Security)

**Best for:** Pre-production testing with real data

```bash
# 1. Start development tunnel (bypasses Google security)
./scripts/dev_tunnel_alpha.sh

# 2. Open dashboard (in browser)
open http://127.0.0.1:28787

# 3. Run tests against live VM (in another terminal)
npm run test:live
```

**Note:** Keep the tunnel running while developing/testing.

---

## 📝 Wire In New Dashboard Template

When you drop a new dashboard template:

```bash
# Development mode (symlink - easy to change)
./scripts/wire_dashboard_template.sh your_template.html dev

# Production mode (copy - permanent)
./scripts/wire_dashboard_template.sh your_template.html prod
```

The template will be served at the root endpoint (`/`).

---

## 🧪 Testing Commands

```bash
# Install Playwright browsers (first time only)
npm run pw:install

# Run all tests
npm test

# Run with UI mode (see browser)
npm run test:ui

# Debug tests
npm run test:debug

# Test against mock API
npm run test:mock

# Test against live VM (requires tunnel)
npm run test:live
```

---

## 📚 Full Documentation

See `DASHBOARD_DEV_ENVIRONMENT.md` for complete guide.

---

## ✅ Checklist When You Drop Template

1. ✅ Wire in template: `./scripts/wire_dashboard_template.sh your_template.html dev`
2. ✅ Start mock API: `python scripts/mock_api_server.py`
3. ✅ Open dashboard: `http://127.0.0.1:8787`
4. ✅ Run tests: `npm test`
5. ✅ Test with live VM: `./scripts/dev_tunnel_alpha.sh` then `npm run test:live`

---

**Ready to develop!** 🎉
