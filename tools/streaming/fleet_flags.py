# SPDX-License-Identifier: MIT
"""Fleet Flags (G533, disk-saver): the G206 streaming budget rolled up by realm.

Every earlier streaming tool works per world or per island. This reads a World Census
`census.json` (read-only), prices it with G206 census_budget.py, and per realm (worlds with
no realm_id are grouped as the unrealmed, id null) reports:

  * worlds, islands, asset_definitions, RAM/disk totals,
  * beacon counts (green/amber/red) and spilling worlds,
  * the heaviest world (most RAM, then disk, then id),
  * a flag: red if any island is red or any world spills, amber if any island is amber, else green.

It also checks the census `realms[]` tallies (worlds, islands, asset_definitions) against
the worlds list and reports each disagreement as a tally_mismatch.

Verdict: fair (every flag green), signal (some amber, no red), distress (some red flag).
Stdlib only, integers only, no clock.

  python tools/streaming/fleet_flags.py CENSUS.json [--config CFG] [--json] [--fail-on-distress]

Exit 0 = report printed, 1 = --fail-on-distress and (distress or any tally_mismatch), 2 = refusal.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-fleet-flags"
MAX_BYTES = 16 * 1024 * 1024
RANK = {"green": 0, "amber": 1, "red": 2}


class FlagError(ValueError):
    pass


def _load_json(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            raise FlagError(f"{path}: too large")
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except OSError as e:
        raise FlagError(f"{path}: {e.strerror}")
    except ValueError:
        raise FlagError(f"{path}: not JSON")


def _rkey(r):
    return (r is not None, r or "")


def muster(census, cfg):
    try:
        rep = cb.plan(census, cfg)
    except cb.CensusBudgetError as e:
        raise FlagError(str(e))
    realm_of = {}
    for w in census["worlds"]:
        r = w.get("realm_id")
        if r is not None and (not isinstance(r, str) or not r.strip()):
            raise FlagError(f"census: world {w['id']} realm_id must be a nonempty string or null")
        realm_of[w["id"]] = r
    realms = {}
    for w in rep["worlds"]:
        rid = realm_of[w["id"]]
        g = realms.setdefault(rid, {"realm": rid, "worlds": 0, "islands": 0, "asset_definitions": 0, "ram_kib": 0,
                                    "disk_kib": 0, "green": 0, "amber": 0, "red": 0, "worlds_spilling": 0, "_heavy": None})
        g["worlds"] += 1
        g["islands"] += len(w["islands"])
        g["asset_definitions"] += sum(i["asset_definitions"] for i in w["islands"])
        g["ram_kib"] += w["total_ram_kib"]
        g["disk_kib"] += w["total_disk_kib"]
        for i in w["islands"]:
            g[i["beacon"]] += 1
        g["worlds_spilling"] += 0 if w["fits_all_resident"] else 1
        key = (-w["total_ram_kib"], -w["total_disk_kib"], w["id"])
        if g["_heavy"] is None or key < g["_heavy"]:
            g["_heavy"] = key
    out = []
    for rid in sorted(realms, key=_rkey):
        g = realms[rid]
        g["heaviest_world"] = g.pop("_heavy")[2]
        g["flag"] = "red" if g["red"] or g["worlds_spilling"] else "amber" if g["amber"] else "green"
        out.append(g)
    mismatches = []
    claimed = census.get("realms")
    if claimed is not None:
        if not isinstance(claimed, list):
            raise FlagError("census: realms must be a list")
        seen = set()
        for c in claimed:
            if not isinstance(c, dict) or "id" not in c:
                raise FlagError("census: bad realm row")
            rid = c["id"]
            seen.add(rid)
            mine = realms.get(rid)
            for k in ("worlds", "islands", "asset_definitions"):
                if k not in c:
                    continue
                if k == "asset_definitions":
                    have = sum(w.get("asset_definitions", 0) for w in census["worlds"] if realm_of[w["id"]] == rid)
                else:
                    have = mine[k] if mine else 0
                if c[k] != have:
                    mismatches.append({"realm": rid, "field": k, "claimed": c[k], "found": have})
        for rid in sorted(set(realms) - seen, key=_rkey):
            mismatches.append({"realm": rid, "field": "missing_row", "claimed": None, "found": realms[rid]["worlds"]})
    flags = {g["flag"] for g in out}
    verdict = "distress" if "red" in flags else "signal" if "amber" in flags else "fair"
    return {"format": FORMAT, "version": 1, "budget": rep["budget"], "realms": out,
            "tally_mismatches": mismatches, "verdict": verdict}


def text(r):
    out = [f"fleet flags: {r['verdict']} ({len(r['realms'])} realms, {len(r['tally_mismatches'])} tally mismatches)"]
    for g in r["realms"]:
        out.append(f"  {g['realm'] or '(unrealmed)'}: {g['flag']} flag; {g['worlds']} worlds, {g['islands']} islands, "
                   f"{g['ram_kib']} KiB RAM, {g['disk_kib']} KiB disk; {g['green']}/{g['amber']}/{g['red']} g/a/r, "
                   f"{g['worlds_spilling']} spilling; heaviest {g['heaviest_world']}")
    for m in r["tally_mismatches"]:
        out.append(f"  ! realm {m['realm'] or '(unrealmed)'} {m['field']}: census says {m['claimed']}, worlds say {m['found']}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fleet Flags: G206 streaming budget rolled up by realm.")
    ap.add_argument("census")
    ap.add_argument("--config", default=cb.DEFAULT_CONFIG)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-distress", action="store_true")
    a = ap.parse_args(argv)
    try:
        r = muster(_load_json(a.census), _load_json(a.config))
    except FlagError as e:
        print(f"fleet_flags: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on_distress and (r["verdict"] == "distress" or r["tally_mismatches"]) else 0


if __name__ == "__main__":
    sys.exit(main())