$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$shadowRoot = Join-Path $taskRoot 'native-hud157'
$savedRoot = Join-Path $shadowRoot 'Saved'
$preflightPath = Join-Path $savedRoot 'hud-build-preflight.json'
$launchPath = Join-Path $savedRoot 'hud-build-launch.json'
$terminalPath = Join-Path $savedRoot 'hud-build-terminal.json'
if ((Test-Path -LiteralPath $launchPath) -or (Test-Path -LiteralPath $terminalPath)) {
    throw 'Retained launch/terminal exists; inspect, never replay.'
}
$preflight = Get-Content -LiteralPath $preflightPath -Raw | ConvertFrom-Json
if ($preflight.stage -ne 'fresh_source_native_backups_complete') { throw 'Preflight incomplete.' }
$leases = Invoke-RestMethod -Uri 'http://127.0.0.1:9890/locks'
if ($leases.compute.holder -ne 'codex-play-guard' -or $leases.unreal.holder -ne 'codex-play-guard') { throw 'Compute/editor lease missing.' }
$processes = @(Get-CimInstance Win32_Process)
$conflicts = @($processes | Where-Object {
    $_.Name -match '^(UnrealBuildTool|cl|link)\.exe$' -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
    ($_.Name -eq 'blender.exe' -and $_.ProcessId -ne 3668) -or
    ($_.CommandLine -match 'claude-hd-batch-v2-w' -and $_.Name -match 'powershell|pwsh')
})
if ($conflicts.Count -ne 0) { throw ('Conflicting heavy processes: ' + ($conflicts | ConvertTo-Json -Compress)) }
$os = Get-CimInstance Win32_OperatingSystem
if ($os.FreePhysicalMemory -lt 5GB / 1KB -or $os.FreeVirtualMemory -lt 5GB / 1KB) {
    throw 'Fresh resources fell below this one serial build reservation floor of5GiB physical/virtual; no universal safe ceiling claimed.'
}
$started = [DateTime]::UtcNow
$launch = [ordered]@{
    stage='serial_hud_build_dispatching'; started_utc=$started.ToString('o'); launcher_pid=$PID;
    engine=$preflight.build.engine; arguments=@($preflight.build.arguments);
    preflight=$preflightPath; free_physical_KiB=$os.FreePhysicalMemory; free_virtual_KiB=$os.FreeVirtualMemory;
    compute_lease=$leases.compute; unreal_lease=$leases.unreal;
    no_conflicting_heavy_processes=$true; normal_shared_pch=$true; max_parallel_actions=1;
    canonical_install_performed=$false
}
$launch | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $launchPath -Encoding utf8
$buildArguments = @($preflight.build.arguments | ForEach-Object { [string]$_ })
& $preflight.build.engine @buildArguments
$buildExit = $LASTEXITCODE
$finished = [DateTime]::UtcNow
$terminal = [ordered]@{
    stage='serial_hud_build_terminal'; exit_code=$buildExit; started_utc=$started.ToString('o');
    completed_utc=$finished.ToString('o'); elapsed_s=($finished-$started).TotalSeconds;
    launcher_pid=$PID; log=(Join-Path $savedRoot 'build-hud-bcfb.log'); arguments=$buildArguments;
    installed=$false; loaded=$false
}
$terminal | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $terminalPath -Encoding utf8
exit $buildExit
