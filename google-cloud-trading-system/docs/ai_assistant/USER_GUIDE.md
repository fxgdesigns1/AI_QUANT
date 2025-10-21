## AI Assistant — User Guide

### What you can ask
- Market overview: "Overview for EURUSD and XAUUSD"
- Positions: "Show my open GBPUSD positions"
- Manage: "Close all XAUUSD longs"
- Risk: "What’s my total portfolio exposure?"
- Scale: "Scale EURUSD longs to 2% exposure"
- SL/TP: "Set XAUUSD longs SL 0.2% TP 0.3%"

### Safety
- Demo-only by default. Live requires typing: `LIVE CONFIRM YES` and clicking Confirm.
- Hard caps: total exposure ≤ 10%, max 5 positions. Requests exceeding caps are blocked.

### Confirmations
- For state changes, the assistant shows a preview first.
- You must press Confirm to execute; Cancel aborts.

### Notifications
- Previews and executions are posted to Telegram with a short summary.

### Troubleshooting
- If the chat is missing, the feature may be disabled. Contact admin to enable `AI_ASSISTANT_ENABLED`.
- If replies time out, the system will notify you; no actions are taken on timeouts.
