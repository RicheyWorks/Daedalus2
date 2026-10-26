Start-Sleep 28
$r=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2); "$(Get-Date -Format HH:mm:ss) RAM $r"
Get-Content C:\Users\730ri\projects\bot-team\link\log.jsonl -Tail 50 | Where-Object { $_ -match 'disk-saver|Disk Saver' -and $_ -notmatch '"from": "disk-saver"|"ack"|asset\.' } | Select-Object -Last 2 | % { $_.Substring(0,[Math]::Min(260,$_.Length)) }
