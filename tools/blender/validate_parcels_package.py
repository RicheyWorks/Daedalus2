"""Validate Parcels first kit and distinguish authored exports from asset reuse."""
import csv
import hashlib
import json
from pathlib import Path
import sys
from validate_labyrinth_cast import validate as validate_cast
from validate_static_kit import validate as validate_static

def build(root):
    validate_cast(root/'cast');validate_cast(root/'creatures');validate_static(root/'environment')
    repo=Path(__file__).resolve().parents[2];rows=[];seen=set();reuse=[]
    for folder in ['cast','creatures','environment']:
        for asset in json.loads((root/folder/'manifest.json').read_text())['assets']:
            assert asset['id'] not in seen;seen.add(asset['id'])
            if asset.get('reused_source'):
                original=(repo/asset['reused_source']).resolve();assert original.is_relative_to(repo)
                assert hashlib.sha256(original.read_bytes()).hexdigest()==asset['sha256']
                assert (root/folder/asset['file']).read_bytes()==original.read_bytes()
                reuse.append(asset)
            rows.append({**asset,'file':folder+'/'+asset['file'],'kind':'Prop' if folder=='environment' else 'Character',
                'realm':'The Parcels','clips':'' if folder=='environment' else 'Idle, Walk, Attack, Hurt',
                'export':'Validated','unreal':'Pending','mechanic':'Binding pending'})
    assert len(rows)==56 and sum(row['role_count'] for row in rows)==32 and len(reuse)==1
    (root/'production-data.json').write_text(json.dumps(rows,indent=2))
    (root/'reuse-register.json').write_text(json.dumps(reuse,indent=2))
    (root/'validation.json').write_text(json.dumps({'assets':56,'new_exports':55,'reused_assets':1,'roles':32,
        'triangles':sum(row['triangles'] for row in rows),'unreal_proven':False},indent=2))
    with (root/'catalog-additions.csv').open('w',newline='',encoding='utf8') as file:
        writer=csv.writer(file);writer.writerow(['name','kind','category','world','owner','status','queue_status','blender_files','uassets','path'])
        for row in rows:
            if row.get('reused_source'):continue # Existing ID/owner stays in MASTER; separate reuse register.
            folder=row['file'].split('/')[0]
            writer.writerow([row['id'],'Mob' if row['kind']=='Character' else 'Prop',
                'fauna' if folder=='creatures' else 'characters' if folder=='cast' else 'props (other)',
                'The Parcels','team-codex','blender_only','READY','parcels-buildout/'+folder+'/parcels-'+folder+'.blend',
                '', 'parcels-buildout/'+row['file']])
    print('PARCELS_PACKAGE_PASS',55,'new exports +',1,'reused asset',sum(row['triangles'] for row in rows),'triangles')

if __name__=='__main__':build(Path(sys.argv[1]))
