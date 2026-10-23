# SPDX-License-Identifier: MIT
"""Strict file-only index for bounded native source-metadata pages.

No Unreal/client imports. A complete registry path capture is distinct from
verified source hashes. Page gaps, duplicates, unsupported/partial rows fail shut.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = '/Game/Daedalus/Art/Islands'
INDEX = 'daedalus.static-source-inventory.v2'
PAGE = 'daedalus.static-source-page.v1'
PAGE_ROWS = 32
PAGE_BYTES = 128 * 1024
INDEX_BYTES = 2 * 1024 * 1024
PATH_BYTES = 16 * 1024 * 1024
SHA = re.compile(r'[a-f0-9]{64}\Z')
ASSET = re.compile(r'/Game/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\Z')


def fingerprint(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(64 * 1024), b''):
            size += len(block); digest.update(block)
    return {'sha256': digest.hexdigest(), 'bytes': size}


def pin(path):
    return {'path': str(Path(path).resolve()), **fingerprint(path)}


def witness(value):
    if (not isinstance(value, dict) or set(value) != {'path', 'sha256', 'bytes'}
            or not isinstance(value['path'], str) or not Path(value['path']).is_absolute()
            or type(value['bytes']) is not int or not 0 < value['bytes'] <= 256 * 1024**2
            or not isinstance(value['sha256'], str) or not SHA.fullmatch(value['sha256'])):
        raise ValueError('Exact local file witness required')
    path = Path(value['path'])
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('Symlink inventory input refused')
    return path


def load(value, cap=INDEX_BYTES):
    path = witness(value)
    if value['bytes'] > cap or path.stat().st_size != value['bytes']:
        raise ValueError('Inventory input exceeds explicit byte bound or changed')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != value['sha256']:
        raise ValueError('Pinned inventory bytes changed')
    def unique(pairs):
        result = {}
        for key, row in pairs:
            if key in result: raise ValueError('Duplicate JSON key in inventory')
            result[key] = row
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def path_digest(paths):
    return hashlib.sha256(json.dumps(paths, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def capture(value):
    data = load(value, PATH_BYTES + 256 * 1024)
    paths = data.get('paths')
    if (data.get('root') != ROOT or not isinstance(paths, list) or not paths
            or type(data.get('count')) is not int or data['count'] != len(paths)
            or sum(len(p.encode()) for p in paths if isinstance(p, str)) > PATH_BYTES
            or any(not isinstance(p, str) or not ASSET.fullmatch(p)
                   or not p.startswith(ROOT + '/') for p in paths)):
        raise ValueError('Complete bounded registry path capture required')
    ordered = sorted(paths)
    if len({p.casefold() for p in paths}) != len(paths):
        raise ValueError('Duplicate registry object path')
    return ordered


def checked_page(page, index, paths, offset):
    if (not isinstance(page, dict) or set(page) != {'schema', 'state', 'editor',
            'registry_sha256', 'reader_sha256', 'offset', 'requested', 'rows', 'issues'}
            or page['schema'] != PAGE or page['state'] != 'complete' or page['issues'] != []
            or page['editor'] != index['editor']
            or page['registry_sha256'] != index['registry']['sha256']
            or page['reader_sha256'] != index['reader']['sha256']
            or type(page['offset']) is not int or page['offset'] != offset
            or type(page['requested']) is not int
            or page['requested'] != min(PAGE_ROWS, len(paths) - offset)
            or not isinstance(page['rows'], list) or len(page['rows']) != page['requested']):
        raise ValueError('Partial/unsupported/mixed inventory page or page gap')
    if [r.get('asset') for r in page['rows'] if isinstance(r, dict)] != paths[offset:offset + page['requested']]:
        raise ValueError('Duplicate/out-of-order/missing inventory page rows')
    for row in page['rows']:
        if (set(row) != {'asset', 'source_sha256', 'package'}
                or not isinstance(row['source_sha256'], str) or not SHA.fullmatch(row['source_sha256'])):
            raise ValueError('Unknown native source hash; absence not established')
        witness(row['package'])
    return page['rows']


def pages(index):
    paths = capture(index['registry'])
    offset, files = 0, set()
    for descriptor in index['pages']:
        if (set(descriptor) != {'file', 'offset', 'count'} or type(descriptor['offset']) is not int
                or descriptor['offset'] != offset or offset >= len(paths)
                or type(descriptor['count']) is not int
                or descriptor['count'] != min(PAGE_ROWS, len(paths) - offset)):
            raise ValueError('Page gap/overlap/count mismatch')
        path = str(witness(descriptor['file']).resolve()).casefold()
        if path in files: raise ValueError('Duplicate page file')
        files.add(path)
        rows = checked_page(load(descriptor['file'], PAGE_BYTES), index, paths, offset)
        offset += len(rows)
        yield rows
    if offset != len(paths):
        raise ValueError('Incomplete source-hash inventory pages')


def validate(index):
    if (not isinstance(index, dict) or set(index) != {'schema', 'root', 'registry',
            'editor', 'reader', 'path_count', 'path_digest', 'pages'}
            or index['schema'] != INDEX or index['root'] != ROOT or not isinstance(index['pages'], list)):
        raise ValueError('Paged v2 inventory required; old fixed-corpus format unsupported')
    paths = capture(index['registry'])
    witness(index['reader'])
    if (type(index['path_count']) is not int or index['path_count'] != len(paths)
            or index['path_digest'] != path_digest(paths)):
        raise ValueError('Complete corpus count/digest differs')
    total = sum(len(rows) for rows in pages(index))
    if total != index['path_count']: raise ValueError('Incomplete source hash coverage')
    return index


def read_index(value):
    return validate(load(value))


def build_index(registry, editor, reader, page_files):
    paths = capture(registry)
    index = {'schema': INDEX, 'root': ROOT, 'registry': registry, 'editor': editor,
             'reader': reader, 'path_count': len(paths), 'path_digest': path_digest(paths), 'pages': []}
    for offset, file in zip(range(0, len(paths), PAGE_ROWS), page_files):
        index['pages'].append({'file': pin(file), 'offset': offset,
                               'count': min(PAGE_ROWS, len(paths) - offset)})
    if len(page_files) != len(index['pages']):
        raise ValueError('Extra/unbound page files')
    return validate(index)
