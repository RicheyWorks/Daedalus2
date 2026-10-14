"""Record the completed production build/test snapshot before adding network fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def record(host, output, prefix='ocean-hull-profile'):
    if not re.fullmatch('[a-z0-9-]+', prefix):
        raise ValueError('Expected a simple proof filename prefix')
    manifest = json.loads((host/'source-manifest.json').read_text(encoding='utf-8-sig'))
    plugin = host/'Plugins/DaedalusLink'
    for name, expected in manifest['files'].items():
        relative = name.removeprefix('engines/unreal/DaedalusLink/')
        if hashlib.sha256((plugin/relative).read_bytes()).hexdigest() != expected:
            raise ValueError('Production source snapshot changed')
    expected_source = {name.removeprefix('engines/unreal/DaedalusLink/')
                       for name in manifest['files'] if '/Source/' in name}
    actual_source = {path.relative_to(plugin).as_posix()
                     for path in (plugin/'Source').rglob('*') if path.is_file()}
    if actual_source != expected_source:
        raise ValueError('Production build proof must precede test fixture additions')
    log = (host/'build.log').read_text(encoding='utf-8-sig', errors='replace')
    if 'Result: Succeeded' not in log:
        raise ValueError('Build has not succeeded')
    seconds = float(re.search(r'Total execution time: ([0-9.]+) seconds', log)[1])
    report = json.loads((host/'automation/index.json').read_text(encoding='utf-8-sig'))
    expected = {'Daedalus.Ocean.HeroDockInteraction', 'Daedalus.Ocean.HostChunkDecoder',
                'Daedalus.Ocean.HostEligibility', 'Daedalus.Ocean.SectorGeometry', 'Daedalus.Ocean.HullProfile'}
    passed = {t['fullTestPath'] for t in report['tests'] if t['state']=='Success'}
    if passed != expected or report['failed'] or report['succeededWithWarnings'] or report['notRun']:
        raise ValueError('Expected five successful native tests without test warnings')
    dll = plugin/'Binaries/Win64/UnrealEditor-DaedalusLink.dll'
    archived = host/'production-module/UnrealEditor-DaedalusLink.dll'
    archived.parent.mkdir(exist_ok=True)
    shutil.copy2(dll, archived)
    actions = int(re.search(r'\bto run (\d+) action', log)[1])
    proof = dict(manifest, seconds=seconds, actions=actions,
                 production_dll_sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),
                 build_log_sha256=hashlib.sha256((host/'build.log').read_bytes()).hexdigest(),
                 scope='Fresh complete production plugin; no test fixture overlay')
    output.mkdir(parents=True, exist_ok=True)
    (output/(prefix+'-build-proof.json')).write_text(json.dumps(proof, indent=2)+'\n', encoding='utf-8')
    shutil.copy2(host/'automation/index.json', output/(prefix+'-runtime-proof.json'))
    print(prefix.upper().replace('-', '_')+'_PRODUCTION_PROOF_PASS', seconds, 'seconds;', len(passed), 'native tests')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('host',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prefix',default='ocean-hull-profile')
    a=p.parse_args();record(a.host.resolve(),a.output.resolve(),a.prefix)
