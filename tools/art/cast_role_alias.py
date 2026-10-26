# SPDX-License-Identifier: MIT
"""Create a cast-role alias without changing geometry, animation bytes or originals."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


def alias_bytes(data, old, new, expected):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('source SHA256 differs from manifest')
    if not all(re.fullmatch(r'Mob_[A-Za-z0-9_]+', value) for value in (old, new)) or old == new:
        raise ValueError('distinct safe cast IDs required')
    if len(data) < 20 or struct.unpack_from('<4sII', data) != (b'glTF', 2, len(data)):
        raise ValueError('invalid GLB2 header')
    length, kind = struct.unpack_from('<I4s', data, 12)
    if kind != b'JSON' or length % 4 or 20 + length > len(data):
        raise ValueError('invalid JSON chunk')
    doc = json.loads(data[20:20+length])
    # Refuse a new alias that would shadow an unrelated existing identity.
    for group in ('nodes', 'skins', 'meshes'):
        items = doc.get(group, [])
        targets = {new + item['name'][len(old):] for item in items
                   if item.get('name') in (old, old + '_Rig')}
        if any(item.get('name') in targets and item.get('name') not in (old, old + '_Rig')
               for item in items):
            raise ValueError('destination name already present in GLB ' + group)
    changed = 0
    for group in ('nodes', 'skins', 'meshes'):
        for item in doc.get(group, []):
            name = item.get('name', '')
            if name == old or name == old + '_Rig':
                item['name'] = new + name[len(old):]
                changed += 1
    if not changed:
        raise ValueError('source ID absent from GLB names')
    body = json.dumps(doc, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    body += b' ' * (-len(body) % 4)
    # Every remaining chunk, including binary geometry/animation payload, stays exact.
    tail = data[20+length:]
    result = struct.pack('<4sII', b'glTF', 2, 20+len(body)+len(tail)) + struct.pack('<I4s', len(body), b'JSON') + body + tail
    return result, changed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--old', required=True)
    ap.add_argument('--new', required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    records = json.loads(a.manifest.read_text(encoding='utf-8'))
    matches = [r for r in records if r['id'] == a.old]
    if len(matches) != 1:
        raise ValueError('exactly one source manifest record required')
    record = dict(matches[0])
    root = a.source_root.resolve()
    source = (root / record['file']).resolve()
    if not source.is_relative_to(root):
        raise ValueError('source escapes root')
    data = source.read_bytes()
    renamed, count = alias_bytes(data, a.old, a.new, record['sha256'])
    # A new delivery directory only: never overwrite art or another bot's delivery.
    a.out.mkdir(parents=True, exist_ok=False)
    target = a.out / (a.new + '.glb')
    target.write_bytes(renamed)
    record.update(id=a.new, file=target.name, sha256=hashlib.sha256(renamed).hexdigest(),
                  source_id=a.old, source_sha256=hashlib.sha256(data).hexdigest(), renamed_fields=count,
                  unreal='Pending', mechanic='Binding pending')
    (a.out / 'manifest.json').write_text(json.dumps({'assets': [record]}, indent=2), encoding='utf-8')
    (a.out / 'alias-proof.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
