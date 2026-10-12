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

print("%d/%d" % (passed, total))
sys.exit(0 if passed == total else 1)
