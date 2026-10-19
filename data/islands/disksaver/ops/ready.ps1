$q='C:\Users\730ri\projects\bot-team\art\QUEUE.md'
$names=(Get-Content 'C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\batch1b.json' -Raw | ConvertFrom-Json) | ForEach-Object { $_.asset }
$raw=[IO.File]::ReadAllText($q)
$n=0
foreach($a in $names){
  $pat='(?m)^(\| \d+ \| '+[regex]::Escape($a)+' \| [^|]*\| [^|]*\| )[^|]*\| [^|\r\n]*\|'
  $new=[regex]::Replace($raw,$pat,{ param($m) $script:n++; $m.Groups[1].Value+'READY | disk-saver re-ship: real mesh now in art\'+($a.Split('_')[0])+'\'+$a+'.blend (first ship was the wrong live-scene mesh) |' })
  $raw=$new
}
$enc=New-Object System.Text.UTF8Encoding($false)
Copy-Item $q 'C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\QUEUE.before-ready.md' -Force
[IO.File]::WriteAllText($q,$raw,$enc)
"rows set READY: $n"
