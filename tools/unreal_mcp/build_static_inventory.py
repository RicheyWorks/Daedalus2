# SPDX-License-Identifier: MIT
"""Seal explicitly selected complete native source pages; file-only, no client."""
import argparse
import json
from pathlib import Path

if __package__:
    from . import unattended_static_adapter as a
else:
    import unattended_static_adapter as a


def build(registry, baseline, page_list, output):
    output = Path(output)
    if output.exists(): raise a.q.Refused('New inventory output required; retain earlier evidence')
    files = a.q.load(page_list)
    if not isinstance(files, list) or any(not isinstance(p, str) or not Path(p).is_absolute() for p in files):
        raise a.q.Refused('Explicit absolute page-file list required')
    reader = a.pin(Path(a.__file__).with_name('unattended_static_native.inc'))
    index = a.inventory.build_index(a.pin(registry), a.q.load(baseline)['editor'], reader, files)
    a.q.receipts.write_receipt(output, index)
    return {'state': 'COMPLETE_SOURCE_INVENTORY_FILES_ONLY', 'meshes': index['path_count'],
            'pages': len(index['pages']), 'path_digest': index['path_digest'],
            'inventory': a.pin(output), 'imports': 0, 'admitted': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('registry', 'baseline', 'page-list', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    print(json.dumps(build(**vars(parser.parse_args())), indent=2))


if __name__ == '__main__': main()
