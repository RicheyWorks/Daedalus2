"""Read-only workbook reconciliation; emits review Markdown, never changes sources."""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import openpyxl

OUT = Path(__file__).resolve().parent
MASTER = Path('C:/Users/730ri/projects/bot-team/BOARD/MASTER.xlsx')
TRACKER = Path('C:/Users/730ri/projects/bot-team/art/Blender-Boss-Asset-Tracker.xlsx')
UNICORNS = Path('C:/Users/730ri/Documents/Codex/2026-10-13/unicorn-guides/manifest.json')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cell(value):
    return str(value if value is not None else '').replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')


def main():
    hashes = {str(p): sha(p) for p in (MASTER, TRACKER, UNICORNS)}
    master = openpyxl.load_workbook(MASTER, read_only=True, data_only=True)
    tracker = openpyxl.load_workbook(TRACKER, read_only=True, data_only=True)
    rows = list(master['Asset Catalog'].values)
    assets = [dict(zip(rows[0], row), source_row=i) for i, row in enumerate(rows[1:], 2) if row[0]]
    detailed = {}
    for sheet in tracker:
        rows = list(sheet.values)
        if rows and rows[0][0] == 'Asset name':
            for i, row in enumerate(rows[1:], 2):
                if row[0]:
                    assert row[0] not in detailed
                    detailed[row[0]] = dict(zip(rows[0], row), source_sheet=sheet.title, source_row=i)
    ids = {a['name'] for a in assets}
    assert len(ids) == len(assets)
    statuses = Counter(a['status'] for a in assets)
    totals = list(master['Totals'].values)[1]
    assert list(totals[2:]) == [statuses[k] for k in ('in_unreal','ready','in_progress','blender_only','rejected')] + [len(assets)]
    extra = {k:v for k,v in detailed.items() if k not in ids}
    unicorns = json.loads(UNICORNS.read_text(encoding='utf-8'))['assets']
    assert not ids.intersection(a['id'] for a in unicorns)
    matched = sum(a['name'] in detailed for a in assets)
    summary = dict(date='2026-10-13', master_rows=len(assets), master_unique=len(ids),
                   master_statuses=dict(statuses), tracker_rows=len(detailed),
                   tracker_statuses=dict(Counter(d['Status'] for d in detailed.values())),
                   exact_matches=matched, master_without_exact_tracker=len(assets)-matched,
                   tracker_only=list(extra), unicorn_addendum=len(unicorns),
                   accounted_unique_art_ids=len(ids)+len(extra)+len(unicorns),
                   world_counts=dict(Counter(a['world'] for a in assets)),
                   category_counts=dict(Counter(a['category'] for a in assets)),
                   source_sha256=hashes, totals_reconciled=True, workbooks_modified=False)
    (OUT/'catalog-audit.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    lines = ['# Item and asset register', '',
        'Read-only snapshot inspected 2026-10-13. Companion to [Game mechanics](GAME-MECHANICS.md) and [Source reconciliation](SOURCE-RECONCILIATION.md).', '',
        f'Accounts for **{summary["accounted_unique_art_ids"]:,} distinct art IDs**: {len(assets):,} MASTER catalog entries, {len(extra)} tracker-only entries and {len(unicorns)} new unicorn variants. These are asset IDs, not distinct usable items or implemented features.', '',
        '**M** = MASTER.xlsx / Asset Catalog; **T** = Blender-Boss-Asset-Tracker.xlsx. Rows are Excel row numbers. Status text is copied from the snapshot and is not current gameplay certification. Source hashes are in [catalog-audit.json](catalog-audit.json).', '',
        f'{matched:,} MASTER names match an explicit tracker mechanic; {len(assets)-matched:,} do not. “Not in tracker” means no exact-name match in this workbook, not proof that no implementation exists. Realm-specific rules and data must supply those bindings.', '',
        'Legacy source names are preserved for traceability; player-facing terminology follows the mechanics document. Neither source workbook was rewritten.', '']
    worlds = defaultdict(list)
    for asset in assets:
        worlds[asset['world']].append(asset)
    for world, group in sorted(worlds.items()):
        lines += [f'## {world} ({len(group):,} entries)', '', '| Asset ID | Category | Recorded state | Documented mechanic / inputs or drops | Source |', '|---|---|---|---|---|']
        for asset in group:
            detail = detailed.get(asset['name'])
            mechanic = 'Not in tracker; realm binding requires reconciliation'
            ref = f'M row {asset["source_row"]}'
            if detail:
                mechanic = str(detail['Mechanic it serves'] or '')
                if detail['Ingredients/drops']:
                    mechanic += '; '+str(detail['Ingredients/drops'])
                ref += f'; T {detail["source_sheet"]} row {detail["source_row"]}'
            lines.append('| '+' | '.join(cell(v) for v in [asset['name'], asset['category'], asset['status'], mechanic, ref])+' |')
        lines.append('')
    lines += ['## Tracker-only entries (not in MASTER snapshot)', '', '| Asset ID | Mechanic | Tracker status | Source |', '|---|---|---|---|']
    for name, d in extra.items():
        lines.append('| '+' | '.join(cell(v) for v in [name,d['Mechanic it serves'],d['Status'],f'T {d["source_sheet"]} row {d["source_row"]}'])+' |')
    lines += ['', '## Unicorn art addendum (not yet in either workbook)', '',
              'Art validation is complete; guidance, defense, fear and reward gameplay are pending. Sex/group/alpha assignments are content metadata, not anatomical or AI proof. See Game Mechanics M09–M10.', '',
              '| Asset ID | Palette | Sex | Intended burning-bull response | Asset state |', '|---|---|---|---|---|']
    for asset in unicorns:
        lines.append('| '+' | '.join(cell(v) for v in [asset['id'],asset['family'],asset['sex'],asset['burning_bull_response'],'Validated static GLB; runtime pending'])+' |')
    lines += ['', '## Workbook coverage boundary', '',
              'MASTER’s Asset Catalog was enumerated in full; World Inventory and Totals are rollups and were not counted again. Tracker category sheets were enumerated in full; Summary is a rollup. Its Uncatalogued sheet contains 15 separately listed saved scene/test files, not item definitions; these are not silently added to the art-ID total. The working economy’s 29 logical item IDs and realm rules are separate gameplay namespaces, discussed in Source Reconciliation, not added to a mesh count.', '']
    (OUT/'ITEM-REGISTER.md').write_text('\n'.join(lines), encoding='utf-8')
    master.close()
    tracker.close()
    assert all(sha(Path(path)) == checksum for path, checksum in hashes.items()), 'Source changed during audit'
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
