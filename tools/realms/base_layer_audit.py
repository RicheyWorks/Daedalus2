"""Read-only source/manifest census for the realm base-layer handoff. Never mints or edits worlds."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
p.add_argument('--layout',type=Path)
a=p.parse_args();repo=Path(__file__).resolve().parents[2]
sources={}
def read(relative):
    path=repo/relative;data=path.read_bytes();sources[relative]=hashlib.sha256(data).hexdigest()
    return data.decode('utf-8-sig')

art={}
for realm in ('portal','gallery','parcels','bricks','labyrinth'):
    rows=json.loads(read('data/art/'+realm+'/production-manifest.json'))
    art[realm]={'manifest_records':len(rows),'export_status':dict(Counter(row.get('export','unspecified') for row in rows)),
                'file_groups':dict(Counter(row['file'].split('/')[0] for row in rows)),
                'kinds':dict(Counter(row.get('kind','unspecified') for row in rows)),
                'counted_roles':sum(row.get('role_count',0) for row in rows)}
ocean=json.loads(read('data/art/ocean/manifest.json'))
art['ocean']={'manifest_records':len(ocean['assets']),'asset_ids':[row['id'] for row in ocean['assets']],
              'triangles':sum(row['triangles'] for row in ocean['assets'])}
catalogs={};casts={}
content='engines/unreal/DaedalusLink/Content/'
for path in sorted((repo/content/'Inventory').glob('*.dic')):
    text=read(path.relative_to(repo).as_posix())
    catalogs[path.stem]={'items':sum(line.startswith('item ') for line in text.splitlines()),
                         'tabs':sum(line.startswith('tab ') for line in text.splitlines())}
for path in sorted((repo/content/'Casts').glob('*.dcs')):
    casts[path.stem]=sum(line.startswith('who ') for line in read(path.relative_to(repo).as_posix()).splitlines())
population=json.loads(read('data/art/portal/population-plan.json'))
pop={'records':len(population['population']),'enemy_target':population['enemy_count'],
     'friendly_target':population['friendly_count'],'types_per_side':population['types_per_side'],
     'individuals_per_type':population['individuals_per_type'],
     'art_status':dict(Counter(row.get('art_status') for row in population['population'])),
     'unreal_status':dict(Counter(row.get('unreal_status') for row in population['population']))}
solidity=read('chain/contracts/RealmIslands.sol')
deed=re.search(r'struct Deed\s*\{(.*?)\}',solidity,re.S)[1]
fields=re.findall(r'\b(address|uint\d*)\s+(\w+)\s*;',deed)
islands=read('daedalus-core/src/main/java/com/daedalus/world/island/IslandOps.java')
legacy={'deed_fields':[{'type':kind,'name':name} for kind,name in fields],
        'island_slot_limit':int(re.search(r'MAX_SLOTS\s*=\s*(\d+)',islands)[1]),
        'deployment_records_found_in_checkout':(repo/'chain/deployments').exists(),
        'on_chain_deployment_verified':False}
read('docs/adr/ADR-065-ten-thousand-lands-per-realm.md')
read('daedalus-wallet/src/main/java/com/daedalus/wallet/DeedVoucher.java')
read('daedalus-server/src/main/java/com/daedalus/server/controller/WalletController.java')
layout=None
if a.layout:
    raw=a.layout.read_bytes();data=json.loads(raw);groups={}
    for row in data['plan']['plan']:
        shape={key:row[key] for key in ('group','cell','estate','deed')}
        if row['group'] in groups and groups[row['group']]!=shape:raise ValueError('Inconsistent shared estate group')
        groups[row['group']]=shape
    # Owner's declared reserved hub mask for this saved layout (teamlink29125).
    hub={(x,y) for x in range(49,52) for y in range(49,52)}
    cells={};overlaps=[];splits=[]
    for name,row in groups.items():
        x,y=row['cell'];size=row['estate']
        if size not in (1,2,3,4) or x<0 or y<0 or x+size>100 or y+size>100:raise ValueError('Invalid estate footprint')
        if x//10!=(x+size-1)//10 or y//10!=(y+size-1)//10:splits.append(name)
        for cx in range(x,x+size):
            for cy in range(y,y+size):
                if (cx,cy) in cells or (cx,cy) in hub:overlaps.append([name,cx,cy])
                cells[(cx,cy)]=name
    layout={'artifact_sha256':hashlib.sha256(raw).hexdigest(),'levels':len(data['undo']),
            'estate_groups':len(groups),'estate_cells':len(cells),'reserved_hub_cells':len(hub),
            'overlaps':overlaps,'district_splits':splits,'estate_labels':sorted(row['deed'] for row in groups.values()),
            'undo_schema':'level to two-dimensional move delta; no actor-count proof',
            'live_positions_verified':False,'minted_ownership_verified':False}
proof={'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
       'scope':'Manifest counts and source contracts, not a complete project asset census or gameplay/chain acceptance',
       'art':art,'catalogs':catalogs,'dialogue_scripts':casts,'portal_population':pop,
       'legacy_mint':legacy,'saved_estate_layout':layout,'source_sha256':sources}
a.output.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
print('BASE_LAYER_AUDIT_WRITTEN',json.dumps({'production_manifest_rows':sum(v['manifest_records'] for v in art.values()),
      'catalog_item_records':sum(v['items'] for v in catalogs.values()),'dialogue_roles':sum(casts.values()),
      'layout_estate_cells':layout['estate_cells'] if layout else None}))
