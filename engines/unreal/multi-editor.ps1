# SPDX-License-Identifier: MIT
# More than one Unreal editor on the same world at once (ADR-059), through Unreal's own Multi-User Editing.
#
#   .\multi-editor.ps1 -Server              start the Multi-User session server (once; it keeps running)
#   .\multi-editor.ps1 -Copy -Name B        make (or refresh) editor B's own project copy, C:\Unreal\DaedalusRealm_B
#   .\multi-editor.ps1 -Open -Name B        open editor B on bridge port 9878, joined to session "Daedalus"
#   .\multi-editor.ps1 -Join                make editor A (the main project) join the session at its next open
#   .\multi-editor.ps1 -Status              server, editors, ports, free RAM
#
# Every editor has its own project folder, so two editors never write the same file. Multi-User keeps the levels in
# step live. Each editor's Claude Unreal Bridge listens on its own port: A on 9877, B on 9878, C on 9879. Each
# editor needs about 5.6 GB of RAM, so -Open refuses when less than 7 GB is free.
param(
    [switch]$Server, [switch]$Copy, [switch]$Open, [switch]$Join, [switch]$Status,
    [string]$Name = "B",
    [string]$Main = "C:\Unreal\DaedalusRealm",
    [string]$Session = "Daedalus",
    [string]$ServerName = "DaedalusServer",
    [int]$MinFreeGB = 7
)
$Engine = "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64"
$Logs = Join-Path $env:LOCALAPPDATA "Daedalus\jobs"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
$Ports = @{ A = 9877; B = 9878; C = 9879; D = 9880 }

function Folder([string]$n) { if ($n -eq "A") { $Main } else { "$Main" + "_" + $n } }
function Uproject([string]$n) { Join-Path (Folder $n) "DaedalusRealm.uproject" }
function FreeGB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1) }
function ConcertArgs([string]$display) {
    "-CONCERTAUTOCONNECT -CONCERTRETRYAUTOCONNECTONERROR -CONCERTSERVER=$ServerName -CONCERTSESSION=$Session -CONCERTDISPLAYNAME=$display"
}

# Both editors need the Multi-User client plugin; the copy also needs it.
function Enable-MultiUser([string]$uproject) {
    $up = Get-Content $uproject -Raw | ConvertFrom-Json
    $plugins = @($up.Plugins)
    if (-not ($plugins | Where-Object { $_.Name -eq "MultiUserClient" })) {
        $plugins += [pscustomobject]@{ Name = "MultiUserClient"; Enabled = $true }
        $up.Plugins = $plugins
        ($up | ConvertTo-Json -Depth 6) | Set-Content -Path $uproject -Encoding UTF8
        "enabled MultiUserClient in $uproject"
    }
}

function Start-Detached([string]$cmd, [string]$cwd) {
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]7 }
    (Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $cmd; CurrentDirectory = $cwd; ProcessStartupInformation = $startup }).ProcessId
}

if ($Server) {
    $running = Get-Process UnrealMultiUserServer -ErrorAction SilentlyContinue
    if ($running) { "server already running (pid $($running.Id))"; exit }
    $log = Join-Path $Logs "multiuser-server.log"
    $pid_ = Start-Detached "cmd.exe /c `"`"$Engine\UnrealMultiUserServer.exe`" -CONCERTSERVER=$ServerName -CONCERTSESSION=$Session > `"$log`" 2>&1`"" $Engine
    "server $ServerName started (pid $pid_); log $log"
    exit
}

if ($Copy) {
    if ($Name -eq "A") { "A is the main project; nothing to copy"; exit }
    $dst = Folder $Name
    # Content, config and plugins (with the compiled DaedalusLink); never Saved, Intermediate or the DDC.
    foreach ($sub in @("Config", "Content", "Plugins")) {
        robocopy (Join-Path $Main $sub) (Join-Path $dst $sub) /MIR /NJH /NJS /NP /NFL /NDL /XD Intermediate | Out-Null
        if ($LASTEXITCODE -ge 8) { "robocopy $sub failed ($LASTEXITCODE)"; exit 1 }
    }
    Copy-Item -Force (Uproject "A") (Uproject $Name)
    Enable-MultiUser (Uproject $Name)
    "editor $Name project ready at $dst"
    exit
}

if ($Join) {
    Enable-MultiUser (Uproject "A")
    # setup-unreal.ps1 adds these to the command line whenever it opens the main project.
    $argsFile = Join-Path $Main "Saved\Daedalus\editor-args.txt"
    New-Item -ItemType Directory -Force -Path (Split-Path $argsFile) | Out-Null
    Set-Content -Path $argsFile -Value (ConcertArgs "EditorA-Claude") -Encoding ASCII
    "editor A will join session $Session at its next open ($argsFile)"
    exit
}

if ($Open) {
    if ($Name -eq "A") { "open A with unreal-job.ps1 (it adds the session args from -Join)"; exit }
    $free = FreeGB
    if ($free -lt $MinFreeGB) { "REFUSED: only $free GB RAM free; an editor needs about 5.6 GB (want $MinFreeGB)"; exit 1 }
    if (-not (Test-Path (Uproject $Name))) { "no project for $Name; run -Copy -Name $Name first"; exit 1 }
    $port = $Ports[$Name]
    $cmd = "cmd.exe /c set CLAUDE_UNREAL_PORT=$port&& `"$Engine\UnrealEditor.exe`" `"$(Uproject $Name)`" $(ConcertArgs ("Editor" + $Name))"
    $pid_ = Start-Detached $cmd $Engine
    "editor $Name opening (cmd pid $pid_), bridge port $port, session $Session"
    exit
}

if ($Status -or $true) {
    $srv = Get-Process UnrealMultiUserServer -ErrorAction SilentlyContinue
    "server: " + $(if ($srv) { "running (pid $($srv.Id))" } else { "not running" })
    foreach ($e in @(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" -ErrorAction SilentlyContinue)) {
        "editor pid $($e.ProcessId): $($e.CommandLine)"
    }
    foreach ($k in $Ports.Keys | Sort-Object) {
        $up = $false
        try { $c = New-Object Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $Ports[$k]); $c.Close(); $up = $true } catch { }
        "bridge $k ($($Ports[$k])): " + $(if ($up) { "up" } else { "-" })
    }
    "RAM free: $(FreeGB) GB"
}
