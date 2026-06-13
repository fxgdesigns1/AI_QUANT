# FXG Windows - Install/repair Scheduled Task for direct ALPHA -> MT5 watchfile pull.
#
# Creates/updates one authoritative task:
#   FXG Windows Direct Pull ALPHA -> MT5 (ftmo_demo2)
#
# Runs every 1 minute while user is logged in (mapped drive / repo availability).
param(
    [string]$TaskName = "FXG Windows Direct Pull ALPHA MT5 ftmo_demo2",
    [int]$EveryMinutes = 1
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir)))
$pullScript = Join-Path $repoRoot "bridges\windows_sidecar\scripts\fxg_win_pull_alpha_signals_to_mt5.ps1"
if (-not (Test-Path -LiteralPath $pullScript)) { throw "Missing pull script: $pullScript" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ("-NoProfile -ExecutionPolicy Bypass -File `"{0}`"" -f $pullScript)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

try {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
} catch { }

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings | Out-Null
Enable-ScheduledTask -TaskName $TaskName | Out-Null
Write-Host "PASS: Installed Scheduled Task: $TaskName" -ForegroundColor Green
