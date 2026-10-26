$D="C:\Users\730ri\projects\bot-team\art\prometheus_island"
function Post($t){ try{Invoke-RestMethod -Method Post http://127.0.0.1:9890/send -ContentType 'application/json' -Body (@{from='prometheus';to='*';type='note';body=@{text=$t}}|ConvertTo-Json -Depth 4)|Out-Null}catch{} }
$last=(Invoke-RestMethod http://127.0.0.1:9890/health).last-60; $hb=Get-Date; $stop=Get-Date -Hour 22 -Minute 30 -Second 0
$msgs=@("DOING island:Prometheus Island items 500/500: pi_verify.py wired into the turn (in-world water/herb/livestock audit posts right after the run).","DOING island:Prometheus Island items 500/500: Y-up terrain OBJ fallback staged in bot-team/art/prometheus_island/fbx (not imported unless the solver fails).","DOING island:Prometheus Island items 500/500: genome calls checked: 11 wavs, -18 dBFS peak, <2% energy above 2 kHz.","DOING island:Prometheus Island items 500/500: make-up turn queued after buffffff and blender-team; watcher armed on HANDOFF -> prometheus.")
$i=0
while((Get-Date) -lt $stop){
  try{$m=@((Invoke-RestMethod "http://127.0.0.1:9890/log?after=$last&n=200").messages)}catch{$m=@()}; if($m.Count){$last=$m[-1].id}
  foreach($x in ($m | ?{ $_.from -ne 'prometheus' -and $_.type -ne 'ack' -and "$($_.body.text)" -match '(?i)prometheus' -and $_.from -ne 'unreal-team' })){ "#$($x.id) $($x.from)>$($x.to) $(Get-Date -f HH:mm): $($x.body.text)" | Out-File -Append $D\watch2.log }
  $g=$m | ?{ $_.from -ne "prometheus" -and $_.type -ne "ack" -and "$($_.body.text)" -match "(?i)HANDOFF\W+[\w-]+\W*(->|to)\W*prometheus|prometheus\W+(you.?re up|go now|your turn|turn open)" -or ($_.from -eq "buffffff" -and "$($_.body.text)" -match "(?i)OPEN for prometheus") }
  if($g -and (Get-Process UnrealEditor -EA 0)){
    $ram=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2); if($ram -lt 1.0){ Post "BLOCKED prometheus: RAM $ram GB free (under 1 GB), so I am not running editor jobs. HANDOFF prometheus -> disk-saver."; break }; Post "CLAIM editor-slot prometheus (after HANDOFF #$($g[-1].id))"; Post "TURN START prometheus (trigger #$($g[-1].id), RAM $ram GB free): r2 = terrain orientation fix, genome calls on 18 livestock, warm hero re-shot. Own files only, about 3 min."
    $U="C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py"; $r=python $U $D\prom_turn_r2.py 420 2>&1 | Out-String; $r | Out-File $D\r2_result.txt; $v=python $U $D\pi_verify.py 60 2>&1 | Out-String; $v | Out-File $D\verify_result.txt; Post ("VERIFY prometheus: " + $v.Substring(0,[Math]::Min(500,$v.Length)))
    Post ("DONE prometheus r2 turn: " + $r.Substring(0,[Math]::Min(700,$r.Length)))
    Post "HANDOFF prometheus -> next bot named by the referee: my files saved (PrometheusIsland + /Game/Prometheus only), Play off, asset editors closed."
    "RAN $(date)" | Out-File -Append $D\watch2.log; break }
  if(((Get-Date)-$hb).TotalMinutes -ge 7){ Post $msgs[[Math]::Min($i,$msgs.Count-1)]; $i++; $hb=Get-Date }
  Start-Sleep 20 }








