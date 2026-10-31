# SPDX-License-Identifier: MIT
"""Golden file for G608 Replay Notary (DiskSaver Island, quest q_replay_notary; Prismheart tournaments lane).

A leaderboard entry is one line, notary1|game|seed|plan|claim. The notary lays the puzzle from the seed and
replays the plan through the game's own rules, here the Python fixture tools of G590 Gantry Sweep
(gantry_sweep_parity.py), G597 Buddy Berths (buddy_berths_parity.py) and G598 Tidelinks Golf
(tidelinks_golf_parity.py), so the C++ DaedalusDiskSaverReplayNotaryCore.h is checked against an independent
reference. Each case writes the entry (hex, so any bytes can be tested) and the result line the notary must give.
Rules: docs/islands/DISKSAVER-REPLAY-NOTARY.md.

  python tools/streaming/replay_notary_parity.py            # print the golden file
  python tools/streaming/replay_notary_parity.py --check    # exit 1 if the checked-in file is stale
  python tools/streaming/replay_notary_parity.py --write    # rewrite it
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import buddy_berths_parity as bbp  # noqa: E402
import gantry_sweep_parity as gsp  # noqa: E402
import tidelinks_golf_parity as tgp  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
GOLDEN = os.path.join(ROOT, "engines", "unreal", "core-test", "disksaver_replay_notary_parity.txt")
MAX_ENTRY, MAX_SEED, MAX_NUMBER, MAX_CLAIM = 8192, 256, 4, 9
GANTRY = {"gantry-calm": "calm", "gantry-rush": "rush", "gantry-spread": "spread", "gantry-storm": "storm"}
GAMES = tuple(GANTRY) + ("berths", "golf")


def number(s, digits):
    if not s or len(s) > digits or (len(s) > 1 and s[0] == "0") or any(c not in "0123456789" for c in s):
        return None
    return int(s)


def numbers(s, dash):
    if s == "":
        return []
    out = []
    for t in s.split(","):
        if dash and t == "-":
            out.append(None)
            continue
        v = number(t, MAX_NUMBER)
        if v is None:
            return False
        out.append(v)
    return out


def golf_card(s):
    if s == "":
        return []
    card = []
    for h in s.split("/"):
        if h == "-":
            card.append([])
            continue
        toks = h.split(",")
        if any(len(t) != 1 for t in toks):
            return False
        card.append(toks)
    return card


def score_fields(game, r):
    if game == "golf":
        return f"strokes={r[0]} topar={tgp.topar(r[1])}"
    if game == "berths":
        return f"turned={r[0]}"
    return f"waits={r[0]} travel={r[1]}"


def notarise(entry):
    """The result line for an entry (bytes)."""
    if len(entry) > MAX_ENTRY:
        return "bad long"
    f = entry.split(b"|")
    if len(f) != 5:
        return "bad fields"
    if f[0] != b"notary1":
        return "bad version"
    game = f[1].decode("latin-1")
    if f[1] not in [g.encode() for g in GAMES]:
        return "bad game"
    if not 1 <= len(f[2]) <= MAX_SEED or any(not 0x20 <= b <= 0x7E for b in f[2]):
        return "bad seed"
    seed = f[2].decode("ascii")
    claim = -1
    if f[4] != b"-":
        claim = number(f[4].decode("latin-1"), MAX_CLAIM)
        if claim is None:
            return "bad claim"
    plan = f[3].decode("latin-1")
    if game == "golf":
        card = golf_card(plan)
        if card is False:
            return "bad plan"
        holes = tgp.course(seed)
        t, e = tgp.play(holes, card)
        if e:
            return f"refused golf {e[0]} hole={e[1]}"
        pl = tgp.plans(holes)
        opt = tgp.strokes_raw(holes, pl["best"])
        hab = min(tgp.strokes_raw(holes, pl[k]) for k in ("safe", "bold", "layup"))
        v = "masterful" if t == opt else "steady" if t <= hab else "rough"
        r = (t, t - sum(tgp.par_of(h[1]) for h in holes))
    elif game == "berths":
        p = numbers(plan, True)
        if p is False:
            return "bad plan"
        out = bbp.play_line(bbp.layout(seed), p).split()
        if out[1] == "refused":
            return f"refused berths {out[2]}"
        r, v = (int(out[2]),), out[3]
    else:
        p = numbers(plan, False)
        if p is False:
            return "bad plan"
        start, ships = gsp.layout(seed, GANTRY[game])
        out = gsp.play(start, ships, p).split()
        if out[1] == "refused":
            return f"refused {game} {out[2]}"
        r, v = (int(out[2]), int(out[3])), out[4]
    head = "ok" if claim < 0 or claim == r[0] else "forged"
    claim_s = f" claim={claim}" if head == "forged" else ""
    return f"{head} {game}{claim_s} {score_fields(game, r)} verdict={v}"


def entry(game, seed, plan, claim):
    return f"notary1|{game}|{seed}|{plan}|{claim}".encode("utf-8")


def gantry_plans(game, seed, rng):
    start, ships = gsp.layout(seed, GANTRY[game])
    n = len(ships)
    best = gsp.best(start, ships)
    out = [gsp.j(best)] + [gsp.j(f(start, ships)) for _, f in gsp.HABITS]
    perm = list(range(n))
    rng.shuffle(perm)
    out += [gsp.j(perm), gsp.j(best[:-1]), gsp.j(best + [best[0]]), gsp.j(best[:-1] + [n]), gsp.j([best[0]] * n),
            "", ",".join(map(str, best)) + ",", " " + gsp.j(best), gsp.j(best).replace(str(best[0]), "0" + str(best[0]), 1)]
    return out, gsp.run(start, ships, best)[0]


def berths_plans(seed, rng):
    ships = bbp.layout(seed)
    best = bbp.best(ships)
    habits = [bbp.habit(ships, f) for f in (bbp.lowest, bbp.tightest, bbp.highest)]
    out = [bbp.j(best)] + [bbp.j(h) for h in habits]
    rnd = [rng.choice([None, 0, 1, 2, 4, 8, 12]) for _ in ships]
    out += [bbp.j(rnd), bbp.j([None] * len(ships)), bbp.j(best[:-1]), bbp.j(best + [None]), bbp.j([0] * len(ships)),
            bbp.j([3] + best[1:]), bbp.j([16] + best[1:]), "x" + bbp.j(best), "", bbp.j([10000] + best[1:])]
    return [p if p != "none" else "" for p in out], bbp.simulate(ships, best)[0]


def golf_plans(seed, rng):
    holes = tgp.course(seed)
    pl = tgp.plans(holes)
    b = pl["best"]
    out = [tgp.card_str(pl[k]) for k in ("best", "safe", "bold", "layup")]
    rnd = [[rng.choice(tgp.CODES) for _ in range(rng.randrange(1, 6))] for _ in holes]
    out += [tgp.card_str(rnd), tgp.card_str([["X"] + b[0]] + b[1:]), tgp.card_str([b[0][:-1]] + b[1:]),
            tgp.card_str([b[0] + ["P"]] + b[1:]), tgp.card_str(b[:-1]), tgp.card_str(b + [["P"]]),
            tgp.card_str([["P"] * 12 for _ in holes]), tgp.card_str([[]] + b[1:]), tgp.card_str(b).replace(",", "", 1),
            tgp.card_str(b) + "/", "", tgp.card_str(b[:1] + [b[1] + ["P"]] + b[2:]), tgp.card_str(b[:-1] + [b[-1][:-1]]),
            tgp.card_str(b[:-1] + [["Q"]])]
    return out, tgp.strokes_raw(holes, b)


def lines():
    out = ["# disksaver replay_notary parity v1: written by tools/streaming/replay_notary_parity.py; do not edit",
           "# E <entry hex>, then R <result line>"]
    rng = random.Random("replay-notary fixture entries")
    cases = []
    seeds = ["tidewatch-cup:2026-10-30", "tidewatch-cup:2026-10-31", "notary:7", "a", "Tidewatch Cup day 42!",
             "~" * MAX_SEED]
    seeds += [f"notary:bulk:{k}" for k in range(8)]
    for s in seeds:
        for g in GANTRY:
            plans, best = gantry_plans(g, s, rng)
            cases += [entry(g, s, p, "-") for p in plans]
            cases += [entry(g, s, plans[0], str(best)), entry(g, s, plans[0], str(best + 1))]
        plans, best = berths_plans(s, rng)
        cases += [entry("berths", s, p, "-") for p in plans]
        cases += [entry("berths", s, plans[0], str(best)), entry("berths", s, plans[1], "0")]
        plans, best = golf_plans(s, rng)
        cases += [entry("golf", s, p, "-") for p in plans]
        cases += [entry("golf", s, plans[0], str(best)), entry("golf", s, plans[0], str(max(best - 1, 0)))]
    good = entry("golf", "tidewatch-cup:2026-10-30", golf_plans("tidewatch-cup:2026-10-30", random.Random(0))[0][0], "-")
    odd = [b"", b"notary1", b"notary1|golf|s|D", b"notary1|golf|s|D|-|x", b"notary2|golf|s|D|-", b"Notary1|golf|s|D|-",
           b"notary1|Golf|s|D|-", b"notary1|gantry|s|0|-", b"notary1|gantry-calm||0|-", b"notary1|golf|" + b"s" * (MAX_SEED + 1) + b"|D|-",
           b"notary1|golf|tab\there|D|-", b"notary1|golf|caf\xc3\xa9|D|-", b"notary1|golf|del\x7f|D|-", b"notary1|golf|s|D|",
           b"notary1|golf|s|D|+3", b"notary1|golf|s|D|03", b"notary1|golf|s|D|1234567890", b"notary1|golf|s|D|123456789",
           b"notary1|golf|s|D|0", b"notary1|gantry-calm|s|1,2,x|-", b"notary1|gantry-calm|s|12345|-",
           b"notary1|gantry-calm|s|-1|-", b"notary1|berths|s|-,--|-", b"notary1|golf|s|DW|-", b"notary1|golf|s|D,,P|-",
           b"notary1|golf|s|//|-", good.replace(b"|-", b"|7"), b"x" * (MAX_ENTRY + 1), good + b"\r",
           b"notary1|golf|" + b"s" * MAX_SEED + b"|" + b"P," * 2000 + b"P|-"]
    cases += odd
    for e in cases:
        out += ["E x" + e.hex(), "R " + notarise(e)]
    return out


def main(argv):
    text = "\n".join(lines()) + "\n"
    if "--write" in argv:
        with open(GOLDEN, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return 0
    if "--check" in argv:
        try:
            with open(GOLDEN, encoding="utf-8") as f:
                ok = f.read() == text
        except OSError:
            ok = False
        print("replay notary parity " + ("up to date" if ok else "STALE (rerun --write)"))
        return 0 if ok else 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
