# OANDA Data Policy

**Effective Date:** January 24, 2026
**Status:** ENFORCED

## 1. Single Source of Truth
ALL historical trade data for the AI Trading System MUST come from the OANDA `/v3/accounts/{accountID}/trades` endpoint.

## 2. Forbidden Endpoints
The `/v3/accounts/{accountID}/transactions` endpoint is **FORBIDDEN** for the purpose of reconstructing trade history. It may only be used for real-time event monitoring if absolutely necessary, but never for historical reporting.

## 3. Deprecation of Trade Reconstruction
The logic that reconstructs trades from raw transaction events (Stage 2) is **DEPRECATED**. Any attempt to use it for historical data will result in a runtime error.

## 4. Dashboard Compliance
The Local Dashboard must reflect the authoritative data from the `/trades` endpoint.
- No "inferred" states.
- No "partial" data.
- Explicit "SOURCE: OANDA /trades (authoritative)" badge required.

## 5. Violation Consequences
Any code found violating this policy (e.g., pulling transactions for history) will be considered a critical bug and must be remediated immediately.
