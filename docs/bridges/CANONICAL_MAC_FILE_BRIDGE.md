# Canonical Mac File Bridge (canonical_mac_file_bridge_v1)

## Identity
- **Bridge ID**: `canonical_mac_file_bridge_v1`
- **Status**: `locked_canonical`
- **Role**: execution_signal_bridge

## Purpose
ONLY path that emits FTMO-facing trade signals from ALPHA after OANDA execution for lane 010 manual flow.

## Invariants (DO NOT MODIFY)
- `manual_execution` emit_signal uses `fanout=true` and `bridge_account='ftmo_demo2'` for FTMO-facing signals.
- FTMO_Bridge_EA on MT5 reads the signal file/stream defined by operations.
- No duplicate writers to canonical signal file.

## Flow
1. Manual lane 010 request on ALPHA
2. ExecutionGuard validation
3. OANDA paper action
4. Emit canonical MT5 signal line
5. Mac sync transport
6. Wine/MT5 file pickup
7. EA consume and broker action

## Hard Locks
- manual_execution.py fanout=true remains
- manual_execution.py bridge_account='ftmo_demo2' remains
- FTMO_Bridge_EA account id ftmo_demo2 remains canonical mapping
- No duplicate writers to canonical signal file

## Pitfall
Do not point the sidecar or dashboard at the canonical signal file for writes. Do not add a second writer to that path.
