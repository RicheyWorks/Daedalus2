$D="C:\Users\730ri\projects\bot-team\art\prometheus_island"; $U="C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py"
function Post($t,$to='*'){ try{Invoke-RestMethod -Method Post http://127.0.0.1:9890/send -ContentType 'application/json' -Body (@{from='prometheus';to=$to;type='note';body=@{text=$t}}|ConvertTo-Json -Depth 4)|Out-Null}catch{} }
$last=(Invoke-RestMethod http://127.0.0.1:9890/health).last; $hb=Get-Date; $stop=(Get-Date).AddMinutes(40)
while((Get-Date) -lt $stop){
  try{$m=@((Invoke-RestMethod "http://127.0.0.1:9890/log?after=$last&n=200").messages)}catch{$m=@()}; if($m.Count){$last=$m[-1].id}
  $g=$m | ?{ $_.from -ne 'prometheus' -and $_.type -ne 'ack' -and $_.body.text -match '(?i)(HANDOFF\W+(\w+\W+){0,3}(->|to)\W*prometheus|prometheus\W+(you.?re up|go now|granted|your (turn|slot))|editor-slot\W+\w*\W*prometheus\W+(go|now|granted))' }
  foreach($x in $g){ "TRIGGER #$($x.id) $($x.from): $($x.body.text)" | Out-File -Append $D\watch.log }
  if($g -and (Get-Process UnrealEditor -EA 0)){
    Post "CLAIM editor-slot grok prometheus (trigger #$($g[-1].id)): one-shot prom_turn.py: Wild Biomes + livestock in pens + scene-capture shots, saves own packages only."
    $r = python $U $D\prom_turn.py 600 2>&1 | Out-String; $r | Out-File $D\turn_result.txt; "RAN $(date)" | Out-File -Append $D\watch.log
    Post ("DONE prometheus turn: " + $r.Substring(0,[Math]::Min(600,$r.Length)))
    Post "HANDOFF prometheus -> disk-saver: Play untouched/off, my packages saved, asset editors closed. Next: youtube-master, then hephaestus."
    break }
  if(((Get-Date)-$hb).TotalMinutes -ge 13){ Post "DOING island:Prometheus Island items 500/500 UE (446 placed). Since last: livestock fixed to real multipart mob paths (/Game/Daedalus/Art/Mob/Mob_X/Mob_X/StaticMeshes/*, Cow/Sheep/Goat/Pig/Donkey/Chicken x3 with coat mats); one-shot prom_turn.py staged; waiting for HANDOFF to prometheus + editor up."; $hb=Get-Date; "hb $(date)" | Out-File -Append $D\watch.log }
  Start-Sleep 20 }
"END $(date)" | Out-File -Append $D\watch.log

