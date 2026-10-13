"""Record actual validated art against planned individuals; never promote Play."""
import argparse
import json
from pathlib import Path
from validate_labyrinth_cast import validate

def reconcile(plan_path, batch):
    validate(batch)
    plan=json.loads(plan_path.read_text())
    manifest=json.loads((batch/'manifest.json').read_text())
    individuals={r['id']:r for r in plan['population']}
    updates={}
    for asset in manifest['assets']:
        key=asset.get('population_id')
        if not key or key not in individuals or key in updates:
            raise ValueError('Unknown or duplicate population identity')
        if individuals[key]['type']!=asset.get('source_monster'):
            raise ValueError('Population species mismatch')
        updates[key]=asset
    for key,asset in updates.items():
        individuals[key]['art_status']='Export validated'
        individuals[key]['art_candidate']={
            'file':str((batch/asset['file']).resolve()),'sha256':asset['sha256'],
            'triangles':asset['triangles'],'acceptance':'Native import and visual acceptance pending'}
    # Do not touch Unreal statuses, other individuals or gameplay rule keys.
    temporary=plan_path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(plan,indent=2),encoding='utf8')
    temporary.replace(plan_path)
    print('POPULATION_ART_RECONCILED',len(updates))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path);parser.add_argument('batch',type=Path)
    args=parser.parse_args();reconcile(args.plan,args.batch)
