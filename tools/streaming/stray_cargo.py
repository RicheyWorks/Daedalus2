# SPDX-License-Identifier: MIT
"""Stray Cargo (G531, disk-saver): the census cargo that the G206 pricing never sees.

G206 census_budget.py prices each island from its asset_definitions count. Anything that
is not counted on an island slips through. This reads a World Census `census.json`
(read-only) and lists, per world:

  errors (adrift):
    * dangling:        an asset whose island_slot names no island in its world,
    * duplicate_name:  the same asset name defined twice in one world,
    * count_mismatch:  assets_without_island disagrees with the asset list;
  advisories (littered):
    * stray:           an asset with no island (island_slot null), with the RAM/disk it
                       would add under the G206 model once placed (24 / 96 KiB each),
    * empty_hull:      an island with no assets still paying the base 16384 KiB RAM,
    * shared_file:     the same asset file defined in several worlds (disk the extra
                       definitions cost, 96 KiB each),
    * no_realm:        a world with no realm_id.

Verdict tidy / littered / adrift. Stdlib only, integers only, no clock.

  python tools/streaming/stray_cargo.py CENSUS.json [--json] [--fail-on littered|adrift]

Exit 0 = report printed, 1 = --fail-on and the verdict is at least that bad, 2 = refusal.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-stray-cargo"
MAX_BYTES = 16 * 1024 * 1024
ERRORS = ("dangling", "duplicate_name", "count_mismatch")
ADVISORIES = ("stray", "empty_hull", "shared_file", "no_realm")
RANK = {"tidy": 0, "littered": 1, "adrift": 2}


class StrayError(ValueError):
    pass


def _load_json(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            raise StrayError(f"{path}: too large")
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except OSError as e:
        raise StrayError(f"{path}: {e.strerror}")
    except ValueError:
        raise StrayError(f"{path}: not JSON")


def _slot(v):
    return isinstance(v, int) and not isinstance(v, bool)


def survey(census):
    if not isinstance(census, dict) or census.get("format") != "daedalus-world-census" or census.get("version") != 1:
        raise StrayError("census: format must be daedalus-world-census v1")
    worlds = census.get("worlds")
    if not isinstance(worlds, list) or not worlds:
        raise StrayError("census: worlds must be a nonempty list")
    findings, files, seen = [], {}, set()
    for w in worlds:
        wid = w.get("id") if isinstance(w, dict) else None
        if not isinstance(wid, str) or not wid.strip() or wid in seen:
            raise StrayError("census: bad or duplicate world id")
        seen.add(wid)
        islands = w.get("islands") or []
        assets = w.get("assets") or []
        if not isinstance(islands, list) or not isinstance(assets, list):
            raise StrayError(f"census: world {wid} islands/assets must be lists")
        slots = {}
        for i in islands:
            if not isinstance(i, dict) or not _slot(i.get("slot")):
                raise StrayError(f"census: world {wid} bad island")
            slots[i["slot"]] = i.get("asset_definitions")
        if w.get("realm_id") is None:
            findings.append({"world": wid, "kind": "no_realm"})
        for s in sorted(slots):
            if slots[s] == 0:
                findings.append({"world": wid, "kind": "empty_hull", "slot": s, "ram_kib": cb.BASE_RAM_KIB,
                                 "disk_kib": cb.BASE_DISK_KIB})
        names, strays = {}, 0
        for a in assets:
            if not isinstance(a, dict) or not isinstance(a.get("name"), str):
                raise StrayError(f"census: world {wid} bad asset")
            name, slot, f = a["name"], a.get("island_slot"), a.get("file")
            names[name] = names.get(name, 0) + 1
            if isinstance(f, str) and f:
                files.setdefault(f, set()).add(wid)
            if slot is None:
                strays += 1
                findings.append({"world": wid, "kind": "stray", "asset": name, "file": f,
                                 "ram_kib": cb.PER_ASSET_RAM_KIB, "disk_kib": cb.PER_ASSET_DISK_KIB})
            elif not _slot(slot) or slot not in slots:
                findings.append({"world": wid, "kind": "dangling", "asset": name, "slot": slot})
        for name in sorted(n for n, c in names.items() if c > 1):
            findings.append({"world": wid, "kind": "duplicate_name", "asset": name, "count": names[name]})
        claimed = w.get("assets_without_island")
        if claimed is not None and claimed != strays:
            findings.append({"world": wid, "kind": "count_mismatch", "claimed": claimed, "found": strays})
    for f in sorted(files):
        if len(files[f]) > 1:
            n = len(files[f])
            findings.append({"world": None, "kind": "shared_file", "file": f, "worlds": sorted(files[f]),
                             "disk_kib": (n - 1) * cb.PER_ASSET_DISK_KIB})
    order = {k: i for i, k in enumerate(ERRORS + ADVISORIES)}
    findings.sort(key=lambda x: (order[x["kind"]], x["world"] or "", json.dumps(x, sort_keys=True)))
    counts = {k: sum(1 for x in findings if x["kind"] == k) for k in ERRORS + ADVISORIES}
    hidden = {"ram_kib": sum(x["ram_kib"] for x in findings if x["kind"] == "stray"),
              "disk_kib": sum(x["disk_kib"] for x in findings if x["kind"] == "stray")}
    verdict = "adrift" if any(counts[k] for k in ERRORS) else "littered" if findings else "tidy"
    return {"format": FORMAT, "version": 1, "verdict": verdict, "counts": counts,
            "hidden_cost_kib": hidden,
            "empty_hull_ram_kib": sum(x["ram_kib"] for x in findings if x["kind"] == "empty_hull"),
            "shared_disk_kib": sum(x["disk_kib"] for x in findings if x["kind"] == "shared_file"),
            "findings": findings}


def text(r):
    out = [f"stray cargo: {r['verdict']}; {r['counts']['stray']} stray assets would add "
           f"{r['hidden_cost_kib']['ram_kib']} KiB RAM / {r['hidden_cost_kib']['disk_kib']} KiB disk once placed"]
    for x in r["findings"]:
        bits = " ".join(f"{k}={json.dumps(v)}" for k, v in sorted(x.items()) if k not in ("kind", "world"))
        out.append(f"  {'!' if x['kind'] in ERRORS else '-'} {x['kind']} {x['world'] or '*'} {bits}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Stray Cargo: census assets the G206 pricing never sees.")
    ap.add_argument("census")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=("littered", "adrift"))
    a = ap.parse_args(argv)
    try:
        r = survey(_load_json(a.census))
    except StrayError as e:
        print(f"stray_cargo: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on and RANK[r["verdict"]] >= RANK[a.fail_on] else 0


if __name__ == "__main__":
    sys.exit(main())