# pythagoras editor-turn runner (run ONLY after CLAIM on our granted turn). Sequence: turn_save -> pyth_fix_ue -> pyth_verify_ue
# -> pyth_succession_ue -> screenshot -> save_mine; posts DOING between steps; writes turn_result.json. HANDOFF is posted by the caller.
$ErrorActionPreference = 'Continue'; Set-Location (Split-Path $PSScriptRoot)
$o = 'C:\Users\730ri\projects\bot-team\link\outbox\pythagoras.jsonl'; $res = [ordered]@{}
# preflight: every UE script that imports a local helper must put this folder on sys.path (bridge exec has no __file__ dir)
foreach ($s in 'pyth_fix_ue.py','pyth_verify_ue.py','pyth_succession_ue.py') { $t = Get-Content $s -Raw
  if ($t -match 'import\s+(pyth_groundfit|succession_metrics)' -and $t -notmatch 'sys\.path\.insert\(0, r"C:\\Users\\730ri\\projects\\Daedalus2-pcg-ecology') { throw "preflight: $s missing sys.path insert" } }
function Post($t) { Add-Content $o (@{to='*';type='note';body=@{text=('DOING pythagoras ' + (Get-Date -f HH:mm:ss) + ' PT: ' + $t)}} | ConvertTo-Json -Compress -Depth 4) }
function Ue($s, $to) { $r = python ue_send.py $s $to 2>&1 | Out-String; try { $j = $r | ConvertFrom-Json; if ($j.status -ne "ok") { "ERROR: " + $j.message } else { $j.result.result } } catch { $r.Trim() } }
$res.turn_save = Ue 'turn_save.py' 120; Post 'turn_save done, running pyth_fix_ue'
$res.fix = Ue 'pyth_fix_ue.py' 600; Post ('fix done: ' + (($res.fix | ConvertTo-Json -Compress -Depth 3) -replace '"', "'"))
$res.lighting = Ue 'pyth_lighting_ue.py' 60
$res.verify = Ue 'pyth_verify_ue.py' 180
$res.succession = Ue 'pyth_succession_ue.py' 120
$res.quest = Ue 'pyth_quest_ue.py' 120
$w = 'C:\Users\730ri\projects\D2-build\connectors\claude-unreal-connector\extension\server\win.ps1'
$r = & $w -Op list 2>&1 | Out-String; $m = [regex]::Match($r, '[A-Za-z0-9+/]{5000,}={0,2}')
if ($m.Success) { [IO.File]::WriteAllBytes('C:\Users\730ri\pyth_island_turn.png', [Convert]::FromBase64String($m.Value)); $res.screenshot = 'C:\Users\730ri\pyth_island_turn.png' }
$res.save_mine = Ue 'save_mine.py' 120
$res | ConvertTo-Json -Depth 6 | Set-Content turn_result.json -Encoding utf8; $res.next = & powershell -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\730ri\projects\bot-team\art\NOTES\pythagoras\next_bot.ps1'
$res | ConvertTo-Json -Depth 6 | Set-Content turn_result.json -Encoding utf8
'RUNNER_DONE'






