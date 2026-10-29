# SPDX-License-Identifier: MIT
"""Plimsoll Lines (G522, disk-saver): how much more cargo each island can take.

Reads a World Census `census.json` (priced with the G206 census_budget.py model) or an
already-made G206 report (format daedalus-census-budget), read-only. For every island it
marks three lines, counted in extra asset definitions (24 KiB RAM + 96 KiB disk each):

  * to_amber: definitions added before its beacon leaves green (0 if already not green),
  * to_red:   definitions added before its beacon turns red (0 if already red),
  * to_spill: definitions added (anywhere in the world) before the world stops fitting
              all-resident (0 if it already spills). Same for every island in a world.

Headroom is closed form and equals a brute-force scan over the G206 beacon model.
A cargo list (--add WORLD:SLOT:N, repeatable) is loaded on top and judged:
afloat (all green, every world fits), awash (some amber), sunk (some red or a spill).
Stdlib only, integers only, no clock.

  python tools/streaming/plimsoll_lines.py INPUT.json [--add alpha:2:40 ...] [--json] [--fail-on-sunk]

Exit 0 = report printed, 1 = --fail-on-sunk and the loaded verdict is sunk, 2 = refusal.
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-plimsoll-lines"
MAX_BYTES = 16 * 1024 * 1024
MAX_ADD = 1_000_000
R, D = cb.PER_ASSET_RAM_KIB, cb.PER_ASSET_DISK_KIB


class PlimsollError(ValueError):
    pass


def _load_json(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            raise PlimsollError(f"{path}: too large")
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except OSError as e:
        raise PlimsollError(f"{path}: {e.strerror}")
    except ValueError:
        raise PlimsollError(f"{path}: not JSON")


def to_report(doc, cfg):
    if isinstance(doc, dict) and doc.get("format") == cb.FORMAT:
        if doc.get("version") != 1:
            raise PlimsollError("unsupported G206 report version")
        return doc
    try:
        return cb.plan(doc, cfg)
    except cb.CensusBudgetError as e:
        raise PlimsollError(f"census: {e}")


def _budget(report):
    b = report.get("budget") or {}
    vals = [b.get(k) for k in ("ram_budget_kib", "disk_budget_kib", "warn_permille")]
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in vals):
        raise PlimsollError("report budget must be positive integers")
    return tuple(vals)


def _first_over(value, per, limit):
    """Smallest k >= 0 with value + per*k > limit."""
    return 0 if value > limit else (limit - value) // per + 1


def _first_over_scaled(value, per, limit_x1000):
    """Smallest k >= 0 with (value + per*k)*1000 > limit_x1000."""
    return 0 if value * 1000 > limit_x1000 else (limit_x1000 - value * 1000) // (per * 1000) + 1


def island_lines(ram, disk, rb, db, warn):
    to_red = min(_first_over(ram, R, rb), _first_over(disk, D, db))
    to_amber = min(to_red, _first_over_scaled(ram, R, rb * warn), _first_over_scaled(disk, D, db * warn))
    return to_amber, to_red


def world_spill(tr, td, rb, db):
    return min(_first_over(tr, R, rb), _first_over(td, D, db))


def _census_from(report):
    worlds = []
    for w in report.get("worlds") or []:
        if not isinstance(w, dict):
            raise PlimsollError("bad world")
        worlds.append({"id": w.get("id"), "islands": [{"slot": i.get("slot"), "asset_definitions": i.get("asset_definitions")}
                                                      for i in w.get("islands") or [] if isinstance(i, dict)]})
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions", "worlds": worlds}


def parse_add(items):
    out = []
    for s in items or []:
        parts = s.rsplit(":", 2)
        if len(parts) != 3 or not parts[0] or not parts[1].isdigit() or not parts[2].isdigit():
            raise PlimsollError(f"--add {s}: expected WORLD:SLOT:N")
        n = int(parts[2])
        if n > MAX_ADD:
            raise PlimsollError(f"--add {s}: N too large")
        out.append((parts[0], int(parts[1]), n))
    return out


def verdict_of(report):
    if any(not w["fits_all_resident"] or any(i["beacon"] == "red" for i in w["islands"]) for w in report["worlds"]):
        return "sunk"
    if any(i["beacon"] == "amber" for w in report["worlds"] for i in w["islands"]):
        return "awash"
    return "afloat"


def build(report, adds=()):
    rb, db, warn = _budget(report)
    census = _census_from(report)
    try:
        cur = cb.plan(census, {"budget": dict(report["budget"])})
    except cb.CensusBudgetError as e:
        raise PlimsollError(f"report: {e}")
    worlds = []
    for w in cur["worlds"]:
        spill = world_spill(w["total_ram_kib"], w["total_disk_kib"], rb, db)
        isl = []
        for i in w["islands"]:
            a, r = island_lines(i["ram_kib"], i["disk_kib"], rb, db, warn)
            isl.append({"slot": i["slot"], "beacon": i["beacon"], "asset_definitions": i["asset_definitions"],
                        "to_amber": a, "to_red": r, "to_spill": spill})
        tight = min(isl, key=lambda x: (x["to_amber"], x["to_red"], x["slot"])) if isl else None
        worlds.append({"world": w["id"], "to_spill": spill, "islands": isl,
                       "tightest_slot": tight["slot"] if tight else None})
    loaded = copy.deepcopy(census)
    index = {(w["id"], i["slot"]): i for w in loaded["worlds"] for i in w["islands"]}
    cargo = []
    for wid, slot, n in adds:
        if (wid, slot) not in index:
            raise PlimsollError(f"--add {wid}:{slot}: no such island")
        index[(wid, slot)]["asset_definitions"] += n
        cargo.append({"world": wid, "slot": slot, "add": n})
    after = cb.plan(loaded, {"budget": dict(report["budget"])}) if cargo else cur
    return {"format": FORMAT, "version": 1,
            "budget": {"ram_budget_kib": rb, "disk_budget_kib": db, "warn_permille": warn},
            "worlds": worlds, "cargo": cargo,
            "verdict_now": verdict_of(cur), "verdict": verdict_of(after),
            "loaded_beacons": [{"world": w["id"], "slot": i["slot"], "beacon": i["beacon"]}
                               for w in after["worlds"] for i in w["islands"]] if cargo else []}


def text(r):
    out = [f"plimsoll lines: now {r['verdict_now']}" + (f"; with cargo {r['verdict']}" if r["cargo"] else "")]
    for w in r["worlds"]:
        out.append(f"  {w['world']}: {w['to_spill']} more definitions before the world spills (tightest slot {w['tightest_slot']})")
        for i in w["islands"]:
            out.append(f"    slot {i['slot']} ({i['beacon']}): +{i['to_amber']} to amber, +{i['to_red']} to red")
    for c in r["cargo"]:
        out.append(f"  cargo: +{c['add']} on {c['world']} slot {c['slot']}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Plimsoll Lines: per-island headroom and cargo what-if over G206.")
    ap.add_argument("input")
    ap.add_argument("--config", default=cb.DEFAULT_CONFIG)
    ap.add_argument("--add", action="append", default=[], metavar="WORLD:SLOT:N")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-sunk", action="store_true")
    a = ap.parse_args(argv)
    try:
        cfg = _load_json(a.config)
        r = build(to_report(_load_json(a.input), cfg), parse_add(a.add))
    except PlimsollError as e:
        print(f"plimsoll_lines: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on_sunk and r["verdict"] == "sunk" else 0


if __name__ == "__main__":
    sys.exit(main())