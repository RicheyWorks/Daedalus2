# pythagoras turn watcher: posts CLAIM itself the moment our turn is called, then writes turn.flag.
# Triggers (from anyone but us): a short handoff post "TURN DONE + HANDOFF x -> pythagoras" / "HANDOFF ... pythagoras" in the first 60 chars,
# or a referee post "@pythagoras: your ... turn is OPEN" / "GRANT ... pythagoras". Ignores long DONE recaps that only mention a future handoff.
param([int]$Minutes = 240)
$f='C:\Users\730ri\projects\bot-team\link\inbox\pythagoras.jsonl'; $o='C:\Users\730ri\projects\bot-team\link\outbox\pythagoras.jsonl'
$g='C:\Users\730ri\projects\bot-team\art\NOTES\pythagoras\turn.flag'; $log='C:\Users\730ri\projects\bot-team\art\NOTES\pythagoras\turnwatch.log'
Remove-Item $g -ErrorAction SilentlyContinue
$n=(Get-Content $f).Count; $end=(Get-Date).AddMinutes($Minutes)
while((Get-Date) -lt $end){
  $new=@(Get-Content $f | Select-Object -Skip $n); $n += $new.Count
  foreach($l in $new){
    try { $m = $l | ConvertFrom-Json } catch { continue }
    if($m.from -eq 'pythagoras'){ continue }
    $t = [string]$m.body.text; $head = $t.Substring(0,[Math]::Min(60,$t.Length))
    $go = ($head -match '(?i)HANDOFF' -and $head -match '(?i)pythagoras') -or
          ($m.from -eq 'buffffff' -and $t -match '(?i)@pythagoras:?\s+(\S+\s+){0,4}turn\s+(is\s+)?OPEN\b') -or
          ($m.from -eq 'buffffff' -and $t -match '(?i)(GRANT\W+(to\W+)?@?pythagoras|@pythagoras\b[^.]*\bGRANT)')
    if($go){
      $now=Get-Date -f HH:mm:ss
      Add-Content $o ('{"to":"*","type":"note","body":{"text":"CLAIM pythagoras ' + $now + ' PT: round-2 editor turn (after #' + $m.id + ' from ' + $m.from + '). Running turn_save -> pyth_fix_ue -> pyth_verify_ue -> screenshot -> save_mine -> HANDOFF."}}')
      Set-Content $g ("$now`n#$($m.id) $($m.from): $head")
      Add-Content $log "$now CLAIM posted on #$($m.id)"
      exit
    }
  }
  Start-Sleep 5
}



