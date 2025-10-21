## AI Assistant API Reference

### Authentication
- Reuse existing session/JWT. Require RBAC roles: `viewer`, `trader_demo`, `trader_live_confirmed`.

### POST /ai/interpret
- Request:
```
{
  "message": "string",
  "session_id": "string",
  "context": {"accounts?": string[], "preferred_mode?": "demo"|"live"}
}
```
- Response:
```
{
  "reply": "string",
  "intent": "market_overview"|"close_positions"|"scale_positions"|"set_sl_tp"|"risk_status"|"help"|"mode",
  "tools": [{"name": "string", "args": {}}],
  "preview": {"summary": "string", "affected_entities": [{}]},
  "requires_confirmation": true|false,
  "mode": "demo"|"live",
  "confirmation_id?": "string"
}
```

### POST /ai/confirm
- Request:
```
{ "session_id": "string", "confirmation_id": "string", "confirm": true|false }
```
- Response:
```
{ "status": "executed"|"cancelled", "result?": {}, "audit_id": "string" }
```

### GET /ai/health
- 200 OK when healthy.

### Socket.IO Namespace `/ai`
- Events from client: `chat_message` {message, session_id}
- Events from server: `assistant_reply`, `command_preview`, `command_result`, `error`

### Tool Argument Schemas
- close_positions:
```
{
  "instrument?": "string",
  "side?": "buy"|"sell"|"both",
  "qty?": "all"|number,
  "account_scope?": "all"|"primary"|"<account_id>"
}
```
- scale_positions:
```
{ "instrument": "string", "target_exposure_pct": number }
```
- set_sl_tp:
```
{ "instrument": "string", "sl_pct?": number, "tp_pct?": number, "absolute?": { "sl?": number, "tp?": number } }
```

### Errors
- 400: validation errors (detail in `errors` array)
- 401/403: auth/RBAC
- 409: policy violation (exposure caps, max positions)
- 429: rate limited
- 502: upstream LLM timeout
