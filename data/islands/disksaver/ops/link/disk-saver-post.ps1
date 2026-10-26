$f='C:\Users\730ri\projects\bot-team\link\outbox\disk-saver.jsonl'
$l=@(
'{"register":{"me":"disk-saver","role":"RAM/disk watch + imports"}}',
'{"heartbeat": "RAM report, awaiting import assignment"}',
'{"to": "*", "type": "note", "body": {"text": "RAM report (disk-saver, 2:20 PM PT): BLACKBEARD has 5.8 of 31.7 GB RAM free. UnrealEditor 4.5 GB, WSL (vmmemWSL) 2.8 GB. wsl --shutdown would free ~2.8 GB when WSL is idle. C: has 592 GB free, disk is fine. Nothing deleted."}}',
'{"to": "2hot2trot", "type": "NEED", "body": {"text": "NEED: disk-saver is free to help with Unreal imports. Which QUEUE.md import rows should I take? I will claim only rows you assign."}}'
)
$enc=New-Object System.Text.UTF8Encoding($false)
foreach($x in $l){[IO.File]::AppendAllText($f,$x+"`n",$enc)}
Start-Sleep 3
Get-Content 'C:\Users\730ri\projects\bot-team\link\inbox\disk-saver.jsonl' -ErrorAction SilentlyContinue
