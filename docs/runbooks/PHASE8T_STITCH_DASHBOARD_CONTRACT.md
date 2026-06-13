# Phase 8T: Stitch dashboard contract and validation

## Purpose

Stitch (and any external operator dashboard) must consume the **same** compact JSON contract as ALPHA: `ARTIFACTS/performance/latest_research_dashboard.json`, produced by `scripts/phase8p_build_research_dashboard.py`. This runbook documents required fields, row separation rules, and how to verify the payload without touching trading runtime.

## Primary artifacts

| Artifact | Role |
|----------|------|
| `ARTIFACTS/performance/latest_research_dashboard.json` | Authoritative dashboard payload (JSON) |
| `ARTIFACTS/performance/research_dashboard/index.html` | Static HTML view + embedded JSON |
| `ARTIFACTS/performance/latest_stitch_dashboard_contract.json` | Machine-readable schema + field list (from Phase 8T) |
| `ARTIFACTS/performance/latest_phase8r_provider_capability_report.json` | Optional merge for provider capability (Phase 8R) |
| `ARTIFACTS/performance/latest_phase8o_backtest_summary.json` | Optional; drives exact-replay / classification fields when present on ALPHA |
| `ARTIFACTS/performance/latest_calendar_api_usage_report.json` | Calendar budget / usage (Phase 8S) |

## MCP / API mapping

This repository does **not** expose a dedicated HTTP JSON API for Stitch in-tree. Production usage is: deploy the files above under `/opt/ai-quant/ARTIFACTS/performance/` on ALPHA (or mirror them behind a read-only file or CDN endpoint you control). Cursor MCP tooling (for example browser automation in development) is auxiliary and must never substitute for validating the files actually deployed.

## Required frontend sections (mapped from JSON)

The static HTML builder renders sections aligned with the Stitch checklist: Research Summary, Promotion Candidates (PROMOTE only), Continue Forward, Watch Only, Demoted/Blocked, Fail-Closed, Proxy rows, calendar usage, provider capability (8R), exact replay status, ALPHA pointers, Stitch/MCP contract health.

## Validation command

```bash
python scripts/phase8t_validate_stitch_dashboard_contract.py --repo-root . --write-contract --validate --write-report
```

Rebuild dashboard first:

```bash
python scripts/phase8p_build_research_dashboard.py --repo-root .
```

## Acceptance rules (summary)

- Promotion candidates must be **PROMOTE_REVIEW_CANDIDATE** only and must not carry proxy or fail-closed replay modes.
- Safety flags `ny_live_enabled`, `live_permission`, `send_trade_unlock_changed`, `execution_paths_changed` must remain false for PASS validation.
- Fail-closed and proxy rows must remain out of the promotion list.

## Secrets

Never embed API keys or tokens in dashboard JSON. Validator and builders must not print secrets.
