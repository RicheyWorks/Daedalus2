# SPDX-License-Identifier: MIT
"""Harbour Cryptogram (G552, disk-saver): decode the telegraph from the world census.

Python dev tooling only; nothing here runs inside Unreal. Telegraphist Philippa sends the harbour
news in a letter-substitution cipher. The news is true: every sentence is built from a world
census (tools/world_census output, read-only), for example

  SYNTHETIC ALPHA CHARTS TWO ISLANDS STOP SYNTHETIC ALPHA CARRIES ARK AND BEACON

A seed picks up to three sentences and a cipher key that is a derangement of A-Z (no letter
stands for itself). A few letters are given away, more for longer messages. The player answers
with a plaintext guess or a partial key (cipher letter -> plain letter), and the grader scores
every letter position.

  verdict   decoded  every letter right,
            partial  at least half of the letter positions right,
            garbled  fewer than half.

  python tools/streaming/harbour_cryptogram.py CENSUS.json [--seed N] [--solution]
         [--guess "PLAIN TEXT" | --mapping KEY.json] [--json]

KEY.json maps cipher letters to plain letters, e.g. {"Q": "S", "X": "T"}. Unmapped letters count
as wrong. Deterministic, stdlib only, no clock. Exit 0 = printed or graded, 2 = refusal.
"""
import argparse
import hashlib
import json
import os
import random
import re
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import census_budget as cb  # noqa: E402

FORMAT = "daedalus-harbour-cryptogram"
VERDICTS = ("decoded", "partial", "garbled")
ALPHA = string.ascii_uppercase
ONES = ("ZERO ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE TEN ELEVEN TWELVE THIRTEEN FOURTEEN "
        "FIFTEEN SIXTEEN SEVENTEEN EIGHTEEN NINETEEN").split()
TENS = "_ _ TWENTY THIRTY FORTY FIFTY SIXTY SEVENTY EIGHTY NINETY".split()
MAX_SENTENCES = 3


class CryptogramError(ValueError):
    pass


def number_words(n):
    if n < 0:
        raise CryptogramError("negative count")
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000:
        rest = n % 100
        return ONES[n // 100] + " HUNDRED" + ("" if rest == 0 else " AND " + number_words(rest))
    return " ".join(ONES[int(d)] for d in str(n))


def clean(text):
    return " ".join(re.sub(r"[^A-Z]+", " ", str(text).upper()).split())


def facts(census_doc):
    """Every true sentence the census supports, in a fixed order."""
    try:
        worlds = cb.read_census(census_doc)
    except cb.CensusBudgetError as e:
        raise CryptogramError(str(e))
    raw = {w.get("id"): w for w in census_doc.get("worlds", []) if isinstance(w, dict)}
    out = []
    total = 0
    for wid, islands in worlds:
        w = raw.get(wid, {})
        name = clean(w.get("title") or wid) or clean(wid) or "A WORLD"
        n = len(islands)
        total += n
        out.append(f"{name} CHARTS {number_words(n)} {'ISLAND' if n == 1 else 'ISLANDS'}")
        assets = sorted({clean(a.get("name")) for a in w.get("assets", []) if isinstance(a, dict) and clean(a.get("name"))})
        if assets:
            out.append(f"{name} CARRIES " + " AND ".join(assets))
        empty = sum(1 for _, k in islands if k == 0)
        if islands:
            out.append(f"{name} HAS {number_words(empty)} EMPTY {'ISLAND' if empty == 1 else 'ISLANDS'}")
    out.append(f"THE HARBOUR HOLDS {number_words(total)} {'ISLAND' if total == 1 else 'ISLANDS'} IN "
               f"{number_words(len(worlds))} {'WORLD' if len(worlds) == 1 else 'WORLDS'}")
    return out


def _rng(census_doc, seed):
    ids = ",".join(sorted(w for w, _ in cb.read_census(census_doc)))
    key = f"{census_doc.get('snapshot_date')}|{ids}|{seed}".encode("utf-8")
    return random.Random(int(hashlib.sha256(key).hexdigest(), 16))


def derangement(rng):
    while True:
        p = list(ALPHA)
        rng.shuffle(p)
        if all(a != b for a, b in zip(ALPHA, p)):
            return dict(zip(ALPHA, p))


def encode(text, key):
    return "".join(key.get(ch, ch) for ch in text)


def make(census_doc, seed=0):
    all_facts = facts(census_doc)
    rng = _rng(census_doc, seed)
    pick = rng.sample(all_facts, min(MAX_SENTENCES, len(all_facts)))
    plain = " STOP ".join(pick)
    key = derangement(rng)
    cipher = encode(plain, key)
    used = sorted({ch for ch in plain if ch in ALPHA})
    k = max(2, len(used) // 5)
    given = sorted(rng.sample(used, min(k, len(used) - 1)))
    freq = {}
    for ch in cipher:
        if ch in ALPHA:
            freq[ch] = freq.get(ch, 0) + 1
    return {"format": FORMAT, "version": 1, "seed": seed, "cipher": cipher,
            "given": {key[p]: p for p in given}, "frequency": dict(sorted(freq.items(), key=lambda t: (-t[1], t[0]))),
            "plain": plain, "key": {key[p]: p for p in used}}


def grade(puzzle, guess):
    plain = puzzle["plain"]
    g = clean(guess)
    letters = [i for i, ch in enumerate(plain) if ch in ALPHA]
    right = sum(1 for i in letters if i < len(g) and g[i] == plain[i])
    exact = g == plain
    verdict = "decoded" if exact else "partial" if 2 * right >= len(letters) else "garbled"
    return {"format": FORMAT, "version": 1, "seed": puzzle["seed"], "right": right, "letters": len(letters),
            "verdict": verdict}


def apply_mapping(puzzle, mapping):
    if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise CryptogramError("mapping must be a JSON object of cipher letter -> plain letter")
    m = {k.strip().upper(): v.strip().upper() for k, v in mapping.items()}
    if any(len(k) != 1 or k not in ALPHA or len(v) != 1 or v not in ALPHA for k, v in m.items()):
        raise CryptogramError("mapping keys and values must be single letters A-Z")
    m.update(puzzle["given"])
    return "".join(m.get(ch, "?") if ch in ALPHA else ch for ch in puzzle["cipher"])


def render(p, solution=False):
    lines = [f"harbour cryptogram (seed {p['seed']})", "  " + p["cipher"],
             "  given: " + ", ".join(f"{c}={v}" for c, v in sorted(p["given"].items())),
             "  frequency: " + " ".join(f"{c}{n}" for c, n in p["frequency"].items()),
             "  board: " + "".join(p["given"].get(ch, "_") if ch in ALPHA else ch for ch in p["cipher"])]
    if solution:
        lines.append("  plain: " + p["plain"])
    return "\n".join(lines) + "\n"


def _load(path, what):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise CryptogramError(f"{what}: {e}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Harbour Cryptogram: decode the telegraph built from the world census.")
    ap.add_argument("census")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--solution", action="store_true")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--guess", help="your plaintext")
    g.add_argument("--mapping", help="JSON file of cipher letter -> plain letter")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        p = make(_load(a.census, "census"), a.seed)
        if a.guess is not None or a.mapping:
            guess = a.guess if a.guess is not None else apply_mapping(p, _load(a.mapping, "mapping"))
            out = grade(p, guess)
            text = f"harbour cryptogram: {out['verdict']} ({out['right']}/{out['letters']} letters)\n"
            if a.mapping:
                text += "  reads: " + guess + "\n"
        else:
            out = p if a.solution else {k: v for k, v in p.items() if k not in ("plain", "key")}
            text = render(p, a.solution)
    except CryptogramError as e:
        print(f"harbour_cryptogram: refused: {e}", file=sys.stderr)
        return 2
    sys.stdout.write(json.dumps(out, indent=2, sort_keys=True) + "\n" if a.json else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
