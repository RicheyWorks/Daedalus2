$f='C:\Users\730ri\projects\bot-team\link\inbox\pythagoras.jsonl'
$src = Get-Content "$PSScriptRoot\turnwatch.ps1" -Raw
$i = $src.IndexOf('$go = '); $j = $src.IndexOf('if($go)'); $expr = $src.Substring($i + 6, $j - $i - 6)
$sb = [scriptblock]::Create($expr)
$hits = Get-Content $f | % { try { $m = $_ | ConvertFrom-Json } catch { return }; if ($m.from -eq 'pythagoras') { return }
  $t = [string]$m.body.text; $head = $t.Substring(0, [Math]::Min(60, $t.Length)); if (& $sb) { [int]$m.id } }
$want = 23039, 23793, 23823, 24099, 24101, 24385   # 24385 = round-3 hephaestus HANDOFF (true)
"hits: $($hits -join ',')"; $miss = $want | ? { $_ -notin $hits }; $extra = $hits | ? { $_ -notin $want }
if (24156 -in $hits) { "FAIL recap 24156" ; exit 1 }
if ($miss -or $extra) { "FAIL miss=$miss extra=$extra"; exit 1 } else { "PASS" }

