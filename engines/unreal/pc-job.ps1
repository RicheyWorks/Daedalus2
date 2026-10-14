# SPDX-License-Identifier: MIT
# A long job on this PC that outlives the Claude call, quiet with antivirus (ADR-045), for anything that is not
# an Unreal build (those are unreal-job.ps1): a Play-scenario run, an import, a server probe.
#
#   .\pc-job.ps1 -Start -Script tools\unreal_play\run_scenarios.py -ScriptArgs "cast realm_switch"   -> "started job-MMdd-HHmmss pid=N"
#   .\pc-job.ps1 -Wait  [-Id x] [-Seconds 50]                                                 -> RUNNING / DONE <code> + the tail
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
$Repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")

function Latest { Get-ChildItem $Jobs -Filter "job-*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { $_.BaseName } }

if ($Start) {
    if (-not $Script) { throw "-Script <path relative to the repo> is required" }
    $full = Join-Path $Repo $Script
    if (-not (Test-Path $full)) { throw "no such script in the repo: $full" }
    if ($full -like "$env:TEMP*") { throw "scripts never run from TEMP (ADR-045)" }
    $Id = "job-" + (Get-Date -Format "MMdd-HHmmss")
    $log = Join-Path $Jobs "$Id.log"
    $exit = Join-Path $Jobs "$Id.exit"
    # A WMI-started cmd has the system PATH only, where "python" is the Store alias that exits 0 doing nothing:
    # resolve the real interpreter here, where the user PATH is.
    $py = (Get-Command python.exe -ErrorAction SilentlyContinue | Where-Object { $_.Source -notlike "*WindowsApps*" } | Select-Object -First 1).Source
    if (-not $py) { $py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe" }
    $runner = if ($full -like "*.py") { "`"$py`"" } elseif ($full -like "*.ps1") { "powershell.exe -NoProfile -File" } else { throw "a .py or .ps1 script" }
    # cmd runs the script and writes the exit code last; the window is minimized and never hidden.
    # /S keeps the inner quotes intact; /c "..." with nested quotes otherwise loses the first and last one.
    $cmd = "cmd.exe /S /c `"cd /d `"$Repo`" && $runner `"$full`" $ScriptArgs >> `"$log`" 2>&1 & echo done %ERRORLEVEL% > `"$exit`"`""
    # The start line goes in BEFORE the job launches: written after, Out-File truncated what the job had already
    # appended (every job read as 'DONE 0' with no output, 2026-10-13).
    "$(Get-Date -Format s) start $Script $ScriptArgs" | Out-File -FilePath $log -Encoding ascii
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]7 }
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = "$Repo"; ProcessStartupInformation = $startup }
    "started $Id pid=$($r.ProcessId)"
    exit
}

if (-not $Id) { $Id = Latest }
$log = Join-Path $Jobs "$Id.log"; $exit = Join-Path $Jobs "$Id.exit"

if ($Wait) {
    $until = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $until -and -not (Test-Path $exit)) { Start-Sleep -Seconds 3 }
    if (Test-Path $exit) { (Get-Content $exit).Trim().ToUpper() } else { "RUNNING $Id" }
}
if (Test-Path $log) { Get-Content $log -Tail $Lines }
$norton = Join-Path $env:TEMP "daedalus-norton.log"
if (Test-Path $norton) { $a = Get-Content $norton | Where-Object { $_ -ge (Get-Date).AddMinutes(-30).ToString("s") }; if ($a) { "NORTON is asking you something:"; $a } }
