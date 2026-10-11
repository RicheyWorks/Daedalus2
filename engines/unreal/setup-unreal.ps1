# SPDX-License-Identifier: MIT
<#
.SYNOPSIS
  Sets up Unreal Engine 5 for Daedalus (ADR-032): the Epic Games Launcher, a project with the
  DaedalusLink plugin enabled, and a World Package downloaded from a Daedalus server.

.DESCRIPTION
  Every step checks before it acts and says what it found; run it again at any time.
    1. Epic Games Launcher  - found, or installed with winget (-InstallLauncher). You sign in to Epic and
                              accept the Unreal Engine EULA yourself; this script never does that for you.
    2. Unreal Engine 5.4+   - found from the launcher's install list (or -EnginePath). Engines download
                              through the launcher (Library > +), so if none is installed the script opens
                              the launcher's Library page and stops.
    3. Project              - -Project names a .uproject; if it does not exist a blank one is made.
    4. Plugin               - DaedalusLink is copied into <Project>/Plugins and enabled in the .uproject.
    5. World Package        - <Server>/api/v1/world/<World>/package is saved under <Project>/Saved/Daedalus.
    6. Build (-Build)       - compiles the plugin with RunUAT BuildPlugin and installs the result (needs
                              Visual Studio 2022 with "Game development with C++"); without it the editor
                              offers to compile the plugin itself on first open.
    7. Import (-Import)     - runs Content/Python/import_world_package.py headless: materials, the world's
                              meshes, the ark, and a live "Daedalus World" actor in the default level.

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
    [switch]$Import,
    [switch]$SkipPackage,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$PluginSource = Join-Path $PSScriptRoot "DaedalusLink"
$script:Steps = 0
$script:Failed = 0

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
    $dat = Join-Path $env:ProgramData "Epic\UnrealEngineLauncher\LauncherInstalled.dat"
    if (-not (Test-Path $dat)) { return $null }
    $best = $null
    foreach ($i in (Get-Content $dat -Raw | ConvertFrom-Json).InstallationList) {
        if ($i.AppName -match '^UE_(\d+\.\d+)$' -and (Test-Version $Matches[1] $want)) {
            if (-not $best -or [version]$Matches[1] -gt [version]$best.Version) {
                $best = [pscustomobject]@{ Version = $Matches[1]; Path = $i.InstallLocation }
            }
        }
    }
    return $best
}

Say "Unreal Engine $EngineVersion or newer"
$engine = $null
if ($EnginePath) {
    $engine = [pscustomobject]@{ Version = $EngineVersion; Path = $EnginePath }
} else {
    $engine = Find-Engine $EngineVersion
}
if ($engine -and (Test-Path (Join-Path $engine.Path "Engine"))) {
    Write-Host ("    found UE {0} at {1}" -f $engine.Version, $engine.Path)
} else {
    $engine = $null
    Warn "no UE $EngineVersion+ found. Install it in the launcher: Unreal Engine > Library > Engine Versions > +"
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

# --- 4. Plugin ---------------------------------------------------------------------------------------------
Say "DaedalusLink plugin"
$PluginDest = Join-Path (Join-Path $ProjectDir "Plugins") "DaedalusLink"
if (-not (Test-Path (Join-Path $PluginSource "DaedalusLink.uplugin"))) {
    Fail "plugin source not found next to this script ($PluginSource)"
} elseif ($WhatIfOnly) {
    Write-Host "    would copy $PluginSource -> $PluginDest and enable it"
} else {
    if (Test-Path $PluginDest) { Remove-Item -Recurse -Force $PluginDest }
    New-Item -ItemType Directory -Force -Path (Split-Path $PluginDest -Parent) | Out-Null
    Copy-Item -Recurse -Force $PluginSource $PluginDest
    $up = Get-Content $Project -Raw | ConvertFrom-Json
    $plugins = @()
    if ($up.PSObject.Properties.Name -contains "Plugins" -and $up.Plugins) { $plugins = @($up.Plugins) }
    $needed = @("DaedalusLink", "ProceduralMeshComponent", "PythonScriptPlugin", "EditorScriptingUtilities")
    foreach ($name in $needed) {
        $hit = $plugins | Where-Object { $_.Name -eq $name }
        if ($hit) { $hit.Enabled = $true } else { $plugins += [pscustomobject]@{ Name = $name; Enabled = $true } }
    }
    $up | Add-Member -NotePropertyName Plugins -NotePropertyValue $plugins -Force
    $up | ConvertTo-Json -Depth 10 | Set-Content -Path $Project -Encoding UTF8
    Write-Host ("    copied to {0}; enabled {1}" -f $PluginDest, ($needed -join ", "))
}

# --- 5. World Package ----------------------------------------------------------------------------------------
$PackageDir = Join-Path (Join-Path $ProjectDir "Saved") "Daedalus"
$PackageFile = Join-Path $PackageDir "$World.daedalus.zip"
if (-not $SkipPackage) {
    $url = "$($Server.TrimEnd('/'))/api/v1/world/$World/package"
    Say "World Package" $url
    if ($WhatIfOnly) {
        Write-Host "    would save it to $PackageFile"
    } else {
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
                Fail "the server at $Server has no world '$World' (GET /api/v1/worlds lists them)"
            } else {
                Fail "could not get the package: $($_.Exception.Message) Is the Daedalus server running at $Server?"
            }
        }
    }
}

# --- 6. Build ------------------------------------------------------------------------------------------------
if ($Build) {
    Say "Build the plugin for the editor"
    if (-not $engine) {
        Fail "no engine to build with"
    } else {
        $bat = Join-Path $engine.Path "Engine\Build\BatchFiles\RunUAT.bat"
        $out = Join-Path (Join-Path $ProjectDir "Saved") "DaedalusLinkBuild"
        if ($WhatIfOnly) {
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
if ($Import) {
    Say "Import the World Package into the project"
    $editor = if ($engine) { Join-Path $engine.Path "Engine\Binaries\Win64\UnrealEditor-Cmd.exe" } else { "" }
    $py = Join-Path (Join-Path (Join-Path $PluginDest "Content") "Python") "import_world_package.py"
    if (-not $engine -or -not (Test-Path $editor -ErrorAction SilentlyContinue)) {
        Fail "UnrealEditor-Cmd.exe not found"
    } elseif ($WhatIfOnly) {
        Write-Host "    would run: $editor `"$Project`" -run=pythonscript -script=`"$py $PackageFile`""
    } else {
        & $editor $Project -run=pythonscript "-script=`"$py`" `"$PackageFile`"" -unattended -nopause
        if ($LASTEXITCODE -ne 0) { Fail "the import exited $LASTEXITCODE; see $ProjectDir\Saved\Logs" }
    }
}

Write-Host ""
if ($script:Failed -gt 0) {
    Write-Host ("{0} of {1} steps need you (see X above)." -f $script:Failed, $script:Steps) -ForegroundColor Red
    exit 1
}
Write-Host ("Done: {0} steps. Open {1} in Unreal; drop a 'Daedalus World' actor in a level, or use the imported one." -f `
    $script:Steps, $Project) -ForegroundColor Green
exit 0
