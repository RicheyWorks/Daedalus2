#!/usr/bin/env python3
"""Prism Satchel + Warden Trials parity fixture (Python rules are the authority; the native core must match).

Writes engines/unreal/core-test/prism_satchel_parity.txt from tools/minigames/prism_satchel.py. Results are real demo
outcomes of all 11 Prismheart games (frozen in RUNS below), recorded into one satchel in a fixed order, with checked
spends in between and a set of tampered saves:

  pays g=<game> hue=<hue> div=<divisor> umbra=<par> heart=<par|perfect>       (the payout table)
  result g=<game> d=<difficulty> score=<s> won=<0|1> perfect=<0|1> pay=<n> hue=<hue> seal=<k> new=<n> text=<satchel save>
  spend cost=<hue:n,..> ok=<0|1> text=<satchel save>
  load text=<save> ok=<0|1>

DaedalusPrismSatchelCore.h reads only the inputs (game, difficulty, score, won, perfect; the cost; the save text) and must
reproduce every output byte for byte. Run `python tools/minigames/prism_satchel_parity.py --check` to verify.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prism_satchel as ps  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "engines", "unreal", "core-test",
                   "prism_satchel_parity.txt")
BAD_SAVES = (
    "PRISMSATCHEL0;0,0,0,0,0;0;",
    "PRISMSATCHEL1;0,0,0,0;0;",
    "PRISMSATCHEL1;0,0,0,0,-1;0;",
    "PRISMSATCHEL1;0,0,0,0,x;0;",
    "PRISMSATCHEL1;0,0,0,0,0;;",
    "PRISMSATCHEL1;0,0,0,0,0;1;nogame:2",
    "PRISMSATCHEL1;0,0,0,0,0;1;glowmoss:7",
    "PRISMSATCHEL1;0,0,0,0,0;1;glowmoss:0",
    "PRISMSATCHEL1;0,0,0,0,0;2;glowmoss:2,glowmoss:3",
    "PRISMSATCHEL1;0,0,0,0,0;2;spiritkite:2,glowmoss:3",
    "PRISMSATCHEL1;00,0,0,0,0;0;",
    "PRISMSATCHEL1;0,0,0,0,0;0;;",
    "PRISMSATCHEL1;1234567890,0,0,0,0;0;",
    "PRISMSATCHEL1;0,0,0,0,0;0;glowmoss:",
    "PRISMSATCHEL1;0,0,0,0,0;0;glowmoss:4",
    "PRISMSATCHEL1;0,0,0,0,0;0;facetlock:1,glowmoss:6",
)


# (game, difficulty, score, won, perfect): real demo outcomes (seeds 0-2 x easy/normal/hard, captured 2026-10-30).
# Frozen here so a rule change in another game never stales this fixture.
RUNS = (
    ('facetlock', 'easy', 160, True, False),
    ('glimmerloom', 'easy', 211, True, False),
    ('glowmoss', 'easy', 33, True, True),
    ('lumenpath', 'easy', 130, True, False),
    ('prismcairn', 'easy', 105, True, False),
    ('prismvault', 'easy', 150, True, False),
    ('shadewatch', 'easy', 125, True, False),
    ('shardfall', 'easy', 41, True, False),
    ('shardring', 'easy', 183, False, False),
    ('spiritkite', 'easy', 33, True, False),
    ('wardens_accord', 'easy', 45, True, False),
    ('facetlock', 'easy', 140, True, False),
    ('glimmerloom', 'easy', 91, False, False),
    ('glowmoss', 'easy', 36, True, True),
    ('lumenpath', 'easy', 190, True, False),
    ('prismcairn', 'easy', 105, True, False),
    ('prismvault', 'easy', 150, True, False),
    ('shadewatch', 'easy', 115, True, False),
    ('shardfall', 'easy', 43, True, False),
    ('shardring', 'easy', 339, True, False),
    ('spiritkite', 'easy', 26, True, False),
    ('wardens_accord', 'easy', 45, True, False),
    ('facetlock', 'easy', 140, True, False),
    ('glimmerloom', 'easy', 216, True, False),
    ('glowmoss', 'easy', 36, True, True),
    ('lumenpath', 'easy', 210, True, False),
    ('prismcairn', 'easy', 105, True, False),
    ('prismvault', 'easy', 150, True, False),
    ('shadewatch', 'easy', 130, True, False),
    ('shardfall', 'easy', 51, True, False),
    ('shardring', 'easy', 54, False, False),
    ('spiritkite', 'easy', 20, True, False),
    ('wardens_accord', 'easy', 55, True, False),
    ('facetlock', 'normal', 140, True, False),
    ('glimmerloom', 'normal', 178, True, False),
    ('glowmoss', 'normal', 48, True, True),
    ('lumenpath', 'normal', 110, True, False),
    ('prismcairn', 'normal', 105, True, False),
    ('prismvault', 'normal', 100, True, False),
    ('shadewatch', 'normal', 144, True, False),
    ('shardfall', 'normal', 38, False, False),
    ('shardring', 'normal', 88, False, False),
    ('spiritkite', 'normal', 24, True, False),
    ('wardens_accord', 'normal', 50, True, False),
    ('facetlock', 'normal', 150, True, False),
    ('glimmerloom', 'normal', 64, False, False),
    ('glowmoss', 'normal', 42, True, True),
    ('lumenpath', 'normal', 160, True, False),
    ('prismcairn', 'normal', 105, True, False),
    ('prismvault', 'normal', 100, True, False),
    ('shadewatch', 'normal', 149, True, False),
    ('shardfall', 'normal', 40, True, False),
    ('shardring', 'normal', 27, False, False),
    ('spiritkite', 'normal', 28, True, False),
    ('wardens_accord', 'normal', 65, True, False),
    ('facetlock', 'normal', 160, True, False),
    ('glimmerloom', 'normal', 108, False, False),
    ('glowmoss', 'normal', 29, True, True),
    ('lumenpath', 'normal', 190, True, False),
    ('prismcairn', 'normal', 105, True, False),
    ('prismvault', 'normal', 100, True, False),
    ('shadewatch', 'normal', 144, True, False),
    ('shardfall', 'normal', 42, True, False),
    ('shardring', 'normal', 108, False, False),
    ('spiritkite', 'normal', 23, True, False),
    ('wardens_accord', 'normal', 50, True, False),
    ('facetlock', 'hard', 160, True, False),
    ('glimmerloom', 'hard', 110, True, False),
    ('glowmoss', 'hard', 51, True, True),
    ('lumenpath', 'hard', 150, True, False),
    ('prismcairn', 'hard', 105, True, False),
    ('prismvault', 'hard', 100, True, False),
    ('shadewatch', 'hard', 97, False, False),
    ('shardfall', 'hard', 30, False, False),
    ('shardring', 'hard', 27, False, False),
    ('spiritkite', 'hard', 31, True, False),
    ('wardens_accord', 'hard', 50, False, False),
    ('facetlock', 'hard', 130, True, False),
    ('glimmerloom', 'hard', 146, True, False),
    ('glowmoss', 'hard', 40, True, True),
    ('lumenpath', 'hard', 170, True, False),
    ('prismcairn', 'hard', 105, True, False),
    ('prismvault', 'hard', 100, True, False),
    ('shadewatch', 'hard', 158, True, False),
    ('shardfall', 'hard', 25, False, False),
    ('shardring', 'hard', 9, False, False),
    ('spiritkite', 'hard', 30, True, False),
    ('wardens_accord', 'hard', 50, False, False),
    ('facetlock', 'hard', 130, True, False),
    ('glimmerloom', 'hard', 88, False, False),
    ('glowmoss', 'hard', 30, True, True),
    ('lumenpath', 'hard', 140, True, False),
    ('prismcairn', 'hard', 105, True, False),
    ('prismvault', 'hard', 100, True, False),
    ('shadewatch', 'hard', 153, True, False),
    ('shardfall', 'hard', 23, False, False),
    ('shardring', 'hard', 27, False, False),
    ('spiritkite', 'hard', 26, True, False),
    ('wardens_accord', 'hard', 55, True, False),
)


def generate():
    out = ["# prism_satchel_parity.txt: generated by tools/minigames/prism_satchel_parity.py from prism_satchel.py (Python "
           "rules are the authority). Do not hand-edit."]
    for game in sorted(ps.PAYOUTS):
        hue, div, umbra, heart = ps.PAYOUTS[game]
        out.append("pays g=%s hue=%s div=%d umbra=%d heart=%s" % (game, hue, div, umbra, heart))
    sat = ps.Satchel()
    for i, (game, d, score, won, perfect) in enumerate(RUNS):
        pay, hue, seal, new = sat.record(game, d, score, won, perfect)
        out.append("result g=%s d=%s score=%d won=%d perfect=%d pay=%d hue=%s seal=%d new=%d text=%s" % (
            game, d, score, int(won), int(perfect), pay, hue, seal, new, sat.to_text()))
        if i % 7 == 6:
            cost = {ps.HUES[i % 5]: 2 + i % 9, ps.HUES[(i * 3 + 1) % 5]: 1 + i % 4}
            try:
                sat.spend(cost)
                ok = 1
            except ValueError:
                ok = 0
            text = ",".join("%s:%d" % (h, cost[h]) for h in ps.HUES if h in cost)
            out.append("spend cost=%s ok=%d text=%s" % (text, ok, sat.to_text()))
    for text in (sat.to_text(), ps.Satchel().to_text()) + BAD_SAVES:
        try:
            ps.Satchel.from_text(text)
            ok = 1
        except ValueError:
            ok = 0
        out.append("load text=%s ok=%d" % (text, ok))
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed file differs")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args(argv)
    text = generate()
    if a.check:
        with open(a.out, encoding="utf-8") as fh:
            same = fh.read() == text
        print("parity file %s" % ("current" if same else "STALE"))
        return 0 if same else 1
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s (%d lines)" % (os.path.normpath(a.out), text.count("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
