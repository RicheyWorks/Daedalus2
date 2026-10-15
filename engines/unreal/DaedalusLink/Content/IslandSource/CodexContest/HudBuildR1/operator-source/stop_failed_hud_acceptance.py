"""Stop only the known failed owned temporary PIE; no repeat of failed keys."""
import json
from pathlib import Path
import sys

TASK = Path(__file__).parent
sys.path.insert(0, str(TASK))
import hud_targeted_acceptance as h


def stop(record):
    state = h.native("result={'state':state(),'world':w.get_path_name(),'hero':h.get_path_name(),'controller':pc.get_path_name()}\n", True)
    h.require(not state['state']['open'] and state['world'].startswith('/Temp/'), 'unexpected active overlay/world; preserve')
    m = h.Mcp(timeout=40)
    h.require(m.call(h.APP, 'IsPIERunning') is True, 'PIE already stopped; inspect')
    result = {'observed_before': state, 'stop_return': m.call(h.APP, 'StopPIE'),
              'pie_running_after_return': m.call(h.APP, 'IsPIERunning'),
              'reason': 'Candidate failed before keys; world pause/cursor were still owned by this temporary PIE.'}
    observer = h.FOLDER / 'slate-observer.json'
    if observer.exists():
        result['owned_observer_removed'] = m.call(h.SLATE, 'Unobserve', identifier=h.load(observer)['identifier'])
    return result


h.phase('failed-candidate-stop', stop)
