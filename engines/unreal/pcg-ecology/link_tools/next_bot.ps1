# HANDOFF recipient: only a referee line naming the bot ON DECK *after pythagoras*, posted after our turn call (turn.flag #id).
# Otherwise "next bot (referee to call)" - never empty, never a stale on-deck name (round-4 bug).
param([string]$Inbox = 'C:\Users\730ri\projects\bot-team\link\inbox\pythagoras.jsonl', [int]$Tail = 800, [int]$SinceId = -1)
if ($SinceId -lt 0) { $SinceId = 0; if (Test-Path "$PSScriptRoot\turn.flag") { $x = [regex]::Match((Get-Content "$PSScriptRoot\turn.flag" -Raw), '#(\d+)'); if ($x.Success) { $SinceId = [int]$x.Groups[1].Value } } }
$who = $null
foreach ($l in (Get-Content $Inbox -Tail $Tail)) {
  try { $m = $l | ConvertFrom-Json } catch { continue }
  if ($m.from -ne 'buffffff' -or [int]$m.id -lt $SinceId) { continue }
  $r = [regex]::Match([string]$m.body.text, '(?i)@([\w-]+):?\s+you are ON DECK[^.]*\bafter pythagoras\b')
  if ($r.Success -and $r.Groups[1].Value -ne 'pythagoras') { $who = $r.Groups[1].Value }
}
if ($who) { $who } else { 'next bot (referee to call)' }
