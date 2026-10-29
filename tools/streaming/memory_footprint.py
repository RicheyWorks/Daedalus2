# SPDX-License-Identifier: MIT
"""Memory Footprint Report (G519, disk-saver): who uses the streaming budget, and the biggest wins.

Reads a World Census `census.json` (priced with the G206 census_budget.py model) or an
already-made G206 report (format daedalus-census-budget), read-only, and reports:

  * per world: RAM/disk footprint and permille of the 40000 KiB RAM / 32768 KiB disk budgets,
  * per world and overall: the top consumers (islands ranked by RAM, then disk),
  * per streaming tool: the source footprint of tools/streaming/*.py (bytes, read-only),
  * a ranked "biggest wins" list: unloading an island or trimming its asset definitions,
    with KiB freed and whether the win brings its world back under budget.

A world is over when its total RAM or disk exceeds the budget (permille > 1000).
Verdict: light (every world under warn_permille), laden (some world at or above warn but
none over), overladen (some world over). Stdlib only, integers only, no clock.

  python tools/streaming/memory_footprint.py INPUT.json [--top N] [--wins N] [--tools-dir DIR]
                                             [--json] [--fail-on-over] [--config CFG]

Exit 0 = report printed, 1 = --fail-on-over and the verdict is overladen, 2 = refusal.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-memory-footprint"
MAX_BYTES = 16 * 1024 * 1024


class FootprintError(ValueError):
    pass


def _int(v, what):
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise FootprintError(f"{what}: expected a nonnegative integer")
    return v


def to_report(doc, cfg):
    if isinstance(doc, dict) and doc.get("format") == cb.FORMAT:
        return doc
    try:
        return cb.plan(doc, cfg)
    except cb.CensusBudgetError as e:
        raise FootprintError(f"census: {e}")


def permille(x, budget):
    return x * 1000 // budget


def tool_footprint(tools_dir):
    """Source bytes of each streaming tool (non-test *.py), sorted by bytes desc then name."""
    if tools_dir is None:
        return []
    try:
        names = sorted(n for n in os.listdir(tools_dir) if n.endswith(".py") and not n.endswith("_test.py") and not n.startswith("test_"))
    except OSError as e:
        raise FootprintError(f"{tools_dir}: {e.strerror}")
    rows = [{"tool": n[:-3], "bytes": os.path.getsize(os.path.join(tools_dir, n))} for n in names]
    for r in rows:
        r["kib"] = -(-r["bytes"] // 1024)
    return sorted(rows, key=lambda r: (-r["bytes"], r["tool"]))


def build(report, top=3, wins=10, tools_dir=None):
    if not isinstance(report, dict) or report.get("format") != cb.FORMAT or report.get("version") != 1:
        raise FootprintError("input must be a census.json or a daedalus-census-budget v1 report")
    if top < 1 or wins < 1:
        raise FootprintError("--top and --wins must be at least 1")
    b = report.get("budget") or {}
    rb = _int(b.get("ram_budget_kib"), "ram_budget_kib")
    db = _int(b.get("disk_budget_kib"), "disk_budget_kib")
    warn = _int(b.get("warn_permille"), "warn_permille")
    if not rb or not db:
        raise FootprintError("budgets must be positive")
    worlds, everyone, cand = [], [], []
    seen = set()
    for w in report.get("worlds") or []:
        wid = w.get("id") if isinstance(w, dict) else None
        if not isinstance(wid, str) or not wid.strip() or wid in seen:
            raise FootprintError("bad or duplicate world id")
        seen.add(wid)
        isl = []
        for i in w.get("islands") or []:
            if not isinstance(i, dict):
                raise FootprintError(f"world {wid}: bad island")
            isl.append({"world": wid, "slot": _int(i.get("slot"), f"world {wid} slot"),
                        "ram_kib": _int(i.get("ram_kib"), f"world {wid} ram"),
                        "disk_kib": _int(i.get("disk_kib"), f"world {wid} disk"),
                        "asset_definitions": _int(i.get("asset_definitions"), f"world {wid} assets")})
        ram, disk = sum(i["ram_kib"] for i in isl), sum(i["disk_kib"] for i in isl)
        rp, dp = permille(ram, rb), permille(disk, db)
        over = rp > 1000 or dp > 1000
        ranked = sorted(isl, key=lambda i: (-i["ram_kib"], -i["disk_kib"], i["slot"]))
        worlds.append({"world": wid, "ram_kib": ram, "disk_kib": disk, "ram_permille": rp, "disk_permille": dp,
                       "over": over, "islands": len(isl),
                       "top": [{"slot": i["slot"], "ram_kib": i["ram_kib"], "disk_kib": i["disk_kib"],
                                "ram_share_permille": permille(i["ram_kib"], ram) if ram else 0} for i in ranked[:top]]})
        everyone += isl
        for i in isl:
            n = i["asset_definitions"]
            moves = [("unload", i["ram_kib"], i["disk_kib"])]
            if n:
                moves.append(("trim", n * cb.PER_ASSET_RAM_KIB, n * cb.PER_ASSET_DISK_KIB))
            for kind, fr, fd in moves:
                cand.append({"world": wid, "slot": i["slot"], "action": kind, "ram_free_kib": fr, "disk_free_kib": fd,
                             "world_over": over,
                             "clears": over and ram - fr <= rb and disk - fd <= db})
    cand.sort(key=lambda c: (not c["world_over"], not c["clears"], -c["ram_free_kib"], -c["disk_free_kib"],
                             c["world"], c["slot"], c["action"]))
    worlds.sort(key=lambda w: (-max(w["ram_permille"], w["disk_permille"]), w["world"]))
    peak = max([max(w["ram_permille"], w["disk_permille"]) for w in worlds] or [0])
    verdict = "overladen" if any(w["over"] for w in worlds) else "laden" if peak >= warn else "light"
    tot_r, tot_d = sum(w["ram_kib"] for w in worlds), sum(w["disk_kib"] for w in worlds)
    return {"format": FORMAT, "version": 1,
            "budget": {"ram_budget_kib": rb, "disk_budget_kib": db, "warn_permille": warn},
            "totals": {"worlds": len(worlds), "islands": len(everyone), "ram_kib": tot_r, "disk_kib": tot_d,
                       "peak_permille": peak},
            "worlds": worlds,
            "top_consumers": [{"world": i["world"], "slot": i["slot"], "ram_kib": i["ram_kib"], "disk_kib": i["disk_kib"]}
                              for i in sorted(everyone, key=lambda i: (-i["ram_kib"], -i["disk_kib"], i["world"], i["slot"]))[:top]],
            "tools": tool_footprint(tools_dir),
            "wins": [dict(c, rank=k + 1) for k, c in enumerate(cand[:wins])],
            "verdict": verdict}


def text(r):
    t = r["totals"]
    out = [f"memory footprint: {t['worlds']} worlds, {t['islands']} islands, {t['ram_kib']} KiB RAM, "
           f"{t['disk_kib']} KiB disk; peak {t['peak_permille']} permille of budget: {r['verdict']}"]
    for w in r["worlds"]:
        out.append(f"  {w['world']}: ram {w['ram_kib']} KiB ({w['ram_permille']}/1000), "
                   f"disk {w['disk_kib']} KiB ({w['disk_permille']}/1000){' OVER' if w['over'] else ''}")
        for c in w["top"]:
            out.append(f"    slot {c['slot']}: {c['ram_kib']} KiB RAM ({c['ram_share_permille']}/1000 of world), {c['disk_kib']} KiB disk")
    if r["tools"]:
        out.append("  streaming tools (source):")
        out += [f"    {x['tool']}: {x['bytes']} bytes" for x in r["tools"]]
    out.append("  biggest wins:")
    for c in r["wins"]:
        out.append(f"    {c['rank']}. {c['action']} {c['world']} slot {c['slot']}: -{c['ram_free_kib']} KiB RAM, "
                   f"-{c['disk_free_kib']} KiB disk{' (clears world)' if c['clears'] else ''}")
    return "\n".join(out) + "\n"


def _load_json(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            raise FootprintError(f"{path}: too large")
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except OSError as e:
        raise FootprintError(f"{path}: {e.strerror}")
    except ValueError:
        raise FootprintError(f"{path}: not JSON")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Memory Footprint Report: streaming budget consumers and biggest wins.")
    ap.add_argument("input")
    ap.add_argument("--config", default=cb.DEFAULT_CONFIG)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--wins", type=int, default=10)
    ap.add_argument("--tools-dir", default=HERE, help="streaming tools dir to measure ('' to skip)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-over", action="store_true", help="exit 1 when any world is over budget")
    a = ap.parse_args(argv)
    try:
        r = build(to_report(_load_json(a.input), _load_json(a.config)), a.top, a.wins, a.tools_dir or None)
    except FootprintError as e:
        print(f"memory_footprint: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on_over and r["verdict"] == "overladen" else 0


if __name__ == "__main__":
    sys.exit(main())