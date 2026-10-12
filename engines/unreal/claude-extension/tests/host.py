# SPDX-License-Identifier: MIT
"""Run the Claude Unreal Bridge against fake_unreal, pumping it like the editor's ticks (~60 per second).
Usage: python3 host.py PORT SECONDS [freeze_after_seconds]"""
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fake_unreal
sys.modules["unreal"] = fake_unreal
sys.path.insert(0, os.path.join(HERE, "..", "..", "DaedalusLink", "Content", "Python"))
import claude_unreal_bridge as bridge

fake_unreal.LOGDIR = tempfile.mkdtemp()
with open(os.path.join(fake_unreal.LOGDIR, "DaedalusRealm.log"), "w") as f:
    f.write("LogInit: Display: start\nLogPython: Error: something broke\nLogPython: Display: Daedalus ok\n")

fake_unreal.NESTED_TICK = lambda: bridge.pump(1 / 60)
port = bridge.start(int(sys.argv[1]), register_tick=False)
print("bridge on", port, flush=True)
end = time.time() + float(sys.argv[2])
freeze = time.time() + float(sys.argv[3]) if len(sys.argv) > 3 else None
while time.time() < end:
    if freeze is None or time.time() < freeze:
        fake_unreal.tick()
        bridge.pump(1 / 60)
    time.sleep(1 / 60)
bridge.stop()
