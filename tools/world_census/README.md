# world_census

Read-only census of every world, realm and island in Daedalus: asset counts by world, category,
owner bot and status (in Unreal / ready / in progress / Blender-only / rejected), the island grid
with ARK_ORIGINs, contest tracker (water, livestock, herb mechanic), realm list and proposals,
island docs, world registries and Unreal uasset counts.

Outputs: `census.json` (source of truth), `CENSUS.md`, `census.html` (static dashboard), and
optional xlsx sheets (World Inventory, Asset Catalog, Totals, Islands, Realms) added to an
existing workbook without touching its other sheets.

## Run (BLACKBEARD, PowerShell)
```powershell
cd C:\Users\730ri\projects\Daedalus2\tools\world_census
python -m world_census --bot-team C:\Users\730ri\projects\bot-team --repo C:\Users\730ri\projects\Daedalus2 `
  --unreal C:\Unreal\DaedalusRealm --out C:\Users\730ri\projects\bot-team\BOARD\census `
  --xlsx C:\Users\730ri\projects\bot-team\BOARD\MASTER.xlsx
```
Other modes: `--snapshot <dir>` (pre-collected files: QUEUE.md, competition.md, REALMS.md, realms/,
islands/, artfiles.txt, uassets.txt) and `--from-json census.json` (re-render only).
Needs Python 3.8+; `openpyxl` only for `--xlsx`.

## Rules
- Same asset name in queue, Blender files and Unreal = one asset. In Unreal = queue SHIPPED or a mesh uasset.
  Material/texture uassets are counted separately (`unreal_support_files`).
- World/owner: name tag after `Kind_` (BUF, AMF, YTM, Orr, SOL, DS, BBIsle, Realm...), then folder,
  then notes; plain `Kind_Name` = Sky Islands (World Zero); anything else = Unassigned.
- All project knowledge is in `config.py`; reuse elsewhere with `--config my.json`.
