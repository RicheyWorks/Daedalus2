function Post($t){ $b=@{from='prometheus';to='*';type='note';body=@{text=$t}} | ConvertTo-Json -Compress; try{ (Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9890/send -ContentType 'application/json' -Body $b).id }catch{ "POSTFAIL $_" } }
$last=Get-Date; $deadline=(Get-Date).AddMinutes(45)
while($true){
  $r=Invoke-RestMethod 'http://127.0.0.1:9890/pending?me=prometheus'
  $h=$r.messages | ?{ $_.from -match 'buff' -and $_.body.text -match 'HANDOFF' -and [datetime]$_.ts -gt [datetime]'2026-10-13T01:48:07' }
  if($h){ "SAW HANDOFF $($h[-1].ts): $($h[-1].body.text)"; break }
  if(((Get-Date)-$last).TotalMinutes -ge 7){ "doing " + (Post "DOING prometheus $(Get-Date -Format HH:mm): waiting on buffffff HANDOFF; r5 terrain-fix + UE hero capture staged, RAM guard 1GB."); $last=Get-Date }
  if((Get-Date) -gt $deadline){ "TIMEOUT waiting"; exit 2 }
  Start-Sleep 20
}
"claim " + (Post "CLAIM editor-slot prometheus"); "CLAIMED $(Get-Date -Format HH:mm:ss)"
$ram=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2); "RAM $ram GB"
if($ram -lt 1){ Post "BLOCKED prometheus: RAM $ram GB < 1GB guard, skipping r5 fix"; Post "HANDOFF unreal-team"; exit 4 }
Post "DOING prometheus $(Get-Date -Format HH:mm): running prom_fix_terrain_r5.py (RAM $ram GB)" | Out-Null
$out = python C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py "$PSScriptRoot\prom_fix_terrain_r5.py" 240 2>&1 | Out-String
$out
$m=[regex]::Match($out,'(?i)err\w*[^0-9\-]{0,20}(-?[0-9]+\.?[0-9]*)\s*m'); $e= if($m.Success){$m.Groups[1].Value+' m'}else{'see log'}
$k= if($out -match '(?i)revert'){'reverted'}elseif($out -match '(?i)kept|keep'){'kept'}else{'?'}
"done " + (Post "DONE prometheus r5: terrain error $e ($k); items re-grounded; saved PrometheusIsland + /Game/Prometheus only; capture shots/PI_hero_ue_r5.png")
"handoff " + (Post "HANDOFF unreal-team")
