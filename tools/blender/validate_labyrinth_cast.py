"""Validate actual exported skins, weights, clips and BBA counts. Standard library only."""
import json, struct, math, hashlib, sys
from pathlib import Path

def validate(root):
    manifest=json.loads((root/'manifest.json').read_text())
    skeleton=None; rows=[]
    bba=(root/'labyrinth-cast.bba').read_text().splitlines();assert bba[0]=='BBA 1'
    for record in manifest['assets']:
        raw=(root/record['file']).read_bytes()
        magic,version,length=struct.unpack_from('<4sII',raw)
        assert magic==b'glTF' and version==2 and length==len(raw)
        size,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
        doc=json.loads(raw[20:20+size]); off=20+size
        binary_size,kind=struct.unpack_from('<II',raw,off);assert kind==0x004e4942
        binary=raw[off+8:off+8+binary_size]
        def accessor(index):
            a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
            assert 'sparse' not in a
            fmt={5121:'B',5123:'H',5125:'I',5126:'f'}[a['componentType']]
            count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
            width=struct.calcsize('<'+fmt*count);stride=v.get('byteStride',width)
            start=v.get('byteOffset',0)+a.get('byteOffset',0)
            assert start+(a['count']-1)*stride+width<=v.get('byteOffset',0)+v['byteLength']<=len(binary)
            return [struct.unpack_from('<'+fmt*count,binary,start+i*stride) for i in range(a['count'])]
        assert len(doc['skins'])==1
        joints=doc['skins'][0]['joints'];assert len(joints)==record['bones']
        signature=[(doc['nodes'][i]['name'],doc['nodes'][i].get('translation'),doc['nodes'][i].get('rotation')) for i in joints]
        if skeleton is None:skeleton=signature
        assert signature==skeleton,'shared rest skeleton differs'
        tris=0; vertices=0
        for mesh in doc['meshes']:
            for p in mesh['primitives']:
                assert p.get('mode',4)==4
                pos=accessor(p['attributes']['POSITION']);weights=accessor(p['attributes']['WEIGHTS_0']);ids=accessor(p['attributes']['JOINTS_0'])
                assert len(pos)==len(weights)==len(ids)
                assert all(all(math.isfinite(v) for v in xyz) for xyz in pos)
                assert all(abs(sum(w)-1)<1e-5 and min(w)>=0 for w in weights)
                assert all(all(j<len(joints) for j in row) for row in ids)
                indices=accessor(p['indices']);assert len(indices)%3==0
                assert all(i[0]<len(pos) for i in indices)
                tris+=len(indices)//3;vertices+=len(pos)
        assert tris==record['triangles']
        assert hashlib.sha256(raw).hexdigest()==record['sha256']
        assert {a['name'] for a in doc['animations']}==set(manifest.get('clips',['Idle','Walk']))
        for animation in doc['animations']:
            varies=False
            for channel in animation['channels']:
                sampler=animation['samplers'][channel['sampler']]
                times=[t[0] for t in accessor(sampler['input'])];values=accessor(sampler['output'])
                assert len(times)==len(values) and len(times)>1
                assert all(b>a for a,b in zip(times,times[1:]))
                assert all(all(math.isfinite(v) for v in row) for row in values)
                varies |= any(any(abs(x-y)>1e-5 for x,y in zip(values[0],row)) for row in values[1:])
                same=all(abs(x-y)<1e-4 for x,y in zip(values[0],values[-1]))
                # Unit quaternions q and -q encode exactly the same orientation.
                if channel['target']['path']=='rotation':
                    assert all(abs(sum(v*v for v in row)-1)<1e-4 for row in values)
                    same |= all(abs(x+y)<1e-4 for x,y in zip(values[0],values[-1]))
                assert same,f"clip does not loop: {record['id']} {animation['name']} {channel['target']}"
            assert varies,'animation has no motion'
        assert any(line.startswith(f"asset {record['id']} lod0 {tris} lod1 - ") for line in bba)
        rows.append({'asset':record['id'],'triangles':tris,'export_vertices':vertices,'joints':len(joints),'clips':manifest.get('clips',['Idle','Walk'])})
    assert len(rows)==len(manifest['assets']) and len(rows)>=3
    (root/'validation.json').write_text(json.dumps({'passed':rows,'unreal_import_proven':False},indent=2))
    print(json.dumps(rows,indent=2))

if __name__=='__main__':validate(Path(sys.argv[1]))
