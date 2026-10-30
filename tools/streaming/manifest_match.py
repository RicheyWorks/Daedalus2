# SPDX-License-Identifier: MIT
"""Manifest Match (G556, disk-saver): a memory (Concentration) game over the world census.

Python dev tooling only; nothing here runs inside Unreal. Wharf Clerk Godfrey dropped the
harbour paperwork face down on the quay. Every island in a world census (tools/world_census
output, read-only) has two cards: its ISLAND card and its MANIFEST card (the island's RAM cost
in the G206 model, census_budget.island_cost). A seed picks up to 12 islands and shuffles the
cards into a row.

Each turn you flip two face-down cards by position (1-based, `3-7`). If they belong to the same
island they stay face up; otherwise they turn back over. The game is deterministic, so you play
by replaying: pass the turns so far, read the faces revealed in the log, add the next turn.

Par is the number of turns a player with perfect memory needs on THIS layout (flip the first
unknown card; if its mate has been seen, take it; otherwise flip the next unknown card, and if
that one's mate was seen earlier, take that pair next turn). It is never less than the number
of pairs.

  verdict   sharp       all pairs matched in par turns or fewer,
            matched     all pairs matched, more turns than par,
            unfinished  pairs still face down after the last turn.

  python tools/streaming/manifest_match.py CENSUS.json [--seed N] [--turns 1-2,3-4 | --auto] [--json]

Refusals (exit 2): a position out of range, a card already matched, the same card twice, or
turns after the game ended. Deterministic, stdlib only, no clock. Exit 0 = played.
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

FORMAT = "daedalus-manifest-match"
VERDICTS = ("sharp", "matched", "unfinished")
MAX_PAIRS = 12


class MatchError(ValueError):
    pass


def layout(census_doc, seed=0):
    """[(pair_id, face)] in table order."""
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise MatchError(str(e))
    islands = sorted((f"{w}:{s}", cb.island_cost(n)[0]) for w, isl in worlds for s, n in isl)
    if not islands:
        raise MatchError("census has no islands to deal")
    key = f"{census_doc.get('snapshot_date')}|{','.join(l for l, _ in islands)}|{seed}".encode("utf-8")
    rng = random.Random(int(hashlib.sha256(key).hexdigest(), 16))
    if len(islands) > MAX_PAIRS:
        islands = sorted(rng.sample(islands, MAX_PAIRS))
    cards = []
    for label, ram in islands:
        cards.append((label, f"ISLAND {label}"))
        cards.append((label, f"MANIFEST {label} {ram} KiB"))
    rng.shuffle(cards)
    return cards


def perfect_turns(cards):
    """Turns a perfect-memory player needs on this layout, and the turns themselves (0-based)."""
    n = len(cards)
    matched, turns = set(), []
    known = {}  # pair -> positions seen but unmatched
    order = list(range(n))
    cursor = 0

    def take_unknown():
        nonlocal cursor
        while cursor < n and (order[cursor] in matched or any(order[cursor] in v for v in known.values())):
            cursor += 1
        return order[cursor] if cursor < n else None

    while len(matched) < n:
        ready = next((p for p, v in known.items() if len(v) == 2), None)
        if ready:
            a, b = sorted(known.pop(ready))
            turns.append((a, b))
            matched.update((a, b))
            continue
        a = take_unknown()
        pa = cards[a][0]
        if pa in known:
            b = known.pop(pa)[0]
            turns.append((a, b))
            matched.update((a, b))
            continue
        known[pa] = [a]
        cursor += 1
        b = take_unknown()
        cursor += 1
        pb = cards[b][0]
        turns.append((a, b))
        if pa == pb:
            known.pop(pa)
            matched.update((a, b))
        else:
            known.setdefault(pb, []).append(b)
    return len(turns), turns


def play(census_doc, seed=0, turns=None, auto=False):
    if (turns is None) == (not auto):
        raise MatchError("give exactly one of turns or auto")
    cards = layout(census_doc, seed)
    par, best = perfect_turns(cards)
    if auto:
        turns = [(a + 1, b + 1) for a, b in best]
    n = len(cards)
    matched, log = set(), []
    for t, (a, b) in enumerate(turns, 1):
        if len(matched) == n:
            raise MatchError(f"turn {t}: the game is already over")
        for p in (a, b):
            if not 1 <= p <= n:
                raise MatchError(f"turn {t}: position {p} is not on the table (1-{n})")
            if p - 1 in matched:
                raise MatchError(f"turn {t}: card {p} is already matched")
        if a == b:
            raise MatchError(f"turn {t}: flip two different cards")
        ca, cb_ = cards[a - 1], cards[b - 1]
        hit = ca[0] == cb_[0]
        if hit:
            matched.update((a - 1, b - 1))
        log.append({"turn": t, "flip": [a, b], "faces": [ca[1], cb_[1]], "match": hit})
    done = len(matched) == n
    verdict = "unfinished" if not done else "sharp" if len(turns) <= par else "matched"
    return {"format": FORMAT, "version": 1, "seed": seed, "cards": n, "pairs": n // 2, "par": par,
            "turns": log, "matched_pairs": len(matched) // 2,
            "face_up": sorted(p + 1 for p in matched), "verdict": verdict}


def parse_turns(text):
    out = []
    for part in (p.strip() for p in text.split(",")):
        if not part:
            continue
        try:
            a, b = part.split("-")
            out.append((int(a), int(b)))
        except ValueError:
            raise MatchError(f"turn {part!r} must look like 3-7")
    return out


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise MatchError(f"census: {e}")


def text(r):
    lines = [f"manifest match: {r['verdict']} ({r['matched_pairs']}/{r['pairs']} pairs in {len(r['turns'])} turns, par {r['par']}; "
             f"{r['cards']} cards, seed {r['seed']})"]
    for t in r["turns"]:
        lines.append(f"  {t['turn']}. {t['flip'][0]}-{t['flip'][1]}: {t['faces'][0]} | {t['faces'][1]}"
                     + ("  MATCH" if t["match"] else ""))
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Manifest Match: a memory game over the world census.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--turns", help="comma-separated flips like 1-2,3-4 (1-based)")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        turns = parse_turns(a.turns) if a.turns is not None else ([] if not a.auto else None)
        r = play(_load(a.census), a.seed, turns, a.auto)
    except MatchError as e:
        print(f"manifest_match: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(r, indent=2, sort_keys=True) + "\n" if a.json else text(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
