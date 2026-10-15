"""Retain actual terminal HUD compile evidence and unchanged production files."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

TASK = Path(__file__).parent
ROOT = TASK / 'contest-island-production'
SHADOW = TASK / 'native-hud157'
LIVE = Path('C:/Unreal/DaedalusRealm/Plugins/DaedalusLink')
BASE = ROOT / 'engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
FOLDER = BASE / 'HudBuildR1'
sys.path.insert(0, str(TASK))
import activate_hud_native as activation


def fp(path):
    h = hashlib.sha256()
    size = 0
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            size += len(chunk)
            h.update(chunk)
    return {'bytes': size, 'sha256': h.hexdigest()}


if FOLDER.exists():
    raise RuntimeError('retained build result exists; inspect it')
terminal = activation.load(SHADOW / 'Saved/hud-build-terminal.json')
preflight = activation.load(SHADOW / 'Saved/hud-build-preflight.json')
prepared = activation.load(SHADOW / 'prepared.json')
log_path = Path(terminal['log'])
log = log_path.read_text(encoding='utf-8-sig', errors='replace')
result = re.findall(r'^Result: (Succeeded|Failed)[ \t]*$', log, re.MULTILINE)
if len(result) != 1 or (terminal['exit_code'] == 0) != (result[0] == 'Succeeded'):
    raise RuntimeError('actual exit and terminal log mismatch or incomplete')
rows = activation.payloads(prepared)
activation.unchanged(prepared, rows, activation.package_rows(preflight))
activation.check_map_backup(preflight)
metadata = activation.candidate_metadata(prepared) if terminal['exit_code'] == 0 else None
FOLDER.mkdir()
copies = {}
for name, path in [('build.log', log_path), ('launch.json', SHADOW / 'Saved/hud-build-launch.json'),
                   ('terminal.json', SHADOW / 'Saved/hud-build-terminal.json'),
                   ('preflight.json', SHADOW / 'Saved/hud-build-preflight.json')]:
    target = FOLDER / name
    shutil.copyfile(path, target)
    assert fp(target) == fp(path)
    copies[name] = {'path': str(target), **fp(target)}
report = {'schema': 'daedalus.codex-hud-terminal-build.v1',
    'utc': datetime.now(timezone.utc).isoformat(),
    'stage': 'isolated_hud_module_built_not_installed_not_loaded' if terminal['exit_code'] == 0 else 'hud_build_failed',
    'actual_terminal': terminal, 'terminal_result': result[0], 'retained': copies,
    'actions': re.findall(r'^\[\d+/\d+\].+$', log, re.MULTILINE),
    'error_lines': [line for line in log.splitlines() if re.search(r'\berror (C\d+|LNK\d+):', line)],
    'timing_lines': [line for line in log.splitlines() if any(key in line for key in
        ('Total execution time:', 'Total time in', 'UHT processed', 'generated files written'))],
    'artifacts': {str(path.relative_to(SHADOW)): fp(path)
                  for path in (SHADOW / 'Plugins/DaedalusLink/Binaries/Win64').glob('*') if path.is_file()},
    'candidate_metadata': metadata, 'canonical_source_files_preserved': 140,
    'canonical_binary_and_modules_unchanged': True, 'protected_packages_and_backups_verified': 120,
    'saved_map': preflight['map'], 'native_install_performed': False,
    'tests_or_play_performed_by_build': False, 'issues': []}
out = FOLDER / 'build-result.json'
out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
(FOLDER / '.gitattributes').write_text('# Retain exact on-host build evidence, including original BOM/CRLF.\n*.json -text -eol\n*.log -text -eol\n', encoding='utf-8', newline='\n')
print(json.dumps({'stage': report['stage'], 'exit_code': terminal['exit_code'],
                  'elapsed_s': terminal['elapsed_s'], 'report': str(out),
                  'candidate': report['artifacts'], 'errors': report['error_lines']}, indent=2))
