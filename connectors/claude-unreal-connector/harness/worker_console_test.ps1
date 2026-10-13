# SPDX-License-Identifier: MIT
# Mock-only regression fixtures. No process or native window APIs are called.
param([string]$PolicyPath = (Join-Path $PSScriptRoot '..\extension\server\worker-console-policy.ps1'))
$ErrorActionPreference = 'Stop'
. $PolicyPath
$script:Failures = @()
$script:Passed = 0
$script:Session = 7
$script:JobsRoot = Join-Path $env:LOCALAPPDATA 'Daedalus\jobs'

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -cne $Actual) { throw "$Message (expected '$Expected', got '$Actual')" }
}
function Assert-True {
    param($Actual, [string]$Message)
    if ($Actual -isnot [bool] -or -not $Actual) { throw $Message }
}
function Copy-Record {
    param([hashtable]$Record, [hashtable]$Changes)
    $copy = @{}
    foreach ($key in $Record.Keys) { $copy[$key] = $Record[$key] }
    foreach ($key in $Changes.Keys) { $copy[$key] = $Changes[$key] }
    return $copy
}
function New-Fixture {
    $python = 'C:\FixturePython\python.exe'
    $scriptPath = Join-Path $script:JobsRoot 'lodworker.py'
    $worker = @{ ProcessId = 101; CreationDate = '2026-10-13T01:02:03.1234567Z'; SessionId = $script:Session;
        ExecutablePath = $python; CommandLine = ('"{0}" "{1}" --job test' -f $python, $scriptPath);
        Arguments = @($python, $scriptPath, '--job', 'test') }
    $hostPath = Join-Path $env:SystemRoot 'System32\conhost.exe'
    $owner = @{ ProcessId = 202; CreationDate = '2026-10-13T01:02:03.2345678Z'; SessionId = $script:Session;
        ExecutablePath = $hostPath; CommandLine = ('"{0}" --headless' -f $hostPath); Arguments = @($hostPath, '--headless') }
    $console = @{ Hwnd = 303L; OwnerProcessId = 202; ClassName = 'ConsoleWindowClass'; Visible = $true;
        Minimized = $false; Members = @(101); OwnerWindow = 0L }
    $state = [pscustomobject]@{ Worker = $worker; Owner = $owner; Console = $console; ExtraProcesses = @();
        Hooks = @{}; Counts = @{}; MinimizeReturn = $true; Calls = (New-Object 'System.Collections.Generic.List[object]') }
    $provider = @{
        GetProcesses = {
            if ($state.Hooks.ContainsKey('GetProcesses')) { & $state.Hooks.GetProcesses $state }
            @($state.Worker) + @($state.ExtraProcesses)
        }.GetNewClosure()
        GetProcess = {
            param($processId)
            $key = "Process:$processId"
            if (-not $state.Counts.ContainsKey($key)) { $state.Counts[$key] = 0 }
            $state.Counts[$key]++
            if ($state.Hooks.ContainsKey($key)) { & $state.Hooks[$key] $state $state.Counts[$key] }
            if ($processId -eq 101) { return $state.Worker }
            if ($processId -eq 202) { return $state.Owner }
            return $null
        }.GetNewClosure()
        GetConsole = {
            param($processId)
            if (-not $state.Counts.ContainsKey('Console')) { $state.Counts.Console = 0 }
            $state.Counts.Console++
            if ($state.Hooks.ContainsKey('Console')) { & $state.Hooks.Console $state $state.Counts.Console }
            return $state.Console
        }.GetNewClosure()
        GetWindow = {
            param($handle)
            if (-not $state.Counts.ContainsKey('Window')) { $state.Counts.Window = 0 }
            $state.Counts.Window++
            if ($state.Hooks.ContainsKey('Window')) { & $state.Hooks.Window $state $state.Counts.Window }
            if ($null -eq $state.Console) { return $null }
            # Window providers need not and cannot infer console membership from the HWND.
            $window = $state.Console.Clone()
            $window.Remove('Members')
            return $window
        }.GetNewClosure()
        Minimize = {
            param($handle, $workerIdentity, $ownerIdentity)
            [void]$state.Calls.Add([pscustomobject]@{ hwnd = $handle; worker = $workerIdentity; owner = $ownerIdentity })
            if ($state.Hooks.ContainsKey('Minimize')) { & $state.Hooks.Minimize $state }
            if ($state.MinimizeReturn -is [bool] -and $state.MinimizeReturn) {
                $state.Console = $state.Console.Clone()
                $state.Console.Minimized = $true
            }
            return $state.MinimizeReturn
        }.GetNewClosure()
    }
    return [pscustomobject]@{ State = $state; Provider = $provider }
}
function Run-Sweep {
    param($Fixture)
    return Invoke-DaedalusWorkerConsoleSweep -Provider $Fixture.Provider -JobsRoot $script:JobsRoot -CurrentSessionId $script:Session
}
function Assert-NoAction {
    param($Fixture, $Result, [string]$Status = 'skipped', [string]$Reason = '')
    Assert-Equal 0 $Fixture.State.Calls.Count 'unsafe minimize call'
    Assert-Equal 1 $Result.workers.Count 'expected one eligible worker result'
    Assert-Equal $Status $Result.workers[0].status 'worker status'
    if ($Reason) { Assert-Equal $Reason $Result.workers[0].reason 'worker reason' }
}
function Test-Case {
    param([string]$Name, [scriptblock]$Body)
    try { & $Body; $script:Passed++; Write-Output "PASS $Name" }
    catch { $script:Failures += "$Name`: $($_.Exception.Message)"; Write-Output "FAIL $Name`: $($_.Exception.Message)" }
}

Test-Case 'dedicated classic worker console is minimized with fresh identities' {
    $f = New-Fixture
    $result = Run-Sweep $f
    Assert-Equal 'ok' $result.status 'sweep status'
    Assert-Equal 'minimized' $result.workers[0].status 'worker status'
    Assert-Equal 1 $f.State.Calls.Count 'minimize count'
    Assert-Equal 303L $f.State.Calls[0].hwnd 'target handle'
    Assert-Equal (Get-DaedalusProcessIdentity $f.State.Worker) (Get-DaedalusProcessIdentity $f.State.Calls[0].worker) 'fresh worker argument'
    Assert-Equal (Get-DaedalusProcessIdentity $f.State.Owner) (Get-DaedalusProcessIdentity $f.State.Calls[0].owner) 'fresh owner argument'
    Assert-Equal 2 $f.State.Counts.'Process:101' 'worker reread'
    Assert-Equal 2 $f.State.Counts.'Process:202' 'owner reread'
    Assert-Equal 2 $f.State.Counts.Console 'console reread'
    Assert-Equal 2 $f.State.Counts.Window 'window reread'
}
Test-Case 'repeated sweeps and restored worker minimize every appearance without PID caching' {
    $f = New-Fixture
    Assert-Equal 'minimized' (Run-Sweep $f).workers[0].status 'first appearance'
    Assert-Equal 'already_minimized' (Run-Sweep $f).workers[0].status 'already minimized'
    Assert-Equal 1 $f.State.Calls.Count 'no redundant action'
    $f.State.Console = Copy-Record $f.State.Console @{ Minimized = $false }
    Assert-Equal 'minimized' (Run-Sweep $f).workers[0].status 'restored appearance'
    Assert-Equal 2 $f.State.Calls.Count 'restored console minimized again'
}
Test-Case 'inspect-only detects while making no window action' {
    $f = New-Fixture
    $f.Provider.InspectOnly = $true
    $f.Provider.Remove('Minimize')
    Assert-NoAction $f (Run-Sweep $f) 'detected'
}
Test-Case 'later legitimate worker appearance with reused PID is freshly evaluated' {
    $f = New-Fixture
    Assert-Equal 'minimized' (Run-Sweep $f).workers[0].status 'original worker'
    $f.State.Worker = Copy-Record $f.State.Worker @{ CreationDate = '2026-10-13T03:04:05Z' }
    $f.State.Console = Copy-Record $f.State.Console @{ Minimized = $false }
    Assert-Equal 'minimized' (Run-Sweep $f).workers[0].status 'new worker incarnation'
    Assert-Equal 2 $f.State.Calls.Count 'both independently validated appearances'
}

$processExclusions = @(
    @{ Name = 'unrelated Python script'; Changes = @{ Arguments = @('C:\FixturePython\python.exe', 'C:\project\run.py') } },
    @{ Name = 'Python -c with worker path string'; Changes = @{ Arguments = @('C:\FixturePython\python.exe', '-c', (Join-Path $script:JobsRoot 'lodworker.py')) } },
    @{ Name = 'Python -m named like the worker'; Changes = @{ Arguments = @('C:\FixturePython\python.exe', '-m', 'lodworker') } },
    @{ Name = 'shell command with spoofed console title'; Changes = @{ ExecutablePath = 'C:\Windows\System32\cmd.exe'; Arguments = @('C:\Windows\System32\cmd.exe', '/c', 'python lodworker.py'); Title = 'C:\FixturePython\python.exe lodworker.py' } },
    @{ Name = 'substring worker path'; Changes = @{ Arguments = @('C:\FixturePython\python.exe', ((Join-Path $script:JobsRoot 'lodworker.py') + '.bak')) } },
    @{ Name = 'other jobs directory'; Changes = @{ Arguments = @('C:\FixturePython\python.exe', 'C:\Other\Daedalus\jobs\lodworker.py') } },
    @{ Name = 'relative script path'; Changes = @{ Arguments = @('C:\FixturePython\python.exe', 'lodworker.py') } },
    @{ Name = 'drive-relative interpreter'; Changes = @{ Arguments = @('C:FixturePython\python.exe', (Join-Path $script:JobsRoot 'lodworker.py')) } },
    @{ Name = 'mismatched interpreter argv'; Changes = @{ Arguments = @('C:\OtherPython\python.exe', (Join-Path $script:JobsRoot 'lodworker.py')) } },
    @{ Name = 'pythonw windowless executable is outside fixed names'; Changes = @{ ExecutablePath = 'C:\FixturePython\pythonw.exe'; Arguments = @('C:\FixturePython\pythonw.exe', (Join-Path $script:JobsRoot 'lodworker.py')) } },
    @{ Name = 'other user session'; Changes = @{ SessionId = 8 } },
    @{ Name = 'missing creation identity'; Changes = @{ CreationDate = $null } },
    @{ Name = 'invalid creation timestamp'; Changes = @{ CreationDate = 'not a timestamp' } },
    @{ Name = 'missing executable identity'; Changes = @{ ExecutablePath = $null } },
    @{ Name = 'missing command line identity'; Changes = @{ CommandLine = $null } }
)
foreach ($exclusion in $processExclusions) {
    Test-Case $exclusion.Name {
        $f = New-Fixture
        $f.State.Worker = Copy-Record $f.State.Worker $exclusion.Changes
        $result = Run-Sweep $f
        Assert-Equal 0 $result.workers.Count 'excluded process reported as worker'
        Assert-Equal 0 $f.State.Calls.Count 'excluded process minimized'
        Assert-Equal 0 $f.State.Counts.Count 'excluded process probed'
    }
}
Test-Case 'absolute python3 identity and case-insensitive Windows paths are accepted' {
    $f = New-Fixture
    $python = 'C:\FixturePython\python3.exe'
    $f.State.Worker = Copy-Record $f.State.Worker @{ ExecutablePath = $python; Arguments = @($python.ToUpperInvariant(), (Join-Path $script:JobsRoot 'LODWORKER.PY')) }
    Assert-Equal 'minimized' (Run-Sweep $f).workers[0].status 'python3 exact identity'
}
Test-Case 'allowlist jobs root cannot be redirected by a caller' {
    $f = New-Fixture
    $result = Invoke-DaedalusWorkerConsoleSweep -Provider $f.Provider -JobsRoot 'C:\other\jobs' -CurrentSessionId $script:Session
    Assert-Equal 'unavailable' $result.status 'redirected policy status'
    Assert-Equal 'jobs_root_not_allowed' $result.reason 'redirected policy reason'
    Assert-Equal 0 $f.State.Calls.Count 'redirected policy action'
}

$windowExclusions = @(
    @{ Name = 'shared console includes unrelated shell'; Changes = @{ Members = @(101, 404) } },
    @{ Name = 'empty membership'; Changes = @{ Members = @() } },
    @{ Name = 'membership belongs to another process'; Changes = @{ Members = @(404) } },
    @{ Name = 'security dialog class'; Changes = @{ ClassName = '#32770' } },
    @{ Name = 'Windows Terminal host'; Changes = @{ ClassName = 'CASCADIA_HOSTING_WINDOW_CLASS' } },
    @{ Name = 'owned dialog'; Changes = @{ OwnerWindow = 999L } },
    @{ Name = 'invisible console'; Changes = @{ Visible = $false } },
    @{ Name = 'missing HWND'; Changes = @{ Hwnd = 0L } },
    @{ Name = 'unknown minimize state'; Changes = @{ Minimized = $null } }
)
foreach ($exclusion in $windowExclusions) {
    Test-Case $exclusion.Name {
        $f = New-Fixture
        $f.State.Console = Copy-Record $f.State.Console $exclusion.Changes
        Assert-NoAction $f (Run-Sweep $f) 'skipped' 'console_not_exclusive_classic'
    }
}
$ownerExclusions = @(
    @{ Name = 'untrusted conhost location'; Changes = @{ ExecutablePath = 'C:\Other\conhost.exe' } },
    @{ Name = 'security process owns window'; Changes = @{ ExecutablePath = 'C:\Security\Norton.exe' } },
    @{ Name = 'owner in another session'; Changes = @{ SessionId = 8 } },
    @{ Name = 'owner missing creation identity'; Changes = @{ CreationDate = $null } }
)
foreach ($exclusion in $ownerExclusions) {
    Test-Case $exclusion.Name {
        $f = New-Fixture
        $f.State.Owner = Copy-Record $f.State.Owner $exclusion.Changes
        Assert-NoAction $f (Run-Sweep $f) 'skipped' 'console_owner_not_allowed'
    }
}
Test-Case 'worker exited between enumeration and first lookup' {
    $f = New-Fixture
    $f.State.Hooks.'Process:101' = { param($state, $number) $state.Worker = $null }
    Assert-NoAction $f (Run-Sweep $f) 'skipped' 'worker_exited'
}
Test-Case 'PID reuse immediately after enumeration' {
    $f = New-Fixture
    $f.State.Hooks.'Process:101' = { param($state, $number) $state.Worker = Copy-Record $state.Worker @{ CreationDate = '2026-10-13T02:03:04Z' } }
    Assert-NoAction $f (Run-Sweep $f) 'skipped' 'worker_identity_changed'
}
$workerRaces = @(
    @{ Name = 'worker exit after console probe'; Changes = $null },
    @{ Name = 'worker PID reused after console probe'; Changes = @{ CreationDate = '2026-10-13T02:03:04Z' } },
    @{ Name = 'worker command line changes after probe'; Changes = @{ CommandLine = 'python.exe unrelated.py' } },
    @{ Name = 'worker executable changes after probe'; Changes = @{ ExecutablePath = 'C:\Other\python.exe' } },
    @{ Name = 'worker session changes after probe'; Changes = @{ SessionId = 8 } }
)
foreach ($race in $workerRaces) {
    Test-Case $race.Name {
        $f = New-Fixture
        $changes = $race.Changes
        $f.State.Hooks.'Process:101' = {
            param($state, $number)
            if ($number -eq 2) {
                if ($null -eq $changes) { $state.Worker = $null }
                else {
                    $state.Worker = $state.Worker.Clone()
                    foreach ($key in $changes.Keys) { $state.Worker[$key] = $changes[$key] }
                }
            }
        }.GetNewClosure()
        Assert-NoAction $f (Run-Sweep $f) 'skipped' 'worker_identity_changed'
    }
}
$ownerRaces = @(
    @{ Name = 'conhost exit after probe'; Changes = $null },
    @{ Name = 'conhost PID reuse after probe'; Changes = @{ CreationDate = '2026-10-13T02:03:04Z' } },
    @{ Name = 'conhost command line changes after probe'; Changes = @{ CommandLine = 'different command' } }
)
foreach ($race in $ownerRaces) {
    Test-Case $race.Name {
        $f = New-Fixture
        $changes = $race.Changes
        $f.State.Hooks.'Process:202' = {
            param($state, $number)
            if ($number -eq 2) {
                if ($null -eq $changes) { $state.Owner = $null }
                else {
                    $state.Owner = $state.Owner.Clone()
                    foreach ($key in $changes.Keys) { $state.Owner[$key] = $changes[$key] }
                }
            }
        }.GetNewClosure()
        Assert-NoAction $f (Run-Sweep $f) 'skipped' 'console_owner_identity_changed'
    }
}
$mappingRaces = @(
    @{ Name = 'console HWND remapped after probe'; Changes = @{ Hwnd = 999L } },
    @{ Name = 'console owner remapped after probe'; Changes = @{ OwnerProcessId = 404 } },
    @{ Name = 'console becomes shared after probe'; Changes = @{ Members = @(101, 404) } },
    @{ Name = 'console disappears after probe'; Changes = $null }
)
foreach ($race in $mappingRaces) {
    Test-Case $race.Name {
        $f = New-Fixture
        $changes = $race.Changes
        $f.State.Hooks.Console = {
            param($state, $number)
            if ($number -eq 2) {
                if ($null -eq $changes) { $state.Console = $null }
                else {
                    $state.Console = $state.Console.Clone()
                    foreach ($key in $changes.Keys) { $state.Console[$key] = $changes[$key] }
                }
            }
        }.GetNewClosure()
        Assert-NoAction $f (Run-Sweep $f) 'skipped' 'console_mapping_changed'
    }
}
Test-Case 'HWND reused by other process between final mapping and window lookup' {
    $f = New-Fixture
    $f.State.Hooks.Window = { param($state, $number) if ($number -eq 2) { $state.Console = Copy-Record $state.Console @{ OwnerProcessId = 404 } } }
    Assert-NoAction $f (Run-Sweep $f) 'skipped' 'console_mapping_changed'
}
Test-Case 'initial window facts cannot contradict console mapping' {
    $f = New-Fixture
    $f.State.Hooks.Window = { param($state, $number) if ($number -eq 1) { $state.Console = Copy-Record $state.Console @{ ClassName = '#32770' } } }
    Assert-NoAction $f (Run-Sweep $f) 'skipped' 'window_identity_changed'
}
Test-Case 'window already minimized during final probe causes no action' {
    $f = New-Fixture
    $f.State.Hooks.Window = { param($state, $number) if ($number -eq 2) { $state.Console = Copy-Record $state.Console @{ Minimized = $true } } }
    Assert-NoAction $f (Run-Sweep $f) 'already_minimized'
}
Test-Case 'missing native minimize capability reports unavailable' {
    $f = New-Fixture
    $f.Provider.Remove('Minimize')
    $result = Run-Sweep $f
    Assert-Equal 'unavailable' $result.status 'missing capability status'
    Assert-Equal 'provider_capability_unavailable' $result.reason 'missing capability reason'
    Assert-Equal 0 $f.State.Calls.Count 'missing capability action'
}
Test-Case 'process enumeration denial reports unavailable without throwing' {
    $f = New-Fixture
    $f.State.Hooks.GetProcesses = { throw [UnauthorizedAccessException]::new('fixture denial') }
    $result = Run-Sweep $f
    Assert-Equal 'unavailable' $result.status 'denied enumeration status'
    Assert-Equal 'process_enumeration_unavailable' $result.reason 'denied enumeration reason'
    Assert-Equal 0 $f.State.Calls.Count 'denied enumeration action'
}
Test-Case 'window API unavailable reports unavailable without fallback' {
    $f = New-Fixture
    $f.State.Hooks.Console = { throw [NotSupportedException]::new('fixture capability') }
    $result = Run-Sweep $f
    Assert-NoAction $f $result 'unavailable' 'window_capability_unavailable'
    Assert-Equal 'unavailable' $result.status 'unavailable overall status'
}
Test-Case 'fresh window lookup denied reports unavailable without fallback' {
    $f = New-Fixture
    $f.State.Hooks.Window = { param($state, $number) if ($number -eq 2) { throw [UnauthorizedAccessException]::new('fixture denial') } }
    Assert-NoAction $f (Run-Sweep $f) 'unavailable' 'window_capability_unavailable'
}
Test-Case 'minimization failure is never reported as success' {
    $f = New-Fixture
    $f.State.MinimizeReturn = $false
    $result = Run-Sweep $f
    Assert-Equal 1 $f.State.Calls.Count 'one minimize attempt'
    Assert-Equal 'failed' $result.status 'overall failure'
    Assert-Equal 'failed' $result.workers[0].status 'worker failure'
    Assert-Equal 'minimization_not_confirmed' $result.workers[0].reason 'failure reason'
}
Test-Case 'truthy nonboolean minimize result does not confirm IsIconic' {
    $f = New-Fixture
    $f.State.MinimizeReturn = 'success'
    Assert-Equal 'failed' (Run-Sweep $f).workers[0].status 'nonboolean confirmation'
}

Write-Output "$script:Passed passed; $($script:Failures.Count) failed"
if ($script:Failures.Count -gt 0) { exit 1 }
exit 0
