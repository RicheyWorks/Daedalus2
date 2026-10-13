# pythagoras heartbeat: every 9 min append a DOING line with the current step (step.txt) to the link outbox.
# Holds a keep-awake request (ES_SYSTEM_REQUIRED, this process only) so idle sleep does not freeze it. Ends after $Minutes.
param([int]$Minutes = 240)
Add-Type -Namespace PyHb -Name K -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[void][PyHb.K]::SetThreadExecutionState([uint32]0x80000001)   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
$o = 'C:\Users\730ri\projects\bot-team\link\outbox\pythagoras.jsonl'; $s = 'C:\Users\730ri\projects\bot-team\art\NOTES\pythagoras\step.txt'
$end = (Get-Date).AddMinutes($Minutes)
while ((Get-Date) -lt $end) {
  Start-Sleep 540
  $t = (Get-Content $s -Raw -ErrorAction SilentlyContinue).Trim() -replace '"', "'"
  Add-Content $o ('{"to":"*","type":"note","body":{"text":"DOING pythagoras ' + (Get-Date -f HH:mm) + ': ' + $t + '"}}')
}
[void][PyHb.K]::SetThreadExecutionState([uint32]0x80000000)
