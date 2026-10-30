# SPDX-License-Identifier: MIT
"""Smuggler's Island (G553, disk-saver): a yes/no deduction game over the world census.

Python dev tooling only; nothing here runs inside Unreal. A smuggler has hidden contraband on ONE
island of the world census (tools/world_census output, read-only); a seed picks which. Exciseman
Bartholomew may ask the harbour only yes/no questions built from the census:

  world:W      is it in world W?
  realm:R      is its world in realm R? (realm:none for worlds with no realm)
  slot>=K      is its island slot at least K?
  cargo>=K     does it carry at least K asset definitions? (K > 0)
  empty        does it carry no asset definitions?

Questions that split the suspects the same way as an earlier one are dropped, so every listed
question is useful at the start. Ask, then accuse an island (world:slot).

An exact minimax search over the suspects still possible (memoised on the suspect set) gives the
fewest questions that ALWAYS find the island, and `--auto` plays that strategy.

  verdict   sharp     correct accusation using no more questions than the optimal worst case,
            caught    correct accusation, but more questions than needed,
            escaped   wrong accusation.

  python tools/streaming/smugglers_island.py CENSUS.json [--seed N] [--list]
         [--ask Q1,Q2,... --accuse WORLD:SLOT | --auto] [--json]

Deterministic, stdlib only, no clock. Exit 0 = printed or played, 2 = refusal.
"""
import argparse
import hashlib
import json
import os
import random
import sys
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-smugglers-island"
VERDICTS = ("sharp", "caught", "escaped")
MAX_SUSPECTS = 40


class SmugglerError(ValueError):
    pass


def suspects(census_doc):
    """[{label, world, realm, slot, cargo}] sorted by label."""
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise SmugglerError(str(e))
    realm = {w.get("id"): w.get("realm_id") for w in census_doc.get("worlds", []) if isinstance(w, dict)}
    out = [{"label": f"{w}:{s}", "world": w, "realm": realm.get(w) or "none", "slot": s, "cargo": n}
           for w, isl in worlds for s, n in isl]
    if not out:
        raise SmugglerError("census has no islands to search")
    if len(out) > MAX_SUSPECTS:
        raise SmugglerError(f"more than {MAX_SUSPECTS} islands")
    return sorted(out, key=lambda t: t["label"])


def questions(sus):
    """Ordered {id: frozenset of suspect indexes answering yes}, no duplicate or trivial splits."""
    cand = []
    for w in sorted({s["world"] for s in sus}):
        cand.append((f"world:{w}", lambda s, w=w: s["world"] == w))
    for r in sorted({s["realm"] for s in sus}):
        cand.append((f"realm:{r}", lambda s, r=r: s["realm"] == r))
    for k in sorted({s["slot"] for s in sus}):
        cand.append((f"slot>={k}", lambda s, k=k: s["slot"] >= k))
    for k in sorted({s["cargo"] for s in sus if s["cargo"] > 0}):
        cand.append((f"cargo>={k}", lambda s, k=k: s["cargo"] >= k))
    cand.append(("empty", lambda s: s["cargo"] == 0))
    every = frozenset(range(len(sus)))
    out, seen = {}, set()
    for qid, pred in cand:
        yes = frozenset(i for i, s in enumerate(sus) if pred(s))
        key = min(yes, every - yes, key=sorted)
        if not yes or yes == every or key in seen:
            continue
        seen.add(key)
        out[qid] = yes
    return out


def solver(qs):
    items = list(qs.items())

    @lru_cache(maxsize=None)
    def depth(group):
        if len(group) <= 1:
            return 0
        best = None
        for _, yes in items:
            a, b = group & yes, group - yes
            if a and b:
                d = 1 + max(depth(a), depth(b))
                if best is None or d < best:
                    best = d
        return best if best is not None else 10 ** 6

    def best_question(group):
        choice = None
        for qid, yes in items:
            a, b = group & yes, group - yes
            if a and b:
                d = 1 + max(depth(a), depth(b))
                if choice is None or d < choice[1]:
                    choice = (qid, d)
        return choice[0] if choice else None

    return depth, best_question


def setup(census_doc, seed):
    sus = suspects(census_doc)
    key = f"{census_doc.get('snapshot_date')}|{','.join(s['label'] for s in sus)}|{seed}".encode("utf-8")
    hidden = random.Random(int(hashlib.sha256(key).hexdigest(), 16)).randrange(len(sus))
    return sus, questions(sus), hidden


def play(census_doc, seed=0, asks=None, accuse=None, auto=False):
    if auto == (asks is not None or accuse is not None):
        raise SmugglerError("give --auto, or --ask with --accuse")
    if not auto and accuse is None:
        raise SmugglerError("an accusation (world:slot) is required")
    sus, qs, hidden = setup(census_doc, seed)
    depth, best_q = solver(qs)
    every = frozenset(range(len(sus)))
    optimal = depth(every)
    group, log = every, []
    plan = list(asks or [])
    while True:
        if auto:
            if len(group) == 1:
                break
            qid = best_q(group)
        else:
            if not plan:
                break
            qid = plan.pop(0)
            if qid not in qs:
                raise SmugglerError(f"unknown question {qid!r} (see --list)")
        yes = hidden in qs[qid]
        group = group & qs[qid] if yes else group - qs[qid]
        log.append({"question": qid, "answer": "yes" if yes else "no", "suspects_left": len(group)})
    labels = [s["label"] for s in sus]
    if auto:
        accuse = labels[min(group)]
    elif accuse not in labels:
        raise SmugglerError(f"no island {accuse!r} in the census")
    correct = accuse == labels[hidden]
    verdict = "escaped" if not correct else "sharp" if len(log) <= optimal else "caught"
    return {"format": FORMAT, "version": 1, "seed": seed, "suspects": len(sus), "optimal_questions": optimal,
            "asked": log, "accused": accuse, "hidden": labels[hidden], "still_possible": sorted(labels[i] for i in group),
            "verdict": verdict}


def _load(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise SmugglerError(f"census: {e}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Smuggler's Island: yes/no deduction over the world census.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--list", action="store_true", help="list suspects and questions")
    ap.add_argument("--ask", help="comma-separated question ids")
    ap.add_argument("--accuse", help="world:slot")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        doc = _load(a.census)
        if a.list or not (a.auto or a.ask or a.accuse):
            sus, qs, _ = setup(doc, a.seed)
            out = {"format": FORMAT, "version": 1, "seed": a.seed, "suspects": [s["label"] for s in sus],
                   "questions": list(qs), "optimal_questions": solver(qs)[0](frozenset(range(len(sus))))}
            text = (f"smuggler's island (seed {a.seed}): {len(sus)} suspects, solvable in {out['optimal_questions']} questions\n"
                    f"  suspects: {', '.join(out['suspects'])}\n  questions: {', '.join(out['questions'])}\n")
        else:
            asks = [q.strip() for q in a.ask.split(",") if q.strip()] if a.ask else ([] if not a.auto else None)
            out = play(doc, a.seed, asks, a.accuse, a.auto)
            text = (f"smuggler's island: {out['verdict']} (accused {out['accused']}, hidden {out['hidden']}; "
                    f"{len(out['asked'])} questions, optimal {out['optimal_questions']})\n" +
                    "".join(f"  {q['question']}? {q['answer']} ({q['suspects_left']} left)\n" for q in out["asked"]))
    except SmugglerError as e:
        print(f"smugglers_island: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n" if a.json else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
