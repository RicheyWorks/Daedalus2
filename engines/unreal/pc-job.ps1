# SPDX-License-Identifier: MIT
# A long job on this PC that outlives the Claude call, quiet with antivirus (ADR-045), for anything that is not
# an Unreal build (those are unreal-job.ps1): a Play-scenario run, an import, a server probe.
#
#   .\pc-job.ps1 -Start -Script tools\unreal_play\run_scenarios.py -ScriptArgs "cast realm_switch"   -> "started job-MMdd-HHmmss-<unique> pid=N"
#   .\pc-job.ps1 -Wait  [-Id x] [-Seconds 50]                                                 -> RUNNING / DONE <code> + the tail; exits with the completed job's code
#   .\pc-job.ps1 -Tail  [-Id x] [-Lines 40]
#
# The rules that keep Norton quiet (2026-10-13: a hidden python started from %TEMP% with redirected output was
# killed as malware): the script lives IN THE REPO (never %TEMP%), it runs in a visible minimized window (never
# -WindowStyle Hidden), it is started through WMI so it outlives the caller, output goes to a log under
# %LOCALAPPDATA%\Daedalus\jobs through the shell (no -RedirectStandardOutput), and there is no -ExecutionPolicy flag.
param(
    [switch]$Start, [switch]$Wait, [switch]$Tail,
    [string]$Script = "", [string]$ScriptArgs = "",
    [string]$Id = "", [int]$Seconds = 50, [int]$Lines = 40
)
$Jobs = Join-Path $env:LOCALAPPDATA "Daedalus\jobs"
New-Item -ItemType Directory -Force -Path $Jobs | Out-Null
$Repo = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")

function Latest {
    # A launch can be waiting for cmd to create its log, or fail before a log exists.
    Get-ChildItem -LiteralPath $Jobs -File | Where-Object { $_.Name -like "job-*.log" -or $_.Name -like "job-*.exit" -or $_.Name -like "job-*.started" } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { $_.BaseName }
}

if ($Start) {
    if (-not $Script) { throw "-Script <path relative to the repo> is required" }
    $full = Join-Path $Repo $Script
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "no such script in the repo: $full" }
    if ($full -like "$env:TEMP*") { throw "scripts never run from TEMP (ADR-045)" }
    # Starts within the same second must never share a log or an old completion marker.
    $Id = "job-" + (Get-Date -Format "MMdd-HHmmss") + "-" + [guid]::NewGuid().ToString("N")
    $log = Join-Path $Jobs "$Id.log"
    $exit = Join-Path $Jobs "$Id.exit"
    # A WMI-started cmd has the system PATH only, where "python" is the Store alias that exits 0 doing nothing:
    # resolve the real interpreter here, where the user PATH is.
    $py = (Get-Command python.exe -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike "*WindowsApps*" } | Select-Object -First 1).Source
    if (-not $py) { $py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe" }
    $runner = if ($full -like "*.py") { "`"$py`"" } elseif ($full -like "*.ps1") { "powershell.exe -NoProfile -File" } else { throw "a .py or .ps1 script" }
    # cmd runs the script and writes the exit code last; the window is minimized and never hidden.
    # /S keeps the inner quotes intact; /c "..." with nested quotes otherwise loses the first and last one.
    # cmd creates the log itself: a log pre-created by PowerShell's Out-File swallowed everything cmd appended to it
    # (every job read 'DONE 0' with no output; reproduced 2026-10-13), so nothing touches the log before cmd does.
    $stamp = Get-Date -Format s
    # A plain %ERRORLEVEL% in this /c line expands before the job runs. CALL expands the
    # caret-protected variable after it finishes. Default to failure until the child
    # actually runs: a failed echo redirection can leave cmd's ERRORLEVEL at zero. Keep
    # delayed expansion off so literal ! in paths and arguments survives, and disable AutoRun.
    # Publish only a complete marker: Wait must not see the file between creation and echo.
    $cmd = "cmd.exe /D /E:ON /V:OFF /S /c `"set `"ERRORLEVEL=`" & set `"PCJOB_CODE=1`" & cd /d `"$Repo`" && (echo $stamp start > `"$log`") && ($runner `"$full`" $ScriptArgs >> `"$log`" 2>&1 & call set PCJOB_CODE=^%ERRORLEVEL^%) & call echo done ^%PCJOB_CODE^% > `"$exit.tmp`" && move /y `"$exit.tmp`" `"$exit`" > nul`""
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]7 } -ErrorAction Stop
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = "$Repo"; ProcessStartupInformation = $startup } -ErrorAction Stop
    if ($r.ReturnValue -ne 0 -or -not $r.ProcessId) { throw "could not start $Id (Win32_Process.Create returned $($r.ReturnValue), pid=$($r.ProcessId))" }
    # Record the accepted launch without precreating cmd's output log.
    # Create already accepted the child. A receipt failure must never invite a retry:
    # return the accepted identity even if the optional disk receipt is unavailable.
    try {
        Set-Content -LiteralPath (Join-Path $Jobs "$Id.started") -Value "pid=$($r.ProcessId)" -Encoding ASCII -ErrorAction Stop
    } catch {
        Write-Warning "Accepted $Id pid=$($r.ProcessId), but launch receipt could not be saved. Do not restart; use -Wait -Id $Id."
    }
    "started $Id pid=$($r.ProcessId)"
    exit 0
}

if (-not $Id) { $Id = Latest }
$log = Join-Path $Jobs "$Id.log"; $exit = Join-Path $Jobs "$Id.exit"

$jobCode = 0
if ($Wait) {
    $until = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $until -and -not (Test-Path -LiteralPath $exit)) { Start-Sleep -Seconds 3 }
    if (Test-Path -LiteralPath $exit) {
        $marker = (Get-Content -LiteralPath $exit -Raw | Out-String).Trim()
        if ($marker -match '^done (-?\d+)$' -and [int]::TryParse($Matches[1], [ref]$jobCode)) { "DONE $jobCode" }
        else { "FAILED $Id invalid exit marker"; $jobCode = 1 }
    } else { "RUNNING $Id" }
}
if (Test-Path -LiteralPath $log -PathType Leaf) { Get-Content -LiteralPath $log -Tail $Lines }
$norton = Join-Path $env:TEMP "daedalus-norton.log"
if (Test-Path $norton) { $a = Get-Content $norton | Where-Object { $_ -ge (Get-Date).AddMinutes(-30).ToString("s") }; if ($a) { "NORTON is asking you something:"; $a } }
if ($Wait) { exit $jobCode }
