# SPDX-License-Identifier: MIT
"""Normalize an editor capture for the existing Java RealmLayoutStore provisioning tool."""
import argparse
import hashlib
import json
from pathlib import Path
import re

REALMS={'WORLD-ZERO','GALLERY-CITY','PARCELS','BRICKS','LABYRINTH','OCEAN','PORTAL'}


def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate JSON field: '+key)
        result[key]=value
    return result


def prepare(capture, namespace):
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,100}',namespace):
        raise ValueError('explicit safe development seed namespace required')
    if len(capture)>2_000_000:raise ValueError('capture exceeds byte bound')
    data=json.loads(capture.decode('utf-8-sig'),object_pairs_hook=unique_object)
    if data.get('format')!='[landNumber, cellX, cellY, size]' or not isinstance(data.get('realms'),dict):
        raise ValueError('unsupported editor capture schema')
    if not data['realms'] or not set(data['realms'])<=REALMS:raise ValueError('unknown/empty realm set')
    lines=['DLAY_IMPORT 1','# capture-sha256='+hashlib.sha256(capture).hexdigest(),'# seed-namespace='+namespace]
    count=0
    for realm,rows in sorted(data['realms'].items()):
        if not isinstance(rows,list) or not rows or len(rows)>10000:raise ValueError('invalid realm row count')
        seen=set()
        for row in rows:
            if not isinstance(row,list) or len(row)!=4 or any(type(x)!=int for x in row):raise ValueError('integer placement tuple required')
            number,x,y,size=row
            if number in seen:raise ValueError('duplicate immutable land identity')
            seen.add(number)
            if not 0<=number<10000 or not 1<=size<=8 or x<0 or y<0 or x+size>100 or y+size>100:
                raise ValueError('placement outside bounded grid')
            # Placement changes do not change identity-derived development seeds.
            digest=hashlib.sha256(f'dlay-development-v1:{namespace}:{realm}:{number}'.encode()).digest()
            seed=int.from_bytes(digest[:8],'big',signed=True)
            lines.append('\t'.join(map(str,[realm,number,x,y,size,seed])));count+=1
    return '\n'.join(lines)+'\n',count


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture',type=Path,required=True);ap.add_argument('--seed-namespace',required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();text,count=prepare(a.capture.read_bytes(),a.seed_namespace)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
    print(json.dumps({'rows':count,'normalized':str(a.out),'seed_namespace':a.seed_namespace,
                      'meaning':'development terrain seeds; no deed/egg/mint/ownership authority'}))

if __name__=='__main__':main()
