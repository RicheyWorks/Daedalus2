$D="C:\Users\730ri\projects\bot-team\art\prometheus_island"
function Post($t){ try{Invoke-RestMethod -Method Post http://127.0.0.1:9890/send -ContentType 'application/json' -Body (@{from='prometheus';to='*';type='note';body=@{text=$t}}|ConvertTo-Json -Depth 4)|Out-Null}catch{} }
$last=(Invoke-RestMethod http://127.0.0.1:9890/health).last; $hb=Get-Date; $stop=Get-Date -Hour 20 -Minute 20 -Second 0
$msgs=@("DOING island:Prometheus Island r2 items 500/500: dry-checked prom_turn_r2.py (syntax OK; 48 terrain orientation candidates x 25 heightmap probes); warm capture post-process set (exposure +1, 5200 K). Waiting for my ~19:54 turn.","DOING island:Prometheus Island r2 items 500/500: calls staged in bot-team/art/prometheus_island/calls (11 coats incl. 3 bred children); livestock root actors mapped to coats by label. Turn ~19:54.","DOING island:Prometheus Island r2 items 500/500: still holding for the 19:54 Grok slot; script ready, saves only /Game/Prometheus + PrometheusIsland.","DOING island:Prometheus Island r2 items 500/500: standing by; DaedalusWorld will NOT be saved by me this round (own files only).","DOING island:Prometheus Island r2 items 500/500: standing by for HANDOFF -> prometheus.")
$i=0
while((Get-Date) -lt $stop){
  try{$m=@((Invoke-RestMethod "http://127.0.0.1:9890/log?after=$last&n=200").messages)}catch{$m=@()}; if($m.Count){$last=$m[-1].id}
  foreach($x in ($m | ?{ $_.from -ne 'prometheus' -and $_.type -ne 'ack' -and "$($_.body.text)" -match '(?i)prometheus' -and $_.from -ne 'unreal-team' })){ "#$($x.id) $($x.from)>$($x.to) $(Get-Date -f HH:mm): $($x.body.text)" | Out-File -Append $D\watch2.log }
  if(((Get-Date)-$hb).TotalMinutes -ge 11){ Post $msgs[[Math]::Min($i,$msgs.Count-1)]; $i++; $hb=Get-Date }
  Start-Sleep 20 }
