"""Retain the OS-backed loaded module witness; no editor operations."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).parent
sys.path.insert(0, str(TASK))
import activate_hud_native as a

OUT = a.BASE / 'codex-hud-loaded-image-os.json'
if OUT.exists():
    raise RuntimeError('existing OS load witness; inspect it')
journal = a.load(a.OUT)
assert journal['stage'] == 'normal_visible_reopen_dispatched'
pid = journal['new_editor_pid']
command = "$p=Get-Process -Id " + str(int(pid)) + ";$r=@($p.Modules | Where-Object {$_.ModuleName -eq 'UnrealEditor-DaedalusLink.dll'} | Select-Object ModuleName,FileName,ModuleMemorySize); ConvertTo-Json -InputObject $r -Compress"
rows = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', command]))
assert len(rows) == 1
expected_path = a.LIVE / 'Binaries/Win64/UnrealEditor-DaedalusLink.dll'
assert Path(rows[0]['FileName']).resolve() == expected_path.resolve()
payload = next(row for row in journal['payloads'] if row['target'].lower().endswith('.dll'))
assert a.fp(expected_path) == payload['expected']
record = {'utc': datetime.now(timezone.utc).isoformat(), 'stage': 'new_hud_dll_loaded_from_canonical_path',
    'editor_pid': pid, 'loaded_modules': rows, 'backing_file_fingerprint': a.fp(expected_path),
    'candidate_matches_installed_backing_file': True,
    'scope': 'OS module mapping plus backing-file hash; no relocated in-memory hash claim', 'issues': []}
OUT.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(record, indent=2))
