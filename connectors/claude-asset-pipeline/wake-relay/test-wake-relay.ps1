# SPDX-License-Identifier: MIT
# Offline route tests for wake-relay.ps1 (uses -DryRun; nothing is posted, no real keys).
$ErrorActionPreference='Stop'
$here=$PSScriptRoot; $relay=Join-Path $here 'wake-relay.ps1'; $bots=Join-Path $here 'wake-bots.json'
$tmp=Join-Path ([IO.Path]::GetTempPath()) ("wake-relay-test-"+[guid]::NewGuid().ToString('N')); New-Item -ItemType Directory $tmp | Out-Null
$fail=0
function Check($name,$ok){ if($ok){Write-Output "PASS $name"}else{Write-Output "FAIL $name"; $script:fail++} }
$lines=@(
  '{"id":1,"ts":"t1","from":"pootscoot-coordination","to":"2hot2trot","type":"probe","topic":"wake","reply_to":10,"body":{"text":"to 2hot","request_id":"req-2hot"}}',
  '{"id":2,"ts":"t2","from":"pootscoot-coordination","to":"blender-team","type":"probe","topic":"wake","reply_to":11,"body":{"text":"to blender","request_id":"req-blender"}}',
  '{"id":3,"ts":"t3","from":"pootscoot-coordination","to":"oddsreaper","type":"probe","body":{"text":"to unbound"}}',
  '{"id":4,"ts":"t4","from":"pootscoot-coordination","to":"unreal-team","type":"note","body":{"text":"not a wake bot"}}',
  '{"id":5,"ts":"t5","from":"buffffff","to":"blender-team","type":"note","body":{"text":"grok to grok, relayed"}}',
  '{"id":6,"ts":"t6","from":"codex-play-guard","to":"2hot2trot-linktest","type":"note","body":"string body"}',
  '{"id":7,"ts":"t7","from":"codex-play-guard","to":"pythagoras","type":"note","body":{"text":"route to missing override"}}',
  '{"id":8,"ts":"t8","from":"prometheus","to":"prometheus","type":"note","body":{"text":"self, skipped"}}',
  '{"id":9,"ts":"t9","from":"2hot2trot-linktest","to":"2hot2trot","type":"note","body":{"text":"linktest to itself, skipped"}}',
  '{"id":10,"ts":"t10","from":"pootscoot-coordination","to":"*","type":"note","body":{"text":"broadcast, skipped"}}'
)
[IO.File]::WriteAllLines((Join-Path $tmp 'log.jsonl'),[string[]]$lines)
function Run($cfg){ [IO.File]::WriteAllText((Join-Path $tmp 'relay-webhook.json'),$cfg); $o=& powershell -NoProfile -ExecutionPolicy Bypass -File $relay -LinkFolder $tmp -BotsPath $bots -DryRun | Select-Object -Last 1; $o | ConvertFrom-Json }
$t='{"url":"https://example.invalid/T","key":"TEST","header":"Authorization","prefix":"Bearer "}'
$strict='{"url":"https://example.invalid/default","key":"TEST","header":"Authorization","prefix":"Bearer ","overrides":{"2hot2trot":'+$t+'},"routes":{"2hot2trot*":"2hot2trot","blender-team":"default","pythagoras":"nosuch"}}'
$r=Run $strict
Check 'direct wake-bot hits from any sender, self/linktest/broadcast skipped (1,2,3,5,6,7)' ((@($r.messages|%{$_.id}) -join ',') -eq '1,2,3,5,6,7')
Check '2hot2trot routes to its own webhook' ((@($r.routes.'2hot2trot') -join ',') -eq '1,6')
Check 'blender-team routes to default dispatcher, grok-to-grok included' ((@($r.routes.default) -join ',') -eq '2,5')
Check 'unbound recipient and missing override stay PENDING' ((@($r.pending) -join ',') -eq '3,7')
Check 'unbound never falls through to default' (-not (@($r.routes.default) -contains 3))
$m2=@($r.messages|?{$_.id -eq 2})[0]
Check 'envelope keeps request_id/topic/reply_to/pointer' ($m2.request_id -eq 'req-blender' -and $m2.topic -eq 'wake' -and $m2.reply_to -eq 11 -and $m2.pointer -eq 'log.jsonl#id=2')
Check 'string body is carried as text' ((@($r.messages|?{$_.id -eq 6})[0]).text -eq 'string body')
$legacy='{"url":"https://example.invalid/default","key":"TEST","header":"Authorization","prefix":"Bearer ","overrides":{"2hot2trot":'+$t+'}}'
$r=Run $legacy
Check 'legacy config without routes: override then default' ((@($r.routes.'2hot2trot') -join ',') -eq '1' -and (@($r.routes.default) -join ',') -eq '2,3,5,6,7')
Remove-Item -Recurse -Force $tmp
if($fail){Write-Output "FAILED $fail"; exit 1}else{Write-Output 'ALL PASS'}
