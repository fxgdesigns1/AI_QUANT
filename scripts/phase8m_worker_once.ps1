# Phase 8M: run one 5950X research-worker poll/execution cycle.
param(
    [string]$GcpProject = "fxg-ai-trading",
    [string]$GcpZone = "us-central1-a",
    [string]$AlphaVm = "fxg-paper-e2-small-main-2026",
    [string]$AlphaRemoteRepo = "/opt/ai-quant",
    [string]$LocalRoot = "C:\Users\gavin\fxg-research\research_worker",
    [string]$PythonExe = "",
    [string]$JobId = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$worker = Join-Path $RepoRoot "scripts\phase8m_5950x_research_worker.py"
if (-not (Test-Path -LiteralPath $worker)) {
    throw "PHASE8M_WORKER_SCRIPT_MISSING:$worker (run from repo; PSScriptRoot=$PSScriptRoot)"
}
$worker = (Resolve-Path -LiteralPath $worker).Path

function Resolve-Phase8mPython {
    param([string]$Explicit)
    if ($Explicit -and (Test-Path -LiteralPath $Explicit)) {
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source) { return $cmd.Source }
    }
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $resolved = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($resolved) { return $resolved.Trim() }
    }
    throw @"
PHASE8M_NO_PYTHON: No Python interpreter found (WinError 2 class failure).
Tried: explicit -PythonExe, Get-Command python/python3, py -3.
Fix: install Python 3, add to PATH, or pass -PythonExe 'C:\Path\to\python.exe'.
RepoRoot=$RepoRoot
"@
}

$pythonResolved = Resolve-Phase8mPython -Explicit $PythonExe

$workerArgs = @(
    $worker,
    "--project", $GcpProject,
    "--zone", $GcpZone,
    "--vm", $AlphaVm,
    "--alpha-repo", $AlphaRemoteRepo,
    "--local-root", $LocalRoot
)
if ($JobId) {
    $workerArgs += @("--job-id", $JobId)
}
if ($DryRun) {
    $workerArgs += "--dry-run"
}

Write-Host "PHASE8M_WORKER_ONCE python=$pythonResolved worker=$worker"
& $pythonResolved @workerArgs
if ($LASTEXITCODE -ne 0) { throw "PHASE8M_WORKER_ONCE_FAILED" }

