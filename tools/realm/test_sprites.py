# SPDX-License-Identifier: MIT
"""Offline checks of the DSP 1 writer/parser, and the parity fixture the C++ test replays. Run: python test_sprites.py"""
import os

import sprites as S

ok = total = 0


def check(name, cond):
    global ok, total
    total += 1
    ok += bool(cond)
    print(("PASS " if cond else "FAIL ") + name)


pal = [0xF8A070, 0x000000, 0xFCFCFC, 0x58D840]
slime = ["....3333....", "...333333...", "..33333333..", ".3332332333.", ".3333333333.", "..33333333..",
         "............", "............", "............", "............", "............", "............"]
slime2 = [r for r in slime[1:]] + ["............"]
text = S.write(pal, {"BLIGHT_SLIME": (12, 12, 2, slime + slime2),
                     "MEMBER:HERO": (4, 4, 8, ["...."] * 32)})
pack, err = S.parse(text)
check("a written pack parses", err is None)
check("black is stored as 010101 (0 means transparent)", pack["palette"][1] == 0x010101)
check("ids and frames survive", pack["sprites"]["BLIGHT_SLIME"][2] == 2 and pack["sprites"]["MEMBER:HERO"][2] == 8)
check("sprites come out sorted", list(pack["sprites"]) == ["BLIGHT_SLIME", "MEMBER:HERO"])

# refusals the C++ parser must give word for word
cases = [
    ("hello\n", "line 1: expected 'DSP 1'"),
    ("DSP 1\nsprite A 2 2 1\n..\n..\n", "line 2: sprite before the palette"),
    ("DSP 1\npalette 1 FF0000\nsprite A 2 2 1\n...\n", "line 4: row of 3 for a sprite 2 wide"),
    ("DSP 1\npalette 1 FF0000\nsprite A 2 2 1\n.1\n..\n", "line 4: colour '1' is not in the palette"),
    ("DSP 1\npalette 1 FF0000\nsprite A 2 2 1\n..\n", "line 5: sprite A ends early"),
    ("DSP 1\npalette 1 FF0000\nsprite A 2 2 1\n..\n..\nsprite A 1 1 1\n.\n", "line 6: duplicate sprite A"),
    ("DSP 1\npalette 1 FF0000\nsprite A 200 2 1\n", "line 3: bad size"),
    ("DSP 1\npalette 1 FF0000\nsprite A 2 2 40\n", "line 3: bad frame count"),
    ("DSP 1\npalette 2 FF0000\n", "line 2: palette count does not match"),
    ("DSP 1\npalette 1 FF00ZZ\n", "line 2: bad colour FF00ZZ"),
    ("DSP 1\npalette 1 FF0000\nthing\n", "line 3: unknown record thing"),
    ("DSP 1\npalette 1 FF0000\n", "line 3: no palette") if False else ("DSP 1\n", "line 2: no palette"),
    ("DSP 1\npalette 1 FF0000\nsprite bad id 2 2 1\n", "line 3: expected 'sprite <id> <w> <h> <frames>'"),
    ("DSP 1\npalette 1 FF0000\nsprite A\t2 2 1\n", "line 3: tab"),
]
for t, want in cases:
    _, e = S.parse(t)
    check("refuses: " + want, e == want)

here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "sprites_parity.txt"), "w", newline="\n") as f:
    f.write("# DSP 1 parity: each case is 'CASE', the text with \\n for newlines, then 'WANT <error or OK n>'\n")
    for t, want in cases:
        f.write("CASE %s\nWANT %s\n" % (t.replace("\n", "\\n"), want))
    f.write("CASE %s\nWANT OK 2\n" % text.replace("\n", "\\n"))
check("the parity fixture is written", os.path.exists(os.path.join(here, "sprites_parity.txt")))
print("%d/%d" % (ok, total))
raise SystemExit(0 if ok == total else 1)
