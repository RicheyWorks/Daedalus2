# SPDX-License-Identifier: MIT
<#
.SYNOPSIS
  Sets up Unreal Engine 5 for Daedalus (ADR-032): the Epic Games Launcher, a project with the
  DaedalusLink plugin enabled, and a World Package downloaded from a Daedalus server.

.DESCRIPTION
  Every step checks before it acts and says what it found; run it again at any time.
    1. Epic Games Launcher  - found, or installed with winget (-InstallLauncher). You sign in to Epic and
                              accept the Unreal Engine EULA yourself; this script never does that for you.
    2. Unreal Engine 5.4+   - the newest found in the launcher's install list, the registry or <drive>:\Epic Games
                              (or -EnginePath). Engines download
                              through the launcher (Library > +), so if none is installed the script opens
                              the launcher's Library page and stops.
    3. Project              - -Project names a .uproject; if it does not exist a blank one is made.
    4. Plugin               - DaedalusLink is copied into <Project>/Plugins and enabled in the .uproject.
    5. World Package        - <Server>/api/v1/world/<World>/package is saved under <Project>/Saved/Daedalus. A
                              localhost server that isn't running is started in its own window (Java 21 via
                              winget and Maven from Apache if missing); -NoServerStart turns that off.
    6. Build (-Build)       - compiles the plugin with RunUAT BuildPlugin and installs the result (needs
                              Visual Studio 2022 with "Game development with C++", installed with winget if
                              missing); without it the editor
                              offers to compile the plugin itself on first open.
    7. Import (-Import)     - runs Content/Python/import_world_package.py headless: materials, the world's
                              meshes, the ark, and a live "Daedalus World" actor in the default level. Then
                              it verifies the result inside Unreal against the manifest and prints PASS/FAIL
                              per check (-Verify alone re-checks an earlier import).

-Open closes this project in Unreal if it is open, does the steps, then opens it again: one line for everything.

.EXAMPLE
  .\setup-unreal.ps1 -Project C:\Unreal\DaedalusRealm\DaedalusRealm.uproject -InstallLauncher -Build -Import

.EXAMPLE
  .\setup-unreal.ps1 -Project .\Realm\Realm.uproject -Server http://192.168.1.20:8088 -World isle-two -WhatIfOnly
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Project,
    [string]$Server = "http://localhost:8088",
    [string]$World = "world-zero",
    [string]$EngineVersion = "5.4",
    [string]$EnginePath = "",
    [switch]$InstallLauncher,
    [switch]$Build,
    [switch]$Fast,        # with -Build: sync sources over the compiled plugin and build only what changed (ADR-055)
    [switch]$Import,
    [switch]$Verify,
    [switch]$Open,
    [switch]$Connector,   # also open the Claude extension installer (once)
    [switch]$SkipPackage,
    [switch]$NoServerStart,
    [switch]$WhatIfOnly,
    [ValidateSet("greedy", "faces")]
    [string]$Mesh = "greedy"   # greedy: merged faces, far fewer triangles in the editor (ADR-064); faces: one quad per cube face
)

$ErrorActionPreference = "Stop"
$PluginSource = Join-Path $PSScriptRoot "DaedalusLink"
$script:Steps = 0
$script:Failed = 0
$keep = $false

function Say([string]$what, [string]$detail) {
    $script:Steps++
    Write-Host ("[{0}] {1}" -f $script:Steps, $what) -ForegroundColor Cyan
    if ($detail) { Write-Host "    $detail" }
}

function Warn([string]$text) { Write-Host "    ! $text" -ForegroundColor Yellow }

function Fail([string]$text) {
    $script:Failed++
    Write-Host "    X $text" -ForegroundColor Red
}

function Test-Version([string]$have, [string]$want) {
    try { return [version]($have -replace '[^0-9.]', '') -ge [version]$want } catch { return $false }
}

# With -Open the script owns the editor: it asks an open copy of this project to close (Unreal offers to save
# anything unsaved), does the work, and opens it again at the end.
function Get-ProjectEditors {
    if (-not (Get-Command Get-CimInstance -ErrorAction SilentlyContinue)) { return @() }   # not Windows
    $leaf = Split-Path $Project -Leaf
    # This project's editor, and an editor started without a project (the launcher's project browser, which may
    # then open this one): either can hold the project's files. Commandlets (-run=) are the script's own.
    $cim = @(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" -ErrorAction SilentlyContinue)
    $found = @($cim | Where-Object { $_.CommandLine -notlike "*-run=*" -and ($_.CommandLine -like "*$leaf*" -or $_.CommandLine -notlike "*.uproject*") })
    # WMI can miss a process (seen 2026-10-12 from a WMI-started job: the editor stayed open and its DLL stayed
    # locked). Any UnrealEditor.exe that WMI didn't describe counts as this project's.
    $seen = @($cim | ForEach-Object { [int]$_.ProcessId })
    foreach ($p in @(Get-Process UnrealEditor -ErrorAction SilentlyContinue)) {
        if ($seen -notcontains $p.Id) { $found += [pscustomobject]@{ ProcessId = $p.Id; CommandLine = "" } }
    }
    return $found
}

# Close an editor by its own main window. Process.CloseMainWindow picks whichever top-level window Windows lists
# first, which can be a floating Content Browser: that closes, the editor stays (seen 2026-10-12).
function Close-EditorWindows([int]$processId) {
    if (-not ("DaedalusSetup.Win" -as [type])) {
        Add-Type -Namespace DaedalusSetup -Name Win -MemberDefinition @'
public delegate bool EnumProc(System.IntPtr h, System.IntPtr l);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, System.IntPtr l);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(System.IntPtr h, out uint pid);
[System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)] public static extern int GetWindowText(System.IntPtr h, System.Text.StringBuilder s, int n);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool IsWindowVisible(System.IntPtr h);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool PostMessage(System.IntPtr h, uint m, System.IntPtr w, System.IntPtr l);
'@
    }
    $hits = New-Object System.Collections.Generic.List[System.IntPtr]
    $cb = [DaedalusSetup.Win+EnumProc]{
        param($h, $l)
        [uint32]$owner = 0
        [void][DaedalusSetup.Win]::GetWindowThreadProcessId($h, [ref]$owner)
        if ($owner -eq $processId -and [DaedalusSetup.Win]::IsWindowVisible($h)) {
            $sb = New-Object System.Text.StringBuilder 256
            [void][DaedalusSetup.Win]::GetWindowText($h, $sb, 256)
            if ($sb.ToString() -like "* - Unreal Editor") { $hits.Add($h) }
        }
        $true
    }
    [void][DaedalusSetup.Win]::EnumWindows($cb, [IntPtr]::Zero)
    foreach ($h in $hits) { [void][DaedalusSetup.Win]::PostMessage($h, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero) }   # WM_CLOSE
    return $hits.Count
}
if ($Open -and -not $WhatIfOnly) {
    $eds = @(Get-ProjectEditors)
    Write-Host ("Open editors of this project: {0}" -f $eds.Count)
    if ($eds.Count -gt 0) {
        # Save through the Claude Unreal Bridge first when it is listening, so closing raises no "Save Content"
        # prompt for someone to click.
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("127.0.0.1", 9877)
            $st = $tcp.GetStream()
            $msg = [Text.Encoding]::UTF8.GetBytes('{"id":1,"type":"save","params":{"bridge_timeout":60}}' + "`n")
            $st.Write($msg, 0, $msg.Length)
            $st.ReadTimeout = 60000
            $reply = (New-Object System.IO.StreamReader($st)).ReadLine()
            $tcp.Close()
            if ($reply -match '"status": *"ok"') { Write-Host "Saved the open level through the Claude Unreal Bridge." }
        } catch { }   # no bridge: Unreal asks about unsaved work itself
        Write-Host "Closing Unreal so the project can be updated (save anything it asks about)..." -ForegroundColor Cyan
        foreach ($e in $eds) {
            if ((Close-EditorWindows ([int]$e.ProcessId)) -eq 0) { (Get-Process -Id $e.ProcessId -ErrorAction SilentlyContinue).CloseMainWindow() | Out-Null }
        }
        for ($i = 0; $i -lt 30 -and @(Get-ProjectEditors).Count -gt 0; $i++) { Start-Sleep -Seconds 1 }
        # A job started through WMI can't always reach the editor's window; ask the editor itself to quit (it saved above).
        for ($n = 0; $n -lt 3 -and @(Get-ProjectEditors).Count -gt 0; $n++) {
            try {
                $tcp = New-Object System.Net.Sockets.TcpClient
                $tcp.Connect("127.0.0.1", 9877)
                $msg = [Text.Encoding]::UTF8.GetBytes('{"id":2,"type":"execute_python","params":{"code":"import unreal\nunreal.SystemLibrary.quit_editor()"}}' + "`n")
                $tcp.GetStream().Write($msg, 0, $msg.Length)
                Start-Sleep -Seconds 2
                $tcp.Close()
                Write-Host "    asked the editor to quit through the Claude Unreal Bridge"
            } catch { }
            for ($i = 0; $i -lt 30 -and @(Get-ProjectEditors).Count -gt 0; $i++) { Start-Sleep -Seconds 1 }
        }
        for ($i = 0; $i -lt 60 -and @(Get-ProjectEditors).Count -gt 0; $i++) { Start-Sleep -Seconds 1 }
        if (@(Get-ProjectEditors).Count -gt 0) {
            Write-Host "Unreal is still open (waiting on a save prompt?). Close it, then run this again." -ForegroundColor Red
            exit 1
        }
        Start-Sleep -Seconds 3   # let Windows release the files the editor had open
    }
}

# --- 1. Epic Games Launcher ---------------------------------------------------------------------------
function Find-Launcher {
    if (-not $IsWindows -and $PSVersionTable.PSEdition -eq "Core") { return $null }
    $candidates = @(
        "${env:ProgramFiles(x86)}\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
        "${env:ProgramFiles}\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe"
    )
    foreach ($c in $candidates) { if ($c -and (Test-Path $c)) { return $c } }
    return $null
}

Say "Epic Games Launcher"
$launcher = Find-Launcher
if ($launcher) {
    Write-Host "    found $launcher"
} elseif (-not ($IsWindows -or $PSVersionTable.PSEdition -eq "Desktop")) {
    Warn "not Windows: Unreal and its launcher install on Windows; skipping (the plugin and package steps still run)"
} elseif ($InstallLauncher) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail "winget is missing; install 'App Installer' from the Microsoft Store, or the launcher from epicgames.com"
    } elseif ($WhatIfOnly) {
        Write-Host "    would run: winget install --id EpicGames.EpicGamesLauncher --exact --source winget"
    } else {
        # No --accept-* flags: winget shows Epic's terms and you agree to them, not this script.
        winget install --id EpicGames.EpicGamesLauncher --exact --source winget
        if ($LASTEXITCODE -ne 0) { Fail "winget exited $LASTEXITCODE" }
        $launcher = Find-Launcher
    }
} else {
    Warn "not installed; run again with -InstallLauncher, or get it from https://store.epicgames.com/download"
}

# --- 2. Unreal Engine ------------------------------------------------------------------------------------
function Find-Engine([string]$want) {
    if (-not $env:ProgramData) { return $null }   # not Windows
    $found = @()
    # a) the launcher's install list
    $dat = Join-Path $env:ProgramData "Epic\UnrealEngineLauncher\LauncherInstalled.dat"
    if (Test-Path $dat) {
        try {
            foreach ($i in (Get-Content $dat -Raw | ConvertFrom-Json).InstallationList) {
                $tag = "$($i.AppName) $($i.InstallLocation)"
                if ($tag -match 'UE_(\d+\.\d+)') {
                    $found += [pscustomobject]@{ Version = $Matches[1]; Path = $i.InstallLocation }
                }
            }
        } catch { Warn "could not read $dat ($($_.Exception.Message))" }
    }
    # b) the registry the launcher writes for each engine
    foreach ($root in @("HKLM:\SOFTWARE\EpicGames\Unreal Engine", "HKLM:\SOFTWARE\WOW6432Node\EpicGames\Unreal Engine")) {
        if (Test-Path $root) {
            foreach ($k in Get-ChildItem $root -ErrorAction SilentlyContinue) {
                $dir = (Get-ItemProperty $k.PSPath -ErrorAction SilentlyContinue).InstalledDirectory
                if ($dir -and $k.PSChildName -match '^(\d+\.\d+)') {
                    $found += [pscustomobject]@{ Version = $Matches[1]; Path = $dir }
                }
            }
        }
    }
    # c) the usual folders, on every drive
    $roots = @("${env:ProgramFiles}\Epic Games") + (Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path $_.Root "Epic Games"; Join-Path $_.Root "Program Files\Epic Games" })
    foreach ($r in ($roots | Select-Object -Unique)) {
        if ($r -and (Test-Path $r)) {
            foreach ($d in Get-ChildItem $r -Directory -Filter "UE_*" -ErrorAction SilentlyContinue) {
                if ($d.Name -match '^UE_(\d+\.\d+)') {
                    $found += [pscustomobject]@{ Version = $Matches[1]; Path = $d.FullName }
                }
            }
        }
    }
    $ok = $found | Where-Object {
        (Test-Version $_.Version $want) -and
        (Test-Path (Join-Path $_.Path "Engine\Binaries\Win64\UnrealEditor.exe"))
    }
    return $ok | Sort-Object { [version]$_.Version } -Descending | Select-Object -First 1
}

Say "Unreal Engine $EngineVersion or newer"
$engine = $null
if ($EnginePath) {
    $v = if ($EnginePath -match 'UE_(\d+\.\d+)') { $Matches[1] } else { $EngineVersion }
    $engine = [pscustomobject]@{ Version = $v; Path = $EnginePath }
} else {
    $engine = Find-Engine $EngineVersion
}
if ($engine -and (Test-Path (Join-Path $engine.Path "Engine"))) {
    Write-Host ("    found UE {0} at {1}" -f $engine.Version, $engine.Path)
} else {
    $engine = $null
    Warn "no UE $EngineVersion+ found (looked in the launcher's list, the registry, and <drive>:\Epic Games\UE_*)."
    Warn "If it is installing, wait for the launcher to finish. If it lives elsewhere, add -EnginePath 'D:\Where\UE_5.8'."
    if ($launcher -and -not $WhatIfOnly) {
        Start-Process "com.epicgames.launcher://ue/library"
    }
}

# --- 3. Project --------------------------------------------------------------------------------------------
Say "Project" $Project
if (-not $Project.EndsWith(".uproject")) {
    $Project = Join-Path $Project ((Split-Path $Project -Leaf) + ".uproject")
}
$ProjectDir = Split-Path ([System.IO.Path]::GetFullPath($Project)) -Parent
$Project = [System.IO.Path]::GetFullPath($Project)
$association = if ($engine) { $engine.Version } else { $EngineVersion }
if (Test-Path $Project) {
    Write-Host "    found"
    if ($engine -and -not $WhatIfOnly) {
        $up = Get-Content $Project -Raw | ConvertFrom-Json
        if ($up.EngineAssociation -ne $engine.Version) {
            $up.EngineAssociation = $engine.Version
            $up | ConvertTo-Json -Depth 10 | Set-Content -Path $Project -Encoding UTF8
            Write-Host "    now opens with UE $($engine.Version)"
        }
    }
} elseif ($WhatIfOnly) {
    Write-Host "    would create a blank project for UE $association"
} else {
    New-Item -ItemType Directory -Force -Path $ProjectDir, (Join-Path $ProjectDir "Content"), (Join-Path $ProjectDir "Config") | Out-Null
    $blank = [ordered]@{
        FileVersion       = 3
        EngineAssociation = $association
        Category          = ""
        Description       = "A Daedalus world in Unreal Engine 5 (made by setup-unreal.ps1)"
        Plugins           = @()
    }
    $blank | ConvertTo-Json -Depth 5 | Set-Content -Path $Project -Encoding UTF8
    # Open the level the import script fills, and let Python run in the editor.
    @(
        "[/Script/EngineSettings.GameMapsSettings]",
        "EditorStartupMap=/Game/Daedalus/DaedalusWorld.DaedalusWorld",
        "GameDefaultMap=/Game/Daedalus/DaedalusWorld.DaedalusWorld"
    ) | Set-Content -Path (Join-Path (Join-Path $ProjectDir "Config") "DefaultEngine.ini") -Encoding UTF8
    Write-Host "    created a blank project for UE $association"
}

# One hash over every file under a folder (relative names and contents), to tell whether two copies match.
function Get-TreeHash([string]$dir) {
    if (-not (Test-Path $dir)) { return "" }
    $root = (Resolve-Path $dir).Path
    $lines = Get-ChildItem $root -Recurse -File | Sort-Object FullName | ForEach-Object {
        $_.FullName.Substring($root.Length).Replace('\', '/') + " " + (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($lines -join "`n"))
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($bytes)) } finally { $sha.Dispose() }
}

# Read and retain the original Unicode encoding, BOM and line endings.
function Read-IniDocument([string]$file) {
    [byte[]]$bytes = @()
    if (Test-Path -LiteralPath $file) { $bytes = [IO.File]::ReadAllBytes($file) }
    $prefix = if ($bytes.Length) { [BitConverter]::ToString($bytes, 0, [Math]::Min(4, $bytes.Length)) } else { "" }
    $skip = 0
    $encoding = New-Object System.Text.UTF8Encoding($false, $true)
    # Select BOMs ourselves: StreamReader BOM detection replaces strict decoders
    # with replacement-fallback encodings. Unmarked input is strict UTF-8.
    if ($prefix.StartsWith("FF-FE-00-00")) {
        $skip = 4; $encoding = New-Object System.Text.UTF32Encoding($false, $false, $true)
    } elseif ($prefix.StartsWith("00-00-FE-FF")) {
        $skip = 4; $encoding = New-Object System.Text.UTF32Encoding($true, $false, $true)
    } elseif ($prefix.StartsWith("EF-BB-BF")) {
        $skip = 3
    } elseif ($prefix.StartsWith("FF-FE")) {
        $skip = 2; $encoding = New-Object System.Text.UnicodeEncoding($false, $false, $true)
    } elseif ($prefix.StartsWith("FE-FF")) {
        $skip = 2; $encoding = New-Object System.Text.UnicodeEncoding($true, $false, $true)
    }
    [byte[]]$bom = @()
    if ($skip) { $bom = $bytes[0..($skip - 1)] }
    $text = $encoding.GetString($bytes, $skip, $bytes.Length - $skip)
    $records = New-Object System.Collections.Generic.List[object]
    $newline = [Environment]::NewLine
    $firstEnding = [regex]::Match($text, '\r\n|\n|\r')
    if ($firstEnding.Success) { $newline = $firstEnding.Value }
    foreach ($match in [regex]::Matches($text, '([^\r\n]*)(\r\n|\n|\r|$)')) {
        if ($match.Length) {
            $records.Add([pscustomobject]@{ Text = $match.Groups[1].Value; Ending = $match.Groups[2].Value })
        }
    }
    return [pscustomobject]@{ Text = $text; Encoding = $encoding; Bom = $bom; Records = $records.ToArray(); Newline = $newline }
}

# Sets key=value under [section], adding the section or key if missing.
# A key listed with a leading '+' (an Unreal array entry) is added once.
function Set-IniValue([string]$file, [string]$section, [string]$key, [string]$value) {
    $document = Read-IniDocument $file
    $out = New-Object System.Collections.Generic.List[string]
    $inSection = $false; $done = $false; $seen = $false
    foreach ($record in $document.Records) {
        $l = $record.Text
        if ($l -match '^\s*\[(.+)\]\s*$') {
            if ($inSection -and -not $done) { $out.Add("$key=$value" + $document.Newline); $done = $true }
            $inSection = ($Matches[1] -eq $section); if ($inSection) { $seen = $true }
            $out.Add($l + $record.Ending); continue
        }
        if ($inSection -and $key.StartsWith("+") -and $l.Trim() -eq "$key=$value") { $done = $true }
        elseif ($inSection -and -not $key.StartsWith("+") -and $l -match ("^\s*" + [regex]::Escape($key) + "\s*=")) {
            if (-not $done) { $out.Add("$key=$value" + $record.Ending); $done = $true }
            continue
        }
        $out.Add($l + $record.Ending)
    }
    $terminal = if (-not $document.Text.Length -or $document.Text -match '[\r\n]$') { $document.Newline } else { "" }
    if ($inSection -and -not $done) {
        if ($out.Count -and $out[$out.Count - 1] -notmatch '[\r\n]$') { $out.Add($document.Newline) }
        $out.Add("$key=$value" + $terminal); $done = $true
    }
    if (-not $seen) {
        if ($out.Count -and $out[$out.Count - 1] -notmatch '[\r\n]$') { $out.Add($document.Newline) }
        $out.Add($document.Newline); $out.Add("[$section]" + $document.Newline); $out.Add("$key=$value" + $terminal)
    }
    [byte[]]$body = $document.Encoding.GetBytes(($out -join ""))
    [byte[]]$encoded = New-Object byte[] ($document.Bom.Length + $body.Length)
    $document.Bom.CopyTo($encoded, 0)
    $body.CopyTo($encoded, $document.Bom.Length)
    [IO.File]::WriteAllBytes($file, $encoded)
}

function Ensure-GameFeatureDataCookRule([string]$file) {
    # Preserve inherited array scans and any existing project rule for this type.
    $section = "/Script/Engine.AssetManagerSettings"
    $inSection = $false
    $document = Read-IniDocument $file
    foreach ($record in $document.Records) {
        $line = $record.Text
        if ($line -match '^\s*\[(.+)\]\s*$') {
            $inSection = ($Matches[1] -eq $section)
        } elseif ($inSection -and $line -match '^\s*[+.]?PrimaryAssetTypesToScan\s*=.*PrimaryAssetType\s*=\s*"?GameFeatureData"?\s*[,)]') {
            return $false
        }
    }
    $rule = '(PrimaryAssetType="GameFeatureData",AssetBaseClass="/Script/GameFeatures.GameFeatureData",bHasBlueprintClasses=False,bIsEditorOnly=False,Directories=(),SpecificAssets=(),Rules=(Priority=-1,ChunkId=-1,bApplyRecursively=True,CookRule=AlwaysCook))'
    Set-IniValue $file $section "+PrimaryAssetTypesToScan" $rule
    return $true
}

# Processes that have a file under $dir loaded (a running editor keeps the plugin's DLL open).
function Get-Lockers([string]$dir) {
    $full = [System.IO.Path]::GetFullPath($dir)
    return @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
        try { @($_.Modules | Where-Object { $_.FileName -and $_.FileName.StartsWith($full, [StringComparison]::OrdinalIgnoreCase) }).Count -gt 0 }
        catch { $false }
    })
}

# Removes the installed plugin. If Windows refuses because a program has it loaded, that program (an Unreal editor
# or one of its helpers) is asked to close, then stopped if it won't, and the removal is tried again.
function Remove-PluginCopy([string]$dir) {
    try { Remove-Item -Recurse -Force $dir -ErrorAction Stop; return } catch { }
    $lockers = Get-Lockers $dir
    if ($lockers.Count -eq 0) {
        $lockers = @(Get-Process UnrealEditor, UnrealEditor-Cmd, LiveCodingConsole, ShaderCompileWorker -ErrorAction SilentlyContinue)
    }
    foreach ($p in $lockers) {
        Write-Host ("    {0} (pid {1}) has the plugin open; closing it" -f $p.ProcessName, $p.Id)
        $p.CloseMainWindow() | Out-Null
    }
    for ($i = 0; $i -lt 30 -and @($lockers | Where-Object { -not $_.HasExited }).Count -gt 0; $i++) { Start-Sleep -Seconds 1 }
    $lockers | Where-Object { -not $_.HasExited } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Remove-Item -Recurse -Force $dir -ErrorAction Stop
}

# --- 4. Plugin ---------------------------------------------------------------------------------------------
Say "DaedalusLink plugin"
$PluginDest = Join-Path (Join-Path $ProjectDir "Plugins") "DaedalusLink"
if (-not (Test-Path (Join-Path $PluginSource "DaedalusLink.uplugin"))) {
    Fail "plugin source not found next to this script ($PluginSource)"
} elseif ($WhatIfOnly) {
    Write-Host "    would copy $PluginSource -> $PluginDest and enable it"
} else {
    # A compiled plugin whose sources match this repo's is kept: copying over it would throw the build away.
    # With -Fast the build tool decides what is stale (it is incremental and quick when nothing is), so never "keep":
    # matching sources don't prove the DLL was linked from them (a link can fail after the sync).
    $keep = (-not $Fast) -and (Test-Path (Join-Path $PluginDest "Binaries\Win64\UnrealEditor-DaedalusLink.dll")) -and
        ((Get-TreeHash (Join-Path $PluginSource "Source")) -eq (Get-TreeHash (Join-Path $PluginDest "Source"))) -and
        ((Get-TreeHash (Join-Path $PluginSource "Content")) -eq (Get-TreeHash (Join-Path $PluginDest "Content")))
    if ($keep) {
        Write-Host "    the compiled plugin there matches these sources; keeping it"
    } elseif ($Fast -and (Test-Path (Join-Path $PluginDest "Binaries\Win64\UnrealEditor-DaedalusLink.dll"))) {
        # Keep Binaries and Intermediate so the compiler only redoes the files that changed.
        foreach ($sub in @("Source", "Content", "Resources")) {
            if (Test-Path (Join-Path $PluginSource $sub)) {
                robocopy (Join-Path $PluginSource $sub) (Join-Path $PluginDest $sub) /MIR /NJH /NJS /NP /NFL /NDL | Out-Null
                if ($LASTEXITCODE -ge 8) { Fail "robocopy $sub exited $LASTEXITCODE" }
            }
        }
        Copy-Item -Force (Join-Path $PluginSource "DaedalusLink.uplugin") $PluginDest
        $global:LASTEXITCODE = 0
        $script:FastSync = $true
        Write-Host "    synced sources over the compiled plugin (fast build)"
    } else {
        if (Test-Path $PluginDest) { Remove-PluginCopy $PluginDest }
        New-Item -ItemType Directory -Force -Path (Split-Path $PluginDest -Parent) | Out-Null
        Copy-Item -Recurse -Force $PluginSource $PluginDest
    }
    $up = Get-Content $Project -Raw | ConvertFrom-Json
    $plugins = @()
    if ($up.PSObject.Properties.Name -contains "Plugins" -and $up.Plugins) { $plugins = @($up.Plugins) }
    $needed = @("DaedalusLink", "ProceduralMeshComponent", "PythonScriptPlugin", "EditorScriptingUtilities", "PCG")   # PCG: procedural ecology (engines/unreal/pcg-ecology)
    foreach ($name in $needed) {
        $hit = $plugins | Where-Object { $_.Name -eq $name }
        if ($hit) { $hit.Enabled = $true } else { $plugins += [pscustomobject]@{ Name = $name; Enabled = $true } }
    }
    $up | Add-Member -NotePropertyName Plugins -NotePropertyValue $plugins -Force
    $up | ConvertTo-Json -Depth 10 | Set-Content -Path $Project -Encoding UTF8
    Write-Host ("    {0} {1}; enabled {2}" -f $(if ($keep) { "in" } else { "copied to" }), $PluginDest, ($needed -join ", "))
}

# --- Project settings the world needs: DirectX 12 with Shader Model 6 (Nanite, which UE 5.8 uses for imported
# meshes, refuses to draw without it), and the Daedalus level as the startup map.
if (-not $WhatIfOnly -and (Test-Path $Project)) {
    $ini = Join-Path (Join-Path $ProjectDir "Config") "DefaultEngine.ini"
    New-Item -ItemType Directory -Force -Path (Split-Path $ini -Parent) | Out-Null
    $win = "/Script/WindowsTargetPlatform.WindowsTargetSettings"
    Set-IniValue $ini $win "DefaultGraphicsRHI" "DefaultGraphicsRHI_DX12"
    Set-IniValue $ini $win "-D3D12TargetedShaderFormats" "PCD3D_SM5"
    Set-IniValue $ini $win "+D3D12TargetedShaderFormats" "PCD3D_SM6"
    Set-IniValue $ini "/Script/EngineSettings.GameMapsSettings" "EditorStartupMap" "/Game/Daedalus/DaedalusWorld.DaedalusWorld"
    Set-IniValue $ini "/Script/EngineSettings.GameMapsSettings" "GameDefaultMap" "/Game/Daedalus/DaedalusWorld.DaedalusWorld"
    # No camera motion blur: a fast mouse turn smeared the whole screen (Richey, 2026-10-13).
    Set-IniValue $ini "/Script/Engine.RendererSettings" "r.DefaultFeature.MotionBlur" "False"
    $gameIni = Join-Path (Join-Path $ProjectDir "Config") "DefaultGame.ini"
    [void](Ensure-GameFeatureDataCookRule $gameIni)
    Write-Host "    project settings: DirectX 12 with Shader Model 6 (for Nanite), Daedalus level at startup, no motion blur"
}

# --- 5. World Package ----------------------------------------------------------------------------------------
# Any HTTP answer means a server is listening; only a refused or timed-out connection means it isn't.
$script:LastProbe = ""
$script:ProbeCode = 0
function Test-Server {
    try {
        $r = Invoke-WebRequest -Uri "$($Server.TrimEnd('/'))/api/v1/world/$World/package/manifest" -UseBasicParsing -TimeoutSec 30
        $script:ProbeCode = [int]$r.StatusCode
        $script:LastProbe = "HTTP $($r.StatusCode)"
        return $true
    } catch {
        if ($_.Exception.Response) {
            $script:ProbeCode = [int]$_.Exception.Response.StatusCode
            $script:LastProbe = "HTTP $script:ProbeCode"
            return $true
        }
        $script:ProbeCode = 0
        $script:LastProbe = $_.Exception.Message
        return $false
    }
}

function Find-Java {
    $cands = @()
    $onPath = Get-Command java -ErrorAction SilentlyContinue
    if ($onPath) { $cands += $onPath.Source }
    if ($env:JAVA_HOME) { $cands += (Join-Path $env:JAVA_HOME "bin\java.exe") }
    foreach ($r in @("${env:ProgramFiles}\Microsoft", "${env:ProgramFiles}\Java", "${env:ProgramFiles}\Eclipse Adoptium")) {
        if (Test-Path $r) { $cands += (Get-ChildItem $r -Directory -Filter "jdk*" | Sort-Object Name -Descending | ForEach-Object { Join-Path $_.FullName "bin\java.exe" }) }
    }
    foreach ($c in $cands) {
        if (-not (Test-Path $c)) { continue }
        $ErrorActionPreference = "Continue"   # java -version writes to stderr; PowerShell 5.1 would stop on it
        $v = (& $c -version 2>&1 | Out-String)
        $ErrorActionPreference = "Stop"
        if ($v -match 'version "(\d+)' -and [int]$Matches[1] -ge 21) { return $c }
    }
    return $null
}

# Maven from PATH, or downloaded once from Apache into %LOCALAPPDATA%\Daedalus.
function Find-Maven {
    $m = Get-Command mvn -ErrorAction SilentlyContinue
    if ($m) { return $m.Source }
    $ver = "3.9.9"
    $home2 = Join-Path $env:LOCALAPPDATA "Daedalus\apache-maven-$ver"
    $cmd = Join-Path $home2 "bin\mvn.cmd"
    if (Test-Path $cmd) { return $cmd }
    $zip = Join-Path $env:TEMP "apache-maven-$ver-bin.zip"
    $url = "https://archive.apache.org/dist/maven/maven-3/$ver/binaries/apache-maven-$ver-bin.zip"
    Write-Host "    downloading Maven $ver from $url"
    try {
        Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing -TimeoutSec 300
        Expand-Archive -Path $zip -DestinationPath (Join-Path $env:LOCALAPPDATA "Daedalus") -Force
    } catch { Warn "could not download Maven: $($_.Exception.Message)"; return $null }
    if (Test-Path $cmd) { return $cmd }
    Warn "Maven unpacked but $cmd is missing"
    return $null
}

# A server on this PC that isn't running is started here: built with Maven if needed, then run in its own window.
# The Daedalus server already listening on this PC's port, if it is one this repo built (an older build
# without World Packages answers 404 and is replaced).
function Stop-OldLocalServer([int]$port) {
    $owners = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($o in $owners) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $o" -ErrorAction SilentlyContinue
        if ($proc -and $proc.CommandLine -match 'daedalus-server-.*\.jar') {
            Write-Host "    stopping an older Daedalus server on port $port (pid $o) to start the current one"
            Stop-Process -Id $o -Force
            Start-Sleep -Seconds 2
            return $true
        }
    }
    return $false
}

function Start-LocalServer {
    if ($NoServerStart) { return }
    $uri = [uri]$Server
    $local = $uri.Host -in @("localhost", "127.0.0.1", "::1")
    $port = if ($uri.Port -gt 0) { $uri.Port } else { 80 }
    if (Test-Server) {
        if ($script:ProbeCode -eq 200 -or -not $local) { return }
        if ($script:ProbeCode -eq 404 -and (Stop-OldLocalServer $port)) {
            # fall through: build if needed, then start the current server
        } else {
            Warn "something else answers on port $port ($script:LastProbe); close it, or pass -Server with another port"
            return
        }
    }
    if (-not $local) { return }
    $repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
    if (-not (Test-Path (Join-Path $repo "daedalus-server\pom.xml"))) { Warn "no daedalus-server next to this script; start the server yourself"; return }
    $java = Find-Java
    if (-not $java) {
        Write-Host "    the server needs Java 21; installing Microsoft's OpenJDK 21 with winget (you accept its license there)"
        winget install --id Microsoft.OpenJDK.21 --exact --source winget
        $java = Find-Java
        if (-not $java) { Warn "no Java 21 after winget; open a new PowerShell and run this again"; return }
    }
    $jar = Get-ChildItem (Join-Path $repo "daedalus-server\target") -Filter "daedalus-server-*-exec.jar" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    # Each module's sources, walked one module at a time (a wildcard in the middle of a -Recurse path
    # matches nothing in Windows PowerShell 5.1, which made an old jar look current).
    $newest = Get-ChildItem $repo -Directory -Filter "daedalus-*" | ForEach-Object {
        $src = Join-Path $_.FullName "src\main"
        if (Test-Path $src) { Get-ChildItem $src -Recurse -File -ErrorAction SilentlyContinue }
    } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $jar -or ($newest -and $newest.LastWriteTime -gt $jar.LastWriteTime)) {
        $mvn = Find-Maven
        if (-not $mvn) { return }
        Write-Host "    building the server (the first time downloads libraries and takes a few minutes)..."
        $env:JAVA_HOME = Split-Path (Split-Path $java -Parent) -Parent
        Push-Location $repo
        $ErrorActionPreference = "Continue"
        try {
            & $mvn -B -q package -pl daedalus-server -am -DskipTests "-Dcheckstyle.skip" "-Dspotbugs.skip" "-Djacoco.skip"
            if ($LASTEXITCODE -ne 0) { Warn "mvn package exited $LASTEXITCODE"; return }
        } finally { Pop-Location; $ErrorActionPreference = "Stop" }
        $jar = Get-ChildItem (Join-Path $repo "daedalus-server\target") -Filter "daedalus-server-*-exec.jar" |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
    }
    Write-Host "    starting the Daedalus server on port $port in its own window (leave it open)"
    $cmd = "`$env:SERVER_PORT='$port'; Set-Location '$repo'; & '$java' -jar '$($jar.FullName)'"
    Start-Process powershell -ArgumentList @("-NoExit", "-Command", $cmd) | Out-Null
    for ($i = 0; $i -lt 90; $i++) {
        Start-Sleep -Seconds 2
        if ((Test-Server) -and $script:ProbeCode -eq 200) { Write-Host "    server is up"; return }
    }
    Warn "the server did not answer within 3 minutes ($script:LastProbe); check its window"
}

$PackageDir = Join-Path (Join-Path $ProjectDir "Saved") "Daedalus"
$PackageFile = Join-Path $PackageDir "$World.daedalus.zip"
if (-not $SkipPackage) {
    $url = "$($Server.TrimEnd('/'))/api/v1/world/$World/package"
    if ($Mesh -eq "greedy") { $url += "?mesh=greedy" }
    Say "World Package" $url
    if ($WhatIfOnly) {
        Write-Host "    would save it to $PackageFile"
    } else {
        Start-LocalServer

        New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null
        try {
            Invoke-WebRequest -Uri $url -OutFile $PackageFile -UseBasicParsing -TimeoutSec 120
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $zip = [System.IO.Compression.ZipFile]::OpenRead($PackageFile)
            try {
                $entry = $zip.GetEntry("manifest.json")
                if (-not $entry) { throw "no manifest.json in the package" }
                $reader = New-Object System.IO.StreamReader($entry.Open())
                try { $manifest = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
            } finally { $zip.Dispose() }
            if ($manifest.format -ne "daedalus-world-package") { throw "not a Daedalus World Package" }
            Write-Host ("    {0} ({1}) r{2}: {3} chunks, {4} triangles, {5} islands, {6} gates -> {7}" -f `
                $manifest.world.title, $manifest.world.style, $manifest.world.revision, $manifest.geometry.chunks,
                $manifest.geometry.triangles, @($manifest.islands).Count, @($manifest.gates).Count, $PackageFile)
        } catch {
            $code = 0
            if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
            if ($code -eq 404) {
                Fail "the server at $Server has no world '$World', or is an older build without World Packages (GET /api/v1/worlds lists worlds)"
            } else {
                Fail "could not get the package: $($_.Exception.Message) Is the Daedalus server running at $Server?"
            }
        }
    }
}

# --- 6. Build ------------------------------------------------------------------------------------------------
$VsInstallerDir = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer"
function Find-VcTools {
    $vswhere = Join-Path $VsInstallerDir "vswhere.exe"
    if (-not (Test-Path $vswhere)) { return $null }
    $p = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($p) { return ($p | Select-Object -First 1) }
    return $null
}

# Any Visual Studio install, with or without the C++ tools, including one an interrupted update left
# incomplete (vswhere hides those unless asked with -all).
function Find-AnyVs {
    $vswhere = Join-Path $VsInstallerDir "vswhere.exe"
    if (-not (Test-Path $vswhere)) { return $null }
    $json = & $vswhere -all -products * -format json | Out-String
    $all = @($json | ConvertFrom-Json)
    if ($all.Count -eq 0) { return $null }
    $i = $all | Sort-Object { [version]$_.installationVersion } -Descending | Select-Object -First 1
    return [pscustomobject]@{ Path = $i.installationPath; Complete = [bool]$i.isComplete; Version = $i.installationVersion }
}

# The MSVC toolsets installed under a Visual Studio, newest first.
function Get-MsvcVersions([string]$vs) {
    $dir = Join-Path $vs "VC\Tools\MSVC"
    if (-not (Test-Path $dir)) { return @() }
    return @(Get-ChildItem $dir -Directory | ForEach-Object { try { [version]$_.Name } catch { } } | Sort-Object -Descending)
}

# Unreal 5.5+ wants MSVC 14.38 or newer and refuses 14.40-14.43 (compiler bugs).
function Test-MsvcUsable([version]$v) {
    return $v -ge [version]"14.38" -and -not ($v -ge [version]"14.40" -and $v -lt [version]"14.44")
}

if ($Build) {
    Say "Build the plugin for the editor"
    $vc = Find-VcTools
    $busy = if ($keep) { $null } else { Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path -like "*Microsoft Visual Studio\Installer*" -and $_.MainWindowHandle -ne [IntPtr]::Zero -and $_.ProcessName -notmatch 'vswhere|BackgroundDownload|ServiceHub' } }
    if ($keep) {
        # built already; the toolchain is not needed
    } elseif ($busy -and -not $WhatIfOnly) {
        Fail "the Visual Studio Installer window is open: if it is installing, let it finish; then close it and run this again"
        $vc = $null
        $script:VcReported = $true
    } elseif (-not $vc -and -not $WhatIfOnly -and (Find-AnyVs)) {
        # Visual Studio is there but without the C++ tools (or an update left them out): add them to it.
        $any = Find-AnyVs
        $setup = Join-Path $VsInstallerDir "setup.exe"
        Write-Host "    Windows will ask to let the Visual Studio Installer make changes: choose Yes."
        if (-not $any.Complete) {
            Write-Host "    Visual Studio $($any.Version) at $($any.Path) is half-installed (an update stopped part way); finishing it"
            Start-Process -FilePath $setup -Verb RunAs -Wait -ArgumentList @("resume", "--installPath", "`"$($any.Path)`"", "--passive", "--norestart")
        }
        Write-Host "    adding 'Game development with C++' to Visual Studio at $($any.Path)"
        Start-Process -FilePath $setup -Verb RunAs -Wait -ArgumentList @("modify", "--installPath", "`"$($any.Path)`"",
            "--passive", "--norestart", "--add", "Microsoft.VisualStudio.Workload.NativeGame", "--add", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "--add", "Microsoft.VisualStudio.Component.Windows11SDK.22621", "--includeRecommended")
        $vc = Find-VcTools
    } elseif (-not $vc -and -not $WhatIfOnly) {
        Write-Host "    no Visual Studio C++ tools; installing Visual Studio 2022 Community with 'Game development with C++'"
        Write-Host "    (a large download; the installer window shows progress, and you accept its license there)"
        winget install --id Microsoft.VisualStudio.2022.Community --exact --source winget --override `
            "--add Microsoft.VisualStudio.Workload.NativeGame --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.22621 --includeRecommended --passive --wait"
        $vc = Find-VcTools
    }
    if ($vc -and -not $WhatIfOnly -and -not $keep) {
        $msvc = Get-MsvcVersions $vc
        if (-not ($msvc | Where-Object { Test-MsvcUsable $_ })) {
            Write-Host ("    MSVC {0} is too old for UE {1}; updating Visual Studio to its latest (MSVC 14.44+)." -f (($msvc | Select-Object -First 1)), $engine.Version)
            Write-Host "    The Visual Studio Installer window shows progress; close Visual Studio first if it is open."
            $setup = Join-Path $VsInstallerDir "setup.exe"
            # --passive needs an elevated installer (exit 5007 otherwise): Windows asks you to allow it.
            Write-Host "    Windows will ask to let the Visual Studio Installer make changes: choose Yes."
            Start-Process -FilePath $setup -Verb RunAs -Wait -ArgumentList @("update", "--installPath", "`"$vc`"", "--passive", "--norestart")
            Start-Process -FilePath $setup -Verb RunAs -Wait -ArgumentList @("modify", "--installPath", "`"$vc`"", "--passive", "--norestart",
                "--add", "Microsoft.VisualStudio.Workload.NativeGame", "--add", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "--add", "Microsoft.VisualStudio.Component.Windows11SDK.22621", "--includeRecommended")
            $msvc = Get-MsvcVersions $vc
            if (-not ($msvc | Where-Object { Test-MsvcUsable $_ })) {
                Fail ("MSVC is still {0}; open the Visual Studio Installer, Update, then run this again" -f ($msvc | Select-Object -First 1))
                $vc = $null
                $script:VcReported = $true
            }
        }
        if ($vc) { Write-Host ("    C++ tools: {0} (MSVC {1})" -f $vc, ($msvc | Where-Object { Test-MsvcUsable $_ } | Select-Object -First 1)) }
    }
    if ($keep) {
        Write-Host "    already built from these sources; nothing to do"
    } elseif (-not $engine) {
        Fail "no engine to build with"
    } elseif (-not $vc -and $script:VcReported) {
        # already said why above
    } elseif (-not $vc -and -not $WhatIfOnly) {
        Fail "no Visual Studio C++ tools (the install above did not finish; run this again when it has)"
    } else {
        $bat = Join-Path $engine.Path "Engine\Build\BatchFiles\RunUAT.bat"
        $out = Join-Path (Join-Path $ProjectDir "Saved") "DaedalusLinkBuild"
        $fastDone = $false
        if ($script:FastSync -and -not $WhatIfOnly) {
            # The editor target only, incrementally, straight into the plugin's Binaries (about a minute, not six).
            $ubt = Join-Path $engine.Path "Engine\Build\BatchFiles\Build.bat"
            $was = $ErrorActionPreference; $ErrorActionPreference = "Continue"   # stderr lines must not stop the script
            $lines = & $ubt UnrealEditor Win64 Development "-Project=$Project" -WaitMutex -NoHotReloadFromIDE 2>&1 | ForEach-Object { "$_" }
            $ErrorActionPreference = $was
            $lines | ForEach-Object { Write-Host $_ }
            if ($LASTEXITCODE -eq 0) {
                $fastDone = $true
                Write-Host "    BUILD SUCCESSFUL (fast: editor target, changed files only)"
            } elseif ($lines -match 'LNK1104|being used by another process') {
                $fastDone = $true
                Fail "the plugin DLL is locked: Unreal is still open with this project; close it and run this again"
            } elseif ($lines -match 'error C\d+|: error |\): Error: ') {   # compiler or UnrealHeaderTool
                $fastDone = $true
                Fail "the fast build found compile errors (above)"
            } else {
                Write-Host "    the fast build could not run here (exit $LASTEXITCODE); doing the full BuildPlugin instead"
            }
        }
        if ($fastDone) {
            # built (or failed with compile errors) by the fast path
        } elseif ($WhatIfOnly) {
            Write-Host "    would run: $bat BuildPlugin -Plugin=$(Join-Path $PluginDest "DaedalusLink.uplugin") -Package=$out -Rocket"
        } else {
            & $bat BuildPlugin "-Plugin=$(Join-Path $PluginDest "DaedalusLink.uplugin")" "-Package=$out" -Rocket
            if ($LASTEXITCODE -ne 0) {
                Fail "BuildPlugin exited $LASTEXITCODE (Visual Studio 2022 with 'Game development with C++' installed?)"
            } else {
                # BuildPlugin leaves the compiled plugin in $out; the project loads it from Plugins.
                Remove-Item -Recurse -Force $PluginDest
                Copy-Item -Recurse -Force $out $PluginDest
                Write-Host "    built; installed the compiled plugin at $PluginDest"
            }
        }
    }
}

# --- 7. Import -----------------------------------------------------------------------------------------------
if ($Import -or $Verify) {
    Say $(if ($Import) { "Import the World Package into the project, then verify it" } else { "Verify the imported world" })
    $editor = if ($engine) { Join-Path $engine.Path "Engine\Binaries\Win64\UnrealEditor-Cmd.exe" } else { "" }
    $py = Join-Path (Join-Path (Join-Path $PluginDest "Content") "Python") "import_world_package.py"
    if (-not $engine -or -not (Test-Path $editor -ErrorAction SilentlyContinue)) {
        Fail "UnrealEditor-Cmd.exe not found"
    } elseif (-not $WhatIfOnly -and -not (Test-Path $PackageFile)) {
        Fail "no World Package to import (step 5)"
    } elseif (-not $WhatIfOnly -and @(Get-ProjectEditors).Count -gt 0) {
        # The open editor holds the level file, so the import could not save it (Windows error 32).
        Fail "Unreal has this project open; close it (File > Exit), then run this again"
    } elseif ($WhatIfOnly) {
        Write-Host "    would run: $editor `"$Project`" -run=pythonscript -script=`"$py $PackageFile`""
    } else {
        # Until the plugin is compiled the editor refuses to open a project that enables it. The import is
        # pure Python, so it runs with DaedalusLink switched off for the moment and switched back on after.
        $built = Test-Path (Join-Path $PluginDest "Binaries\Win64\UnrealEditor-DaedalusLink.dll")
        $saved = $null
        if (-not $built) {
            Write-Host "    the plugin isn't compiled yet: importing meshes now; the live actor comes once it builds"
            $saved = Get-Content $Project -Raw
            $up = $saved | ConvertFrom-Json
            foreach ($pl in @($up.Plugins)) { if ($pl.Name -eq "DaedalusLink") { $pl.Enabled = $false } }
            $up | ConvertTo-Json -Depth 10 | Set-Content -Path $Project -Encoding UTF8
        }
        try {
            $flags = if ($Import) { "" } else { " --verify" }
            $report = Join-Path $PackageDir "verify-$World.json"
            if (Test-Path $report) { Remove-Item $report }   # only this run's report counts
            & $editor $Project -run=pythonscript "-script=`"$py`" `"$PackageFile`"$flags" -unattended -nopause
            $code = $LASTEXITCODE
            if (-not (Test-Path $report) -and $code -eq 0) {
                Fail "Unreal finished without writing $report, so nothing was verified"
            } elseif (Test-Path $report) {
                $v = Get-Content $report -Raw | ConvertFrom-Json
                Write-Host ("    verified {0} r{1} in Unreal:" -f $v.world, $v.revision)
                foreach ($c in $v.checks) {
                    $color = if ($c.ok) { "Green" } else { "Red" }
                    Write-Host ("      {0} {1} ({2})" -f $(if ($c.ok) { "PASS" } else { "FAIL" }), $c.name, $c.detail) -ForegroundColor $color
                }
            }
            if ($code -eq 3) { Fail "the world in Unreal does not match the package (FAIL lines above)" }
            elseif ($code -ne 0) { Fail "the import exited $code; see $ProjectDir\Saved\Logs" }
        } finally {
            if ($saved) { Set-Content -Path $Project -Value $saved -Encoding UTF8 -NoNewline }
        }
    }
}

# --- The Claude Unreal connector (connectors/claude-unreal-connector) -----------------------------------------
# Its bridge plugin goes into the project every run (Python only: nothing to build), through the connector's own
# installer, so Claude can operate the editor. -Connector also opens its Claude extension installer, which is
# needed once.
$ConnectorInstall = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "connectors\claude-unreal-connector\install.ps1"
Say "Claude Unreal connector"
if (-not (Test-Path $ConnectorInstall)) {
    Warn "connectors\claude-unreal-connector not found next to this repo; Claude won't be able to operate the editor"
} elseif ($WhatIfOnly) {
    Write-Host "    would install the Claude Unreal Bridge plugin$(if ($Connector) { ' and open the Claude extension installer' })"
} elseif (-not (Test-Path $Project)) {
    Warn "no project yet"
} else {
    try {
        if ($Connector) { & $ConnectorInstall -Project $Project } else { & $ConnectorInstall -Project $Project -NoExtension }
    } catch { Fail "the connector did not install: $($_.Exception.Message)" }
}

# A Start-menu shortcut to this project's editor. It opens the project in one click, and lets Claude's computer
# use find "Unreal Editor" by name (it can only reach apps in the Start menu) to answer a dialog when needed.
if ($engine -and -not $WhatIfOnly -and $env:APPDATA -and (Test-Path $Project)) {
    try {
        $lnk = Join-Path $env:APPDATA ("Microsoft\Windows\Start Menu\Programs\Unreal Editor ({0}).lnk" -f [IO.Path]::GetFileNameWithoutExtension($Project))
        $exe = Join-Path $engine.Path "Engine\Binaries\Win64\UnrealEditor.exe"
        $sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
        $sc.TargetPath = $exe
        $sc.Arguments = "`"$Project`""
        $sc.WorkingDirectory = Split-Path $exe -Parent
        $sc.IconLocation = "$exe,0"
        $sc.Save()
    } catch { Warn "could not make the Start menu shortcut: $($_.Exception.Message)" }
}

Write-Host ""
if ($Open -and -not $WhatIfOnly) {
    $exe = if ($engine) { Join-Path $engine.Path "Engine\Binaries\Win64\UnrealEditor.exe" } else { "" }
    if ($exe -and (Test-Path $exe)) {
        Write-Host "Opening $Project in Unreal $($engine.Version)..." -ForegroundColor Cyan
        # multi-editor.ps1 -Join leaves the Multi-User session arguments here (ADR-059).
        $extraFile = Join-Path (Join-Path (Split-Path $Project) "Saved\Daedalus") "editor-args.txt"
        $extra = if (Test-Path $extraFile) { (Get-Content $extraFile -Raw).Trim() } else { "" }
        # The shared editor always runs D3D11 with GPU crash breadcrumbs: a no-flag D3D12 launch hit a GPU page fault
        # twice under imports (bot-team LESSONS-LEARNED-UNREAL, hephaestus 2026-10-13 05:58).
        foreach ($flag in @("-d3d11", "-gpucrashdebugging")) {
            if ($extra -notmatch [regex]::Escape($flag)) { $extra = ($extra + " " + $flag).Trim() }
        }
        Write-Host "    editor flags: $extra"
        Start-Process -FilePath $exe -ArgumentList ("`"$Project`" " + $extra).Trim()
        # Answer the startup dialogs (rebuild modules, restore packages) so nobody has to click them.
        $watch = Join-Path $PSScriptRoot "dialog-watch.ps1"
        if (Test-Path $watch) {
            Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$watch`"")
            Write-Host "    the dialog watcher answers startup prompts (log: $env:TEMP\daedalus-dialog-watch.log)"
        }
    } else {
        Fail "can't open Unreal: no UnrealEditor.exe found"
    }
}
if ($script:Failed -gt 0) {
    Write-Host ("{0} of {1} steps need you (see X above)." -f $script:Failed, $script:Steps) -ForegroundColor Red
    exit 1
}
Write-Host ("Done: {0} steps. Open {1} in Unreal; drop a 'Daedalus World' actor in a level, or use the imported one." -f `
    $script:Steps, $Project) -ForegroundColor Green
exit 0
