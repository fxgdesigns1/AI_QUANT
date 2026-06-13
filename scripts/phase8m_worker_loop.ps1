# Phase 8M: continuous safe polling loop for the 5950X research worker.
param(
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRemoteRepo = "/opt/ai-quant",
    [string]$LocalRoot = "C:\Users\gavin\fxg-research\research_worker",
    [int]$SleepSeconds = 60
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$once = Join-Path $RepoRoot "scripts\phase8m_worker_once.ps1"

while ($true) {
    try {
        powershell -ExecutionPolicy Bypass -File $once `
            -GcpProject $GcpProject `
            -GcpZone $GcpZone `
            -AlphaVm $AlphaVm `
            -AlphaRemoteRepo $AlphaRemoteRepo `
            -LocalRoot $LocalRoot
    } catch {
        Write-Host ("PHASE8M_WORKER_LOOP_ERROR=" + $_.Exception.Message) -ForegroundColor Red
    }
    Start-Sleep -Seconds $SleepSeconds
}

