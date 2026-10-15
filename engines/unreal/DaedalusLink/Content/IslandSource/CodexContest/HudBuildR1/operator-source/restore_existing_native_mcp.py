"""Restore the pre-existing project MCP listener through its supported command."""
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).parent / 'contest-island-production'
BASE = ROOT / 'engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
OUT = BASE / 'codex-native-mcp-runtime-restore.json'
sys.path.insert(0, str(ROOT / 'connectors/claude-asset-pipeline'))
from asset_pipeline import wire

if OUT.exists():
    raise RuntimeError('Inspect retained outcome before any retry')
with socket.socket() as probe:
    probe.settimeout(3)
    if probe.connect_ex(('127.0.0.1', 8000)) == 0:
        raise RuntimeError('Existing listener present; do not restart it')
record = {'utc': datetime.now(timezone.utc).isoformat(),
          'stage': 'supported_runtime_start_dispatching',
          'target': '127.0.0.1:8000/mcp', 'configuration_changes': False,
          'editor_restart': False, 'command': 'ModelContextProtocol.StartServer 8000',
          'listener_absent_before_dispatch': True}
OUT.write_text(json.dumps(record, indent=2)+'\n')
code = '''# Codex restore existing native MCP through supported command
import unreal,sys
b=sys.modules['claude_unreal_bridge']
others=[req.get('type') for gen,req,box in b._running if req.get('type')!='execute_python' or not (req.get('params') or {}).get('code','').startswith('# Codex restore existing native MCP through supported command')]
dirty_maps=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
dirty_content=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
pie=bool(unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor())
if others or b._jobs.qsize() or b._remote_lock.locked() or pie or dirty_maps or dirty_content:raise RuntimeError('Preserve current active or dirty operation')
unreal.SystemLibrary.execute_console_command(None,'ModelContextProtocol.StartServer 8000')
result={'runtime_command_dispatched':True,'pie':pie,'dirty_maps':dirty_maps,'dirty_content':dirty_content,'other_running':others,'queued':b._jobs.qsize(),'world':unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name()}
'''
reply = wire.obj(wire.call(wire.UNREAL, 'execute_python', code=code,
    unattended=False, timeout=30, side='Unreal'), side='Unreal', what='supported native MCP runtime restore')
record.update(stage='runtime_command_returned_listener_and_mcp_readback_pending', native=reply,
              utc_returned=datetime.now(timezone.utc).isoformat())
OUT.write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record))
