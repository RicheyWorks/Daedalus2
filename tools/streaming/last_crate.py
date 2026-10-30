# SPDX-License-Identifier: MIT
"""Last Crate (G549, disk-saver): a push-your-luck loading game over the world census.

Python dev tooling only; nothing here runs inside Unreal. Dockhand Ambrose turns every island
in a world census (tools/world_census output, read-only) into a crate whose weight is that
island's RAM cost in the G206 model (census_budget.island_cost). The crates are shuffled by a
seed into a face-down stack. On each turn you either `load` the top crate into the hold or
`sail`. Go over the hold (default: the G206 RAM budget) and the whole load goes overboard.

  outcome     full      you sailed with the best load this stack allowed (no later stop was better),
              light     you sailed safely but a later stop would have carried more,
              overboard the hold burst.

The advisor knows only what a player knows (the crates already loaded and the multiset of crates
still in the stack, not their order) and reports, exactly, as fractions:
  bust_chance   chance the next crate bursts the hold,
  load_value    expected KiB carried if you load one more and then sail (bust = 0),
  sail_value    KiB carried if you sail now,
  advice        "load" when load_value > sail_value, else "sail".
`--auto` plays the advisor's one-step policy. Deterministic, stdlib only, no clock.

  python tools/streaming/last_crate.py CENSUS.json [--seed N] [--hold-kib K] [--moves load,load,sail | --auto] [--json]

Exit 0 = game printed, 2 = refusal.
"""
import argparse
import hashlib
import json
import os
import random
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-last-crate"
OUTCOMES = ("full", "light", "overboard")
MOVES = ("load", "sail")


class CrateError(ValueError):
    pass


def crates(census_doc):
    """[(label, ram_kib)] for every island, sorted by label."""
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise CrateError(str(e))
    out = sorted((f"{w}:{s}", cb.island_cost(n)[0]) for w, isl in worlds for s, n in isl)
    if not out:
        raise CrateError("census has no islands to load")
    return out


def stack(census_doc, seed):
    deck = crates(census_doc)
    key = f"{census_doc.get('snapshot_date')}|{','.join(l for l, _ in deck)}|{seed}".encode("utf-8")
    random.Random(int(hashlib.sha256(key).hexdigest(), 16)).shuffle(deck)
    return deck


def advise(loaded_kib, remaining, hold):
    """Exact advice from the loaded total and the unseen crate weights (order unknown)."""
    sail = Fraction(loaded_kib)
    if not remaining:
        return {"bust_chance": "0", "load_value": str(sail), "sail_value": str(sail), "advice": "sail"}
    n = len(remaining)
    busts = sum(1 for w in remaining if loaded_kib + w > hold)
    load = sum(Fraction(loaded_kib + w) for w in remaining if loaded_kib + w <= hold) / n
    return {"bust_chance": str(Fraction(busts, n)), "load_value": str(load), "sail_value": str(sail),
            "advice": "load" if load > sail else "sail"}


def best_stop(deck, hold):
    """Most KiB any stopping point of this exact stack carries safely."""
    best = total = 0
    for _, w in deck:
        total += w
        if total > hold:
            break
        best = total
    return best


def play(census_doc, seed=0, hold=None, moves=None, auto=False, cfg=None):
    if hold is None:
        try:
            hold = cb.load_budget(cfg)[0]
        except cb.CensusBudgetError as e:
            raise CrateError(str(e))
    if isinstance(hold, bool) or not isinstance(hold, int) or not 1 <= hold <= cb.MAX_KIB:
        raise CrateError("hold-kib must be 1..100000000")
    if (moves is None) == (not auto):
        raise CrateError("give exactly one of moves or auto")
    deck = stack(census_doc, seed)
    turns, loaded, total, i, outcome = [], [], 0, 0, None
    plan = list(moves) if moves is not None else None
    while outcome is None:
        a = advise(total, [w for _, w in deck[i:]], hold)
        if plan is not None:
            if not plan:
                raise CrateError("moves ran out before sailing (end with sail)")
            move = plan.pop(0)
            if move not in MOVES:
                raise CrateError(f"unknown move {move!r} (use load or sail)")
        else:
            move = a["advice"]
        turn = {"turn": len(turns) + 1, "move": move, "advice": a}
        if move == "load":
            if i == len(deck):
                raise CrateError("the stack is empty; you can only sail")
            label, w = deck[i]
            i += 1
            total += w
            loaded.append(label)
            turn.update(crate=label, kib=w, hold_kib=total)
            if total > hold:
                outcome = "overboard"
        else:
            outcome = "sail"
        turns.append(turn)
    if plan:
        raise CrateError("moves continue after the game ended")
    best = best_stop(deck, hold)
    carried = 0 if outcome == "overboard" else total
    if outcome == "sail":
        outcome = "full" if carried == best else "light"
    return {"format": FORMAT, "version": 1, "seed": seed, "hold_kib": hold, "stack_size": len(deck),
            "turns": turns, "loaded": loaded, "carried_kib": carried, "best_kib": best, "outcome": outcome}


def _load(path, what):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise CrateError(f"{what}: {e}")


def text(r):
    out = [f"last crate: {r['outcome']} (carried {r['carried_kib']} of best {r['best_kib']} KiB; hold {r['hold_kib']} KiB, "
           f"{r['stack_size']} crates, seed {r['seed']})"]
    for t in r["turns"]:
        a = t["advice"]
        tip = f"[bust {a['bust_chance']}, load ~{float(Fraction(a['load_value'])):.0f} vs sail {a['sail_value']}: {a['advice']}]"
        what = f"{t['move']} {t['crate']} (+{t['kib']} -> {t['hold_kib']})" if t["move"] == "load" else "sail"
        out.append(f"  {t['turn']}. {what} {tip}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Last Crate: push-your-luck hold loading over the world census.")
    ap.add_argument("census")
    ap.add_argument("--config", default=cb.DEFAULT_CONFIG)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--hold-kib", type=int)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--moves", help="comma-separated load/sail moves")
    g.add_argument("--auto", action="store_true", help="play the advisor's policy")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        cfg = None if a.hold_kib is not None else _load(a.config, "config")
        moves = [m.strip().lower() for m in a.moves.split(",") if m.strip()] if a.moves is not None else None
        r = play(_load(a.census, "census"), a.seed, a.hold_kib, moves, a.auto, cfg)
    except CrateError as e:
        print(f"last_crate: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
