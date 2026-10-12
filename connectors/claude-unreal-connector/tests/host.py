# SPDX-License-Identifier: MIT
"""Run the Claude Unreal Bridge against fake_unreal, pumping it like the editor's ticks (~60 per second).
Usage: python3 host.py PORT SECONDS
The test add-on test.freeze stops the ticks, the way a modal dialog freezes the real editor."""
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fake_unreal
sys.modules["unreal"] = fake_unreal
sys.path.insert(0, os.path.join(HERE, "..", "plugin", "ClaudeUnrealBridge", "Content", "Python"))
import claude_unreal_bridge as bridge

fake_unreal.LOGDIR = tempfile.mkdtemp()
import remote_execution as fake_rex     # the stand-in, from this tests folder
fake_rex.PROJECT_ROOT = fake_unreal.LOGDIR
bridge.register("test.remote_off", lambda p: setattr(fake_rex, "ENABLED", False) or bridge._remote.update(rx=None, node=None) or {"off": True},
                "Act as an editor with Remote Execution switched off")
bridge.register("test.remote_calls", lambda p: {"calls": [list(c) for c in fake_rex.CALLS]}, "What Remote Execution was asked")
with open(os.path.join(fake_unreal.LOGDIR, "DaedalusRealm.log"), "w") as f:
    f.write("LogInit: Display: start\nLogPython: Error: something broke\nLogPython: Display: Daedalus ok\n")

fake_unreal.NESTED_TICK = lambda: bridge.pump(1 / 60)


def _countdown(p):
    """A project add-on that takes several editor ticks, as a real one might."""
    n = int(p.get("from", 3))
    seen = []
    while n > 0:
        seen.append(n)
        n -= 1
        yield
    return {"counted": seen, "by": p.get("who", "test")}


FROZEN = []
bridge.register("test.freeze", lambda p: FROZEN.append(True) or {"frozen": True}, "Stop ticking, like a modal dialog")
bridge.register("test.countdown", _countdown, "Counts down one number per editor tick", {"from": "int", "who": "str"})
port = bridge.start(int(sys.argv[1]), register_tick=False)
print("bridge on", port, flush=True)
end = time.time() + float(sys.argv[2])
while time.time() < end:
    if not FROZEN:
        fake_unreal.tick()
        bridge.pump(1 / 60)
    time.sleep(1 / 60)
bridge.stop()
