"""Use the existing GLB witness rather than trusting the producer's counts."""
import hashlib
import json
import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'connectors/claude-asset-pipeline'))
from asset_pipeline import glb

def validate(folder):
    manifest = json.loads((folder/'manifest.json').read_text())
    assets = manifest['assets']
    expected={'daedalus.sol.art/v1':500,'daedalus.sol.adventure-art/v1':5}.get(manifest['schema'])
    if expected is None or len(assets)!=expected or len({a['asset'] for a in assets})!=expected:
        raise ValueError('incorrect or duplicate asset identifiers for schema')
    witnesses = []
    for asset in assets:
        path = pathlib.Path(asset['glb'])
        observed = glb.summarize(str(path))
        if len(observed['nodes']) != 1 or len(observed['meshes']) != 1:
            raise ValueError('one mesh per asset required: '+asset['asset'])
        mesh = observed['meshes'][0]
        if mesh['triangles'] != asset['triangles'] or not 0 < mesh['triangles'] <= 3000:
            raise ValueError('triangle parity/budget: '+asset['asset'])
        if len(mesh['materials']) != asset['materials'] or not 1 <= len(mesh['materials']) <= 3:
            raise ValueError('material parity/budget: '+asset['asset'])
        if any(abs(a-b) > .0001 for a,b in zip(mesh['dims'], sorted(asset['dimensions_m'],reverse=True))):
            raise ValueError('size parity: '+asset['asset'])
        if not pathlib.Path(asset['blend']).is_file(): raise ValueError('missing .blend')
        witnesses.append({'asset':asset['asset'],'triangles':mesh['triangles'],
                          'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    result = {'passed':len(witnesses),'total':expected,'triangles':sum(w['triangles'] for w in witnesses),
              'stage':'Blender/file parity only; Unreal not imported','witnesses':witnesses}
    (folder/'validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='witnesses'}))
    return manifest

if __name__=='__main__': validate(pathlib.Path(sys.argv[1]))
