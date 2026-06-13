# Phase 8U Stitch Dashboard Integration

## Scope

Phase 8U rectifies dashboard truthfulness:

- `research_dashboard/index.html` is fallback/static only.
- Stitch project UI is treated as the operator source of truth.
- Stitch-facing payload comes from one canonical artifact:
  `ARTIFACTS/performance/latest_stitch_dashboard_payload.json`.

## Safety Constraints

- Trading stays off.
- `ny_live_enabled` must remain false.
- `send_trade_unlock_changed` must remain false.
- `execution_paths_changed` must remain false.
- No runtime policy edits, no lane policy changes.

## Build Steps

1. Build payload:
   - `python scripts\phase8u_build_stitch_dashboard_payload.py --repo-root . --write`
2. Validate contract + payload + Stitch evidence:
   - `python scripts\phase8u_validate_stitch_dashboard_integration.py --repo-root . --validate-contract --validate-payload --write-report`
3. Optional inventory report write (requires local snapshot JSON):
   - `python scripts\phase8u_stitch_project_inventory.py --repo-root . --write`

## Required Artifacts

- `ARTIFACTS/performance/latest_stitch_dashboard_payload.json`
- `ARTIFACTS/performance/latest_stitch_dashboard_contract.json`
- `artifacts/PHASE8U_STITCH_PROJECT_INVENTORY_<UTC>.json`
- `artifacts/PHASE8U_STITCH_RECTIFICATION_FINAL_REPORT_<UTC>.json`

## Fail-Closed Conditions

- Stitch MCP project not found or not inspected.
- Stitch screen inventory includes mock/tournament placeholder labeling.
- Payload contract fields missing.
- Promotion table includes proxy or fail-closed rows.
- Safety flags missing or true.

## PASS Criteria

- Stitch project was inspected through MCP.
- Contract and payload both validate.
- Payload contains separated tables (`promotion_candidates`, `proxy_research`, `fail_closed`).
- Calendar budget and provider capability fields are visible.
- Safety flags are present and false.

## Local browser preview (Windows, real payload)

After pulling `latest_stitch_dashboard_payload.json` to `%USERPROFILE%\fxg-phase8-dashboard\` (for example from ALPHA with `gcloud compute scp`), render a file-based preview (not the static `research_dashboard/index.html` fallback):

```text
python scripts\phase8u_open_stitch_dashboard_preview.py --payload "%USERPROFILE%\fxg-phase8-dashboard\latest_stitch_dashboard_payload.json" --output "%USERPROFILE%\fxg-phase8-dashboard\phase8u_stitch_dashboard_preview.html" --open-browser
```

The generated page must show the banner **REAL PHASE 8U STITCH PAYLOAD PREVIEW** and **NOT FALLBACK STATIC HTML**. For live API truth on ALPHA, use `GET /api/phase8/research-dashboard` on the control plane (JSON under the truth envelope); the file preview is for offline/structural verification of the same payload artifact.
