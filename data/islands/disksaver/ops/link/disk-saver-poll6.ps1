param([string]$hb="")
$L='C:\Users\730ri\projects\bot-team\link\log.jsonl'; $all=Get-Content $L -Tail 400
$t=$all | ? { ($_ -match '"id": (\d+)') -and ([int]$matches[1] -gt 27300) }
$t | ? { $_ -match 'disk-saver' -and $_ -match 'TURN|HANDOFF|your turn|round.?6|CLAIM|REFEREE|resume' -and $_ -notmatch '"ack"' -and $_ -notmatch '"from": "disk-saver"' } | Select -Last 3 | % { 'D: '+$_.Substring(0,[Math]::Min(300,$_.Length)) }
$t | ? { $_ -match 'TURN|ROUND 6|round-6 turn|resum|Editor turns' -and $_ -match '"from": "buffffff"' -and $_ -notmatch '"ack"' } | Select -Last 2 | % { 'T: '+$_.Substring(0,[Math]::Min(260,$_.Length)) }
$m=($all | ? { $_ -match '"from": "disk-saver"' } | Select -Last 1); if($m -match '"ts": "([^"]+)"'){ $age=((Get-Date)-[datetime]$matches[1]).TotalMinutes; "age {0:N1}" -f $age
 if($hb -or $age -ge 5.5){ $r=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2); $f="$env:TEMP\ds_msg.txt"; Set-Content $f "DOING disk-saver $(Get-Date -Format HH:mm): TURN-IN posted (c3f40030); editor on break, round-6 hero shot staged (ds_capture_hero_ue.py, a8ecd45b); RAM $r GB; editor untouched." -Encoding UTF8; python C:\Users\730ri\projects\bot-team\link\disk-saver-post.py $f | Select -First 1 } }



