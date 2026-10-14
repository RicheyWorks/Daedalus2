# SPDX-License-Identifier: MIT
# Explicit operator checkpoint and rollback; never stops an editor or starts a build.
param(
    [Parameter(Mandatory=$true)][string]$Project,
    [switch]$SaveGreen, [switch]$Rollback,
    [string]$GreenBuildId = '', [string]$Snapshot = '',
    [ValidateRange(1,300)][int]$DeadlineSeconds = 60
)
$ErrorActionPreference = 'Stop'
if ([bool]$SaveGreen -eq [bool]$Rollback) { throw 'Choose exactly one of -SaveGreen or -Rollback' }
$projectFile = (Resolve-Path -LiteralPath $Project).Path
if ([IO.Path]::GetExtension($projectFile) -ne '.uproject') { throw 'Expected .uproject' }
$projectRoot = Split-Path $projectFile
$engineAssociation = (Get-Content -LiteralPath $projectFile -Raw | ConvertFrom-Json).EngineAssociation
$plugin = Join-Path $projectRoot 'Plugins\DaedalusLink'
$live = Join-Path $plugin 'Binaries\Win64'
$recovery = Join-Path $projectRoot 'Saved\DaedalusPluginRecovery'
New-Item -ItemType Directory -Force -Path $recovery | Out-Null
$watch = [Diagnostics.Stopwatch]::StartNew()
function CheckDeadline {
    if ($watch.Elapsed.TotalSeconds -gt $DeadlineSeconds) { throw 'Recovery preparation exceeded deadline; live binaries not published' }
}
function AssertIdle {
    # Refuse unknown ownership instead of closing another team's editor/job.
    if (Get-Process UnrealEditor,UnrealEditor-Cmd,UnrealBuildTool,AutomationTool -ErrorAction SilentlyContinue) {
        throw 'Editor/build process active; coordinate handoff before recovery'
    }
    $builds = @(Get-CimInstance Win32_Process -Filter "Name = 'dotnet.exe'" |
        Where-Object { $_.CommandLine -match 'UnrealBuildTool|AutomationTool' })
    if ($builds.Count) { throw 'Unreal dotnet build active; recovery refused' }
}
function FileTable([string]$root) {
    $prefix = [IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
    @(Get-ChildItem -LiteralPath $root -Recurse -File | Sort-Object FullName | ForEach-Object {
        CheckDeadline
        if ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse files forbidden in recovery' }
        [pscustomobject]@{ path=$_.FullName.Substring($prefix.Length); bytes=$_.Length;
            sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
    })
}
function AssertTree([string]$root) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw "Missing binary directory: $root" }
    if (@(Get-Item -LiteralPath $root; Get-ChildItem -LiteralPath $root -Recurse -Directory) |
        Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) { throw 'Reparse directories forbidden' }
    foreach ($required in @('UnrealEditor-DaedalusLink.dll','UnrealEditor.modules')) {
        if (-not (Test-Path -LiteralPath (Join-Path $root $required) -PathType Leaf)) { throw "Missing $required" }
    }
}
function AssertTable($expected, $actual) {
    if (@($expected).Count -ne @($actual).Count) { throw 'Binary file set changed' }
    for ($i=0; $i -lt @($expected).Count; $i++) {
        if ($expected[$i].path -cne $actual[$i].path -or $expected[$i].sha256 -cne $actual[$i].sha256 -or
            $expected[$i].bytes -ne $actual[$i].bytes) { throw "Binary identity mismatch: $($expected[$i].path)" }
    }
}
$lock = [IO.File]::Open((Join-Path $recovery 'recovery.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
try {
    AssertIdle
    if ($SaveGreen) {
        if ($GreenBuildId -notmatch '^[A-Za-z0-9._-]{1,128}$') { throw 'Explicit operator-approved -GreenBuildId required' }
        AssertTree $live
        $before = FileTable $live
        $token = [guid]::NewGuid().ToString('N')
        $stage = Join-Path $recovery "capture-$token"
        New-Item -ItemType Directory -Path $stage | Out-Null
        Copy-Item -LiteralPath $live -Destination (Join-Path $stage 'Win64') -Recurse
        AssertTree (Join-Path $stage 'Win64')
        AssertTable $before (FileTable (Join-Path $stage 'Win64'))
        AssertTable $before (FileTable $live)
        $modules = Get-Content -LiteralPath (Join-Path $live 'UnrealEditor.modules') -Raw | ConvertFrom-Json
        if (-not $modules.BuildId) { throw 'Module build identity missing' }
        $manifest = @{schema=1; project=$projectFile; approved_build=$GreenBuildId; module_build=$modules.BuildId;
            engine_association=$engineAssociation;
            created_utc=[DateTime]::UtcNow.ToString('o'); files=$before}
        $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $stage 'manifest.json') -Encoding UTF8
        CheckDeadline
        $final = Join-Path $recovery "green-$token"
        Move-Item -LiteralPath $stage -Destination $final
        $pointer = Join-Path $recovery "latest-$token.tmp"
        [IO.File]::WriteAllText($pointer, (Split-Path $final -Leaf))
        $latest = Join-Path $recovery 'latest-green.txt'
        if (Test-Path -LiteralPath $latest) { [IO.File]::Replace($pointer,$latest,$null) }
        else { [IO.File]::Move($pointer,$latest) }
        "GREEN SNAPSHOT $final elapsed=$([math]::Round($watch.Elapsed.TotalSeconds,3))"
        return
    }
    if (-not $Snapshot) { $Snapshot = [IO.File]::ReadAllText((Join-Path $recovery 'latest-green.txt')).Trim() }
    if ($Snapshot -notmatch '^green-[a-f0-9]{32}$') { throw 'Snapshot must be a saved green directory name' }
    $saved = Join-Path $recovery $Snapshot
    AssertTree (Join-Path $saved 'Win64')
    $manifest = Get-Content -LiteralPath (Join-Path $saved 'manifest.json') -Raw | ConvertFrom-Json
    if ($manifest.schema -ne 1 -or $manifest.project -ne $projectFile -or -not $manifest.approved_build) { throw 'Snapshot belongs to another project or schema' }
    if ($manifest.engine_association -ne $engineAssociation) { throw 'Engine association changed; old binaries cannot be restored' }
    AssertTable $manifest.files (FileTable (Join-Path $saved 'Win64'))
    $token = [guid]::NewGuid().ToString('N')
    $prepared = Join-Path (Split-Path $live) "Win64-recovery-$token"
    Copy-Item -LiteralPath (Join-Path $saved 'Win64') -Destination $prepared -Recurse
    AssertTable $manifest.files (FileTable $prepared)
    CheckDeadline
    AssertIdle
    CheckDeadline
    $previous = Join-Path (Split-Path $live) "Win64-before-rollback-$token"
    $moved = $false
    try {
        if (Test-Path -LiteralPath $live) { Move-Item -LiteralPath $live -Destination $previous; $moved=$true }
        Move-Item -LiteralPath $prepared -Destination $live
    } catch {
        if ($moved -and -not (Test-Path -LiteralPath $live)) { Move-Item -LiteralPath $previous -Destination $live }
        throw
    }
    "ROLLED BACK approved=$($manifest.approved_build) module=$($manifest.module_build) previous=$previous elapsed=$([math]::Round($watch.Elapsed.TotalSeconds,3))"
    'Editor remains closed. Runtime health must be checked after the owner opens it.'
} finally { $lock.Dispose() }
