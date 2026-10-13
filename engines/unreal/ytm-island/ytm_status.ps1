param([string]$Doing="")
$bt="C:\Users\730ri\projects\bot-team"; $e=New-Object Text.UTF8Encoding $false
if($Doing){ [IO.File]::AppendAllText("$bt\link\outbox\youtube-master.jsonl",(@{to="*";type="note";body=@{text=$Doing}}|ConvertTo-Json -Compress)+"`n",$e) }
"now $(Get-Date -Format HH:mm:ss)"
"-- to me:"; Get-Content "$bt\link\inbox\youtube-master.jsonl" -Tail 400 | Select-String '"to": "youtube-master"' | ? {$_.Line -notmatch '"type": "(ack|error)"'} | select -Last 3 | % {$_.Line.Substring(0,[Math]::Min(260,$_.Line.Length))}
"-- editor:"; Get-Content "$bt\link\log.jsonl" -Tail 3000 | Select-String 'HANDOFF|editor is yours|editor-slot' | ? {$_.Line -notmatch '"from": "youtube-master"'} | select -Last 3 | % {$_.Line.Substring(0,[Math]::Min(260,$_.Line.Length))}
"-- ytm queue: " + ((Get-Content "$bt\art\QUEUE.md" | ? {$_ -match '_YTM_'} | % {($_.Split('|')[5].Trim() -split ' ')[0]} | group | % {"$($_.Name)=$($_.Count)"}) -join " ")
