# FXG Pull Signals Service for Windows
# Monitors signal files from ALPHA VM and processes them
# Fixed: Changed threshold from 1000 bytes to 100 bytes

param(
    [string]$LogFile = "C:\FXG\logs\pull_signals.log",
    [string]$SignalSource = "fxg-paper-e2-small-main-2026:/home/aiquant/gcloud-system/logs/signals_ftmo_demo2.jsonl",
    [string]$LocalSignalFile = "C:\FXG\data\signals_local.jsonl",
    [int]$PullIntervalSeconds = 30,
    [int]$FileSizeThreshold = 100  # FIXED: Changed from 1000 to 100 bytes
)

# Ensure directories exist
$LogDir = Split-Path $LogFile -Parent
$SignalDir = Split-Path $LocalSignalFile -Parent

if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force
}

if (!(Test-Path $SignalDir)) {
    New-Item -ItemType Directory -Path $SignalDir -Force
}

# Logging function
function Write-Log {
    param(
        [string]$Level,
        [string]$Message
    )

    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] [$Level] $Message"

    Write-Output $LogEntry
    Add-Content -Path $LogFile -Value $LogEntry
}

# Function to check file size with new threshold
function Test-SignalFileSize {
    param([string]$FilePath)

    if (!(Test-Path $FilePath)) {
        Write-Log "WARNING" "Signal file not found: $FilePath"
        return $false
    }

    $FileSize = (Get-Item $FilePath).Length
    Write-Log "INFO" "Signal file size: $FileSize bytes (threshold: $FileSizeThreshold)"

    if ($FileSize -lt $FileSizeThreshold) {
        Write-Log "WARNING" "Signal file below threshold: $FileSize < $FileSizeThreshold bytes"
        return $false
    }

    return $true
}

# Function to pull signals from ALPHA VM
function Sync-SignalsFromAlpha {
    try {
        Write-Log "INFO" "Pulling signals from ALPHA VM..."

        # Use gcloud to copy signal file from ALPHA
        $GcloudCommand = "gcloud compute scp --tunnel-through-iap --zone us-central1-a $SignalSource $LocalSignalFile --project fxg-ai-trading"

        $ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
        $ProcessInfo.FileName = "powershell.exe"
        $ProcessInfo.Arguments = "-Command `"$GcloudCommand`""
        $ProcessInfo.RedirectStandardOutput = $true
        $ProcessInfo.RedirectStandardError = $true
        $ProcessInfo.UseShellExecute = $false
        $ProcessInfo.CreateNoWindow = $true

        $Process = [System.Diagnostics.Process]::Start($ProcessInfo)
        $Process.WaitForExit()

        if ($Process.ExitCode -eq 0) {
            Write-Log "INFO" "Successfully pulled signals from ALPHA"

            # Check file size with new threshold
            if (Test-SignalFileSize -FilePath $LocalSignalFile) {
                Write-Log "INFO" "Signal file passed size check"
                return $true
            } else {
                Write-Log "WARNING" "Signal file failed size check"
                return $false
            }
        } else {
            $ErrorOutput = $Process.StandardError.ReadToEnd()
            Write-Log "ERROR" "Failed to pull signals: $ErrorOutput"
            return $false
        }
    }
    catch {
        Write-Log "ERROR" "Exception during signal sync: $($_.Exception.Message)"
        return $false
    }
}

# Function to process signals
function Process-LocalSignals {
    try {
        if (!(Test-Path $LocalSignalFile)) {
            Write-Log "WARNING" "No local signal file to process"
            return
        }

        $Content = Get-Content $LocalSignalFile -Raw
        if ([string]::IsNullOrWhiteSpace($Content)) {
            Write-Log "WARNING" "Local signal file is empty"
            return
        }

        # Process each line as JSON signal
        $Lines = $Content -split "`n" | Where-Object { $_.Trim() -ne "" }
        Write-Log "INFO" "Processing $($Lines.Count) signal lines"

        foreach ($Line in $Lines) {
            try {
                $Signal = $Line | ConvertFrom-Json

                # Log signal details
                $SignalType = $Signal.type
                $SignalTimestamp = $Signal.timestamp
                Write-Log "INFO" "Processed signal: $SignalType at $SignalTimestamp"

                # TODO: Add actual signal processing logic here
                # This could include sending to MT5, updating local database, etc.

            }
            catch {
                Write-Log "WARNING" "Failed to parse signal JSON: $Line"
            }
        }

        Write-Log "INFO" "Signal processing completed"
    }
    catch {
        Write-Log "ERROR" "Exception during signal processing: $($_.Exception.Message)"
    }
}

# Function to check service health
function Test-ServiceHealth {
    try {
        # Check if we can reach ALPHA VM
        $TestCommand = "gcloud compute ssh --tunnel-through-iap --zone us-central1-a fxg-paper-e2-small-main-2026 --command='echo test' --project fxg-ai-trading"

        $ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
        $ProcessInfo.FileName = "powershell.exe"
        $ProcessInfo.Arguments = "-Command `"$TestCommand`""
        $ProcessInfo.RedirectStandardOutput = $true
        $ProcessInfo.RedirectStandardError = $true
        $ProcessInfo.UseShellExecute = $false
        $ProcessInfo.CreateNoWindow = $true

        $Process = [System.Diagnostics.Process]::Start($ProcessInfo)
        $Process.WaitForExit()

        if ($Process.ExitCode -eq 0) {
            Write-Log "INFO" "ALPHA VM connectivity test passed"
            return $true
        } else {
            Write-Log "ERROR" "ALPHA VM connectivity test failed"
            return $false
        }
    }
    catch {
        Write-Log "ERROR" "Health check exception: $($_.Exception.Message)"
        return $false
    }
}

# Main service loop
function Start-PullSignalsService {
    Write-Log "INFO" "=== FXG Pull Signals Service Started ==="
    Write-Log "INFO" "Log file: $LogFile"
    Write-Log "INFO" "Signal source: $SignalSource"
    Write-Log "INFO" "Local signal file: $LocalSignalFile"
    Write-Log "INFO" "Pull interval: $PullIntervalSeconds seconds"
    Write-Log "INFO" "File size threshold: $FileSizeThreshold bytes (FIXED: was 1000)"

    $LastHealthCheck = Get-Date
    $HealthCheckIntervalMinutes = 10

    while ($true) {
        try {
            # Periodic health check
            $Now = Get-Date
            if (($Now - $LastHealthCheck).TotalMinutes -gt $HealthCheckIntervalMinutes) {
                Write-Log "INFO" "Running periodic health check..."
                Test-ServiceHealth
                $LastHealthCheck = $Now
            }

            # Pull and process signals
            Write-Log "INFO" "Starting signal pull cycle..."

            if (Sync-SignalsFromAlpha) {
                Process-LocalSignals
                Write-Log "INFO" "Signal pull cycle completed successfully"
            } else {
                Write-Log "WARNING" "Signal pull cycle completed with warnings"
            }

            # Wait for next cycle
            Write-Log "INFO" "Waiting $PullIntervalSeconds seconds until next cycle..."
            Start-Sleep -Seconds $PullIntervalSeconds

        }
        catch {
            Write-Log "ERROR" "Main loop exception: $($_.Exception.Message)"
            Write-Log "INFO" "Continuing service after error..."
            Start-Sleep -Seconds $PullIntervalSeconds
        }
    }
}

# Handle Ctrl+C gracefully
$ExitHandler = {
    Write-Log "INFO" "=== FXG Pull Signals Service Stopping ==="
    exit 0
}

Register-EngineEvent PowerShell.Exiting -Action $ExitHandler

# Start the service
try {
    Start-PullSignalsService
}
catch {
    Write-Log "CRITICAL" "Service startup failed: $($_.Exception.Message)"
    exit 1
}