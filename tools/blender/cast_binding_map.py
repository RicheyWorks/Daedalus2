"""Resolve verified cast art to existing DCS role names without editing scripts."""
import argparse
import hashlib
import json
from pathlib import Path
import re

def normalize(name):return re.sub('[^a-z0-9]','',name.lower())

def build(root,script,prefix,output):
    manifest=json.loads((root/'manifest.json').read_text())
    checked={row['asset'] for row in json.loads((root/'validation.json').read_text())['passed']}
    raw=script.read_bytes();text=raw.decode('utf8')
    if not text.startswith('DCS 1'):raise ValueError('Unsupported cast script')
    realm_keys={'The Parcels':'PARCELS','Gallery City':'GALLERY-CITY','Brick Realm':'BRICKS','Labyrinth':'LABYRINTH'}
    headers=re.findall(r'^cast (.+)$',text,re.M)
    if len(headers)!=1 or headers[0].strip()!=realm_keys.get(manifest['realm']):raise ValueError('Cast realm mismatch')
    if any(not asset['id'].startswith(prefix) for asset in manifest['assets']):raise ValueError('Cast ID prefix mismatch')
    candidates={normalize(asset['id'].removeprefix(prefix)):asset for asset in manifest['assets']}
    if len(candidates)!=len(manifest['assets']):raise ValueError('Ambiguous normalized asset names')
    roles=re.findall(r'^who (.+)$',text,re.M);roles=[role.strip() for role in roles]
    if len(set(roles))!=len(roles):raise ValueError('Duplicate DCS role')
    aliases={'lostletterghost':'lostlettercourier'} if manifest['realm']=='The Parcels' else {}
    if manifest['realm']=='Brick Realm':aliases={'gluewitch':'adhesivealchemist'}
    rows=[]
    for who in roles:
        key=aliases.get(normalize(who),normalize(who))
        if key not in candidates:raise ValueError('No art candidate for '+who)
        asset=candidates[key]
        if asset['id'] not in checked:raise ValueError('Unvalidated cast export')
        actual=(root/asset['file']).read_bytes()
        if hashlib.sha256(actual).hexdigest()!=asset['sha256']:raise ValueError('Changed export')
        rows.append({'native_who':who,'asset_id':asset['id'],'file':asset['file'],
                     'sha256':asset['sha256'],'rig':asset['rig'],'status':'Native binding pending'})
    if len(rows)!=12:raise ValueError('Expected twelve NPC roles; review source changes')
    output.write_text(json.dumps({'script':str(script),'script_sha256':hashlib.sha256(raw).hexdigest(),
        'bindings':rows,'hero_binding':'Separate player binding; not a DCS role'},indent=2))
    print('CAST_BINDINGS_PASS',len(rows),'existing script roles')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['root','script','prefix','output']:parser.add_argument(name)
    args=parser.parse_args();build(Path(args.root),Path(args.script),args.prefix,Path(args.output))
