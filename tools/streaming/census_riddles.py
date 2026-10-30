# SPDX-License-Identifier: MIT
"""Census Riddles (G546, disk-saver): the tide-clerk's harbour quiz over the world census.

A small playable quiz for players and designers. Python dev tooling only; nothing here runs
inside Unreal. It reads a world census (tools/world_census output, read-only) and the G206
census-budget config (read-only), draws a seeded set of riddles about the harbour, and grades
a player's answers. Every answer is computed from the census with the G206 cost model
(tools/streaming/census_budget.py: island_cost, max_resident), so the quiz always matches what
the budget tools would say.

Riddle kinds (each skipped when the census cannot pose it):
  islands_total    how many islands are charted in all worlds
  cargo_total      how many asset definitions are bound to islands
  empty_islands    how many islands carry no asset definitions
  widest_world     which world has the most islands (ties: smallest id)
  heaviest_island  which island (world:slot) needs the most RAM (ties: smallest world, slot)
  world_ram        how many KiB of RAM one world's islands need together
  world_disk       how many KiB of disk one world's islands need together
  islands_fit      how many islands fit the RAM budget on their own
  max_resident     the most islands of one world resident at once within the RAM budget

The draw depends only on the census bytes' snapshot_date and world ids plus --seed, so the same
seed gives the same quiz on every machine. No clock, no network, stdlib only.

  python tools/streaming/census_riddles.py CENSUS.json [--seed N] [--count 5] [--key] [--answers FILE] [--json]

Without --answers the riddles are printed (with --key, the answers too). With --answers
(a JSON object {"r1": "3", ...}) the quiz is graded: shipshape (all right), adrift (at least
half), aground (fewer than half). Exit 0 = printed or graded, 2 = refusal.
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

FORMAT = "daedalus-census-riddles"
KINDS = ("islands_total", "cargo_total", "empty_islands", "widest_world", "heaviest_island",
         "world_ram", "world_disk", "islands_fit", "max_resident")
GRADES = ("shipshape", "adrift", "aground")
MAX_COUNT = 20


class RiddleError(ValueError):
    pass


def _world_param(kind, worlds, rng, ram_budget):
    ids = [w for w, isl in worlds if isl]
    return rng.choice(ids) if ids else None


def pose(kind, worlds, ram_budget, rng):
    """(question, answer string) or None when the census cannot pose this riddle."""
    islands = [(w, s, n) for w, isl in worlds for s, n in isl]
    if not islands:
        return None
    if kind == "islands_total":
        return "How many islands are charted across every world in the census?", str(len(islands))
    if kind == "cargo_total":
        return "How many asset definitions are stowed on islands (all worlds together)?", str(sum(n for _, _, n in islands))
    if kind == "empty_islands":
        return "How many islands carry no asset definitions at all?", str(sum(1 for *_, n in islands if n == 0))
    if kind == "widest_world":
        best = min(worlds, key=lambda w: (-len(w[1]), w[0]))
        return "Which world has the most islands? (answer the world id)", best[0]
    if kind == "heaviest_island":
        w, s, _ = min(islands, key=lambda t: (-cb.island_cost(t[2])[0], t[0], t[1]))
        return "Which island needs the most RAM? (answer world:slot)", f"{w}:{s}"
    if kind == "islands_fit":
        q = f"With a RAM budget of {ram_budget} KiB, how many islands would fit the hold on their own?"
        return q, str(sum(1 for *_, n in islands if cb.island_cost(n)[0] <= ram_budget))
    w = _world_param(kind, worlds, rng, ram_budget)
    isl = dict(worlds)[w]
    if kind == "world_ram":
        return f"How many KiB of RAM do all islands of world '{w}' need together?", str(sum(cb.island_cost(n)[0] for _, n in isl))
    if kind == "world_disk":
        return f"How many KiB of disk do all islands of world '{w}' need together?", str(sum(cb.island_cost(n)[1] for _, n in isl))
    if kind == "max_resident":
        rams = [cb.island_cost(n)[0] for _, n in isl]
        q = f"With a RAM budget of {ram_budget} KiB, what is the most islands of world '{w}' that can be resident at once?"
        return q, str(cb.max_resident(rams, ram_budget))
    raise RiddleError(f"unknown riddle kind {kind}")


def _rng(census_doc, seed):
    ids = ",".join(sorted(w for w, _ in cb.read_census(census_doc)))
    key = f"{census_doc.get('snapshot_date')}|{ids}|{seed}".encode("utf-8")
    return random.Random(int(hashlib.sha256(key).hexdigest(), 16))


def draw(census_doc, cfg, seed=0, count=5):
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= MAX_COUNT:
        raise RiddleError(f"count must be 1..{MAX_COUNT}")
    try:
        worlds = cb.read_census(census_doc)
        ram_budget = cb.load_budget(cfg)[0]
    except cb.CensusBudgetError as e:
        raise RiddleError(str(e))
    rng = _rng(census_doc, seed)
    kinds = list(KINDS)
    rng.shuffle(kinds)
    riddles = []
    for kind in kinds:
        if len(riddles) == count:
            break
        p = pose(kind, worlds, ram_budget, rng)
        if p:
            riddles.append({"id": f"r{len(riddles) + 1}", "kind": kind, "question": p[0], "answer": p[1]})
    if not riddles:
        raise RiddleError("census has no islands to ask about")
    return {"format": FORMAT, "version": 1, "seed": seed, "snapshot_date": census_doc.get("snapshot_date"),
            "ram_budget_kib": ram_budget, "riddles": riddles}


def _norm(v):
    s = str(v).strip().lower()
    try:
        return str(int(s.replace(",", "").replace("_", "")))
    except ValueError:
        return s


def grade(quiz, answers):
    if not isinstance(answers, dict):
        raise RiddleError("answers must be a JSON object of riddle id -> answer")
    rows, right = [], 0
    for r in quiz["riddles"]:
        given = answers.get(r["id"])
        ok = given is not None and _norm(given) == _norm(r["answer"])
        right += ok
        rows.append({"id": r["id"], "kind": r["kind"], "given": given, "answer": r["answer"], "correct": ok})
    n = len(rows)
    verdict = "shipshape" if right == n else "adrift" if 2 * right >= n else "aground"
    return {"format": FORMAT, "version": 1, "seed": quiz["seed"], "score": right, "out_of": n,
            "results": rows, "verdict": verdict}


def _load(path, what):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise RiddleError(f"{what}: {e}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Census Riddles: a seeded harbour quiz over the world census.")
    ap.add_argument("census")
    ap.add_argument("--config", default=cb.DEFAULT_CONFIG)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--key", action="store_true", help="also print the answers")
    ap.add_argument("--answers", help="JSON object {riddle id: answer} to grade")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        quiz = draw(_load(a.census, "census"), _load(a.config, "config"), a.seed, a.count)
        if a.answers:
            out = grade(quiz, _load(a.answers, "answers"))
        else:
            out = quiz if a.key else dict(quiz, riddles=[{k: v for k, v in r.items() if k != "answer"} for r in quiz["riddles"]])
    except RiddleError as e:
        print(f"census_riddles: refused: {e}", file=sys.stderr)
        return 2
    if a.json:
        sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n")
    elif a.answers:
        lines = [f"census riddles: {out['verdict']} ({out['score']}/{out['out_of']}, seed {out['seed']})"]
        lines += [f"  {'+' if r['correct'] else 'x'} {r['id']} {r['kind']}: {r['given']!s} (answer {r['answer']})" for r in out["results"]]
        sys.stdout.write("\n".join(lines) + "\n")
    else:
        lines = [f"census riddles (seed {out['seed']}, snapshot {out['snapshot_date']}, RAM budget {out['ram_budget_kib']} KiB)"]
        lines += [f"  {r['id']}. {r['question']}" + (f"  -> {r['answer']}" if a.key else "") for r in out["riddles"]]
        sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
