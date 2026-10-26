"""Validate and register the complete first Gallery art package; no live proof."""
import csv
import json
from pathlib import Path
import sys
from validate_labyrinth_cast import validate as validate_cast
from validate_static_kit import validate as validate_static

def build(root,realm='Gallery City',prefix='gallery-buildout',scenes=None):
    scenes=scenes or {'cast':'gallery-city-cast','creatures':'gallery-creatures','environment':'gallery-environment'}
    validate_cast(root/'cast');validate_cast(root/'creatures');validate_static(root/'environment')
    rows=[];seen=set()
    for folder in ['cast','creatures','environment']:
        manifest=json.loads((root/folder/'manifest.json').read_text())
        assert manifest['realm']==realm,'Wrong realm manifest'
        for asset in manifest['assets']:
            assert asset['id'] not in seen;seen.add(asset['id'])
            rows.append({**asset,'file':folder+'/'+asset['file'],'kind':'Prop' if folder=='environment' else 'Character',
                'realm':realm,'clips':'' if folder=='environment' else 'Idle, Walk, Attack, Hurt',
                'export':'Validated','unreal':'Pending','mechanic':'Binding pending'})
    assert len(rows)==56 and sum(row['role_count'] for row in rows)==32
    (root/'production-data.json').write_text(json.dumps(rows,indent=2))
    (root/'validation.json').write_text(json.dumps({'assets':56,'role_count':32,
        'triangles':sum(row['triangles'] for row in rows),'unreal_proven':False},indent=2))
    with (root/'catalog-additions.csv').open('w',newline='',encoding='utf8') as file:
        writer=csv.writer(file);writer.writerow(['name','kind','category','world','owner','status','queue_status','blender_files','uassets','path'])
        for row in rows:
            folder=row['file'].split('/')[0]
            scene=scenes[folder]
            writer.writerow([row['id'],'Mob' if row['kind']=='Character' else 'Prop',
                'fauna' if folder=='creatures' else 'characters' if folder=='cast' else 'props (other)',
                realm,'team-codex','blender_only','READY',prefix+'/'+folder+'/'+scene+'.blend',
                '', prefix+'/'+row['file']])
    print('REALM_PACKAGE_PASS',realm,56,'exports',sum(row['triangles'] for row in rows),'triangles')

if __name__=='__main__':build(Path(sys.argv[1]))
