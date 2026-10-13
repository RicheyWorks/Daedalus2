$q='C:\Users\730ri\projects\bot-team\art\QUEUE.md'
$rows=Select-String $q -Pattern '^\| \d+ \| [A-Za-z]+_DS_' | ForEach-Object Line
"DS rows: $($rows.Count)"
$rows | ForEach-Object { ($_ -split '\|')[5].Trim() -replace '\(.*','' -replace ':.*','' } | Group-Object | ForEach-Object { "  $($_.Count) $($_.Name)" }
foreach($a in 'Bld_DS_Coop','Mob_DS_ByteHen','Prop_DS_Herb_CacheLeaf_S1','Prop_DS_Water_Well_V0','Prop_DS_Tree_10','Mob_DS_CacheCow'){ $r=$rows | Where-Object { $_ -match "\| $a \|" }; if($r){ $c=$r -split '\|'; "$a -> $($c[5].Trim())" } else { "$a -> no row" } }
$j=@(); foreach($b in 'batch1b','batch2'){ $j+= (Get-Content "C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\$b.json" -Raw | ConvertFrom-Json) }
$bad=0; foreach($r in $rows){ $c=$r -split '\|'; $n=$c[2].Trim(); $st=$c[5].Trim(); if($st -match 'SHIPPED \((\d+) tris'){ $e=($j | Where-Object asset -eq $n | Select-Object -First 1).tris; if($e -and [int]$matches[1] -ne $e){ $bad++; if($bad -le 5){"MISMATCH $n got $($matches[1]) expected $e"} } } }
"tri mismatches: $bad"
