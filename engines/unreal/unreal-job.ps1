# SPDX-License-Identifier: MIT
# Long Unreal jobs (build, open) for Claude, in one call each, and quiet with antivirus (ADR-045).
#
#   .\unreal-job.ps1 -Start            pull, build the DaedalusLink plugin into the project, reopen the editor
#   .\unreal-job.ps1 -Wait  [-Id x]    wait up to 50 s; prints RUNNING / BUILD OK / BUILD FAILED + the errors
#   .\unreal-job.ps1 -Run   -Id x      (internal) the job body
#
# Why it looks like this: the Claude app ends anything its shell starts when the call returns, so the job is
# started through WMI to outlive it. Everything else is chosen not to look like malware to Norton: the script
# runs from the repo (not %TEMP%), in a visible minimized window (not hidden), with no -ExecutionPolicy flag
# (this machine's policy already allows local scripts). Logs: %LOCALAPPDATA%\Daedalus\jobs.
param(
    [switch]$Start, [switch]$Wait, [switch]$Run,
    [string]$Id = "",
    [string]$Project = "C:\Unreal\DaedalusRealm\DaedalusRealm.uproject",
    [int]$Seconds = 50
)
$Jobs = Join-Path $env:LOCALAPPDATA "Daedalus\jobs"
New-Item -ItemType Directory -Force -Path $Jobs | Out-Null
$Repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")

function Latest { (Get-ChildItem $Jobs -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).BaseName }

function BuildToolsBusy {
    # Unreal's AutomationTool and UnrealBuildTool run as dotnet; only one may build at a time.
    @(Get-CimInstance Win32_Process -Filter "Name = 'dotnet.exe' OR Name = 'UnrealBuildTool.exe' OR Name = 'AutomationTool.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' }).Count -gt 0
}

if ($Run) {
    $log = Join-Path $Jobs "$Id.log"
    Set-Location $Repo
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        # Wait (up to 5 min) for any other Unreal build to finish instead of colliding with it.
        $until = (Get-Date).AddMinutes(5)
        while ((BuildToolsBusy) -and (Get-Date) -lt $until) {
            "waiting for another Unreal build tool to finish..." | Out-File -FilePath $log -Append -Encoding utf8
            Start-Sleep -Seconds 10
        }
        $mark = if (Test-Path $log) { (Get-Content $log).Count } else { 0 }
        & { git pull --ff-only; & (Join-Path $PSScriptRoot "setup-unreal.ps1") -Project $Project -Build -Open } *>&1 |
            Out-File -FilePath $log -Append -Encoding utf8
        $code = $LASTEXITCODE
        $fresh = Get-Content $log | Select-Object -Skip $mark
        if (-not ($fresh -match 'conflicting instance of AutomationTool')) { break }
        "another build tool collided; retrying in 20 s (attempt $attempt)" | Out-File -FilePath $log -Append -Encoding utf8
        Start-Sleep -Seconds 20
    }
    "done $code" | Out-File -FilePath (Join-Path $Jobs "$Id.exit") -Encoding ascii
    exit
}

if ($Start) {
    $Id = "build-" + (Get-Date -Format "MMdd-HHmmss")
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]7 }   # minimized, no focus
    $cmd = "powershell.exe -NoProfile -File `"$PSCommandPath`" -Run -Id $Id -Project `"$Project`""
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $cmd; CurrentDirectory = "$Repo"; ProcessStartupInformation = $startup }
    "started $Id pid=$($r.ProcessId)"
    exit
}

if ($Wait) {
    if (-not $Id) { $Id = Latest }
    $log = Join-Path $Jobs "$Id.log"; $exit = Join-Path $Jobs "$Id.exit"
    $until = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $until -and -not (Test-Path $exit)) {
        if ((Test-Path $log) -and (Select-String -Path $log -Pattern 'error C\d+|: error ' -Quiet)) { break }
        Start-Sleep -Seconds 3
    }
    $errors = if (Test-Path $log) { Select-String -Path $log -Pattern 'error C\d+|: error ' | Select-Object -First 15 | ForEach-Object { $_.Line } } else { @() }
    $norton = Join-Path $env:TEMP "daedalus-norton.log"
    $alerts = if (Test-Path $norton) { Get-Content $norton | Where-Object { $_ -ge (Get-Date).AddMinutes(-30).ToString("s") } } else { @() }
    if ((Test-Path $log) -and (Select-String -Path $log -Pattern 'X BuildPlugin exited' -Quiet) -and -not (Select-String -Path $log -Pattern 'BUILD SUCCESSFUL' -Quiet) -and (Test-Path $exit)) {
        "BUILD FAILED $Id (the plugin build step failed; the AutomationTool error log says why):"
        Get-Content (Join-Path $env:LOCALAPPDATA "UnrealEngine\Programs\AutomationTool\Saved\Logs\ErrorLog.txt") -Tail 6 -ErrorAction SilentlyContinue
    }
    elseif ($errors) { "BUILD FAILED $Id"; $errors }
    elseif (Test-Path $exit) {
        $ok = Select-String -Path $log -Pattern 'BUILD SUCCESSFUL' -Quiet
        if ($ok) { "BUILD OK $Id" } else { "JOB ENDED $Id"; Get-Content $log -Tail 8 }
        $up = $false
        for ($i = 0; $i -lt 10 -and -not $up; $i++) {
            try { $c = New-Object Net.Sockets.TcpClient('127.0.0.1', 9877); $c.Close(); $up = $true } catch { Start-Sleep 2 }
        }
        "editor bridge: " + $(if ($up) { "up" } else { "not yet" })
        # The job runs minimised, and the editor it opens inherits that: a minimised editor doesn't render, so
        # screenshots time out and Play crawls (~3 fps). Restore it without taking focus.
        Add-Type -Namespace DaedalusJob -Name Win -MemberDefinition '[DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h); [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);' -ErrorAction SilentlyContinue
        foreach ($e in Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
            if ($e.MainWindowHandle -ne 0 -and [DaedalusJob.Win]::IsIconic($e.MainWindowHandle)) {
                [void][DaedalusJob.Win]::ShowWindow($e.MainWindowHandle, 4)   # SW_SHOWNOACTIVATE
                "editor window restored (it was minimised; a minimised editor doesn't render)"
            }
        }
    }
    else { "RUNNING $Id ($([int]((Get-Item $log -ErrorAction SilentlyContinue).Length / 1KB)) KB of log)" }
    if ($alerts) { "NORTON is asking you something:"; $alerts }
    exit
}
"use -Start or -Wait"
