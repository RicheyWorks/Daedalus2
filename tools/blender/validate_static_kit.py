"""Validate joined static GLB geometry, hashes, accessor bounds and BBA counts."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

def validate(root):
    manifest=json.loads((root/'manifest.json').read_text());seen=set();rows=[]
    bbas=list(root.glob('*.bba'));assert len(bbas)==1
    bba=bbas[0].read_text().splitlines();assert bba[0]=='BBA 1'
    for record in manifest['assets']:
        assert record['id'] not in seen;seen.add(record['id'])
        raw=(root/record['file']).read_bytes();magic,version,length=struct.unpack_from('<4sII',raw)
        assert magic==b'glTF' and version==2 and length==len(raw)
        size,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
        doc=json.loads(raw[20:20+size]);offset=20+size
        size,kind=struct.unpack_from('<II',raw,offset);assert kind==0x004e4942
        binary=raw[offset+8:offset+8+size];assert len(binary)==size
        assert not doc.get('skins') and not doc.get('animations')
        assert len(doc['meshes'])==1,'static kit must export one joined mesh'
        def accessor(index):
            a=doc['accessors'][index];view=doc['bufferViews'][a['bufferView']]
            assert 'sparse' not in a and a['count']>0
            fmt={5121:'B',5123:'H',5125:'I',5126:'f'}[a['componentType']]
            count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
            width=struct.calcsize('<'+fmt*count);stride=view.get('byteStride',width)
            start=view.get('byteOffset',0)+a.get('byteOffset',0)
            assert stride>=width and start+(a['count']-1)*stride+width<=view.get('byteOffset',0)+view['byteLength']<=len(binary)
            return [struct.unpack_from('<'+fmt*count,binary,start+i*stride) for i in range(a['count'])]
        triangles=0
        for primitive in doc['meshes'][0]['primitives']:
            assert primitive.get('mode',4)==4
            vertices=accessor(primitive['attributes']['POSITION']);indices=accessor(primitive['indices'])
            assert all(math.isfinite(value) for vertex in vertices for value in vertex)
            assert len(indices)%3==0 and all(0<=index[0]<len(vertices) for index in indices)
            triangles+=len(indices)//3
            if 'NORMAL' in primitive['attributes']:
                normals=accessor(primitive['attributes']['NORMAL']);assert len(normals)==len(vertices)
                assert all(abs(sum(value*value for value in normal)-1)<.01 for normal in normals)
        assert triangles==record['triangles'] and record['bones']==0
        assert hashlib.sha256(raw).hexdigest()==record['sha256']
        assert any(line.startswith(f"asset {record['id']} lod0 {triangles} lod1 - ") for line in bba)
        rows.append({'asset':record['id'],'triangles':triangles})
    assert rows
    (root/'validation.json').write_text(json.dumps({'passed':rows,'native_collision_proven':False},indent=2))
    print('STATIC_KIT_PASS',len(rows),'assets',sum(r['triangles'] for r in rows),'triangles')

if __name__=='__main__':validate(Path(sys.argv[1]))
