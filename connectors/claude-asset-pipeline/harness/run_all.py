# SPDX-License-Identifier: MIT
"""Run every pipeline suite; print each suite's n/m and the count of green suites last; exit 1 on any red."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUITES = [("glb", ["glb_test.py"]), ("judge", ["judge_test.py"]), ("artqueue", ["artqueue_test.py"]), ("link", ["teamlink_test.py"]), ("e2e", ["e2e.py"] + sys.argv[1:])]

green = 0
for name, args in SUITES:
    p = subprocess.run([sys.executable, os.path.join(HERE, args[0])] + args[1:], capture_output=True, text=True,
                       timeout=900)
    last = (p.stdout.strip().splitlines() or ["(no output)"])[-1]
    ok = p.returncode == 0
    green += ok
    print("%-5s  %-6s %s" % ("ok" if ok else "FAIL", name, last), flush=True)
print("%d/%d" % (green, len(SUITES)))
sys.exit(0 if green == len(SUITES) else 1)
