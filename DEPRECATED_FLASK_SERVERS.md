# ⚠️ DEPRECATION WARNING

**This Flask server (`fixed_dashboard.py`) is DEPRECATED.**

**Use the canonical Control Plane API instead:**
```bash
./scripts/run_control_plane.sh
```

**Why?**
- Multiple Flask servers compete for `/api/status` endpoint
- Control Plane (FastAPI) is the single source of truth
- Better performance, better security, hot-reload support

**Migration:**
- All dashboard functionality now served by `src/control_plane/api.py`
- Dashboard: `templates/dashboard_advanced.html`
- Start: `python -m src.control_plane.api` or `./scripts/run_control_plane.sh`

**This file kept for reference only. DO NOT RUN in production.**
