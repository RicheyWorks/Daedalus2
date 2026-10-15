# SPDX-License-Identifier: MIT
"""Check data/ocean/sea-sources.json against the repo, so the Sea Realm source inventory cannot drift.

  * implemented / data-only: the path exists and every listed symbol occurs in it
  * absent: the probe regex matches nothing under probe_roots (.java .h .cpp), so "absent" is a claim the check can lose
  * owner: last git author + commit per path, printed (computed, never stored)

    python tools/ocean/sources_check.py [--self-test]

Last line "SOURCES n/m PASS|FAIL"; exit 0 only on PASS. --self-test: broken copies (canaries) must each FAIL.
"""
import copy
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "ocean", "sea-sources.json")
EXT = (".java", ".h", ".cpp")


def corpus(roots):
    for r in roots:
        for d, _, fs in os.walk(os.path.join(ROOT, r)):
            for f in fs:
                if f.endswith(EXT):
                    p = os.path.join(d, f)
                    yield p, open(p, encoding="utf-8", errors="replace").read()


def owner(path):
    try:
        return subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%h %an %ad", "--date=short", "--", path],
                              capture_output=True, text=True, timeout=30).stdout.strip() or "untracked"
    except OSError:
        return "git unavailable"


def check(doc, out, owners=True):
    res = []
    def ok(name, cond, info=""):
        res.append(bool(cond))
        out.append(("ok   " if cond else "FAIL ") + name + (" " + info if info else ""))
    ids = [e["id"] for e in doc["entries"]] + [a["id"] for a in doc["absent"]]
    ok("ids unique", len(ids) == len(set(ids)))
    for e in doc["entries"]:
        p = os.path.join(ROOT, e["path"])
        ok("%s status known" % e["id"], e["status"] in ("implemented", "data-only"))
        if not os.path.exists(p):
            ok("%s path exists" % e["id"], False, e["path"])
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        miss = [s for s in e["symbols"] if s not in text]
        ok("%s symbols" % e["id"], e["symbols"] and not miss, ("missing " + ", ".join(miss)) if miss else (owner(e["path"]) if owners else ""))
    files = list(corpus(doc["probe_roots"]))
    for a in doc["absent"]:
        rx = re.compile(a["probe"])
        hits = [os.path.relpath(p, ROOT) for p, t in files if rx.search(t)]
        ok("%s absent" % a["id"], not hits, ("found in " + ", ".join(hits[:3])) if hits else "")
    return res


def main(argv):
    doc = json.load(open(DATA, encoding="utf-8"))
    if "--self-test" in argv:
        cans = []
        D = copy.deepcopy(doc); D["entries"][0]["symbols"].append("NoSuchSymbolXyz"); cans.append(("symbol not in file", D))
        D = copy.deepcopy(doc); D["entries"][1]["path"] = "nope/Missing.java"; cans.append(("path missing", D))
        D = copy.deepcopy(doc); D["absent"].append({"id": "terrain", "probe": "OceanTerrain"}); cans.append(("absent claim that is present", D))
        D = copy.deepcopy(doc); D["entries"][2]["status"] = "done"; cans.append(("unknown status", D))
        D = copy.deepcopy(doc); D["absent"].append({"id": D["entries"][0]["id"], "probe": "zzzq"}); cans.append(("duplicate id", D))
        n = 0
        for name, D in cans:
            failed = not all(check(D, [], owners=False))
            print(("ok   " if failed else "FAIL ") + "canary FAILs: " + name)
            n += failed
        print("SOURCES-CANARIES %d/%d %s" % (n, len(cans), "PASS" if n == len(cans) else "FAIL"))
        return 0 if n == len(cans) else 1
    out = []
    res = check(doc, out)
    print("\n".join(out))
    k = sum(res)
    print("SOURCES %d/%d %s" % (k, len(res), "PASS" if k == len(res) else "FAIL"))
    return 0 if k == len(res) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
