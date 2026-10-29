# SPDX-License-Identifier: MIT
"""Beacon Watch (G505, disk-saver): streaming-budget regression gate over G206 beacons.

Compares a current Census Budget Beacons report (census_budget.py output, format
daedalus-census-budget v1) against a committed baseline report and fails when the
streaming budget got worse:

  * an island's beacon worsens (green < amber < red),
  * a new island arrives amber or red,
  * a world that held every island resident now spills (fits_all_resident true -> false),
  * a world's max_resident drops.

Improvements, new green islands and removed islands are reported but never fail.
Read-only over both reports; stdlib only, integers only, deterministic bytes.

  python tools/streaming/beacon_watch.py BASELINE.json CURRENT.json [-o VERDICT.json] [--strict]

Exit 0 = verdict printed/written, 1 = --strict and the verdict is storm, 2 = refusal.
"""
import argparse
import json
import sys

FORMAT_IN = "daedalus-census-budget"
FORMAT = "daedalus-beacon-watch"
RANK = {"green": 0, "amber": 1, "red": 2}
WORSE = ("worse", "new_hot", "spill", "max_resident_drop")
MAX_BYTES = 4 * 1024 * 1024


class BeaconWatchError(ValueError):
    pass


def _int(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise BeaconWatchError(f"{what}: expected a nonnegative integer")
    return v


def read_report(doc, name):
    """Validate the fields we consume; return {world: (fits, max_resident, {slot: beacon})}."""
    if not isinstance(doc, dict) or doc.get("format") != FORMAT_IN:
        raise BeaconWatchError(f"{name}: format must be {FORMAT_IN}")
    if doc.get("version") != 1 or isinstance(doc.get("version"), bool):
        raise BeaconWatchError(f"{name}: unsupported version")
    worlds = doc.get("worlds")
    if not isinstance(worlds, list):
        raise BeaconWatchError(f"{name}: worlds must be a list")
    out = {}
    for w in worlds:
        wid = w.get("id") if isinstance(w, dict) else None
        if not isinstance(wid, str) or not wid.strip():
            raise BeaconWatchError(f"{name}: world id missing")
        if wid in out:
            raise BeaconWatchError(f"{name}: duplicate world {wid}")
        fits = w.get("fits_all_resident")
        if not isinstance(fits, bool):
            raise BeaconWatchError(f"{name}: world {wid} fits_all_resident must be true/false")
        mr = _int(w.get("max_resident"), f"{name}: world {wid} max_resident")
        isl = w.get("islands")
        if not isinstance(isl, list):
            raise BeaconWatchError(f"{name}: world {wid} islands must be a list")
        slots = {}
        for i in isl:
            if not isinstance(i, dict):
                raise BeaconWatchError(f"{name}: world {wid} bad island")
            s = _int(i.get("slot"), f"{name}: world {wid} slot")
            b = i.get("beacon")
            if b not in RANK:
                raise BeaconWatchError(f"{name}: world {wid} slot {s} beacon must be green/amber/red")
            if s in slots:
                raise BeaconWatchError(f"{name}: world {wid} duplicate slot {s}")
            slots[s] = b
        out[wid] = (fits, mr, slots)
    return out


def findings(base, cur):
    """Sorted list of (world, slot or -1, kind, before, after)."""
    out = []
    for wid in sorted(set(base) | set(cur)):
        if wid not in cur:
            out.append((wid, -1, "world_gone", "present", "absent"))
            continue
        cfits, cmr, cslots = cur[wid]
        if wid not in base:
            out.append((wid, -1, "world_new", "absent", "present"))
            bfits, bmr, bslots = None, None, {}
        else:
            bfits, bmr, bslots = base[wid]
            if bfits and not cfits:
                out.append((wid, -1, "spill", "fits", "spills"))
            elif cfits and not bfits:
                out.append((wid, -1, "unspill", "spills", "fits"))
            if cmr < bmr:
                out.append((wid, -1, "max_resident_drop", str(bmr), str(cmr)))
        for s in sorted(set(bslots) | set(cslots)):
            b, c = bslots.get(s), cslots.get(s)
            if c is None:
                out.append((wid, s, "gone", b, "absent"))
            elif b is None:
                out.append((wid, s, "new_hot" if RANK[c] else "new", "absent", c))
            elif RANK[c] > RANK[b]:
                out.append((wid, s, "worse", b, c))
            elif RANK[c] < RANK[b]:
                out.append((wid, s, "better", b, c))
    return out


def findings_oracle(base_doc, cur_doc):
    """Independent brute-force scan over the raw lists (tests only)."""
    def worlds(doc):
        return doc["worlds"]
    def find(ws, wid):
        hit = [w for w in ws if w["id"] == wid]
        return hit[0] if hit else None
    out = []
    bw, cw = worlds(base_doc), worlds(cur_doc)
    ids = sorted({w["id"] for w in bw} | {w["id"] for w in cw})
    for wid in ids:
        b, c = find(bw, wid), find(cw, wid)
        if c is None:
            out.append((wid, -1, "world_gone", "present", "absent"))
            continue
        if b is None:
            out.append((wid, -1, "world_new", "absent", "present"))
            b = {"islands": [], "fits_all_resident": None, "max_resident": None}
        else:
            if b["fits_all_resident"] is True and c["fits_all_resident"] is False:
                out.append((wid, -1, "spill", "fits", "spills"))
            if b["fits_all_resident"] is False and c["fits_all_resident"] is True:
                out.append((wid, -1, "unspill", "spills", "fits"))
            if c["max_resident"] < b["max_resident"]:
                out.append((wid, -1, "max_resident_drop", str(b["max_resident"]), str(c["max_resident"])))
        order = ["green", "amber", "red"]
        slots = sorted({i["slot"] for i in b["islands"]} | {i["slot"] for i in c["islands"]})
        for s in slots:
            bb = [i["beacon"] for i in b["islands"] if i["slot"] == s]
            cc = [i["beacon"] for i in c["islands"] if i["slot"] == s]
            if not cc:
                out.append((wid, s, "gone", bb[0], "absent"))
            elif not bb:
                out.append((wid, s, "new" if cc[0] == "green" else "new_hot", "absent", cc[0]))
            elif order.index(cc[0]) > order.index(bb[0]):
                out.append((wid, s, "worse", bb[0], cc[0]))
            elif order.index(cc[0]) < order.index(bb[0]):
                out.append((wid, s, "better", bb[0], cc[0]))
    return out


def watch(base_doc, cur_doc):
    base, cur = read_report(base_doc, "baseline"), read_report(cur_doc, "current")
    fs = findings(base, cur)
    counts = {}
    for f in fs:
        counts[f[2]] = counts.get(f[2], 0) + 1
    bad = sum(1 for f in fs if f[2] in WORSE)
    return {
        "format": FORMAT, "version": 1,
        "verdict": "storm" if bad else "calm",
        "regressions": bad,
        "budget_changed": base_doc.get("budget") != cur_doc.get("budget"),
        "cost_model_changed": base_doc.get("cost_model") != cur_doc.get("cost_model"),
        "baseline_snapshot": base_doc.get("snapshot_date"),
        "current_snapshot": cur_doc.get("snapshot_date"),
        "counts": dict(sorted(counts.items())),
        "findings": [{"world": w, "slot": None if s < 0 else s, "kind": k, "before": b, "after": a,
                      "fails": k in WORSE} for w, s, k, b, a in fs],
    }


def dumps(verdict):
    return json.dumps(verdict, sort_keys=True, indent=2) + "\n"


def _load_json(path):
    try:
        with open(path, "rb") as f:
            raw = f.read(MAX_BYTES + 1)
    except OSError as e:
        raise BeaconWatchError(f"{path}: {e.strerror}")
    if len(raw) > MAX_BYTES:
        raise BeaconWatchError(f"{path}: larger than 4 MiB")
    try:
        return json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise BeaconWatchError(f"{path}: not JSON ({e})")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fail when G206 streaming-budget beacons get worse than a baseline.")
    ap.add_argument("baseline")
    ap.add_argument("current")
    ap.add_argument("-o", "--output", help="new verdict file (never overwritten)")
    ap.add_argument("--strict", action="store_true", help="exit 1 when the verdict is storm")
    a = ap.parse_args(argv)
    try:
        v = watch(_load_json(a.baseline), _load_json(a.current))
        text = dumps(v)
        if a.output:
            try:
                with open(a.output, "x", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            except OSError as e:
                raise BeaconWatchError(f"{a.output}: {e.strerror}")
    except BeaconWatchError as e:
        print(f"beacon_watch: refused: {e}", file=sys.stderr)
        return 2
    print(f"beacon watch: {v['verdict']}, {v['regressions']} regressions, {len(v['findings'])} findings")
    for f in v["findings"]:
        if f["fails"]:
            where = f["world"] if f["slot"] is None else f"{f['world']} slot {f['slot']}"
            print(f"  FAIL {f['kind']}: {where} {f['before']} -> {f['after']}")
    if not a.output:
        sys.stdout.write(text)
    return 1 if a.strict and v["verdict"] == "storm" else 0


if __name__ == "__main__":
    sys.exit(main())
