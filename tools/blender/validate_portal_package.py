"""Validate source-key coverage and exported bytes. No Unreal or gameplay proof implied."""
import json,struct,hashlib,re,sys,csv
from pathlib import Path
from validate_labyrinth_cast import validate

def build(root):
    validate(root/'cast');validate(root/'monsters')
    repo=Path(__file__).resolve().parents[2]
    source_path=repo/'daedalus-core/src/main/java/com/daedalus/world/retro/RetroMonster.java'
    source=source_path.read_bytes();digest=hashlib.sha256(source).hexdigest()
    keys=set(re.findall(r'^\s*([A-Z_]+)\("',source.decode(),re.M));assert len(keys)==15
    rows=[];seen=set();tiers={k:set() for k in keys}
    for folder in ['cast','monsters','environment']:
        manifest=json.loads((root/folder/'manifest.json').read_text())
        for a in manifest['assets']:
            assert a['id'] not in seen;seen.add(a['id'])
            raw=(root/folder/a['file']).read_bytes();magic,version,length=struct.unpack_from('<4sII',raw)
            assert magic==b'glTF' and version==2 and length==len(raw)
            n,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
            j=json.loads(raw[20:20+n]);tri=sum(j['accessors'][p['indices']]['count']//3 for m in j['meshes'] for p in m['primitives'])
            assert tri==a['triangles'] and hashlib.sha256(raw).hexdigest()==a['sha256']
            if folder=='environment':assert not j.get('skins') and not j.get('animations')
            if a.get('source_monster'):
                assert a['source_file_sha256']==digest and a['source_monster'] in keys
                tiers[a['source_monster']].add(a['visual_tier'])
            kind='Character' if folder!='environment' else 'Item' if a['id'].startswith('Item_') else 'Prop'
            rows.append({**a,'file':folder+'/'+a['file'],'kind':kind,'realm':'Portal Realm','clips':', '.join(x['name'] for x in j.get('animations',[])),'export':'Validated','unreal':'Pending','mechanic':'Binding pending','role_count':a.get('role_count',1 if kind=='Character' else 0)})
    assert len(rows)==91 and all(t=={1,2,3} for t in tiers.values())
    assert sum(a['role_count'] for a in rows)==33
    (root/'production-data.json').write_text(json.dumps(rows,indent=2))
    (root/'validation.json').write_text(json.dumps({'assets':len(rows),'role_count':33,'source_monster_types':15,'visual_variants_of_source_monsters':45,'triangles':sum(a['triangles'] for a in rows),'unreal_proven':False},indent=2))
    with (root/'catalog-additions.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.writer(f);w.writerow(['name','kind','category','world','owner','status','queue_status','blender_files','uassets','path'])
        names={'cast':'portal-town-cast.blend','monsters':'portal-bestiary.blend','environment':'portal-environment.blend'}
        for a in rows:
            folder=a['file'].split('/')[0]
            w.writerow([a['id'],'Mob' if a['kind']=='Character' else a['kind'],'fauna' if a['kind']=='Character' else 'items (other)' if a['kind']=='Item' else 'props (other)','Portal Realm','team-codex','blender_only','READY','portal-buildout/'+folder+'/'+names[folder],'','portal-buildout/'+a['file']])
    print('PORTAL_PACKAGE_PASS',len(rows),'exports',sum(a['triangles'] for a in rows),'triangles')

if __name__=='__main__':build(Path(sys.argv[1]))
