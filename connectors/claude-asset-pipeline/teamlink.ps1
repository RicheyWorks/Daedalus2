# SPDX-License-Identifier: MIT
# The team link (ADR-053): the Blender team <-> Unreal team real-time channel, kept running on this PC.
#
#   .\teamlink.ps1 -Start     start the broker on 127.0.0.1:9890 (log: bot-team\link\log.jsonl)
#   .\teamlink.ps1 -Status    is it up, who is alive on it, the last messages
#   .\teamlink.ps1 -Ping      a live round trip to the Unreal team's watcher (or -To blender-team)
#   .\teamlink.ps1 -Watch    health observer; state changes + 5-minute heartbeat, no auto-restart
#   .\teamlink.ps1 -Stop      stop it
#
# Same launch rules as art-queue.ps1: WMI so it outlives the calling shell, run from the repo, minimized window.
param([switch]$Start, [switch]$Stop, [switch]$Status, [switch]$Ping, [switch]$Watch, [string]$To = "unreal-team",
      [string]$Folder = (Join-Path $env:USERPROFILE "projects\bot-team\link"),
      [ValidateRange(1,60)][int]$IntervalSeconds = 5,
      [ValidateRange(30,3600)][int]$HeartbeatSeconds = 300,
      [ValidateRange(0,1000000)][int]$Checks = 0)
$Here = $PSScriptRoot
$Log = Join-Path $env:LOCALAPPDATA "Daedalus\jobs\teamlink.log"
New-Item -ItemType Directory -Force -Path (Split-Path $Log), $Folder | Out-Null

function Alive {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'asset_pipeline.teamlink serve' } | Select-Object -First 1
}
function Get($path) {
    try { Invoke-RestMethod -Uri "http://127.0.0.1:9890$path" -TimeoutSec 5 } catch { $null }
}

if ($Watch) {
    # Observe only. Never restart on an observation timeout or replay messages.
    $previous = "unknown"; $lastHeartbeat = [DateTime]::MinValue; $observations = 0
    do {
        $h = Get "/health"
        $state = if ($h -and $h.ok -eq $true) { "up" } else { "unavailable" }
        $now = [DateTime]::UtcNow
        if ($state -ne $previous -or ($now - $lastHeartbeat).TotalSeconds -ge $HeartbeatSeconds) {
            if ($state -eq "up") {
                "hub watch: up last=$($h.last) pid=$($h.pid) since=$($h.since) observed=$($now.ToString('o'))"
            } else {
                "hub watch: unavailable; observation failed, process outcome unknown; no restart attempted observed=$($now.ToString('o'))"
            }
            $lastHeartbeat = $now
        }
        $previous = $state; $observations++
        if ($Checks -gt 0 -and $observations -ge $Checks) { break }
        Start-Sleep -Seconds $IntervalSeconds
    } while ($true)
    if ($previous -eq "up") { exit 0 } else { exit 2 }
}

if ($Start) {
    if (Alive) { "already running (pid $((Alive).ProcessId))"; exit }
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]7 }
    $cmd = "cmd.exe /c python -m asset_pipeline.teamlink serve --folder `"$Folder`" >> `"$Log`" 2>&1"
    Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $cmd; CurrentDirectory = $Here; ProcessStartupInformation = $startup } | Out-Null
    Start-Sleep -Seconds 2
    $h = Get "/health"
    if ($h) { "team link up on 127.0.0.1:9890 (last id $($h.last)); log $Folder\log.jsonl" } else { "did not start; log:"; Get-Content $Log -Tail 10 -ErrorAction SilentlyContinue }
    exit
}
if ($Stop) {
    $a = Alive
    if ($a) { Stop-Process -Id $a.ProcessId -Force; "stopped" } else { "not running" }
    exit
}
if ($Ping) {
    Push-Location $Here
    python -m asset_pipeline.teamlink ping --me "ping-$env:USERNAME" --to $To --timeout 15
    Pop-Location
    exit
}
$h = Get "/health"
"bot hub: " + $(if ($h) { "up (last id $($h.last), since $($h.since)); dashboard http://127.0.0.1:9890/" } else { "down" })
if ($h) {
    "presence:"
    (Get "/presence").PSObject.Properties | ForEach-Object { "  {0,-14} alive={1} age={2}s {3}" -f $_.Name, $_.Value.alive, $_.Value.age_s, $_.Value.status }
    "last messages:"
    $after = [Math]::Max(0, $h.last - 8)
    (Get "/log?after=$after").messages | ForEach-Object { "  #{0} {1} {2} -> {3} {4} {5}" -f $_.id, $_.ts, $_.from, $_.to, $_.type, ($_.body | ConvertTo-Json -Compress -Depth 4) }
}
