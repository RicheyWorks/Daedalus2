# SPDX-License-Identifier: MIT
<#
.SYNOPSIS
  Installs claude-unreal-connector: the Claude Unreal Bridge plugin into an Unreal project, and the MCP
  extension into the Claude desktop app.

.DESCRIPTION
  Run from a clone or an unzipped copy of the repo, or straight from GitHub:
    & ([scriptblock]::Create((irm https://raw.githubusercontent.com/RicheyWorks/claude-unreal-connector/main/install.ps1))) -Project C:\Path\Game.uproject
  Steps (each says what it found; run it again any time):
    1. Copies plugin\ClaudeUnrealBridge into <Project>\Plugins and enables it, with PythonScriptPlugin and
       EditorScriptingUtilities, in the .uproject. Python only: nothing to compile.
    2. Packs extension\ into claude-unreal-connector.mcpb and opens it, so Claude shows its Install card.
       -NoExtension skips this, for agents that use PROTOCOL.md or clients\python instead of MCP.
  Close the project in Unreal first; open it again afterwards and the bridge starts with the editor.
#>
param(
    [Parameter(Mandatory = $true)][string]$Project,
    [switch]$NoExtension,
    [string]$Branch = "main"
)
$ErrorActionPreference = "Stop"
$repo = "RicheyWorks/claude-unreal-connector"

# Where the connector's files are: next to this script, or downloaded from GitHub when run through irm.
$root = if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "plugin\ClaudeUnrealBridge"))) { $PSScriptRoot } else { $null }
if (-not $root) {
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) "claude-unreal-connector"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $zip = Join-Path $tmp "src.zip"
    Write-Host "Downloading $repo ($Branch)..."
    Invoke-WebRequest "https://github.com/$repo/archive/refs/heads/$Branch.zip" -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $tmp
    $root = (Get-ChildItem $tmp -Directory | Select-Object -First 1).FullName
}

if (-not $Project.EndsWith(".uproject")) { throw "-Project must be a .uproject file" }
$Project = [System.IO.Path]::GetFullPath($Project)
if (-not (Test-Path $Project)) { throw "no project at $Project" }
$leaf = Split-Path $Project -Leaf
$open = if (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) {
    Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*$leaf*" -and $_.CommandLine -notlike "*-run=*" }
} else { $null }   # not Windows: nothing to check
if ($open) { throw "Unreal has $leaf open. Close it (File > Exit), then run this again." }

# 1. The plugin.
$dest = Join-Path (Join-Path (Split-Path $Project -Parent) "Plugins") "ClaudeUnrealBridge"
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
Copy-Item -Recurse -Force (Join-Path $root "plugin\ClaudeUnrealBridge") $dest
Get-ChildItem $dest -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
$up = Get-Content $Project -Raw | ConvertFrom-Json
$plugins = @(); if ($up.PSObject.Properties.Name -contains "Plugins" -and $up.Plugins) { $plugins = @($up.Plugins) }
foreach ($name in @("ClaudeUnrealBridge", "PythonScriptPlugin", "EditorScriptingUtilities")) {
    $hit = $plugins | Where-Object { $_.Name -eq $name }
    if ($hit) { $hit.Enabled = $true } else { $plugins += [pscustomobject]@{ Name = $name; Enabled = $true } }
}
$up | Add-Member -NotePropertyName Plugins -NotePropertyValue $plugins -Force
$up | ConvertTo-Json -Depth 10 | Set-Content -Path $Project -Encoding UTF8
Write-Host "Plugin installed at $dest and enabled in $leaf" -ForegroundColor Green

# 2. The Claude extension. An .mcpb is a zip with manifest.json at its root; entries are named with '/'
#    (Compress-Archive in Windows PowerShell 5.1 writes backslashes).
if (-not $NoExtension) {
    $mcpb = Join-Path ([System.IO.Path]::GetTempPath()) "claude-unreal-connector.mcpb"
    if (Test-Path $mcpb) { Remove-Item $mcpb }
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::Open($mcpb, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($entry in @("manifest.json", "server/index.js", "server/win.ps1")) {
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, (Join-Path (Join-Path $root "extension") $entry), $entry) | Out-Null
        }
    } finally { $archive.Dispose() }
    Start-Process $mcpb
    Write-Host "Opened the Claude extension: click Install (if Windows asks which app, pick Claude)." -ForegroundColor Cyan
}
Write-Host "Open $leaf in Unreal; the bridge starts with the editor on 127.0.0.1:9877."
