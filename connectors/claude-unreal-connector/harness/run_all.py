# SPDX-License-Identifier: MIT
"""Run every suite in harness/suites.json and judge each one from its exit code and its last "n/m" line.
(CSRBT tools/verify/run_all.py and FlowersForever scripts/verify_harness.py, cut down.)

Marks: ok, FAIL (non-zero exit), FAIL* (exit 0 but a FAIL line, or n < m), SHORT (counted fewer checks than
its floor), EMPTY (no n/m at all). Writes ledgers/runs.json and prints n/m over suites last.

    python -m harness.run_all [-j 3] [--raise-floors] [--root DIR]
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import ledger

HERE = os.path.dirname(os.path.abspath(__file__))
SCORE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")
FAIL_LINE = re.compile(r"^\s*FAIL\b", re.M)


def score(out):
    for line in reversed(out.strip().splitlines()):
        m = SCORE.match(line)
        if m:
            return int(m.group(1)), int(m.group(2))
    return None, None


def judge(rc, out, floor):
    got, tot = score(out)
    if rc != 0:
        return "FAIL", got, tot
    if got is None or not tot:
        return "EMPTY", got, tot
    if got < tot or FAIL_LINE.search(out):
        return "FAIL*", got, tot
    if tot < floor:
        return "SHORT", got, tot
    return "ok", got, tot


def run_one(suite, root):
    env = dict(os.environ, PYTHONPATH=root)
    try:
        r = subprocess.run([sys.executable] + suite["cmd"], cwd=root, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=suite.get("timeout", 300))
        out, rc = r.stdout.decode("utf-8", "replace"), r.returncode
    except subprocess.TimeoutExpired as e:
        out, rc = (e.stdout or b"").decode("utf-8", "replace") + "\nTIMEOUT", 124
    mark, got, tot = judge(rc, out, suite.get("floor", 1))
    return {"name": suite["name"], "mark": mark, "got": got, "total": tot, "floor": suite.get("floor", 1),
            "rc": rc, "tail": out.strip().splitlines()[-8:]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("-j", type=int, default=3)
    ap.add_argument("--root", default=os.path.dirname(HERE))
    ap.add_argument("--raise-floors", action="store_true", help="lift each passing suite's floor to its count")
    ap.add_argument("--no-ledger", action="store_true", help="don't write ledgers/runs.json (the mutant runner)")
    a = ap.parse_args(argv)
    cfg_path = os.path.join(a.root, "harness", "suites.json")
    with io.open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    with ThreadPoolExecutor(max_workers=max(1, a.j)) as pool:
        results = list(pool.map(lambda s: run_one(s, a.root), cfg["suites"]))
    for r in results:
        print("%-6s %-10s %s/%s (floor %s)" % (r["mark"], r["name"], r["got"], r["total"], r["floor"]))
        if r["mark"] != "ok":
            for t in r["tail"]:
                print("         | " + t)
    good = sum(1 for r in results if r["mark"] == "ok")
    if a.raise_floors:
        for s, r in zip(cfg["suites"], results):
            if r["mark"] == "ok" and r["total"] > s["floor"]:
                s["floor"] = r["total"]
        with io.open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    if not a.no_ledger:
        ledger.record("runs", "standin", {"suites": results, "ok": good, "of": len(results)})
    print("%d/%d" % (good, len(results)))
    return 0 if good == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
