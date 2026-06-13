# FXG Windows - Remote Overlay Status
$tailscaleExe = "C:\Program Files\Tailscale\tailscale.exe"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $scriptDir)))
$artifactsDir = Join-Path $repoRoot "artifacts"

$result = @{
    tailscale_installed = Test-Path $tailscaleExe
    tailscale_connected = $false
    tailscale_ip = $null
    sidecar_listening = $false
    sidecar_base_url = $null
}
if ($result.tailscale_installed) {
    $ip = (& $tailscaleExe ip -4 2>&1).Trim()
    if ($ip -match '^\d+\.\d+\.\d+\.\d+$') {
        $result.tailscale_connected = $true
        $result.tailscale_ip = $ip
        $result.sidecar_base_url = "http://${ip}:8877"
    }
}
$listener = Get-NetTCPConnection -LocalPort 8877 -ErrorAction SilentlyContinue
$result.sidecar_listening = [bool]$listener
$result | ConvertTo-Json | Set-Content (Join-Path $artifactsDir "windows_remote_overlay_status.json") -Encoding UTF8
$result | ConvertTo-Json
