# SPDX-License-Identifier: MIT
"""Measure per-island streaming costs from an Unreal project's Content folder (read-only; ADR-063, disk-saver).

Walks the content folders each island owns (data/islands/streaming_sources.json) and sums file sizes:
  disk_kib = every package file (.uasset .umap .uexp .ubulk .uptnl) in those folders  -> MEASURED
  ram_kib  = the loadable payload (.uasset .uexp .ubulk .uptnl, no .umap) * RAM_FACTOR_PCT/100 -> DERIVED
Editor packages are not cooked, so ram_kib is an upper-bound proxy until a cooked/in-game memreport replaces it.
Writes data/islands/streaming_measured.json, which dsb_manifest.py uses ahead of the placement-count estimate.
Never writes inside the Unreal project and never needs the editor.

  python tools/streaming/dsb_measure.py --content C:/Unreal/DaedalusRealm/Content -o data/islands/streaming_measured.json
"""
import argparse
import datetime
import json
import os
import sys

PACKAGE_EXT = {".uasset", ".umap", ".uexp", ".ubulk", ".uptnl"}
RAM_EXT = PACKAGE_EXT - {".umap"}
RAM_FACTOR_PCT = 100
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def ceil_kib(n):
    return max(1, (n + 1023) // 1024)


def measure_dirs(content, dirs):
    disk = ram = files = 0
    missing = []
    for d in dirs:
        p = os.path.join(content, *d.replace("\\", "/").strip("/").split("/"))
        if not os.path.isdir(p):
            missing.append(d)
            continue
        for base, _, names in os.walk(p):
            for n in names:
                ext = os.path.splitext(n)[1].lower()
                if ext not in PACKAGE_EXT:
                    continue
                size = os.path.getsize(os.path.join(base, n))
                disk += size
                files += 1
                if ext in RAM_EXT:
                    ram += size
    return {"disk_kib": ceil_kib(disk), "ram_kib": ceil_kib(ram * RAM_FACTOR_PCT // 100), "files": files, "missing": missing}


def measure(content, sources):
    out = {}
    for isl in sources.get("islands", []):
        m = measure_dirs(content, isl.get("content_dirs", []))
        if m["files"] == 0:
            m["note"] = "no package files found; dsb_manifest.py keeps the estimate"
        out[isl["island"]] = m
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content", required=True, help="the Unreal project's Content folder")
    ap.add_argument("--sources", default=os.path.join(ROOT, "data", "islands", "streaming_sources.json"))
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)
    with open(a.sources, encoding="utf-8") as f:
        sources = json.load(f)
    doc = {"_comment": "Written by tools/streaming/dsb_measure.py. disk_kib measured from editor package files; "
                       "ram_kib is a derived upper-bound proxy (uncooked payload) until an in-game memreport.",
           "measured_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "ram_factor_pct": RAM_FACTOR_PCT, "islands": measure(a.content, sources)}
    text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
