"""Restore the same existing MCP listener after the authorized normal reopen."""
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import sys

TASK = Path(__file__).parent
ROOT = TASK / 'contest-island-production'
BASE = ROOT / 'engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
OUT = BASE / 'codex-hud-restored-mcp.json'
sys.path.insert(0, str(ROOT / 'connectors/claude-asset-pipeline'))
sys.path.insert(0, str(ROOT / 'tools'))
from asset_pipeline import wire
from unreal_mcp.client import Mcp

if OUT.exists():
    raise RuntimeError('retained MCP restoration outcome exists; inspect it')
loaded = json.loads((BASE / 'codex-hud-restored-readback.json').read_text())
assert loaded['issues'] == []
with socket.socket() as probe:
    probe.settimeout(3)
    present = probe.connect_ex(('127.0.0.1', 8000)) == 0
record = {'utc': datetime.now(timezone.utc).isoformat(),
    'stage': 'existing_listener_present' if present else 'same_runtime_listener_restore_dispatching',
    'target': '127.0.0.1:8000/mcp', 'listener_present_before': present,
    'configuration_changes': False, 'editor_restarted_by_this_step': False}
def keep():
    OUT.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
keep()
if not present:
    tree = ast.parse((TASK / 'restore_existing_native_mcp.py').read_text())
    code = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'code' for t in node.targets))
    record['command'] = 'ModelContextProtocol.StartServer 8000'
    record['native'] = wire.obj(wire.call(wire.UNREAL, 'execute_python', code=code,
        unattended=False, timeout=30, side='Unreal'), side='Unreal', what='restore same existing native MCP listener')
    record['stage'] = 'supported_runtime_command_returned'
    keep()
record['mcp_pie_running'] = Mcp(timeout=15).call('EditorToolset.EditorAppToolset', 'IsPIERunning')
assert record['mcp_pie_running'] is False
record['stage'] = 'existing_mcp_restored_fresh_native_response_verified'
keep()
print(json.dumps(record, indent=2))
