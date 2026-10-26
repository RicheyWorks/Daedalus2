# SPDX-License-Identifier: MIT
"""Count and classify the editor's errors and warnings since Play began, from the project log.

    python tools/unreal_play/editor_log_report.py            # the current log, last Play only
    python tools/unreal_play/editor_log_report.py --all      # the whole log

Prints "errors=N warnings=M" first, then the top classes with counts (one representative line each, timestamps
and counters stripped), so a Play run's result line can carry them. Exit 1 when there is any error, 0 otherwise.
"""
import re
import sys
from collections import Counter

LOG = r"C:\Unreal\DaedalusRealm\Saved\Logs\DaedalusRealm.log"
STRIP = re.compile(r"^\[[^\]]+\]\[\s*\d+\]")
NOISE = re.compile(r"LogPython|LogStaticMesh: Display|Display:")


def classify(line):
    t = STRIP.sub("", line).strip()
    t = re.sub(r"/Game/\S+", "/Game/...", t)            # one class per message shape, not per asset
    t = re.sub(r"UEDPIE_\d+_\S+", "UEDPIE...", t)
    return t[:160]


def report(path=LOG, last_play=True):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError as e:
        print("errors=? warnings=? (no log: %s)" % e)
        return 2
    if last_play:
        starts = [i for i, l in enumerate(lines) if "Bringing World" in l and "up for play" in l]
        if starts:
            lines = lines[starts[-1]:]
    errs, warns = Counter(), Counter()
    for l in lines:
        if NOISE.search(l):
            continue
        if ": Error:" in l or "Error: " in l and "LogUtils" in l:
            errs[classify(l)] += 1
        elif ": Warning:" in l:
            warns[classify(l)] += 1
    print("errors=%d warnings=%d" % (sum(errs.values()), sum(warns.values())))
    for name, c in errs.most_common(8):
        print("  E %4dx %s" % (c, name))
    for name, c in warns.most_common(8):
        print("  W %4dx %s" % (c, name))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(report(last_play="--all" not in sys.argv))
