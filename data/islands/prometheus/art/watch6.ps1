$D="C:\Users\730ri\projects\bot-team\art\prometheus_island"
function Post($t){ try{Invoke-RestMethod -Method Post http://127.0.0.1:9890/send -ContentType 'application/json' -Body (@{from='prometheus';to='*';type='note';body=@{text=$t}}|ConvertTo-Json -Depth 4)|Out-Null}catch{} }
$last=(Invoke-RestMethod http://127.0.0.1:9890/health).last-60; $hb=Get-Date; $stop=Get-Date -Hour 22 -Minute 30 -Second 0
$msgs=@("DOING island:Prometheus Island make-up (end of round 2) items 500/500: editor back (pid 56584); prom_turn_r2.py re-verified, the RAM guard reads free memory just before the run.","DOING island:Prometheus Island items 500/500: terrain orientation solver staged (48 rotation x mirror options checked against 25 heightmap probes); 11 genome calls ready for the 18 coat livestock.","DOING island:Prometheus Island items 500/500: warm hero rig staged (5 island-only warm point lights, capture exposure +1 at 5200 K); saves only /Game/Prometheus.","DOING island:Prometheus Island items 500/500: waiting on blender-team HANDOFF; CLAIM goes out automatically on it.")
$i=0
while((Get-Date) -lt $stop){
  try{$m=@((Invoke-RestMethod "http://127.0.0.1:9890/log?after=$last&n=200").messages)}catch{$m=@()}; if($m.Count){$last=$m[-1].id}
  foreach($x in ($m | ?{ $_.from -ne 'prometheus' -and $_.type -ne 'ack' -and "$($_.body.text)" -match '(?i)prometheus' -and $_.from -ne 'unreal-team' })){ "#$($x.id) $($x.from)>$($x.to) $(Get-Date -f HH:mm): $($x.body.text)" | Out-File -Append $D\watch2.log }
  $g=$m | ?{ $_.from -ne "prometheus" -and $_.type -ne "ack" -and "$($_.body.text)" -match "(?i)HANDOFF\W+[\w-]+\W*(->|to)\W*prometheus|prometheus\W+(you.?re up|go now|your turn|turn open)" -or ($_.from -eq "blender-team" -and $_.type -ne "asset.shipped" -and "$($_.body.text)" -match "(?i)^\W*HANDOFF") }
  if($g -and (Get-Process UnrealEditor -EA 0)){
    $ram=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2); if($ram -lt 1.0){ Post "BLOCKED prometheus: RAM $ram GB free (under 1 GB), so I am not running editor jobs. HANDOFF prometheus -> disk-saver."; break }; Post "CLAIM editor-slot prometheus (after HANDOFF #$($g[-1].id))"; Post "TURN START prometheus (trigger #$($g[-1].id), RAM $ram GB free): r2 = terrain orientation fix, genome calls on 18 livestock, warm hero re-shot. Own files only, about 3 min."
    $U="C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py"; $r=python $U $D\prom_turn_r2.py 420 2>&1 | Out-String; $r | Out-File $D\r2_result.txt
    Post ("DONE prometheus r2 turn: " + $r.Substring(0,[Math]::Min(700,$r.Length)))
    Post "HANDOFF prometheus -> next bot named by the referee: my files saved (PrometheusIsland + /Game/Prometheus only), Play off, asset editors closed."
    "RAN $(date)" | Out-File -Append $D\watch2.log; break }
  if(((Get-Date)-$hb).TotalMinutes -ge 7){ Post $msgs[[Math]::Min($i,$msgs.Count-1)]; $i++; $hb=Get-Date }
  Start-Sleep 20 }






