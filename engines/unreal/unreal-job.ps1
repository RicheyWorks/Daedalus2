# SPDX-License-Identifier: MIT
# Long Unreal jobs (build, open) for Claude, in one call each, and quiet with antivirus (ADR-045).
#
#   .\unreal-job.ps1 -Start            pull, build the DaedalusLink plugin into the project, reopen the editor
#   .\unreal-job.ps1 -Start -Fast      the same, but only recompile what changed (editor target; ~1 min, ADR-055)
#   .\unreal-job.ps1 -Wait  [-Id x]    wait up to 50 s; prints RUNNING / BUILD OK / BUILD FAILED + the errors
#   .\unreal-job.ps1 -Run   -Id x      (internal) the job body
#
# Why it looks like this: the Claude app ends anything its shell starts when the call returns, so the job is
# started through WMI to outlive it. Everything else is chosen not to look like malware to Norton: the script
# runs from the repo (not %TEMP%), in a visible minimized window (not hidden), with no -ExecutionPolicy flag
# (this machine's policy already allows local scripts). Logs: %LOCALAPPDATA%\Daedalus\jobs.
param(
    [switch]$Start, [switch]$Wait, [switch]$Run, [switch]$Fast,
    [switch]$Rollback, [switch]$SaveGreen,
    [string]$GreenBuildId = '', [string]$Snapshot = '',
    [string]$Id = "",
    [string]$Project = "C:\Unreal\DaedalusRealm\DaedalusRealm.uproject",
    [int]$Seconds = 50
)
if ($Rollback -or $SaveGreen) {
    if ($Start -or $Run -or $Wait) { throw 'Recovery cannot be combined with build/start/wait' }
    & (Join-Path $PSScriptRoot 'plugin-recovery.ps1') -Project $Project -Rollback:$Rollback -SaveGreen:$SaveGreen -GreenBuildId $GreenBuildId -Snapshot $Snapshot
    return
}
$Jobs = Join-Path $env:LOCALAPPDATA "Daedalus\jobs"
New-Item -ItemType Directory -Force -Path $Jobs | Out-Null
$Repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")

function Latest { (Get-ChildItem $Jobs -Filter "build-*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).BaseName }

function BuildToolsBusy {
    # Unreal's AutomationTool and UnrealBuildTool run as dotnet; only one may build at a time.
    @(Get-CimInstance Win32_Process -Filter "Name = 'dotnet.exe' OR Name = 'UnrealBuildTool.exe' OR Name = 'AutomationTool.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'AutomationTool|UnrealBuildTool' }).Count -gt 0
}

# Play must not crawl when the editor isn't the window in front (it ran at ~3 fps). The per-user ini is rewritten by
# the editor on exit, so the setting goes in the project's default config, which the editor never overwrites.
function Set-FullSpeedDefault {
    $cfg = Join-Path (Split-Path $Project) "Config\DefaultEditorPerProjectUserSettings.ini"
    $section = "[/Script/UnrealEd.EditorPerformanceSettings]"
    $key = "bThrottleCPUWhenNotForeground=False"
    $text = if (Test-Path $cfg) { [IO.File]::ReadAllText($cfg) } else { "" }
    if ($text -notmatch [regex]::Escape($key)) {
        if ($text -match [regex]::Escape($section)) { $text = $text.Replace($section, "$section`r`n$key") }
        else { $text = $text.TrimEnd() + "`r`n`r`n$section`r`n$key`r`n" }
        [IO.File]::WriteAllText($cfg, $text)
    }
}

# Crash recovery with no popups (2hot2trot, 2026-10-12). UE 5.8 has no auto-restore setting: PackageAutoSaver.cpp only
# knows -AutoDeclinePackageRecovery and -unattended, and both throw the restore list away. So before the editor opens,
# copy each autosave in Saved\Autosaves\PackageRestoreData.json (UTF-16) over its package, back up what it overwrites,
# and rename the json so the Slate "Restore Packages" window never appears (it has no controls automation can press).
# A crash reporter left behind by a crash is closed without sending. Same logic as studio-screen-connector/crashguard.ps1.
function Restore-CrashAutosaves {
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { return }
    Get-Process CrashReportClient, CrashReportClientEditor -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    $proj = Split-Path $Project; $auto = Join-Path $proj "Saved\Autosaves"; $json = Join-Path $auto "PackageRestoreData.json"
    if (-not (Test-Path $json)) { return }
    $b = [IO.File]::ReadAllBytes($json)
    $text = if ($b.Length -ge 2 -and ($b[1] -eq 0 -or ($b[0] -eq 0xFF -and $b[1] -eq 0xFE))) { [Text.Encoding]::Unicode.GetString($b) } else { [Text.Encoding]::UTF8.GetString($b) }
    $data = $text.TrimStart([char]0xFEFF) | ConvertFrom-Json
    if ($data.RestoreEnabled -ne $true) { return }
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"; $bk = Join-Path $Jobs "autosave-restore-$stamp"; $done = @()
    New-Item -ItemType Directory -Force -Path $bk | Out-Null; Copy-Item $json $bk
    foreach ($k in @($data.Packages)) {
        $src = Join-Path $auto ($k.AutoSavePath -replace '/', '\')
        if (-not (Test-Path $src) -or $k.PackagePathName -notmatch '^/Game/') { "autosave missing for $($k.PackagePathName)"; continue }
        $rel = ($k.PackagePathName -replace '^/Game/', '' -replace '/', '\') + [IO.Path]::GetExtension($src)
        $dst = Join-Path $proj "Content\$rel"
        if (Test-Path $dst) { $to = Join-Path $bk "Content\$rel"; New-Item -ItemType Directory -Force -Path (Split-Path $to) | Out-Null; Copy-Item $dst $to -Force }
        New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null; Copy-Item $src $dst -Force; $done += $k.PackagePathName
    }
    Rename-Item $json "PackageRestoreData.restored-$stamp.json"
    "restored $($done.Count) autosaved package(s) before opening the editor (backup $bk): $($done -join ', ')"
}

# Unattended crash uploads off, in the project's default config (never rewritten by the editor).
function Set-NoUnattendedCrashUpload {
    $cfg = Join-Path (Split-Path $Project) "Config\DefaultEditorSettings.ini"
    $section = "[/Script/UnrealEd.CrashReportsPrivacySettings]"; $key = "bSendUnattendedBugReports=False"
    $text = if (Test-Path $cfg) { [IO.File]::ReadAllText($cfg) } else { "" }
    if ($text -match [regex]::Escape($key)) { return }
    $text = [regex]::Replace($text, "(?m)^bSendUnattendedBugReports=.*\r?\n?", "")
    if ($text -match [regex]::Escape($section)) { $text = $text.Replace($section, "$section`r`n$key") }
    else { $text = $text.TrimEnd() + "`r`n`r`n$section`r`n$key`r`n" }
    [IO.File]::WriteAllText($cfg, $text)
}
if ($Run) {
    $log = Join-Path $Jobs "$Id.log"
    Set-Location $Repo
    Set-FullSpeedDefault
    # Preflight (tools/unreal_preflight): catch the mistakes that cost a whole build slot (a shadowed actor member, a
    # missing Category, a bare Error, a saved component array) BEFORE the editor is closed. Fails = no build, editor stays up.
    git pull --ff-only *>&1 | Out-File -FilePath $log -Append -Encoding utf8
    $py = (Get-Command python -ErrorAction SilentlyContinue)
    if ($py) {
        & python (Join-Path $Repo "tools\unreal_preflight\preflight.py") *>&1 | Out-File -FilePath $log -Append -Encoding utf8
        if ($LASTEXITCODE -ne 0) {
            "PREFLIGHT FAILED: fix the lines above; the editor was left open" | Out-File -FilePath $log -Append -Encoding utf8
            "done 2" | Out-File -FilePath (Join-Path $Jobs "$Id.exit") -Encoding ascii
            exit
        }
    }
    Set-NoUnattendedCrashUpload
    Restore-CrashAutosaves *>&1 | Out-File -FilePath $log -Append -Encoding utf8
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        # Wait (up to 5 min) for any other Unreal build to finish instead of colliding with it.
        $until = (Get-Date).AddMinutes(5)
        while ((BuildToolsBusy) -and (Get-Date) -lt $until) {
            "waiting for another Unreal build tool to finish..." | Out-File -FilePath $log -Append -Encoding utf8
            Start-Sleep -Seconds 10
        }
        $mark = if (Test-Path $log) { (Get-Content $log).Count } else { 0 }
        try {
            & { git pull --ff-only; & (Join-Path $PSScriptRoot "setup-unreal.ps1") -Project $Project -Build -Open -Fast:$Fast } *>&1 |
                Out-File -FilePath $log -Append -Encoding utf8
            $code = $LASTEXITCODE
        } catch {
            # A terminating error (a locked file, say) used to end the job with no .exit file, so -Wait said RUNNING forever.
            "JOB STOPPED: $($_.Exception.Message)" | Out-File -FilePath $log -Append -Encoding utf8
            $code = 1
        }
        $fresh = Get-Content $log | Select-Object -Skip $mark
        if (-not ($fresh -match 'conflicting instance of AutomationTool')) { break }
        "another build tool collided; retrying in 20 s (attempt $attempt)" | Out-File -FilePath $log -Append -Encoding utf8
        Start-Sleep -Seconds 20
    }
    # Job end: close the floating Unreal panels it left (studio-screen-connector tidy.ps1, one pass, best effort).
    $tidy = Join-Path $Repo "..\studio-screen-connector\tidy.ps1"; if (Test-Path $tidy) { try { & powershell.exe -NoProfile -WindowStyle Hidden -File $tidy -Once *>> $log } catch { } }
    "done $code" | Out-File -FilePath (Join-Path $Jobs "$Id.exit") -Encoding ascii
    exit
}

if ($Start) {
    $Id = "build-" + (Get-Date -Format "MMdd-HHmmss")
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]7 }   # minimized, no focus
    $cmd = "powershell.exe -NoProfile -File `"$PSCommandPath`" -Run -Id $Id -Project `"$Project`"" + $(if ($Fast) { " -Fast" } else { "" })
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
        if ((Test-Path $log) -and (Select-String -Path $log -Pattern 'error C\d+|: error |\): Error: ' -Quiet)) { break }
        Start-Sleep -Seconds 3
    }
    $errors = if (Test-Path $log) { Select-String -Path $log -Pattern 'error C\d+|: error |\): Error: ' | Select-Object -First 15 | ForEach-Object { $_.Line } } else { @() }
    $norton = Join-Path $env:TEMP "daedalus-norton.log"
    $alerts = if (Test-Path $norton) { Get-Content $norton | Where-Object { $_ -ge (Get-Date).AddMinutes(-30).ToString("s") } } else { @() }
    # Compiler errors first: they are the real cause. AutomationTool's ErrorLog.txt is only written when it dies
    # before logging, so an old one is stale; show it only if it was written during this job.
    if ($errors) { "BUILD FAILED $Id"; $errors }
    elseif ((Test-Path $log) -and (Select-String -Path $log -Pattern 'X BuildPlugin exited' -Quiet) -and -not (Select-String -Path $log -Pattern 'BUILD SUCCESSFUL' -Quiet) -and (Test-Path $exit)) {
        $uat = Join-Path $env:LOCALAPPDATA "UnrealEngine\Programs\AutomationTool\Saved\Logs\ErrorLog.txt"
        if ((Test-Path $uat) -and (Get-Item $uat).LastWriteTime -ge (Get-Item $log).CreationTime) {
            "BUILD FAILED $Id (AutomationTool stopped before building):"
            Get-Content $uat -Tail 6
        }
        else { "BUILD FAILED $Id (the plugin build step failed):"; Get-Content $log | Select-String -Pattern 'Result:|ERROR|failed' | Select-Object -Last 8 | ForEach-Object { $_.Line } }
    }
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
