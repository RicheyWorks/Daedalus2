# SPDX-License-Identifier: MIT
# The Daedalus server on this PC, in one call each (ADR-050 delivery; same launch rules as unreal-job.ps1).
#
#   .\daedalus-server\server.ps1 -Restart    stop it, rebuild the jar (tests skipped: CI runs them), start it again
#   .\daedalus-server\server.ps1 -Status     running? which jar? answering on :8088? and the last log lines
#
# The job outlives the calling shell (WMI), runs from the repo (not AppData/%TEMP%, where scripts got stopped),
# and uses full paths for Java and Maven (a WMI-started process doesn't get the user's PATH). The world lives in
# %USERPROFILE%\.daedalus\ (daedalus.world.file), so a restart never touches it.
param([switch]$Restart, [switch]$Status, [switch]$Run,
      [string]$JavaHome = "C:\Program Files\Eclipse Adoptium\jdk-22.0.2.9-hotspot",
      [string]$Maven = "C:\Maven\apache-maven-3.9.9\bin\mvn.cmd")
$Repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$Jobs = Join-Path $env:LOCALAPPDATA "Daedalus\jobs"
New-Item -ItemType Directory -Force -Path $Jobs | Out-Null
$Log = Join-Path $Jobs "server.log"

function Servers { Get-CimInstance Win32_Process -Filter "Name = 'java.exe'" | Where-Object { $_.CommandLine -match 'daedalus-server.*exec\.jar' } }
function Answering { try { (Invoke-WebRequest -UseBasicParsing http://localhost:8088/api/v1/worlds -TimeoutSec 3).StatusCode -eq 200 } catch { $false } }

if ($Run) {
    $env:JAVA_HOME = $JavaHome
    $env:Path = "$JavaHome\bin;" + (Split-Path $Maven) + ";" + $env:Path
    Set-Location $Repo
    "$(Get-Date -Format s) stopping the server" | Out-File $Log -Encoding utf8
    Servers | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Start-Sleep -Seconds 3
    "$(Get-Date -Format s) building" | Out-File $Log -Append -Encoding utf8
    & $Maven -q -pl daedalus-server -am package -DskipTests *>> $Log
    "$(Get-Date -Format s) build exit $LASTEXITCODE; starting" | Out-File $Log -Append -Encoding utf8
    $jar = Get-ChildItem (Join-Path $Repo "daedalus-server\target") -Filter "daedalus-server-*-exec.jar" | Sort-Object LastWriteTime -Descending | Select-Object -First 1   # newest: old versions linger in target
    $st = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]7 }
    Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{
        CommandLine = "cmd.exe /c `"`"$JavaHome\bin\java.exe`" -jar `"$($jar.FullName)`" > `"$Jobs\server-out.log`" 2>&1`""
        CurrentDirectory = "$Repo"; ProcessStartupInformation = $st } | Out-Null
    for ($i = 0; $i -lt 60 -and -not (Answering); $i++) { Start-Sleep -Seconds 2 }
    "$(Get-Date -Format s) " + $(if (Answering) { "UP on :8088" } else { "NOT answering on :8088" }) | Out-File $Log -Append -Encoding utf8
    exit
}
if ($Restart) {
    $st = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]7 }
    $r = Invoke-CimMethod Win32_Process -MethodName Create -Arguments @{
        CommandLine = "powershell.exe -NoProfile -File `"$PSCommandPath`" -Run"; CurrentDirectory = "$Repo"; ProcessStartupInformation = $st }
    "restarting (pid $($r.ProcessId)); check with -Status in a minute or two"
    exit
}
$s = @(Servers)
"server: " + $(if ($s.Count) { "running pid $($s[0].ProcessId)" } else { "not running" }) + "; answering: " + (Answering)
Get-Content $Log -Tail 4 -ErrorAction SilentlyContinue
"--- server output (last lines) ---"
Get-Content (Join-Path $Jobs "server-out.log") -Tail 8 -ErrorAction SilentlyContinue
