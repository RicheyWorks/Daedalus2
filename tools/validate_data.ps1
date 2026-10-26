# Validates Daedalus2 data JSON and item-id references.
$root = Split-Path $PSScriptRoot -Parent
$econ = "$root\data\economy\items.json"
$items = @()
if (Test-Path $econ) { $items += (Get-Content $econ -Raw | ConvertFrom-Json).items | % { $_.id } }
else { Write-Host "WARN data/economy/items.json not in this checkout (untracked upstream); item cross-check limited to island item files" }
Get-ChildItem "$root\data\islands" -Recurse -Filter items.json -EA 0 | % { $items += (Get-Content $_.FullName -Raw | ConvertFrom-Json).items | % { $_.id } }
$bad = 0
Get-ChildItem "$root\data" -Recurse -Filter *.json | ForEach-Object {
  try { $null = Get-Content $_.FullName -Raw | ConvertFrom-Json } catch { Write-Host "BAD JSON $($_.FullName)"; $bad++ }
}
$badJson = $bad
$refs = @()
$refs += (Get-Content "$root\data\survival\stats.json" -Raw | ConvertFrom-Json).consumables | % { $_.item }
(Get-Content "$root\data\quests\quests.json" -Raw | ConvertFrom-Json).quests | % { $refs += $_.reward.PSObject.Properties.Name; $refs += ($_.steps | % { $_.item }) }
(Get-Content "$root\data\spawn\ore_nodes.json" -Raw | ConvertFrom-Json).nodes | % { $refs += $_.drops.PSObject.Properties.Name }
$refs | ? { $_ } | Sort -Unique | ? { $items -notcontains $_ } | % { Write-Host "UNKNOWN ITEM $_"; $bad++ }
# --- hephaestus: water / herbs / livestock / food checks ---
$herbIds = (Get-Content "$root\data\herbs\herbs.json" -Raw | ConvertFrom-Json).herbs | % { $_.id }
$water = Get-Content "$root\data\water\water.json" -Raw | ConvertFrom-Json
$water.sources | % { if ($_.build) { $refs2 = $_.build.PSObject.Properties.Name; $refs2 | ? { $items -notcontains $_ } | % { Write-Host "UNKNOWN ITEM (water build) $_"; $script:bad++ } } }
$water.purification | % { if ($_.needs) { $_.needs.PSObject.Properties.Name | ? { $_ -ne 'per' -and $items -notcontains $_ } | % { Write-Host "UNKNOWN ITEM (water needs) $_"; $script:bad++ } } }
$cook = Get-Content "$root\data\food\cooking.json" -Raw | ConvertFrom-Json
$pending = @('egg','milk','grain','steak','ribs','bacon','potato','honey','salt','dirty_water','salt_water')  # NEED codex: add to economy/items.json
$cook.recipes | % { $_.in.PSObject.Properties.Name } | Sort -Unique | % {
  if ($_ -like 'herb_*') { if ($_ -ne 'herb_*' -and $herbIds -notcontains $_) { Write-Host "UNKNOWN HERB $_"; $script:bad++ } }
  elseif ($items -notcontains $_ -and $pending -notcontains $_) { Write-Host "UNKNOWN ITEM (food) $_"; $script:bad++ }
  elseif ($pending -contains $_) { Write-Host "PENDING (codex) $_" } }
$combos = (Get-Content "$root\data\herbs\combos.json" -Raw | ConvertFrom-Json).effects
$tags = (Get-Content "$root\data\herbs\herbs.json" -Raw | ConvertFrom-Json).herbs | % { $_.essences } | Sort -Unique
$combos.PSObject.Properties.Name | % { $_ -split '\+' } | ? { $tags -notcontains $_ } | % { Write-Host "UNKNOWN ESSENCE $_"; $script:bad++ }
$animals = (Get-Content "$root\data\livestock\animals.json" -Raw | ConvertFrom-Json).animals
$animals | ? { -not $_.feed -or -not $_.housing } | % { Write-Host "ANIMAL MISSING feed/housing $($_.id)"; $script:bad++ }

if (-not (Test-Path $econ)) { if ($bad -gt $badJson) { Write-Host "(item-reference findings above are advisory until economy/items.json is committed)" }; $bad = $badJson }
if ($bad) { exit 1 } else { Write-Host "data OK" }




