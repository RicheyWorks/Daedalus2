param([string]$After)
$L="C:\Users\730ri\projects\bot-team\link\log.jsonl"; $end=(Get-Date).AddMinutes(11.5); $got=$null
while((Get-Date) -lt $end -and -not $got){ Get-Content $L -Tail 400 | % { try{$_|ConvertFrom-Json}catch{} } | ? { $_.ts -gt $After -and (($_.from -eq 'disk-saver' -and ($_.type -eq 'HANDOFF' -or $_.body.text -match '^\s*HANDOFF')) -or ($_.from -in 'buffffff','2hot2trot' -and $_.body.text -match 'youtube-master' -and $_.body.text -match 'GRANT|your turn|editor is yours')) } | select -Last 1 | % {$got=$_}; if(-not $got){Start-Sleep 8} }
"t=$(Get-Date -Format HH:mm:ss)"; if($got){"GOT $($got.ts) $($got.from): $($got.body.text)"} else {"none"; Get-Content $L -Tail 600 | % { try{$_|ConvertFrom-Json}catch{} } | ? { $_.ts -gt $After -and $_.from -in 'buffffff','prometheus','disk-saver','oddsreaper' -and $_.body.text } | select -Last 3 | % {"$($_.ts) $($_.from): $($_.body.text.Substring(0,[Math]::Min(220,$_.body.text.Length)))"}}



