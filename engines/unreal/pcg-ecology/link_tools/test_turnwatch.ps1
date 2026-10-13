# Replays real link messages through turnwatch.ps1's trigger rules. Expect: 23039, 23793, 23823, 24101 hit; nothing else.
$f='C:\Users\730ri\projects\bot-team\link\inbox\pythagoras.jsonl'
$src = Get-Content "$PSScriptRoot\turnwatch.ps1" -Raw
$pat = [regex]::Matches($src, "'\(\?i\)[^']+'") | % { $_.Value.Trim("'") }
$hits = Get-Content $f | % { try { $m = $_ | ConvertFrom-Json } catch { return }; if ($m.from -eq 'pythagoras') { return }
  $t = [string]$m.body.text; $h = $t.Substring(0, [Math]::Min(60, $t.Length))
  if (($h -match $pat[0] -and $h -match $pat[1]) -or ($m.from -eq 'buffffff' -and ($t -match $pat[2] -or $t -match $pat[3]))) { [int]$m.id } }
$want = 23039, 23793, 23823, 24099, 24101
"patterns: $($pat -join ' | ')"; "hits: $($hits -join ',')"
$miss = $want | ? { $_ -notin $hits }; $extra = $hits | ? { $_ -notin $want }
if ($miss -or $extra) { "FAIL miss=$miss extra=$extra"; exit 1 } else { "PASS" }

