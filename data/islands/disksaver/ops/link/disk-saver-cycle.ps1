param([string]$Tag="",[string]$Msg="")
$d='C:\Users\730ri\projects\bot-team\link'
$st="$d\disk-saver-state.txt"
$out="$d\outbox\disk-saver.jsonl"; $inb="$d\inbox\disk-saver.jsonl"
$enc=New-Object System.Text.UTF8Encoding($false)
$os=Get-CimInstance Win32_OperatingSystem
$free=[math]::Round($os.FreePhysicalMemory/1MB,2)
$ue=(Get-Process UnrealEditor -ErrorAction SilentlyContinue | Measure-Object WorkingSet64 -Sum).Sum/1GB
$ue=[math]::Round($ue,2)
$t=Get-Date -Format 'HH:mm'
"RAM free=$free GB editor=$ue GB at $t"
$hb='{"heartbeat": "RAM watch: '+$free+' GB free at '+$t+' PT"}'
[IO.File]::AppendAllText($out,$hb+"`n",$enc)
if($free -lt 1.5){ $w='{"to": "*", "type": "BLOCKED", "body": {"text": "BLOCKED (URGENT) disk-saver: BLACKBEARD free RAM CRITICAL at '+$free+' GB ('+$t+' PT), UnrealEditor '+$ue+' GB. Save work now; stop launching heavy jobs. Nothing closed or deleted."}}'; [IO.File]::AppendAllText($out,$w+"`n",$enc); "POSTED CRITICAL" }
elseif($free -lt 3){ $w='{"to": "*", "type": "BLOCKED", "body": {"text": "BLOCKED disk-saver: BLACKBEARD free RAM low at '+$free+' GB ('+$t+' PT), UnrealEditor '+$ue+' GB. Avoid new heavy processes."}}'; [IO.File]::AppendAllText($out,$w+"`n",$enc); "POSTED WARN" }
$lines=Get-Content $inb
$prev= if(Test-Path $st){[int](Get-Content $st)}else{3089}
"inbox lines $prev -> $($lines.Count)"
$lines | Select-Object -Skip $prev | Where-Object { $_ -notmatch '"type": "(ack|asset\.added)"' -and ($_ -match '"to": "disk-saver"' -or $_ -match 'disk-saver' -or $_ -match '"to": "*"' -and ($_ -match 'BLOCKED|NEED.*(disk|RAM|memory)|disk-saver|2hot2trot.*(turn|import)')) }
Set-Content $st $lines.Count
if($Tag){ $dl='{"to": "*", "type": "note", "body": {"text": "DONE '+$Tag+' disk-saver: RAM checkpoint '+$t+' PT: '+$free+' GB free, UnrealEditor '+$ue+' GB."}}'; [IO.File]::AppendAllText($out,$dl+"`n",$enc); "posted DONE $Tag" }
if($Msg){ $dl='{"to": "*", "type": "note", "body": {"text": "DOING island:DiskSaver '+$t+' PT: '+$Msg+' RAM '+$free+' GB free, editor '+$ue+' GB."}}'; [IO.File]::AppendAllText($out,$dl+"`n",$enc); "posted status" }
