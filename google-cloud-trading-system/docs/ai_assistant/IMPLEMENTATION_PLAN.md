## AI Assistant Integration — Implementation Plan (Zero-Interruption)

### Objectives
- Embed an AI chat assistant in the dashboard for Q&A and safe command execution.
- Maintain complete isolation behind a feature flag; default disabled.
- Test thoroughly (unit, integration, Playwright E2E) before any production enablement.

### Principles
- Demo-only execution by default; explicit per-command live confirmation required.
- Enforce portfolio caps: total exposure ≤ 10%, max 5 positions.
- Live data only in live contexts; represent missing values as null.
- Non-invasive: separate blueprint, socket namespace, env flag.

### Components
1) Chat UI (flag-guarded)
2) AI Gateway (LLM + tool-calling)
3) Tool Layer (safe wrappers over existing trading modules)
4) Policy Layer (risk and permission enforcement)
5) Observability (audit logs, Telegram notifications, metrics)

### Feature Flags & Config
- AI_ASSISTANT_ENABLED=false
- AI_MODEL_PROVIDER, AI_MODEL_NAME, AI_MAX_TOKENS, AI_TEMPERATURE
- AI_RATE_LIMIT_PER_MINUTE=10
- AI_SOCKET_NAMESPACE=/ai
- AI_REQUIRE_LIVE_CONFIRMATION=true

### Backend Interfaces (Blueprint `ai_assistant`)
- POST /ai/interpret → parse message, return reply, inferred intent, tool previews, and confirmation need
- POST /ai/confirm → execute a previously previewed command upon confirmation
- GET  /ai/health → readiness/liveness
- Socket.IO namespace `/ai`: chat_message, assistant_reply, command_preview, command_result, error

### Allowed Tools (whitelist)
- get_market_overview({ instruments: string[] })
- get_positions({ account_id?: string })
- close_positions({ instrument?: string, side?: 'buy'|'sell'|'both', qty?: 'all'|number, account_scope?: 'all'|'primary'|string })
- scale_positions({ instrument: string, target_exposure_pct: number })
- set_sl_tp({ instrument: string, sl_pct?: number, tp_pct?: number, absolute?: { sl?: number, tp?: number } })
- risk_snapshot()

### Policy Enforcement
- Default DEMO execution; LIVE requires exact "LIVE CONFIRM YES" + UI confirmation.
- Validate instruments, market state, min SL/TP distances, size steps, exposure caps.
- Rate-limit per session; exponential backoff on consecutive errors.

### UI Plan (non-invasive)
- Add a compact widget to `dashboard_advanced.html` only when `AI_ASSISTANT_ENABLED=true`.
- Scoped CSS classes `.ai-assistant-*` to prevent style bleed.
- Uses `/ai` Socket.IO namespace; REST fallback to `/ai/interpret`.

### Data Flow
1) User message → /ai/interpret → LLM decides intent + tools (preview only)
2) Assistant shows preview; requires explicit confirm for state changes
3) /ai/confirm executes via tool wrappers (DEMO by default)
4) Result sent to UI + Telegram; audit log updated

### Testing Strategy
- Unit: intent parser, schema validators, policy checks
- Integration: tool wrappers with OANDA practice; audit + Telegram
- Playwright E2E: chat flows, previews, confirmations, live guards, rate limits
- Non-functional: load/chaos/security

### Deployment & Rollout
- Stage in separate Cloud Run service or isolated blueprint with flag off.
- Staging enablement for tests; production remains off.
- Canary enablement via RBAC; rollback by turning the flag off.

### Acceptance Criteria
- Feature off by default, no regression with assistant code present.
- Policy caps enforced; demo-only unless explicitly confirmed live.
- Full passing test suite in staging before production enablement.
