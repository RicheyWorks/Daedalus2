# SPDX-License-Identifier: MIT
# Pure policy: providers own all process/window access. Never infer ownership from a title.
function Get-DaedalusRecordValue {
    param([object]$Record, [string]$Name)
    if ($null -eq $Record) { return $null }
    if ($Record -is [System.Collections.IDictionary]) { return $Record[$Name] }
    $property = $Record.PSObject.Properties[$Name]
    if ($null -ne $property) { return $property.Value }
    return $null
}

function Resolve-DaedalusAbsolutePath {
    param([string]$Path)
    # IsPathRooted also accepts drive-relative paths; those are not identities.
    if ([string]::IsNullOrWhiteSpace($Path) -or $Path -notmatch '^(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+[\\/])') { return $null }
    try { return [System.IO.Path]::GetFullPath($Path).TrimEnd([char[]]'\/') }
    catch { return $null }
}

function Get-DaedalusProcessIdentity {
    param([object]$Process)
    try {
        $processId = [int](Get-DaedalusRecordValue $Process 'ProcessId')
        $session = Get-DaedalusRecordValue $Process 'SessionId'
        $creation = Get-DaedalusRecordValue $Process 'CreationDate'
        $executable = Resolve-DaedalusAbsolutePath (Get-DaedalusRecordValue $Process 'ExecutablePath')
        $command = Get-DaedalusRecordValue $Process 'CommandLine'
        if ($processId -le 0 -or $null -eq $session -or [int]$session -lt 0 -or
            $null -eq $creation -or [string]::IsNullOrWhiteSpace([string]$creation) -or
            -not $executable -or [string]::IsNullOrWhiteSpace([string]$command)) { return $null }
        $stamp = if ($creation -is [datetime]) { $creation.ToUniversalTime().ToString('o') }
                 elseif ($creation -is [datetimeoffset]) { $creation.ToUniversalTime().ToString('o') }
                 else { [datetimeoffset]::Parse([string]$creation, [Globalization.CultureInfo]::InvariantCulture,
                     [Globalization.DateTimeStyles]::AssumeUniversal).ToUniversalTime().ToString('o') }
        return ([ordered]@{ pid = $processId; created = $stamp; session = [int]$session;
            executable = $executable.ToUpperInvariant(); command = [string]$command } | ConvertTo-Json -Compress)
    } catch { return $null }
}

function Test-DaedalusWorkerProcess {
    param([object]$Process, [string]$JobsRoot, [int]$CurrentSessionId)
    try {
        if (-not (Get-DaedalusProcessIdentity $Process)) { return $false }
        if ([int](Get-DaedalusRecordValue $Process 'SessionId') -ne $CurrentSessionId) { return $false }
        $root = Resolve-DaedalusAbsolutePath $JobsRoot
        $executable = Resolve-DaedalusAbsolutePath (Get-DaedalusRecordValue $Process 'ExecutablePath')
        if (-not $root -or -not $executable) { return $false }
        $name = [System.IO.Path]::GetFileName($executable)
        if ($name -ine 'python.exe' -and $name -ine 'python3.exe') { return $false }
        $arguments = @(Get-DaedalusRecordValue $Process 'Arguments')
        if ($arguments.Count -lt 2) { return $false }
        $interpreter = Resolve-DaedalusAbsolutePath ([string]$arguments[0])
        $script = Resolve-DaedalusAbsolutePath ([string]$arguments[1])
        $allowed = [System.IO.Path]::Combine($root, 'lodworker.py')
        return ($interpreter -and $script -and
            [string]::Equals($executable, $interpreter, [StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals($allowed, $script, [StringComparison]::OrdinalIgnoreCase))
    } catch { return $false }
}

function Test-DaedalusConsoleRecord {
    param([object]$Console, [int]$WorkerId, [long]$ExpectedHwnd = 0, [int]$ExpectedOwner = 0, [switch]$WindowOnly)
    try {
        $handle = [long](Get-DaedalusRecordValue $Console 'Hwnd')
        $ownerId = [int](Get-DaedalusRecordValue $Console 'OwnerProcessId')
        $ownerWindow = Get-DaedalusRecordValue $Console 'OwnerWindow'
        $visible = Get-DaedalusRecordValue $Console 'Visible'
        $minimized = Get-DaedalusRecordValue $Console 'Minimized'
        $members = @(Get-DaedalusRecordValue $Console 'Members')
        return ($handle -gt 0 -and $ownerId -gt 0 -and $null -ne $ownerWindow -and [long]$ownerWindow -eq 0 -and
            $visible -is [bool] -and $visible -and $minimized -is [bool] -and
            [string]::Equals([string](Get-DaedalusRecordValue $Console 'ClassName'), 'ConsoleWindowClass', [StringComparison]::Ordinal) -and
            ($WindowOnly -or ($members.Count -eq 1 -and [int]$members[0] -eq $WorkerId)) -and
            ($ExpectedHwnd -eq 0 -or $handle -eq $ExpectedHwnd) -and
            ($ExpectedOwner -eq 0 -or $ownerId -eq $ExpectedOwner))
    } catch { return $false }
}

function Test-DaedalusConsoleOwner {
    param([object]$Process, [int]$OwnerId, [int]$CurrentSessionId)
    try {
        $expected = Resolve-DaedalusAbsolutePath ([System.IO.Path]::Combine($env:SystemRoot, 'System32', 'conhost.exe'))
        $actual = Resolve-DaedalusAbsolutePath (Get-DaedalusRecordValue $Process 'ExecutablePath')
        return ((Get-DaedalusProcessIdentity $Process) -and $expected -and $actual -and
            [int](Get-DaedalusRecordValue $Process 'ProcessId') -eq $OwnerId -and
            [int](Get-DaedalusRecordValue $Process 'SessionId') -eq $CurrentSessionId -and
            [string]::Equals($actual, $expected, [StringComparison]::OrdinalIgnoreCase))
    } catch { return $false }
}

function New-DaedalusWorkerConsoleResult {
    param([int]$WorkerId, [long]$WindowHandle, [string]$Status, [string]$Reason)
    return [pscustomobject]@{ pid = $WorkerId; hwnd = $WindowHandle; status = $Status; reason = $Reason }
}

function Invoke-DaedalusWorkerConsoleSweep {
    param([hashtable]$Provider, [string]$JobsRoot, [int]$CurrentSessionId)
    $results = @()
    $inspectOnly = [bool](Get-DaedalusRecordValue $Provider 'InspectOnly')
    $required = @('GetProcesses', 'GetProcess', 'GetConsole', 'GetWindow')
    if (-not $inspectOnly) { $required += 'Minimize' }
    foreach ($operation in $required) {
        if (-not $Provider -or $Provider[$operation] -isnot [scriptblock]) {
            return [pscustomobject]@{ status = 'unavailable'; reason = 'provider_capability_unavailable'; workers = @() }
        }
    }
    $root = Resolve-DaedalusAbsolutePath $JobsRoot
    $allowedRoot = $null
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        $allowedRoot = Resolve-DaedalusAbsolutePath ([System.IO.Path]::Combine($env:LOCALAPPDATA, 'Daedalus', 'jobs'))
    }
    if (-not $root -or -not $allowedRoot -or -not [string]::Equals($root, $allowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        return [pscustomobject]@{ status = 'unavailable'; reason = 'jobs_root_not_allowed'; workers = @() }
    }
    try { $processes = @(& $Provider.GetProcesses) }
    catch { return [pscustomobject]@{ status = 'unavailable'; reason = 'process_enumeration_unavailable'; workers = @() } }
    foreach ($candidate in $processes) {
        if (-not (Test-DaedalusWorkerProcess $candidate $root $CurrentSessionId)) { continue }
        $workerId = [int](Get-DaedalusRecordValue $candidate 'ProcessId')
        $handle = 0L
        $candidateIdentity = Get-DaedalusProcessIdentity $candidate
        try {
            $worker = & $Provider.GetProcess $workerId
            if ($null -eq $worker) {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'skipped' 'worker_exited'; continue
            }
            if (-not [string]::Equals($candidateIdentity, (Get-DaedalusProcessIdentity $worker), [StringComparison]::Ordinal) -or
                -not (Test-DaedalusWorkerProcess $worker $root $CurrentSessionId)) {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'skipped' 'worker_identity_changed'; continue
            }
            $console = & $Provider.GetConsole $workerId
            if (-not (Test-DaedalusConsoleRecord $console $workerId)) {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'skipped' 'console_not_exclusive_classic'; continue
            }
            $handle = [long](Get-DaedalusRecordValue $console 'Hwnd')
            $ownerId = [int](Get-DaedalusRecordValue $console 'OwnerProcessId')
            $owner = & $Provider.GetProcess $ownerId
            if (-not (Test-DaedalusConsoleOwner $owner $ownerId $CurrentSessionId)) {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'skipped' 'console_owner_not_allowed'; continue
            }
            $ownerIdentity = Get-DaedalusProcessIdentity $owner
            $window = & $Provider.GetWindow $handle
            if (-not (Test-DaedalusConsoleRecord $window $workerId $handle $ownerId -WindowOnly)) {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'skipped' 'window_identity_changed'; continue
            }
            # Probe results are not authority for the action. Re-read every identity/mapping.
            $freshWorker = & $Provider.GetProcess $workerId
            $freshOwner = & $Provider.GetProcess $ownerId
            if (-not [string]::Equals($candidateIdentity, (Get-DaedalusProcessIdentity $freshWorker), [StringComparison]::Ordinal) -or
                -not (Test-DaedalusWorkerProcess $freshWorker $root $CurrentSessionId)) {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'skipped' 'worker_identity_changed'; continue
            }
            if (-not [string]::Equals($ownerIdentity, (Get-DaedalusProcessIdentity $freshOwner), [StringComparison]::Ordinal) -or
                -not (Test-DaedalusConsoleOwner $freshOwner $ownerId $CurrentSessionId)) {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'skipped' 'console_owner_identity_changed'; continue
            }
            $freshConsole = & $Provider.GetConsole $workerId
            $freshWindow = & $Provider.GetWindow $handle
            if (-not (Test-DaedalusConsoleRecord $freshConsole $workerId $handle $ownerId) -or
                -not (Test-DaedalusConsoleRecord $freshWindow $workerId $handle $ownerId -WindowOnly)) {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'skipped' 'console_mapping_changed'; continue
            }
            if (Get-DaedalusRecordValue $freshWindow 'Minimized') {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'already_minimized' ''; continue
            }
            if ($inspectOnly) {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'detected' ''; continue
            }
            $confirmed = & $Provider.Minimize $handle $freshWorker $freshOwner
            if ($confirmed -is [bool] -and $confirmed) {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'minimized' ''
            } else {
                $results += New-DaedalusWorkerConsoleResult $workerId $handle 'failed' 'minimization_not_confirmed'
            }
        } catch {
            # Access denial and unsupported console APIs are capability failures, never a reason to broaden the policy.
            $results += New-DaedalusWorkerConsoleResult $workerId $handle 'unavailable' 'window_capability_unavailable'
        }
    }
    $status = if (@($results | Where-Object status -eq 'unavailable').Count -gt 0) { 'unavailable' }
              elseif (@($results | Where-Object status -eq 'failed').Count -gt 0) { 'failed' }
              else { 'ok' }
    return [pscustomobject]@{ status = $status; workers = @($results) }
}
