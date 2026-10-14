# SPDX-License-Identifier: MIT
"""DaedalusLink adds its commands to the Claude Unreal Bridge through the connector's public register() API,
and the connector itself stays free of Daedalus. Runs outside Unreal with the connector's stand-in `unreal`.
Prints n/m last; exits 1 on a failure."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..", "..")
CONN = os.path.join(ROOT, "connectors", "claude-unreal-connector")
sys.path.insert(0, os.path.join(CONN, "tests"))
import fake_unreal
sys.modules["unreal"] = fake_unreal
sys.path.insert(0, os.path.join(CONN, "plugin", "ClaudeUnrealBridge", "Content", "Python"))
sys.path.insert(0, os.path.join(HERE, "..", "DaedalusLink", "Content", "Python"))

passed = total = 0


def check(label, ok, detail=""):
    global passed, total
    total += 1
    passed += bool(ok)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  " + str(detail)))


import claude_unreal_bridge as bridge
before = set(bridge.COMMANDS)
check("the connector alone knows nothing of Daedalus", not any("daedalus" in n for n in before), sorted(before))
src = open(bridge.__file__, encoding="utf-8").read()
check("the connector's code imports nothing from Daedalus", "import_world_package" not in src and "daedalus_view" not in src)

import daedalus_bridge_commands
daedalus_bridge_commands.install()
listed = {c["name"]: c for c in bridge.cmd_list_commands({})["commands"]}
check("DaedalusLink registers daedalus.import_world and daedalus.frame_world",
      "daedalus.import_world" in listed and "daedalus.frame_world" in listed, sorted(listed))
check("each comes with a description and its parameters",
      listed["daedalus.import_world"]["description"] and "server" in listed["daedalus.import_world"]["params"])
check("the built-ins are still there", {"ping", "execute_python", "viewport_screenshot"} <= set(listed))

# daedalus.steps: one editor tick per item (the GPU-watchdog fix at the root, 2026-10-13)
import types
code = "def steps():\n    for i in range(5):\n        yield 'item %d' % i\n    return {'done': 5}\n"
gen = daedalus_bridge_commands.run_steps({"code": code})
check("daedalus.steps is a generator command (the bridge steps it once per tick)", isinstance(gen, types.GeneratorType))
ticks = 0
try:
    while True:
        next(gen); ticks += 1
except StopIteration as stop:
    result = stop.value
check("five items took five ticks: one yield per item", ticks == 5, ticks)
check("every yielded value is collected and the return value is the result", result["steps"] == 5 and result["yielded"][0] == "item 0" and result["result"] == {"done": 5}, result)
bad = daedalus_bridge_commands.run_steps({"code": "def steps():\n    yield 1\n    raise RuntimeError('boom at 2')\n"})
try:
    while True:
        next(bad)
except StopIteration as stop:
    r2 = stop.value
check("an error inside a step ends the run with the count so far and the error text", r2["steps"] == 1 and "boom at 2" in r2["error"], r2)
try:
    daedalus_bridge_commands.run_steps({"code": "x = 1\n"}).send(None)
    check("code without steps() is refused", False)
except ValueError:
    check("code without steps() is refused", True)

print("%d/%d" % (passed, total))
sys.exit(0 if passed == total else 1)
