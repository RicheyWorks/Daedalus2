# SPDX-License-Identifier: MIT
"""Generate a DSB 1 island streaming budget manifest from the island data in this repo (ADR-063, disk-saver).

Sources: every data/islands/*/layout.json that has origin_cm and placements, plus data/islands/streaming_extra.json
(islands whose layout is not in a layout.json, e.g. DiskSaver at cell 4000000,4000000). Per island the cost is an
ESTIMATE, not a measurement: ram_kib = BASE_RAM + placements * PER_PLACEMENT_RAM, disk likewise; an island can pin
exact numbers with "streaming": {"ram_kib": N, "disk_kib": N} in its layout. Output is the canonical DSB 1 text,
re-parsed before it is written so a bad manifest can never be produced.

  python tools/streaming/dsb_manifest.py            # print to stdout
  python tools/streaming/dsb_manifest.py -o data/islands/streaming.dsb
  python tools/streaming/dsb_manifest.py --check data/islands/streaming.dsb   # exit 1 if the file is stale
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsb  # noqa: E402

BASE_RAM_KIB = 16384
PER_PLACEMENT_RAM_KIB = 24
BASE_DISK_KIB = 4096
PER_PLACEMENT_DISK_KIB = 96
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def island_id(name):
    s = re.sub(r"[^A-Za-z0-9_]", "_", str(name)).strip("_") or "island"
    return s[:64]


def cost(placements, pinned=None):
    pinned = pinned or {}
    ram = int(pinned.get("ram_kib", BASE_RAM_KIB + placements * PER_PLACEMENT_RAM_KIB))
    disk = int(pinned.get("disk_kib", BASE_DISK_KIB + placements * PER_PLACEMENT_DISK_KIB))
    return max(1, ram), max(1, disk)


def entry(doc, source):
    o = doc.get("origin_cm")
    if not (isinstance(o, list) and len(o) >= 2 and all(isinstance(v, (int, float)) for v in o[:2])):
        return None
    pl = doc.get("placements")
    n = len(pl) if isinstance(pl, list) else int(doc.get("placement_count", 0))
    ram, disk = cost(n, doc.get("streaming"))
    return (island_id(doc.get("island", os.path.basename(os.path.dirname(source)))), int(round(o[0])), int(round(o[1])), ram, disk)


def collect(root=ROOT):
    found, skipped = [], []
    base = os.path.join(root, "data", "islands")
    for d in sorted(os.listdir(base)):
        p = os.path.join(base, d, "layout.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                e = entry(json.load(f), p)
            (found if e else skipped).append(e or p)
    extra = os.path.join(base, "streaming_extra.json")
    if os.path.isfile(extra):
        with open(extra, encoding="utf-8") as f:
            for doc in json.load(f).get("islands", []):
                e = entry(doc, extra)
                (found if e else skipped).append(e or doc.get("island", "?"))
    ids = [e[0] for e in found]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise dsb.DsbError("duplicate island ids across sources: " + ", ".join(dupes))
    return found, skipped


def build(root=ROOT):
    found, skipped = collect(root)
    text = dsb.write(found)
    dsb.parse(text)   # never emit something the C++/Java parsers would refuse
    return text, skipped


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out")
    ap.add_argument("--check", help="compare against an existing manifest; exit 1 if different")
    ap.add_argument("--root", default=ROOT)
    a = ap.parse_args(argv)
    text, skipped = build(a.root)
    for s in skipped:
        print("skipped (no origin_cm): " + str(s), file=sys.stderr)
    if a.check:
        with open(a.check, encoding="utf-8", newline="") as f:
            same = f.read() == text
        print("up to date" if same else "STALE: regenerate with -o", file=sys.stderr)
        return 0 if same else 1
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
