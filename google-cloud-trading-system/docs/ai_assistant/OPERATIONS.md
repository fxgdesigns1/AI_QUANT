## Operations Runbook — AI Assistant

### Enablement (Staging)
1) Set `AI_ASSISTANT_ENABLED=true` in staging env.
2) Deploy assistant code or separate service; keep production flag off.
3) Run Playwright suite headless; ensure 100% pass.
4) Manually verify Telegram notifications and audit logs.

### Enablement (Production)
1) Keep `AI_ASSISTANT_ENABLED=false` initially after deploy.
2) Canary: enable for RBAC user only; monitor metrics and logs.
3) Full enable: set `AI_ASSISTANT_ENABLED=true` for all users.

### Monitoring
- Metrics: intent success rate, tool error rate, response latency, rate-limit triggers.
- Logs: structured with request/session IDs, intent, tool, mode, duration.
- Alerts: error spikes, LLM latency breaches, policy violation attempts.

### Rollback
- Immediate: set `AI_ASSISTANT_ENABLED=false`.
- If separate service: disable routing to assistant base URL.

### Secrets & Config
- Store model keys in Secret Manager/SSM; never in repo.
- Rotate keys on schedule; audit fetch events.

### DR/Resilience
- Graceful degradation on LLM timeouts (no execution, safe messaging).
- Retry policies for transient network issues.

### Data Retention
- Audit logs retained per compliance policy (recommend ≥ 90 days).
