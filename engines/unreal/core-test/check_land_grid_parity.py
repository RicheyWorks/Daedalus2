"""Check compiled native rows and editor Python against the reviewed Java golden output."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def check(native_file):
    root = Path(__file__).resolve().parents[3]
    proof = json.loads((root / 'docs/production/land-grid-parity-proof.json').read_text())
    expected = proof['canonical_output_sha256_lf']
    raw = Path(native_file).read_bytes().replace(b'\r\n', b'\n')
    if len(raw.splitlines()) != 50000 or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Native land grid differs from reviewed Java parity output')
    module_path = root / 'engines/unreal/DaedalusLink/Content/Python/daedalus_land_grid.py'
    spec = importlib.util.spec_from_file_location('land_grid', module_path)
    grid = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grid)
    digest = hashlib.sha256()
    for n in range(grid.COUNT):
        x, y = grid.cell(n)
        east, north = grid.metres(n)
        row = f'{n},{x},{y},{grid.number(x,y)},{grid.ring(n)},{grid.district(n)},{int(east)},{int(north)}\n'
        digest.update(row.encode('ascii'))
    for y in range(grid.SIDE):
        for x in range(grid.SIDE):
            for size in range(1, 5):
                digest.update(f'{x},{y},{size},{grid.estate(x,y,size)}\n'.encode('ascii'))
    if digest.hexdigest() != expected:
        raise ValueError('Editor Python land grid differs from reviewed Java parity output')
    print('LAND_GRID_PARITY_OK native+python+Java-golden: 10000 cells +40000 estate candidates')


if __name__ == '__main__':
    check(sys.argv[1])
