# Validates Daedalus2 data JSON and item-id references.
$root = Split-Path $PSScriptRoot -Parent
$items = (Get-Content "$root\data\economy\items.json" -Raw | ConvertFrom-Json).items.id
$bad = 0
Get-ChildItem "$root\data" -Recurse -Filter *.json | ForEach-Object {
  try { $null = Get-Content $_.FullName -Raw | ConvertFrom-Json } catch { Write-Host "BAD JSON $($_.FullName)"; $bad++ }
}
$refs = @()
$refs += (Get-Content "$root\data\survival\stats.json" -Raw | ConvertFrom-Json).consumables | % { $_.item }
(Get-Content "$root\data\quests\quests.json" -Raw | ConvertFrom-Json).quests | % { $refs += $_.reward.PSObject.Properties.Name; $refs += ($_.steps | % { $_.item }) }
(Get-Content "$root\data\spawn\ore_nodes.json" -Raw | ConvertFrom-Json).nodes | % { $refs += $_.drops.PSObject.Properties.Name }
$refs | ? { $_ } | Sort -Unique | ? { $items -notcontains $_ } | % { Write-Host "UNKNOWN ITEM $_"; $bad++ }
if ($bad) { exit 1 } else { Write-Host "data OK" }

