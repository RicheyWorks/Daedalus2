"""Check actual UBT JsonExport runtime declarations against an exact-head plugin snapshot."""
import argparse
import hashlib
import json
import re
import os
import uuid
from pathlib import Path


def read_json(path,evidence=None):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON field: '+key)
            result[key]=value
        return result
    def invalid(value):raise ValueError('Nonfinite JSON value: '+value)
    with Path(path).open('rb') as stream:raw=stream.read(64*1024*1024+1)
    if len(raw)>64*1024*1024:raise ValueError('JSON document exceeds64MiB')
    value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique,parse_constant=invalid)
    if not isinstance(value,dict):raise ValueError('Expected JSON object')
    if evidence is not None:
        evidence.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
    return value


def write_proof(path,proof):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('x',encoding='utf-8',newline='\n') as stream:
            json.dump(proof,stream,indent=2,allow_nan=False)
            stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()


def verify(host, exported):
    host = Path(host).resolve()
    manifest_identity={};target_identity={}
    manifest = read_json(host / 'source-manifest.json',manifest_identity)
    target = read_json(exported,target_identity)
    if not isinstance(manifest.get('files'),dict) or not manifest['files']:
        raise ValueError('Source manifest files missing')
    if target.get('Configuration') != 'Shipping':
        raise ValueError('Expected an actual Shipping target export')
    module = target.get('Modules', {}).get('DaedalusLink')
    if not module:
        raise ValueError('DaedalusLink is not linked into this target')
    prefix = 'engines/unreal/DaedalusLink/'
    plugin = host / 'Plugins/DaedalusLink'
    expected = {}
    data_types = {'Inventory': {'.dic'}, 'Casts': {'.dcs'}, 'Realm': {'.drr', '.dsp'}}
    for name, digest in manifest['files'].items():
        if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):
            raise ValueError('Source manifest hash is not SHA256')
        relative = Path(name.removeprefix(prefix))
        if not name.startswith(prefix) or relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid source manifest path')
        source = plugin / relative
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError('Snapshot missing or changed: ' + name)
        if len(relative.parts) == 3 and relative.parts[0] == 'Content':
            if relative.suffix in data_types.get(relative.parts[1], set()):
                expected[source.resolve()] = digest
    if not expected or any(not any(p.parent.name == folder for p in expected) for folder in data_types):
        raise ValueError('Missing a required runtime data family')
    staged = set()
    declarations = []
    for dependency in module.get('RuntimeDependencies', []):
        pattern = Path(dependency['Path'])
        try:
            pattern.relative_to(plugin)
        except ValueError:
            continue  # Engine/third-party dependencies are outside this verifier's scope.
        if dependency.get('Type') != 'UFS':
            raise ValueError('Runtime data must be declared UFS')
        matches = list(pattern.parent.glob(pattern.name))
        if not matches:
            raise ValueError('Runtime dependency pattern matches no files')
        declarations.append(dependency)
        for file in matches:
            resolved = file.resolve()
            if resolved not in expected:
                raise ValueError('Unexpected plugin data staged: ' + str(file))
            staged.add(resolved)
    if staged != expected.keys():
        raise ValueError('Runtime files omitted: ' + ', '.join(str(p.name) for p in expected.keys() - staged))
    return {'schema': 1, 'sourceHead': manifest['source_head'],
            'inputDocuments':{'sourceManifest':manifest_identity,'targetExport':target_identity},
            'trackedPluginFiles': manifest['tracked_file_count'],
            'targetConfiguration': target['Configuration'], 'targetPlatform': target.get('Platform'),
            'declarations': declarations,
            'files': {p.relative_to(plugin).as_posix(): digest for p, digest in sorted(expected.items())},
            'scope': 'Actual UBT Shipping target declarations and exact snapshot hashes; not a cook, staged archive or game launch',
            'packagedGameLaunchVerified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('host', type=Path)
    parser.add_argument('export', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof = verify(args.host, args.export)
    write_proof(args.output,proof)
    print('RUNTIME_DATA_PASS', len(proof['files']), 'files covered by UBT Shipping declarations')
