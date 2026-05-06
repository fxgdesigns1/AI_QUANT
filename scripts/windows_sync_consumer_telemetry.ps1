<#
.SYNOPSIS
  Publish Windows MT5 consumer telemetry artifacts to ALPHA (telemetry-only).

.DESCRIPTION
  Copies the EA-written heartbeat JSON (ftmo_consumer_heartbeat.json) from the MT5 terminal
  data directory (MQL5/Files) to ALPHA's canonical artifact path:
    /opt/ai-quant/ARTIFACTS/windows_consumer_heartbeat.json

  This script is intentionally telemetry-only:
  - does NOT modify any signal file
  - does NOT place orders
  - does NOT touch MT5 state

  Transport reuse: uses the same `gcloud compute scp/ssh` pattern already used by ALPHA operator scripts.

.PARAMETER HeartbeatPath
  Optional explicit path to ftmo_consumer_heartbeat.json.

.PARAMETER TerminalDataDir
  Optional explicit terminal data directory (the folder containing MQL5/Files).
  Example: $env:APPDATA\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075

.PARAMETER Project
  GCP project name (default fxg-ai-trading).

.PARAMETER Zone
  GCE zone (default us-central1-a).

.PARAMETER Host
  ALPHA VM host (default fxg-paper-e2-small-main-2026).

.PARAMETER RemoteUser
  Remote Linux user (default aiquant).

.PARAMETER RemoteTmpDir
  Remote temp directory (default /tmp).

.PARAMETER RemoteArtifactDir
  Remote artifact directory (default /opt/ai-quant/ARTIFACTS).

.EXAMPLE
  PowerShell -ExecutionPolicy Bypass -File .\scripts\windows_sync_consumer_telemetry.ps1 -WhatIf
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [string]$HeartbeatPath = "",
  [string]$TerminalDataDir = "",
  [string]$Project = "fxg-ai-trading",
  [string]$Zone = "us-central1-a",
  [string]$Host = "fxg-paper-e2-small-main-2026",
  [string]$RemoteUser = "aiquant",
  [string]$RemoteTmpDir = "/tmp",
  [string]$RemoteArtifactDir = "/opt/ai-quant/ARTIFACTS"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-HeartbeatPath {
  param([string]$ExplicitHeartbeatPath, [string]$ExplicitTerminalDataDir)

  if ($ExplicitHeartbeatPath -and (Test-Path -LiteralPath $ExplicitHeartbeatPath)) {
    return (Resolve-Path -LiteralPath $ExplicitHeartbeatPath).Path
  }

  if ($ExplicitTerminalDataDir) {
    $cand = Join-Path -Path $ExplicitTerminalDataDir -ChildPath "MQL5\Files\ftmo_consumer_heartbeat.json"
    if (Test-Path -LiteralPath $cand) { return (Resolve-Path -LiteralPath $cand).Path }
  }

  $root = Join-Path -Path $env:APPDATA -ChildPath "MetaQuotes\Terminal"
  if (-not (Test-Path -LiteralPath $root)) {
    throw "APPDATA terminal root not found at '$root'. Provide -HeartbeatPath or -TerminalDataDir."
  }

  $matches = Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
    ForEach-Object {
      $p = Join-Path -Path $_.FullName -ChildPath "MQL5\Files\ftmo_consumer_heartbeat.json"
      if (Test-Path -LiteralPath $p) {
        $fi = Get-Item -LiteralPath $p
        [PSCustomObject]@{ Path = $fi.FullName; LastWriteTimeUtc = $fi.LastWriteTimeUtc }
      }
    } |
    Where-Object { $_ -ne $null } |
    Sort-Object -Property LastWriteTimeUtc -Descending

  if (-not $matches -or $matches.Count -lt 1) {
    throw "No heartbeat file found under '$root'. Ensure EA writes 'ftmo_consumer_heartbeat.json' to MQL5\Files."
  }

  return $matches[0].Path
}

function Require-Command {
  param([string]$Name)
  $cmd = Get-Command $Name -ErrorAction SilentlyContinue
  if (-not $cmd) { throw "Required command not found in PATH: $Name" }
}

Require-Command "gcloud"

$hb = Resolve-HeartbeatPath -ExplicitHeartbeatPath $HeartbeatPath -ExplicitTerminalDataDir $TerminalDataDir
$hbItem = Get-Item -LiteralPath $hb

Write-Host "=== windows_sync_consumer_telemetry ==="
Write-Host "heartbeat_source=$hb"
Write-Host ("heartbeat_mtime_utc={0:o}" -f $hbItem.LastWriteTimeUtc)
Write-Host "alpha_target=$RemoteUser@$Host:$RemoteArtifactDir/windows_consumer_heartbeat.json"
Write-Host "transport=gcloud_compute_scp+ssh (telemetry-only)"

$remoteTmpHeartbeat = "$RemoteTmpDir/windows_consumer_heartbeat.json"

if ($PSCmdlet.ShouldProcess("ALPHA:$Host", "Upload heartbeat to $remoteTmpHeartbeat")) {
  & gcloud compute scp --zone $Zone --project $Project $hb "$RemoteUser@$Host:`"$remoteTmpHeartbeat`""
}

if ($PSCmdlet.ShouldProcess("ALPHA:$Host", "Install heartbeat to $RemoteArtifactDir/windows_consumer_heartbeat.json")) {
  $installCmd = @"
set -euo pipefail
sudo install -o aiquant -g aiquant -m 0644 "$remoteTmpHeartbeat" "$RemoteArtifactDir/windows_consumer_heartbeat.json"
"@
  & gcloud compute ssh --zone $Zone --project $Project "$RemoteUser@$Host" --command $installCmd
}

Write-Host "ok=true"

