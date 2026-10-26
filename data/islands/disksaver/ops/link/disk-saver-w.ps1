param([string]$Msg='')
$r=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2); "RAM $r GB at $(Get-Date -Format HH:mm)"
if($Msg){ $f="$env:TEMP\ds_msg.txt"; Set-Content $f ($Msg -replace 'RAMX',"$r GB") -Encoding UTF8; python C:\Users\730ri\projects\bot-team\link\disk-saver-post.py $f }
Select-String C:\Users\730ri\projects\bot-team\link\log.jsonl -Pattern 'HANDOFF|TURN START|TURN DONE|REFEREE 7|REFEREE 8|disk-saver' | Where-Object { $_.Line -notmatch '"ack"' } | Select-Object -Last 5 | ForEach-Object { $_.Line.Substring(0,[Math]::Min(260,$_.Line.Length)) }
