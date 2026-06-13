"""
VM Trade Log Canonical Schema
Source: data/trade_ledger.jsonl (and optionally logs/session_regime_gate_audit.jsonl)

Required Fields (Canonical):
- timestamp: ISO 8601 UTC string (from 'openTime', 'ts_utc', or 'logged_at')
- account_suffix: String (three-digit lane suffix; legacy allocated 001–006, current active 010–011; derived from 'account_id' or 'account_suffix')
- strategy_name: String (e.g., 'MOMENTUM_V2', 'GOLD_SCALPER')
- instrument: String (e.g., 'EUR_USD', 'XAU_USD')
- direction: String ('BUY' or 'SELL', derived from units > 0 or explicit 'direction')
- entry_price: Float
- stop_loss: Float (optional, but highly desired for RR)
- take_profit: Float (optional, but highly desired for RR)
- risk_r: Float (calculated: abs(entry - SL) / abs(TP - entry))
- event_type: String ('signal', 'placed', 'blocked', 'closed')
- block_reason: String (only if event_type == 'blocked')
- exit_price: Float (only if event_type == 'closed')
- exit_reason: String ('TP', 'SL', 'manual', 'forced')
- pnl: Float (realized P&L, only if closed)
- rr_realized: Float (calculated if P&L known and risk known)

Parsing Rules:
1. trade_ledger.jsonl is the primary source for CLOSED trades (contains 'realizedPL', 'state': 'CLOSED').
2. session_regime_gate_audit.jsonl is the source for BLOCKED signals (contains 'allowed': false, 'reason').
3. order_manager logs (if available) would be source for PLACED orders, but trade_ledger seems to cover 'OPEN' state too?
   - Looking at trade_ledger.jsonl sample: {"id": "TRD-2024-001", ..., "state": "CLOSED", ...}
   - We need to handle OPEN trades if they exist in ledger.

Mapping:
- account_id "101-004-30719775-005" -> suffix "005"
- account_id_masked "-010" / "***010" / "101***010" -> suffix "010"
- account_id "001-001-MOCK" -> suffix "001" (needs robust parsing; treat suffix as canonical key)
- units > 0 -> BUY, units < 0 -> SELL
- realizedPL -> pnl
"""
