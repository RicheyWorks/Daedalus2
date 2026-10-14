# SPDX-License-Identifier: MIT
# Filesystem-only fixture: process probes are replaced, never operates on an installed plugin.
$ErrorActionPreference='Stop'
function Get-Process { param($Name,$ErrorAction) @() }
function Get-CimInstance { param($ClassName,$Filter) @() }
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('daedalus-recovery-fixture-'+[guid]::NewGuid().ToString('N'))
$project = Join-Path $fixture 'Fixture.uproject'
$binary = Join-Path $fixture 'Plugins\DaedalusLink\Binaries\Win64'
$tool = Join-Path $PSScriptRoot '..\plugin-recovery.ps1'
New-Item -ItemType Directory -Path $binary -Force | Out-Null
[IO.File]::WriteAllText($project,'{}')
[IO.File]::WriteAllText((Join-Path $binary 'UnrealEditor-DaedalusLink.dll'),'known-good-fixture')
[IO.File]::WriteAllText((Join-Path $binary 'UnrealEditor.modules'),'{"BuildId":"fixture-engine","Modules":{"DaedalusLink":"UnrealEditor-DaedalusLink.dll"}}')
& $tool -Project $project -SaveGreen -GreenBuildId fixture-reviewed
[IO.File]::WriteAllText((Join-Path $binary 'UnrealEditor-DaedalusLink.dll'),'broken-fixture')
& $tool -Project $project -Rollback
if ([IO.File]::ReadAllText((Join-Path $binary 'UnrealEditor-DaedalusLink.dll')) -cne 'known-good-fixture') { throw 'Good binary was not restored' }
$retained = @(Get-ChildItem -LiteralPath (Split-Path $binary) -Directory -Filter 'Win64-before-rollback-*')
if ($retained.Count -ne 1 -or [IO.File]::ReadAllText((Join-Path $retained[0].FullName 'UnrealEditor-DaedalusLink.dll')) -cne 'broken-fixture') { throw 'Replaced binary not retained' }
$saved = Get-ChildItem -LiteralPath (Join-Path $fixture 'Saved\DaedalusPluginRecovery') -Directory -Filter 'green-*' | Select-Object -First 1
[IO.File]::WriteAllText((Join-Path $saved.FullName 'Win64\UnrealEditor-DaedalusLink.dll'),'tampered-snapshot')
$refused=$false
try { & $tool -Project $project -Rollback } catch { $refused=$_.Exception.Message -like '*identity mismatch*' }
if (-not $refused) { throw 'Tampered snapshot accepted' }
if ([IO.File]::ReadAllText((Join-Path $binary 'UnrealEditor-DaedalusLink.dll')) -cne 'known-good-fixture') { throw 'Refusal altered installed fixture' }
"PASS native filesystem restore, preserved previous files, tamper refusal; fixture=$fixture"
