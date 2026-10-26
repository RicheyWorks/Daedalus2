$f='C:\Users\730ri\projects\bot-team\link\inbox\disk-saver.jsonl'
$start=(Get-Content $f).Count
for($i=0;$i -lt 40;$i++){
  $new = Get-Content $f | Select-Object -Skip $start
  $hit = $new | Where-Object { $_ -match '"from": "2hot2trot"' -and $_ -notmatch '"type": "ack"' }
  if($hit){ $hit; break }
  Start-Sleep 20
}
'--- new lines mentioning disk-saver:'
Get-Content $f | Select-Object -Skip $start | Where-Object { $_ -match 'disk-saver' -and $_ -notmatch '"type": "ack"' }
