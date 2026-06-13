# Phase 8P: install a local Windows Task Scheduler entry for Saturday-only research cycle.
# The task runs on the 5950X/Windows host and calls the Phase 8P weekend orchestrator.

[CmdletBinding()]
param(
    [string]$TaskName = "FXG Phase 8P Weekend Research Cycle",
    [string]$At = "08:00",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Fail([string]$Msg) {
    Write-Host "PHASE8P_SCHEDULER_INSTALL_FAILED"
    Write-Host $Msg
    exit 1
}

try {
    $RepoRoot = Split-Path -Parent $PSScriptRoot
    $CycleScript = Join-Path $PSScriptRoot "phase8p_weekend_research_cycle.ps1"
    if (-not (Test-Path -LiteralPath $CycleScript)) { throw "MISSING_PHASE8P_CYCLE_SCRIPT:$CycleScript" }

    $pwsh = (Get-Command powershell -ErrorAction SilentlyContinue)
    if (-not $pwsh) { throw "MISSING_POWERSHELL" }

    $actionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$CycleScript`""
    $action = New-ScheduledTaskAction -Execute $pwsh.Source -Argument $actionArgs -WorkingDirectory $RepoRoot
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At $At
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

    if ($DryRun) {
        $report = @{
            ok = $true
            phase = "Phase 8P"
            classification = "PHASE8P_SCHEDULER_DRY_RUN"
            task_name = $TaskName
            schedule = "Saturday $At local PC time"
            action = $actionArgs
            working_directory = $RepoRoot
            do_not_schedule_on_alpha = $true
            paper_review_only = $true
            live_permission = $false
            ny_live_enabled = $false
            send_trade_unlock_changed = $false
            execution_paths_changed = $false
        }
        Write-Host ($report | ConvertTo-Json -Depth 8)
        exit 0
    }

    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "FXG Phase 8P weekend-only research dashboard cycle on 5950X." -Force | Out-Null
    $task = Get-ScheduledTask -TaskName $TaskName
    $report = @{
        ok = $true
        phase = "Phase 8P"
        classification = "PHASE8P_SCHEDULER_INSTALLED"
        task_name = $TaskName
        state = $task.State.ToString()
        schedule = "Saturday $At local PC time"
        do_not_schedule_on_alpha = $true
        paper_review_only = $true
        live_permission = $false
        ny_live_enabled = $false
        send_trade_unlock_changed = $false
        execution_paths_changed = $false
    }
    Write-Host ($report | ConvertTo-Json -Depth 8)
    exit 0
} catch {
    Fail $_.Exception.Message
}
