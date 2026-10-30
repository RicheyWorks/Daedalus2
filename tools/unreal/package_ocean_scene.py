"""Package only declared Ocean assets, with portable content hashes and no host config."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def package(delivery, plugin, output, proof):
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((delivery / 'manifest.json').read_text(encoding='utf-8'))
    scene = json.loads(proof.read_text(encoding='utf-8'))
    art = {name: delivery / name for name in ['manifest.json', 'validation.json', 'ocean.bba', 'ocean-vessels.blend']}
    for asset in manifest['assets']:
        name = asset['file']
        if Path(name).name != name or not name.endswith('.glb'):
            raise ValueError('Unexpected asset path')
        path = delivery / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('Source asset hash mismatch')
        art[name] = path
    native = {}
    for name, expected in scene['private_scene_content_sha256'].items():
        if not name.startswith('Content/Ocean/') or '..' in Path(name).parts or not name.endswith('.uasset'):
            raise ValueError('Unexpected native content path')
        path = plugin / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Private native content changed after capture')
        native[name] = path
    result = {'scope': 'Static art and private UE5.8 inspection assets; gameplay acceptance pending', 'archives': {}}
    for name, members in [('ocean-vessels.zip', art), ('ocean-native-content.zip', native)]:
        target = output / name
        with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for member, source in sorted(members.items()):
                archive.writestr(member, source.read_bytes())
        result['archives'][name] = {'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'members': {
            member: hashlib.sha256(source.read_bytes()).hexdigest() for member, source in sorted(members.items())}}
    (output / 'delivery.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('OCEAN_PACKAGE_PASS', len(art), 'source files;', len(native), 'native assets')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['delivery', 'plugin', 'output', 'proof']:
        p.add_argument('--' + name, required=True, type=Path)
    a = p.parse_args()
    package(a.delivery.resolve(), a.plugin.resolve(), a.output.resolve(), a.proof.resolve())
