# FXG Windows - Build Active Dashboard
# Callable from any directory. Detects repo root and dashboard path, runs npm run build.
# PowerShell 5.1 compatible (no &&).

$ErrorActionPreference = "Stop"

# Detect repo root via script location
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sidecarRoot = Split-Path -Parent $scriptDir
$bridgesRoot = Split-Path -Parent $sidecarRoot
$repoRoot = (Split-Path -Parent $bridgesRoot)

$dashboardPath = Join-Path $repoRoot "frontend\fxg-dashboard"
$packageJson = Join-Path $dashboardPath "package.json"

if (-not (Test-Path $packageJson)) {
    Write-Host "FAIL: Dashboard package.json not found at $dashboardPath" -ForegroundColor Red
    exit 1
}

Set-Location $dashboardPath
Write-Host "Building dashboard at: $dashboardPath" -ForegroundColor Cyan

try {
    npm run build
    $code = $LASTEXITCODE
    if ($code -eq 0) {
        Write-Host "PASS: Dashboard build completed" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "FAIL: npm run build exited with $code" -ForegroundColor Red
        exit $code
    }
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    exit 1
}
