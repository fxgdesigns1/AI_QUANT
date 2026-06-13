# Windows Sidecar Bridge (parallel_windows_sidecar_bridge_v1)

Read-only HTTP API exposing MT5 account, positions, orders, symbols, and diagnostics.

## Runtime
- Python 3.11+
- MetaTrader5 package (talks to logged-in MT5 terminal)
- Host: Windows with MT5 installed and logged in

## Default
- Listen: 127.0.0.1:8877
- Auth: x-api-key or Bearer header required

## Start
```powershell
.\scripts\start_windows_sidecar.ps1
```

## Verify
```powershell
.\scripts\verify_windows_sidecar.ps1
```
