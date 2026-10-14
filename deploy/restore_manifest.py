"""Compare a backup's mounted-world identities with the restored server, without extracting files."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

ID = re.compile(r'^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$')


def manifest(archive):
    files = set()
    registry = None
    names = set()
    with tarfile.open(archive, 'r|gz') as source:
        for count, member in enumerate(source):
            if count >= 100000:
                raise ValueError('Backup has too many entries')
            path = PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or path.as_posix() in names:
                raise ValueError('Unsafe or duplicate archive path')
            names.add(path.as_posix())
            if path.parts[:2] != ('worlds', 'world') or len(path.parts) != 3:
                continue
            if path.name == 'worlds.registry':
                if not member.isfile() or member.size > 1024 * 1024:
                    raise ValueError('Invalid world registry entry')
                registry = source.extractfile(member).read().decode('utf-8')
            elif path.suffix == '.daew':
                if not member.isfile() or not ID.fullmatch(path.stem):
                    raise ValueError('Invalid world snapshot entry')
                if source.extractfile(member).read(4) != b'DAEW':
                    raise ValueError('World snapshot header missing')
                files.add(path.stem)
    expected = {'world-zero': {'id': 'world-zero', 'style': 'SKY_ISLANDS', 'seed': 0, 'title': 'World Zero'}}
    for line in (registry or '').splitlines():
        text = line.strip()
        if not text or text.startswith('#'):
            continue
        fields = text.split(None, 3)
        if len(fields) != 4 or not ID.fullmatch(fields[0]) or fields[0] in expected:
            raise ValueError('Invalid or duplicate registry world')
        key, style, seed_text, title = fields
        seed = int(seed_text)
        if not -(1 << 63) <= seed < (1 << 63):
            raise ValueError('Registry seed outside signed long range')
        expected[key] = {'id': key, 'style': style, 'seed': seed, 'title': title}
    if set(expected) - {'world-zero'} != files - {'world-zero'}:
        raise ValueError('Backup registry and world files do not agree')
    if not files:
        raise ValueError('Backup has no saved world snapshots')
    return {'schema': 1, 'worlds': list(expected.values()), 'savedWorlds': sorted(files)}


def verify(expected, response):
    if len(response) > 4 * 1024 * 1024:
        raise ValueError('World response too large')
    headers, separator, body = response.partition(b'\r\n\r\n')
    if not separator or not re.match(rb'^HTTP/1\.[01] 200(?: |\r|$)', headers):
        raise ValueError('Expected an HTTP 200 world response')
    actual = json.loads(body).get('worlds')
    if not isinstance(actual, list) or not all(isinstance(row, dict) for row in actual):
        raise ValueError('Invalid world response')
    rows = {}
    for row in actual:
        key = row.get('id')
        if not isinstance(key, str) or key in rows:
            raise ValueError('Duplicate or invalid served world')
        rows[key] = row
    wanted = {row['id']: row for row in expected['worlds']}
    if rows.keys() != wanted.keys():
        raise ValueError('Served world IDs differ from backup: expected ' + ','.join(sorted(wanted))
                         + '; got ' + ','.join(sorted(rows)))
    for key, row in wanted.items():
        for field in ('style', 'seed', 'title'):
            if rows[key].get(field) != row[field] or (field == 'seed' and type(rows[key].get(field)) is not int):
                raise ValueError('Restored world metadata differs: ' + key + '/' + field)
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('manifest')
    create.add_argument('archive', type=Path)
    create.add_argument('output', type=Path)
    compare = commands.add_parser('verify')
    compare.add_argument('expected', type=Path)
    compare.add_argument('response', type=Path)
    args = parser.parse_args()
    if args.command == 'manifest':
        args.output.write_text(json.dumps(manifest(args.archive), indent=2) + '\n')
    else:
        count = verify(json.loads(args.expected.read_text()), args.response.read_bytes())
        print('RESTORE_WORLDS_PASS', count, 'world identities and metadata agree with the backup')
