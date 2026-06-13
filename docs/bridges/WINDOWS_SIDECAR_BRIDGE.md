# Windows Sidecar Bridge (parallel_windows_sidecar_bridge_v1)

## Identity
- **Bridge ID**: `parallel_windows_sidecar_bridge_v1`
- **Status**: `new_parallel_estate`
- **Role**: account_price_diagnostics_bridge

## Purpose
Read-only HTTP API exposing MT5-native account, positions, orders, symbols, prices, spreads, and diagnostics for dashboards/operators.

## Location
- **Repo**: `bridges/windows_sidecar/`
- **Runtime**: Python 3.11+; MetaTrader5 Python package talks to a logged-in MT5 terminal.
- **Host**: Windows machine where MT5 terminal is installed and logged in.
- **Default listen**: 127.0.0.1:8877

## Auth
All routes require API key via `x-api-key` header or `Bearer` token.

## Write Actions
Phase 1: **Read-only**. Write actions disabled or absent. No stealth trading.

## Relationship to Canonical
- **Never** writes to canonical signal paths.
- **Never** duplicates canonical signal writer.
- Runs in parallel; does not replace canonical bridge.
