# SPDX-License-Identifier: MIT
# The art queue watcher (ADR-051), kept running on this PC.
#
#   .\art-queue.ps1 -Start     start watching bot-team\art\QUEUE.md (READY rows ship into Unreal by themselves)
#   .\art-queue.ps1 -Status    is it running, and the board's live summary (STATUS.md)
#   .\art-queue.ps1 -Stop      stop it
#   .\art-queue.ps1 -Start -First _Orr_    ship rows whose names contain _Orr_ ahead of the rest
#
# It needs Python 3 and, to ship, Blender (Claude Blender Connector, port 9876) and the Unreal Editor (Claude
# Unreal Bridge, port 9877) open. Without them it keeps watching and says what it's waiting for in STATUS.md.
param([switch]$Start, [switch]$Stop, [switch]$Status,
      [string]$Folder = (Join-Path $env:USERPROFILE "projects\bot-team\art"), [int]$Every = 10, [string]$First = "")
$Here = $PSScriptRoot
$Lock = Join-Path $Folder ".watcher.lock"
$Log = Join-Path $env:LOCALAPPDATA "Daedalus\jobs\art-queue.log"
New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null

function Alive {
    if (-not (Test-Path $Lock)) { return $null }
    $watcherPid = [int](Get-Content $Lock -ErrorAction SilentlyContinue | Select-Object -First 1)
    $p = Get-CimInstance Win32_Process -Filter "ProcessId = $watcherPid" -ErrorAction SilentlyContinue
    if ($p -and $p.CommandLine -match 'asset_pipeline.artqueue') { return $p } else { return $null }
}

if ($Start) {
    if (Alive) { "already running (pid $((Alive).ProcessId))"; exit }
    Remove-Item $Lock -ErrorAction SilentlyContinue
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]7 }
    $cmd = "cmd.exe /c python -m asset_pipeline.artqueue --folder `"$Folder`" --every $Every$(if ($First) { " --first $First" }) >> `"$Log`" 2>&1"
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $cmd; CurrentDirectory = $Here; ProcessStartupInformation = $startup }
    Start-Sleep -Seconds 3
    $a = Alive
    if ($a) { "watching $Folder every $Every s (pid $($a.ProcessId)); log: $Log" } else { "did not start; log:"; Get-Content $Log -Tail 10 -ErrorAction SilentlyContinue }
    exit
}
if ($Stop) {
    $a = Alive
    if ($a) { Stop-Process -Id $a.ProcessId -Force; Remove-Item $Lock -ErrorAction SilentlyContinue; "stopped" } else { "not running" }
    exit
}
$a = Alive
"watcher: " + $(if ($a) { "running (pid $($a.ProcessId))" } else { "not running" })
Get-Content (Join-Path $Folder "STATUS.md") -ErrorAction SilentlyContinue
