# Phase 8Z: ALPHA live read-only Stitch dashboard (tunnel only)

## Purpose

Serve the functional Phase 8W Stitch-style dashboard from the **ai-quant-control-plane** on ALPHA so desktop and MacBook can view **live read-only** research payload and batch queue progress. **No public HTTP exposure** and **no unauthenticated internet URL** in this phase.

## Policy

- **Access**: `gcloud compute ssh` local port forward to `127.0.0.1:8787` only.
- **Do not** open GCP firewall for port 8787 to `0.0.0.0/0`.
- **Do not** embed secrets or API keys in HTML/JS.
- **Do not** restart `ai-quant-runner`; only `ai-quant-control-plane` after API/route changes.

## Routes (localhost on ALPHA)

| Path | Description |
|------|-------------|
| `GET /phase8/dashboard/` | Stitch dashboard `index.html` |
| `GET /phase8/dashboard/app.js` | Dashboard JS |
| `GET /phase8/dashboard/styles.css` | Dashboard CSS |
| `GET /api/phase8/research-dashboard` | Phase 8U payload JSON (TruthEnvelope) |
| `GET /api/phase8/batch-progress` | Queue counts + merged metadata (TruthEnvelope) |

Static files are resolved from `ARTIFACTS/performance/phase8_stitch_dashboard/` first, then `dashboard/phase8_stitch_dashboard/`.

## Operator commands

**Tunnel (PowerShell / CMD — Windows):**

```text
gcloud compute ssh --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026" -- -L 8787:127.0.0.1:8787
```

Then open:

```text
Start-Process "http://127.0.0.1:8787/phase8/dashboard/"
```

**Tunnel (macOS / Linux):**

```text
gcloud compute ssh --zone "us-central1-a" --project "fxg-ai-trading" "fxg-paper-e2-small-main-2026" -- -L 8787:127.0.0.1:8787
```

```text
open "http://127.0.0.1:8787/phase8/dashboard/"
```

## Deploy bundle

Use `scripts/phase8z_deploy_alpha_live_dashboard.ps1` from the repo root (runs tests, refreshes payload JSON, packs compact tarball, uploads, extracts under `/opt/ai-quant`, restarts control plane only).

## Verification (on ALPHA via SSH)

```bash
curl -fsS http://127.0.0.1:8787/phase8/dashboard/ | grep -q 'Phase 8' && echo PHASE8Z_DASHBOARD_HTML_OK
curl -fsS http://127.0.0.1:8787/api/phase8/research-dashboard | python3 -m json.tool >/tmp/phase8z_research.valid.json && echo PHASE8Z_RESEARCH_API_OK
curl -fsS http://127.0.0.1:8787/api/phase8/batch-progress | python3 -m json.tool >/tmp/phase8z_progress.valid.json && echo PHASE8Z_PROGRESS_API_OK
```

## Classification

Read-only research visibility; **no broker orders**, **no NY live enable**, **no runtime/config.yaml** edits via this path.
