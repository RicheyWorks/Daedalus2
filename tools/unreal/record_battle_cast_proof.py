"""Record an exact tracked-plugin build and native cast-selection automation result."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import runpy
import shutil


def diagnostics(path):
    reporter=Path(__file__).resolve().parents[1]/'unreal_play/editor_log_report.py'
    module=runpy.run_path(str(reporter),run_name='battle_log_report')
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream):result=module['report'](str(path),False)
    if result:raise ValueError('Editor log has errors: '+stream.getvalue())
    match=re.search(r'errors=(\d+) warnings=(\d+)',stream.getvalue())
    return {'errors':int(match[1]),'warnings':int(match[2]),'details':stream.getvalue().strip(),
            'reporter_sha256':hashlib.sha256(reporter.read_bytes()).hexdigest()}


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
           'editor_log_diagnostics':diagnostics(host/'automation.log'),
           'scope':'Full tracked plugin build and synthetic native clip selection. No imported art or rendered battle claim.'}
    output.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    imported=host/'imported-cast-proof.json'
    if imported.exists():
        art=json.loads((host/'cast-art-manifest.json').read_text(encoding='utf-8'))
        binding=json.loads(imported.read_text(encoding='utf-8'))
        if sorted(row['id'] for row in binding['verified'])!=sorted(art['cast_ids']):
            raise ValueError('Imported cast coverage differs from manifest')
        for name,digest in art['files'].items():
            if hashlib.sha256((host/'Content'/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Imported art changed during probe: '+name)
        imported_log=host/'imported-cast.log'
        imported_text=imported_log.read_text(encoding='utf-8-sig',errors='replace')
        binding.update(production_source_head=manifest['source_head'],
                       production_dll_sha256=proof['production_dll_sha256'],art_inputs=art,
                       editor_log_diagnostics=diagnostics(imported_log),
                       editor_log_sha256=hashlib.sha256(imported_log.read_bytes()).hexdigest(),
                       commandlet_seconds=float(re.search(r'Execution of commandlet took:\s*([\d.]+) seconds',imported_text)[1]),
                       time_scope='Commandlet body only; excludes process startup')
        output.with_name('battle-cast-imported-proof.json').write_text(json.dumps(binding,indent=2)+'\n',encoding='utf-8')
        print('IMPORTED_CAST_PROOF_PASS',len(binding['verified']),len(art['files']))
    print('BATTLE_CAST_PROOF_PASS',manifest['tracked_file_count'],proof['seconds'],tests[0]['duration'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('host',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();record(a.host,a.output)
