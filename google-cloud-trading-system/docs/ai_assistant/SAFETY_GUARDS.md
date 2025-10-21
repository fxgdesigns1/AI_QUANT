## Safety Guards & Policies

### Modes
- Default mode: DEMO. State-changing tools run on practice/demo accounts.
- Live execution requires both: explicit text token "LIVE CONFIRM YES" and UI confirmation.

### Risk Limits
- Portfolio exposure cap: 10% of equity.
- Max concurrent positions: 5.
- Scaling may not exceed caps; reductions always permitted.

### Validations (before execution)
- Instrument tradability and market open.
- Min SL/TP distance and price bounds.
- Order sizing increments and notional checks.
- Spread and slippage sanity thresholds.

### Rate Limiting & Cooldowns
- Per-session: 10 commands/minute.
- On 3 consecutive errors: 60s cooldown.

### Audit & Notifications
- Every preview and execution recorded with args, mode, result.
- Telegram notification on previews and executions.

### RBAC
- viewer: Q&A, read-only tools.
- trader_demo: can execute DEMO commands.
- trader_live_confirmed: per-command live allowed with explicit confirmation.
