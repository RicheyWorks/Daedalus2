"""Compare real native and Java readers, including corrupted fixture refusals."""
import argparse
import subprocess
import tempfile
from pathlib import Path

def run(command, path):
    return subprocess.run([*command, str(path)], capture_output=True, text=True, timeout=30)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cpp', required=True)
    parser.add_argument('--java', default='java')
    parser.add_argument('--classpath', required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    native=[args.cpp]; java=[args.java,'-cp',args.classpath,'InventoryCatalogDump']
    fixtures=sorted((root/'engines/unreal/DaedalusLink/Content/Inventory').glob('*.dic'))
    expected={'world-zero','gallery-city','parcels','bricks','labyrinth','ocean'}
    if {path.stem for path in fixtures}!=expected: raise RuntimeError('Canonical realm catalog set differs')
    for path in fixtures:
        a,b=run(native,path),run(java,path)
        if a.returncode or b.returncode or a.stdout!=b.stdout:
            raise RuntimeError('Catalog parity failed: '+path.name)
        print('PARITY_PASS',path.name)
    with tempfile.TemporaryDirectory() as folder:
        bad=Path(folder)/'bad.dic'
        for text in ['DIC 2\n', 'DIC 1\nrealm TEST\ntab ALL\nitem BAD MISSING - USE Bad\n',
                     'DIC 1\nrealm TEST\ntab ALL\ntab ALL\n',
                     'DIC 1\nrealm TEST\ntab ALL\ndetail MISSING Bad\n']:
            bad.write_text(text)
            if run(native,bad).returncode==0 or run(java,bad).returncode==0:
                raise RuntimeError('Corrupted catalog accepted')
    print('PARITY_PASS four corrupted catalogs refused by both readers')

if __name__=='__main__': main()
