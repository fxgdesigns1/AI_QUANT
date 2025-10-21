## Test Plan (Unit, Integration, E2E, Non-Functional)

### Unit Tests
- Intent parsing → message → intent + normalized args
- Schema validation (tools) → happy and edge paths
- Policy checks → exposure caps, max positions, live confirmation gating

### Integration Tests (Sandbox / Practice)
- Tool wrappers against OANDA practice accounts
- Scenarios: no positions, single/multiple, caps reached, market closed
- Verify: audit entries created, Telegram notifications sent

### Playwright E2E (Staging Only)
1) Visibility: widget hidden when flag off; visible when on
2) Q&A: market overview response renders structured data
3) Preview: closing positions shows preview without execution
4) Confirm: DEMO execution after confirm; Telegram receives confirmation
5) Live guard: requires exact token + UI confirm for live
6) Risk caps: attempts exceeding caps are blocked with clear messages
7) Invalid instrument: informative error; no side-effects
8) Resilience: socket reconnect preserves session context
9) Rate-limit feedback UX

### Non-Functional
- Load: /ai/interpret under expected concurrency; no impact on core sockets
- Chaos: LLM timeout → graceful error; no actions executed
- Security: RBAC bypass attempts; prompt-injection sanitization

### Staging Verification Script
1) Enable flag in staging only
2) Run Playwright suite headless
3) Manually verify Telegram alerts
4) Review audit logs (random samples)
