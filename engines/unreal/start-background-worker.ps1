# SPDX-License-Identifier: MIT
# Start the fixed Daedalus LOD worker detached; an existing worker is left running.
param([string]$Python = '')

$ErrorActionPreference = 'Stop'
$server = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../connectors/claude-unreal-connector/extension/server'))
. (Join-Path $server 'worker-console.ps1')

function Start-DaedalusBackgroundWorker {
    param([string]$Python = '')
    if ($env:OS -ne 'Windows_NT') { throw 'worker console startup is unavailable on this platform' }
    $jobs = Resolve-DaedalusAbsolutePath (Join-Path $env:LOCALAPPDATA 'Daedalus\jobs')
    if (-not $jobs -or -not (Test-Path -LiteralPath (Join-Path $jobs 'lodworker.py') -PathType Leaf)) {
        throw 'the installed Daedalus jobs/lodworker.py is unavailable'
    }
    if (-not $Python) { $Python = (Get-Command python.exe -CommandType Application -ErrorAction Stop).Source }
    $executable = Resolve-DaedalusAbsolutePath $Python
    $name = [System.IO.Path]::GetFileName($executable)
    if (-not $executable -or ($name -ine 'python.exe' -and $name -ine 'python3.exe') -or
        -not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw 'an existing absolute python.exe or python3.exe is required'
    }
    $launcher = Join-Path $server 'background-worker-launch.py'
    if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw 'the worker launcher is unavailable' }

    # Denied/unavailable inspection aborts startup; no broad name/title heuristic can authorize it.
    $provider = New-DaedalusWorkerConsoleProvider -InspectOnly
    $session = [System.Diagnostics.Process]::GetCurrentProcess().SessionId
    $existing = @(& $provider.GetProcesses | Where-Object {
        Test-DaedalusWorkerProcess -Process $_ -JobsRoot $jobs -CurrentSessionId $session
    })
    if ($existing.Count) {
        return [pscustomobject]@{ status = 'already_running'; pids = @($existing | ForEach-Object { $_.ProcessId }) }
    }

    # WMI leaves the launcher detached from this shell, as with the existing Unreal job launcher.
    # The Python launcher gives the actual worker its own visible, minimized console and append logs.
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]7 } -ErrorAction Stop
    $created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = ('"{0}" "{1}"' -f $executable, $launcher)
        CurrentDirectory = $jobs
        ProcessStartupInformation = $startup
    } -ErrorAction Stop
    if ([int]$created.ReturnValue -ne 0 -or [uint32]$created.ProcessId -eq 0) {
        throw "worker launcher creation failed (WMI return $($created.ReturnValue))"
    }
    # Creation confirms the launcher request, not that the asynchronous worker has started.
    return [pscustomobject]@{ status = 'launcher_requested'; launcher_pid = [uint32]$created.ProcessId }
}

if ($MyInvocation.InvocationName -ne '.') {
    try { Start-DaedalusBackgroundWorker -Python $Python | ConvertTo-Json -Compress }
    catch {
        [pscustomobject]@{ status = 'unavailable'; reason = $_.Exception.Message } | ConvertTo-Json -Compress
        exit 1
    }
}
