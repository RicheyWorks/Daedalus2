"""Explicitly release compute after safe HUD rejection/rollback; no app launch."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import urllib.request

TASK = Path(__file__).parent
BASE = TASK / 'contest-island-production/engines/unreal/DaedalusLink/Content/IslandSource/CodexContest'
OUT = BASE / 'codex-hud-compute-release.json'
HUB = 'http://127.0.0.1:9890'


def post(path, data):
    request = urllib.request.Request(HUB + path, data=json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    return json.load(urllib.request.urlopen(request, timeout=10))


def keep(record):
    OUT.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')


if OUT.exists():
    raise RuntimeError('retained release exists; inspect before any retry')
restored = json.loads((BASE / 'codex-hud-restored-readback.json').read_text())
mcp = json.loads((BASE / 'codex-hud-restored-mcp.json').read_text())
assert restored['issues'] == [] and restored['stage'] == 'prior_working_binary_restored_loaded_and_preserved'
assert mcp['stage'] == 'existing_mcp_restored_fresh_native_response_verified' and mcp['mcp_pie_running'] is False
command = r"""$os=Get-CimInstance Win32_OperatingSystem;$p=@(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and ($_.Name -match '^(cl|link|UnrealBuildTool)\.exe$' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'blender.exe' -and $_.ProcessId -ne 3668) -or ($_.CommandLine -match 'claude-hd-batch-v2-w' -and $_.Name -match 'powershell|pwsh')) }); [pscustomobject]@{utc=[DateTime]::UtcNow.ToString('o');free_physical_KiB=$os.FreePhysicalMemory;free_virtual_KiB=$os.FreeVirtualMemory;heavy_processes=@($p | Select-Object ProcessId,Name,CommandLine)} | ConvertTo-Json -Depth 5 -Compress"""
resources = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', command]))
assert resources['heavy_processes'] == []
before = json.load(urllib.request.urlopen(HUB + '/locks', timeout=10))
assert before['compute']['holder'] == 'codex-play-guard'
record = {'schema': 'daedalus.codex-hud-compute-release.v1',
    'utc': datetime.now(timezone.utc).isoformat(), 'stage': 'compute_release_dispatch_pending',
    'resources': resources, 'leases_before': before, 'build_exit_code': 0,
    'hud_candidate_accepted': False, 'known_prior_binary_loaded': True,
    'next_owner': 'pootscoot-practical-apps', 'app_compile_dispatched': False,
    'app_precondition': 'Fresh app-owner resource and no-conflict preflight; release is not a current RAM safety claim.',
    'unreal_custody_transferred': False}
keep(record)
record['unlock_reply'] = post('/unlock', {'me': 'codex-play-guard', 'name': 'compute'})
record['leases_after'] = json.load(urllib.request.urlopen(HUB + '/locks', timeout=10))
assert record['leases_after'].get('compute', {}).get('holder') != 'codex-play-guard'
assert record['leases_after']['unreal']['holder'] == 'codex-play-guard'
record['stage'] = 'compute_explicitly_released_app_compile_next_after_fresh_resource_check'
keep(record)
text = ('COMPUTE RELEASED. One HUD build exited0 (UBT350.13s); candidate e2b00824 installed/loaded but FAILED targeted acceptance: Hero initially opened Pong, then canvas absent/open=false before any key, pause/cursor remained true. Cause unknown; no second build. Owned PIE ended, exact user saves restored, slow single map load reconciled without replay. Normal rollback restored only5 prior leaves; current editor PID' + str(restored['editor_pid']) + ' loads old80eca DLL, all140source/120packages/101actors/map5690/camera preserved; clean queue/PIE and existing MCP verified. App compile-only is NEXT under its own fresh no-conflict/resource preflight. Current free physical/virtual KiB=' + str(resources['free_physical_KiB']) + '/' + str(resources['free_virtual_KiB']) + '; this release does NOT assert sufficient RAM. Do not install older f498 whole DLL. Unreal custody remains codex-play-guard. Exact receipts codex-hud-restored-readback.json and codex-hud-compute-release.json; full candidate/error/rollback evidence being published to existing PR147.')
record['messages'] = []
for recipient in ('pootscoot-coordination', 'pootscoot-practical-apps'):
    payload = {'from': 'codex-play-guard', 'to': recipient, 'type': 'handoff',
        'topic': 'serial-build-window-after-current-exports', 'body': {'text': text}}
    if recipient == 'pootscoot-coordination':
        payload['reply_to'] = 31557
    record['messages'].append({'recipient': recipient, 'reply': post('/send', payload)})
    keep(record)
record['request_ack'] = post('/ack', {'me': 'codex-play-guard', 'id': 31557})
post('/heartbeat', {'me': 'codex-play-guard', 'status': 'HUD build0; candidate acceptance failed; prior80eca restored PID67184;120packages/101actors/map/saves preserved; compute RELEASED for app fresh preflight.'})
keep(record)
print(json.dumps({key: record[key] for key in ('stage', 'resources', 'leases_after', 'messages')}, indent=2))
