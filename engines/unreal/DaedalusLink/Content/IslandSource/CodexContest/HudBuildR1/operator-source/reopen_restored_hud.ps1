$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$journalPath = Join-Path $taskRoot 'contest-island-production/engines/unreal/DaedalusLink/Content/IslandSource/CodexContest/codex-hud-rejected-rollback.json'
$journal = Get-Content -LiteralPath $journalPath -Raw | ConvertFrom-Json
if ($journal.stage -ne 'five_original_leaves_restored_normal_visible_reopen_pending' -or $journal.reopen_dispatched) { throw 'Restoration incomplete or reopen already dispatched.' }
if (@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe'}).Count -ne 0) { throw 'Existing editor; no duplicate launch.' }
$journal.stage = 'normal_visible_restored_reopen_dispatching'
$journal.reopen_dispatched = $true
$journal | Add-Member -NotePropertyName reopen_requested_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o'))
$journal | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $journalPath -Encoding utf8
$editorProcess = Start-Process -FilePath 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList @('C:\Unreal\DaedalusRealm\DaedalusRealm.uproject','/Game/Daedalus/DaedalusWorld') -PassThru
$journal.stage = 'normal_visible_restored_reopen_dispatched'
$journal | Add-Member -NotePropertyName restored_editor_pid -NotePropertyValue $editorProcess.Id
$journal | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $journalPath -Encoding utf8
[pscustomobject]@{stage=$journal.stage;restored_editor_pid=$editorProcess.Id;normal_visible_launch=$true} | ConvertTo-Json
