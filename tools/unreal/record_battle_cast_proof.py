"""Record an exact tracked-plugin build and native cast-selection automation result."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def record(host, output):
    manifest=json.loads((host/'source-manifest.json').read_text(encoding='utf-8'))
    plugin=host/'Plugins/DaedalusLink'
    prefix='engines/unreal/DaedalusLink/'
    for name,digest in manifest['files'].items():
        if hashlib.sha256((plugin/name.removeprefix(prefix)).read_bytes()).hexdigest()!=digest:
            raise ValueError('Production input changed: '+name)
    expected={name.removeprefix(prefix+'Source/') for name in manifest['files'] if name.startswith(prefix+'Source/')}
    actual={p.relative_to(plugin/'Source').as_posix() for p in (plugin/'Source').rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('Undeclared source additions or missing files')
    log=host/'build.log';text=log.read_text(encoding='utf-8-sig',errors='replace')
    if 'Result: Succeeded' not in text:raise ValueError('Build did not succeed')
    report_path=host/'automation/index.json'
    report=json.loads(report_path.read_text(encoding='utf-8-sig'))
    tests=[t for t in report['tests'] if t['fullTestPath']=='Daedalus.Battle.CastAnimations']
    if len(tests)!=1 or tests[0]['state']!='Success' or tests[0]['warnings'] or tests[0]['errors']:
        raise ValueError('Native cast selection did not pass cleanly')
    dll=plugin/'Binaries/Win64/UnrealEditor-DaedalusLink.dll'
    archive=host/'production-module';archive.mkdir(exist_ok=True)
    shutil.copy2(dll,archive/dll.name)
    proof={**manifest,'seconds':float(re.search(r'Total execution time: ([\d.]+) seconds',text)[1]),
           'actions':int(re.search(r'run (\d+) action',text)[1]),'tests':tests,
           'production_dll_sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),
           'build_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),
           'automation_report_sha256':hashlib.sha256(report_path.read_bytes()).hexdigest(),
           'scope':'Full tracked plugin build and synthetic native clip selection. No imported art or rendered battle claim.'}
    output.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print('BATTLE_CAST_PROOF_PASS',manifest['tracked_file_count'],proof['seconds'],tests[0]['duration'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('host',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();record(a.host,a.output)
