# SPDX-License-Identifier: MIT
"""Budget Fathoms (G529, disk-saver): the smallest streaming budgets the census needs.

G206 census_budget.py colours islands at a fixed budget; this solves the inverse. From a
World Census `census.json` (priced with the G206 model) or an already-made G206 report,
read-only, it computes in KiB, separately for RAM and disk:

  * per island: green_kib (smallest budget keeping it green at warn_permille) and
    clear_kib (smallest budget keeping it out of red),
  * per world: fit_kib (smallest budget holding every island resident at once),
  * fleet: all_green / no_red / all_fit = the max of those, and the slack of the current
    budget against each (negative = short),
  * optional sweep (--sweep-ram / --sweep-disk KiB lists): G206 beacon counts and spilling
    worlds re-priced at each budget.

Verdict at the current budget: deep (all green and all fit), shoal (no red and all fit,
some amber), aground (some red or a world spills). Breakpoints are closed form and equal a
brute-force scan over the G206 beacon. Stdlib only, integers only, no clock.

  python tools/streaming/budget_fathoms.py INPUT.json [--sweep-ram 32000,40000] [--sweep-disk ...]
                                           [--json] [--fail-on-aground] [--config CFG]

Exit 0 = report printed, 1 = --fail-on-aground and the verdict is aground, 2 = refusal.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-budget-fathoms"
MAX_BYTES = 16 * 1024 * 1024
MAX_SWEEP = 64


class FathomError(ValueError):
    pass


def _load_json(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            raise FathomError(f"{path}: too large")
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except OSError as e:
        raise FathomError(f"{path}: {e.strerror}")
    except ValueError:
        raise FathomError(f"{path}: not JSON")


def to_report(doc, cfg):
    if isinstance(doc, dict) and doc.get("format") == cb.FORMAT:
        if doc.get("version") != 1:
            raise FathomError("unsupported G206 report version")
        return doc
    try:
        return cb.plan(doc, cfg)
    except cb.CensusBudgetError as e:
        raise FathomError(f"census: {e}")


def green_kib(cost, warn):
    """Smallest budget B with cost*1000 <= B*warn (and cost <= B)."""
    return max(cost, -(-cost * 1000 // warn))


def _census_from(report):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions",
            "worlds": [{"id": w.get("id"), "islands": [{"slot": i.get("slot"), "asset_definitions": i.get("asset_definitions")}
                                                       for i in w.get("islands") or []]}
                       for w in report.get("worlds") or [] if isinstance(w, dict)]}


def parse_list(s, what):
    if s is None:
        return []
    out = []
    for p in s.split(","):
        p = p.strip()
        if not p.isdigit() or int(p) <= 0 or int(p) > cb.MAX_KIB:
            raise FathomError(f"{what}: {p!r} is not a positive KiB value")
        out.append(int(p))
    if len(out) > MAX_SWEEP:
        raise FathomError(f"{what}: at most {MAX_SWEEP} values")
    return sorted(set(out))


def _state(rep):
    spill = sum(1 for w in rep["worlds"] if not w["fits_all_resident"])
    s = rep["summary"]
    return {"green": s["green"], "amber": s["amber"], "red": s["red"], "worlds_spilling": spill}


def verdict_of(st):
    if st["red"] or st["worlds_spilling"]:
        return "aground"
    return "shoal" if st["amber"] else "deep"


def build(report, sweep_ram=(), sweep_disk=()):
    b = report.get("budget") or {}
    vals = [b.get(k) for k in ("ram_budget_kib", "disk_budget_kib", "warn_permille")]
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in vals) or vals[2] > 1000:
        raise FathomError("report budget must be positive integers, warn_permille <= 1000")
    rb, db, warn = vals
    census = _census_from(report)
    try:
        cur = cb.plan(census, {"budget": dict(b)})
    except cb.CensusBudgetError as e:
        raise FathomError(f"report: {e}")
    worlds, need = [], {"ram": {"all_green": 0, "no_red": 0, "all_fit": 0}, "disk": {"all_green": 0, "no_red": 0, "all_fit": 0}}
    for w in cur["worlds"]:
        isl = []
        for i in w["islands"]:
            row = {"slot": i["slot"], "ram_green_kib": green_kib(i["ram_kib"], warn), "ram_clear_kib": i["ram_kib"],
                   "disk_green_kib": green_kib(i["disk_kib"], warn), "disk_clear_kib": i["disk_kib"]}
            isl.append(row)
            for dim in ("ram", "disk"):
                need[dim]["all_green"] = max(need[dim]["all_green"], row[f"{dim}_green_kib"])
                need[dim]["no_red"] = max(need[dim]["no_red"], row[f"{dim}_clear_kib"])
        worlds.append({"world": w["id"], "ram_fit_kib": w["total_ram_kib"], "disk_fit_kib": w["total_disk_kib"], "islands": isl})
        need["ram"]["all_fit"] = max(need["ram"]["all_fit"], w["total_ram_kib"])
        need["disk"]["all_fit"] = max(need["disk"]["all_fit"], w["total_disk_kib"])
    for dim in need:
        need[dim]["deep"] = max(need[dim]["all_green"], need[dim]["all_fit"])
    budget = {"ram": rb, "disk": db}
    slack = {dim: {k: budget[dim] - v for k, v in need[dim].items()} for dim in need}
    sweep = []
    for dim, values in (("ram", sweep_ram), ("disk", sweep_disk)):
        for v in values:
            nb = dict(b)
            nb[f"{dim}_budget_kib"] = v
            sweep.append(dict({"dim": dim, "budget_kib": v}, **_state(cb.plan(census, {"budget": nb}))))
    for s in sweep:
        s["verdict"] = verdict_of(s)
    now = _state(cur)
    return {"format": FORMAT, "version": 1,
            "budget": {"ram_budget_kib": rb, "disk_budget_kib": db, "warn_permille": warn},
            "need_kib": need, "slack_kib": slack, "worlds": worlds, "sweep": sweep,
            "now": now, "verdict": verdict_of(now)}


def text(r):
    out = [f"budget fathoms: {r['verdict']} at {r['budget']['ram_budget_kib']} KiB RAM / {r['budget']['disk_budget_kib']} KiB disk"]
    for dim in ("ram", "disk"):
        n, s = r["need_kib"][dim], r["slack_kib"][dim]
        out.append(f"  {dim}: all green >= {n['all_green']} ({s['all_green']:+d}), no red >= {n['no_red']} ({s['no_red']:+d}), "
                   f"all fit >= {n['all_fit']} ({s['all_fit']:+d}), deep >= {n['deep']} ({s['deep']:+d}) KiB")
    for w in r["worlds"]:
        out.append(f"  {w['world']}: fits at {w['ram_fit_kib']} KiB RAM / {w['disk_fit_kib']} KiB disk")
    for s in r["sweep"]:
        out.append(f"  sweep {s['dim']} {s['budget_kib']} KiB: {s['green']} green, {s['amber']} amber, {s['red']} red, "
                   f"{s['worlds_spilling']} spilling: {s['verdict']}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Budget Fathoms: smallest streaming budgets for the census.")
    ap.add_argument("input")
    ap.add_argument("--config", default=cb.DEFAULT_CONFIG)
    ap.add_argument("--sweep-ram")
    ap.add_argument("--sweep-disk")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-aground", action="store_true")
    a = ap.parse_args(argv)
    try:
        cfg = _load_json(a.config)
        r = build(to_report(_load_json(a.input), cfg), parse_list(a.sweep_ram, "--sweep-ram"),
                  parse_list(a.sweep_disk, "--sweep-disk"))
    except FathomError as e:
        print(f"budget_fathoms: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 1 if a.fail_on_aground and r["verdict"] == "aground" else 0


if __name__ == "__main__":
    sys.exit(main())