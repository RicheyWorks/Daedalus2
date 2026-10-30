# SPDX-License-Identifier: MIT
"""Quay Duel (G550, disk-saver): a two-captain draft game over the world census.

Python dev tooling only; nothing here runs inside Unreal. Every island in a world census
(tools/world_census output, read-only) becomes a crate worth its RAM cost in the G206 model
(census_budget.island_cost). A seed lines the crates up along the quay. Two captains take turns
taking ONE crate from either end of the line (L or R) until the quay is empty; the captain with
more cargo wins. You play against Wharfinger Casimir, who plays perfectly.

An exact interval DP gives the best margin the player to move can force from any stretch of
quay (checked against plain minimax in the tests). Every turn reports the best move and how much
margin a weaker move gave away, so the duel teaches as you play.

  outcome   won / tied / lost (your cargo vs Casimir's); `perfect` is true when you never gave
            margin away.

  python tools/streaming/quay_duel.py CENSUS.json [--seed N] [--second] [--moves L,R,... | --auto] [--json]

`--second` lets Casimir open. `--auto` plays you perfectly too. With an even number of crates the
opener can never lose (take all the odd-placed or all the even-placed crates); the tool
reports that guarantee. Deterministic, stdlib only, no clock. Exit 0 = duel printed, 2 = refusal.
"""
import argparse
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-quay-duel"
OUTCOMES = ("won", "tied", "lost")
MAX_CRATES = 400


class DuelError(ValueError):
    pass


def quay(census_doc, seed):
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise DuelError(str(e))
    line = sorted((f"{w}:{s}", cb.island_cost(n)[0]) for w, isl in worlds for s, n in isl)
    if not line:
        raise DuelError("census has no islands to line up")
    if len(line) > MAX_CRATES:
        raise DuelError(f"more than {MAX_CRATES} crates on the quay")
    key = f"{census_doc.get('snapshot_date')}|{','.join(l for l, _ in line)}|{seed}".encode("utf-8")
    random.Random(int(hashlib.sha256(key).hexdigest(), 16)).shuffle(line)
    return line


def margins(values):
    """f[i][j] = best (mover - other) margin on values[i..j]; f[i][i-1] = 0."""
    n = len(values)
    f = [[0] * (n + 1) for _ in range(n + 1)]
    for length in range(1, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            left = values[i] - (f[i + 1][j] if i + 1 <= j else 0)
            right = values[j] - (f[i][j - 1] if i <= j - 1 else 0)
            f[i][j] = max(left, right)
    return f


def _val(f, i, j):
    return f[i][j] if i <= j else 0


def best_move(values, f, i, j):
    """(move, margin) for the mover on values[i..j]; ties go to L."""
    left = values[i] - _val(f, i + 1, j)
    right = values[j] - _val(f, i, j - 1)
    return ("L", left) if left >= right else ("R", right)


def duel(census_doc, seed=0, moves=None, auto=False, second=False):
    if (moves is None) == (not auto):
        raise DuelError("give exactly one of moves or auto")
    line = quay(census_doc, seed)
    values = [v for _, v in line]
    f = margins(values)
    i, j = 0, len(values) - 1
    plan = list(moves) if moves is not None else None
    you = casimir = given_away = 0
    turns = []
    mover = "casimir" if second else "you"
    while i <= j:
        best, best_margin = best_move(values, f, i, j)
        if mover == "you" and plan is not None:
            if not plan:
                raise DuelError("moves ran out while crates remain on the quay")
            move = plan.pop(0)
            if move not in ("L", "R"):
                raise DuelError(f"unknown move {move!r} (use L or R)")
        else:
            move = best
        idx = i if move == "L" else j
        got = values[idx] - (_val(f, i + 1, j) if move == "L" else _val(f, i, j - 1))
        lost = best_margin - got
        label, v = line[idx]
        if mover == "you":
            you += v
            given_away += lost
        else:
            casimir += v
        turns.append({"turn": len(turns) + 1, "captain": mover, "move": move, "crate": label, "kib": v,
                      "best": best, "gave_away_kib": lost})
        if move == "L":
            i += 1
        else:
            j -= 1
        mover = "casimir" if mover == "you" else "you"
    if plan:
        raise DuelError("moves continue after the quay is empty")
    opener_margin = f[0][len(values) - 1]
    best_for_you = -opener_margin if second else opener_margin
    outcome = "won" if you > casimir else "tied" if you == casimir else "lost"
    return {"format": FORMAT, "version": 1, "seed": seed, "you_open": not second, "crates": len(line),
            "quay": [l for l, _ in line], "turns": turns, "you_kib": you, "casimir_kib": casimir,
            "best_margin_kib": best_for_you, "margin_kib": you - casimir, "gave_away_kib": given_away,
            "perfect": given_away == 0, "opener_cannot_lose": len(line) % 2 == 0, "outcome": outcome}


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise DuelError(f"census: {e}")


def text(r):
    out = [f"quay duel: {r['outcome']} ({r['you_kib']} vs Casimir {r['casimir_kib']} KiB; margin {r['margin_kib']}, "
           f"best forceable {r['best_margin_kib']}; {'perfect' if r['perfect'] else 'gave away ' + str(r['gave_away_kib']) + ' KiB'}; "
           f"{r['crates']} crates, seed {r['seed']})"]
    for t in r["turns"]:
        note = f" (best {t['best']}, gave away {t['gave_away_kib']})" if t["gave_away_kib"] else ""
        out.append(f"  {t['turn']}. {t['captain']} {t['move']} {t['crate']} +{t['kib']}{note}")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Quay Duel: take crates from either end against a perfect wharfinger.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--second", action="store_true", help="Casimir opens")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--moves", help="comma-separated L/R moves for you")
    g.add_argument("--auto", action="store_true", help="you play perfectly too")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        moves = [m.strip().upper() for m in a.moves.split(",") if m.strip()] if a.moves is not None else None
        r = duel(_load(a.census), a.seed, moves, a.auto, a.second)
    except DuelError as e:
        print(f"quay_duel: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
