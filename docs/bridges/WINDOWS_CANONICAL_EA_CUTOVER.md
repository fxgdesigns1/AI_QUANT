# Windows Canonical EA Cutover

## Overview

The FTMO_Bridge_EA consumes canonical trade signals from `signals_ftmo_demo2.jsonl` and executes them on Windows MT5. Only one canonical consumer may be active at a time.

## Prerequisites

- Windows MT5 installed, logged into FTMO-Demo (or target account)
- Canonical producer (Mac/ALPHA) emitting to `signals_ftmo_demo2.jsonl`
- Sync or copy delivering the signal file to Windows MT5 MQL5/Files

## Install Steps

1. **Install EA**
   ```powershell
   Set-Location "H:\My Drive\AI Trading\Gcloud system"
   .\bridges\windows_sidecar\scripts\fxg_win_install_canonical_ea.ps1
   ```

2. **Wire signal files**
   ```powershell
   .\bridges\windows_sidecar\scripts\fxg_win_wire_canonical_signals.ps1
   ```

3. **Disable Mac canonical consumer** (REQUIRED before Windows test trade)
   - On Mac: Detach FTMO_Bridge_EA from chart, or stop the Mac MT5/Wine instance that consumes the signal file
   - Record what was disabled in `artifacts/mac_canonical_consumer_disable_result.json`

4. **Attach EA to chart**
   - In MT5: Navigator -> Expert Advisors -> FTMO_Bridge_EA
   - Drag to EURUSD M1 (or any chart)
   - Inputs: InpSignalFilePath=signals_ftmo_demo2.jsonl, InpBridgeAccount=ftmo_demo2, InpPaperOnly=true
   - Enable AutoTrading (Ctrl+E)

5. **Save profile for auto-load**
   - File -> Save As -> Save as profile "FXG_Canonical_Bridge"
   - Or: Save chart as template with EA attached
   - Configure MT5 to open this profile on startup (Tools -> Options -> Start)

## EA Inputs

| Input | Default | Description |
|-------|---------|-------------|
| InpSignalFilePath | signals_ftmo_demo2.jsonl | Canonical signal file name in MQL5/Files |
| InpBridgeAccount | ftmo_demo2 | Must match bridge_account in signal JSON |
| InpBridgeLogFile | ftmo_bridge_log.jsonl | EA log file in MQL5/Files |
| InpMaxLotSize | 0.01 | Max lots per trade |
| InpPollMs | 1000 | Poll interval ms |
| InpPaperOnly | true | When true, only execute when execution_allowed=true |

## Rollback to Mac

1. Detach FTMO_Bridge_EA from Windows MT5 chart
2. Re-attach FTMO_Bridge_EA on Mac MT5
3. Update `artifacts/rollback_windows_to_mac_execution_plan.json`

## Safety

- Windows sidecar remains read-only (data/diagnostics)
- Canonical producer semantics unchanged
- Only one consumer active at a time
