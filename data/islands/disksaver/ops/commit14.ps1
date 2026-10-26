$r='C:\Users\730ri\projects\Daedalus2'; $src='C:\Users\730ri\projects\bot-team\art\NOTES\disksaver'; $dst="$r\data\islands\disksaver"
New-Item -ItemType Directory -Force "$dst\glb" | Out-Null
foreach($f in 'ISLAND.md','ds_items.py','ds_items2.py','ds_food_fix.py','ds_island_ue.py','run_island.ps1','ds_island_fix_ue.py','run_island_fix.ps1','ds_save_ue.py','ds_lab_ue.py','ds_layout.png','layout.py','ds_island_fix_light_ue.py','run_island_fix_light.ps1','verify.ps1','ds_ue_send.py','batch1b.json','batch2.json','batch1c_food.json'){ Copy-Item "$src\$f" $dst -Force }
Copy-Item "$src\glb\*.glb" "$dst\glb" -Force
$items=@(); foreach($b in 'batch1b','batch2'){ $items+= (Get-Content "$src\$b.json" -Raw | ConvertFrom-Json) }
$m=@{island='DiskSaver'; bot='disk-saver'; origin=@(4000000,4000000,0); count=$items.Count; note='.blend sources (~1 GB, one per item) stay in bot-team\art\<Kind>\<Asset>.blend; too big for git without LFS. glb exports are in glb/.'; items=$items}
$m | ConvertTo-Json -Depth 4 | Set-Content "$dst\manifest.json" -Encoding UTF8
cd $r
git add -- data/islands/disksaver
git diff --cached --name-only | Measure-Object | ForEach-Object { "staged files: $($_.Count)" }
git diff --cached --name-only | Where-Object { $_ -notlike 'data/islands/disksaver/*' }
git commit -q -m "disksaver: layout map ds_layout.png from stubbed placement run" -- data/islands/disksaver
git pull --rebase --autostash -q
git push -q origin HEAD:main
git log -1 --format=%H
git status --short | Measure-Object | ForEach-Object { "other uncommitted: $($_.Count)" }
