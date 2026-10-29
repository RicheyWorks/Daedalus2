# SPDX-License-Identifier: MIT
"""youtube-master YTM wave d (G254..G492, 71 asks 55071..56438, 2026-10-26 21:15 -> 2026-10-27 PT), blender-kit/v1, G66 island palette.
Built from archetype helpers (pot, basket, crate, post, stone, tree, critter, line, hut, mat) on top of ytm_wave_c (table, stool, board,
boat_parts, stall, lantern_pole, small). Origin bottom-centre, Blender front -Y (place yaw -90), sockets for the Daedalus hook,
UCX on anything walked into. Variants that are one mesh with a different face/tint are one mesh + spec.mi_set.
Assets named in more than one ask (GrainSack, RowBoat, SoupPot, FireLogSeat) are built once (first gap) and staged in every folder;
Prop_YTM_RopeCoil (G212) and Prop_YTM_Fiddle are REUSE, not rebuilt.
Usage: python ytm_wave_d.py --gap G254 --out data/contest/ytm_d_g254.kit.json"""
import argparse, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "kit")); sys.path.insert(0, HERE)
import kitlib as K
from backlog_20261026 import M, asset, TIMBER, SIGN, IRON, STONE, EMBER, SAND, ROPE, PAPER, BRASS
import ytm_wave_c
from ytm_wave_c import CLOTH4, legs4, table, stool, board, boat_parts, stall, lantern_pole

ASK = {}
for _l in """55071 G254 55087 G258 55107 G262 55125 G266 55141 G269 55156 G272 55175 G275 55203 G278 55232 G282 55271 G289 55296 G293
55312 G297 55339 G301 55365 G306 55389 G312 55408 G316 55430 G319 55456 G323 55481 G328 55502 G333 55526 G338 55557 G342 55577 G348
55603 G351 55616 G357 55636 G360 55664 G363 55687 G368 55707 G374 55731 G378 55753 G383 55775 G387 55798 G390 55815 G395 55832 G398
55855 G401 55869 G404 55890 G407 55919 G410 55937 G415 55961 G417 55984 G420 56003 G424 56022 G427 56047 G429 56062 G434 56082 G437
56100 G440 56122 G443 56144 G448 56169 G453 56189 G456 56206 G460 56236 G463 56250 G466 56262 G468 56271 G470 56284 G471 56290 G472
56303 G474 56319 G476 56327 G478 56339 G479 56350 G481 56363 G482 56374 G484 56385 G486 56396 G487 56408 G489 56420 G490 56438 G492""".split("\n"):
    t = _l.split()
    for i in range(0, len(t), 2): ASK[t[i + 1]] = int(t[i])
ytm_wave_c.ASK.update(ASK)   # wave c helpers (table/board/stall/lantern_pole) look up the ask id by gap
WATER, LEAF, BARK, CLAY, WICKER, RED, FUR, SHELL = "4A9AB0", "5E9A48", "6A4E36", "B8643C", "C8A060", "C83A30", "D8CCB8", "F0D8C8"


def Y(g):
    return (g, "youtube-master %d" % ASK[g])


def sm(a, g, P, mats, S, size, ucx=None):
    return asset(a, *Y(g), P, [M(a, i, *m) for i, m in enumerate(mats)], S, ucx or [], size)


def hand(z):
    return K.socket("Hand", (0, 0, z))


# ---- archetypes -------------------------------------------------------------------------------------------------------------
def pot(a, g, r, h, col=CLAY, lid=False, handles=False, note="pot", seg=14):
    P = [K.lathe("Body", [(r * 0.65, 0), (r, h * 0.35), (r * 0.92, h * 0.8), (r * 0.7, h * 0.93), (r * 0.78, h)], (0, 0, 0), 0, seg, cap_top=lid)]
    if lid: P.append(K.cyl("Lid", "z", r * 0.8, r * 0.4, h * 0.12, (0, 0, h + h * 0.06), 0, seg))
    if handles:
        for s in (-1, 1): P.append(K.box("Ear%d" % s, (r * 0.25, r * 0.12, r * 0.18), (s * r * 1.05, 0, h * 0.72), 0))
    return sm(a, g, P, [(note + " (G66 clay)", col)], [K.socket("Contents", (0, 0, h * 0.85)), hand(h * 0.7)], "%.2f m dia x %.2f m %s" % (2 * r, h, note),
              [K.ucx_prism(a, 0, "z", r, h, (0, 0, h / 2))] if r > 0.15 else [])


def arch(name, R, t, centre, slot, n=10, width=0.02):
    """Semicircular handle/bail in the X-Z plane: outer radius R, band t, ends at centre +-R."""
    out = [(R * math.cos(math.pi * k / n), R * math.sin(math.pi * k / n)) for k in range(n + 1)]
    inn = [((R - t) * math.cos(math.pi * k / n), (R - t) * math.sin(math.pi * k / n)) for k in range(n, -1, -1)]
    return K.slab(name, out + inn, width, centre, slot, rot=(90, 0, 0))


def basket(a, g, r, h, handle=True, col=WICKER, note="basket", oval=1.0, fill=None):
    P = [K.lathe("Weave", [(r * 0.8, 0), (r, h * 0.85), (r * 1.04, h)], (0, 0, 0), 0, 14, cap_top=False, rot=None)]
    P.append(K.lathe("Rim", [(r * 0.98, h - 0.012), (r * 1.08, h - 0.012), (r * 1.08, h + 0.018), (r * 0.98, h + 0.018)], (0, 0, 0), 1, 14, cap_bottom=False, cap_top=False))
    if handle: P.append(arch("Handle", r * 0.95, r * 0.06, (0, 0, h), 1))
    mats = [("wicker (G66)", col), ("rim / handle", BARK)]
    if fill:
        P.append(K.cyl("Fill", "z", r * 0.95, r * 0.6, h * 0.25, (0, 0, h * 0.95), 2, 12)); mats.append(fill)
    return sm(a, g, P, mats, [K.socket("Contents", (0, 0, h)), hand(h + r * 0.85 if handle else h)], "%.2f m dia x %.2f m %s" % (2 * r, h, note))


def crate(a, g, w, d, h, col=TIMBER, note="crate"):
    P = [K.box("Box", (w, d, h), (0, 0, h / 2), 0)] + [K.box("Slat%d" % i, (w + 0.01, d + 0.01, 0.04), (0, 0, h * (0.2 + 0.6 * i)), 1) for i in range(2)]
    return sm(a, g, P, [("planks (G66 timber)", col), ("bands", BARK)], [K.socket("Top", (0, 0, h)), K.socket("Lift", (0, 0, h / 2))], "%.2f x %.2f x %.2f m %s" % (w, d, h, note),
              [K.ucx_box(a, 0, (w, d, h), (0, 0, h / 2))])


def post(a, g, h, r=0.07, top=None, slot1=SIGN, note="post", extra=None, socks=None):
    P = [K.cyl("Post", "z", r, r * 0.85, h, (0, 0, h / 2), 0, 8), K.cyl("Cap", "z", r * 1.2, r * 0.3, 0.08, (0, 0, h + 0.04), 1, 8)] + (extra or [])
    return sm(a, g, P, [("post (G66 timber)", TIMBER), ("cap / marks (G66)", slot1), ("detail", top or CLOTH4[0])], [K.socket("Top", (0, 0, h + 0.08)), K.socket("Base", (0, 0, 0))] + (socks or []),
              "%.2f m %s" % (h, note), [K.ucx_prism(a, 0, "z", r, h, (0, 0, h / 2))])


def stone(a, g, w, d, h, seed, col=STONE, note="stone", n=3, socks=None):
    r = K.rng(seed, a); P = []
    for i in range(n):
        f = 1 - 0.22 * i
        P.append(K.box("Chunk%d" % i, (w * f * r.uniform(0.85, 1), d * f * r.uniform(0.85, 1), h / n * r.uniform(0.95, 1.15)), (r.uniform(-0.04, 0.04) * w, r.uniform(-0.04, 0.04) * d, h / n * (i + 0.5)), 0, rot=(r.uniform(-4, 4), r.uniform(-4, 4), r.uniform(-20, 20))))
    return sm(a, g, P, [(note + " (G66 stone)", col)], [K.socket("Top", (0, 0, h))] + (socks or []), "%.2f x %.2f x %.2f m %s" % (w, d, h, note), [K.ucx_box(a, 0, (w, d, h), (0, 0, h / 2))])


def tree(a, g, h, cr, fruit=0, fcol=RED, note="tree", seed=1):
    r = K.rng(seed, a); P = [K.cyl("Trunk", "z", 0.14, 0.08, h * 0.55, (0, 0, h * 0.275), 0, 8)]
    for i in range(5):
        an = i * 2 * math.pi / 5; P.append(K.lathe("Crown%d" % i, [(0.01, -cr * 0.55), (cr * 0.6, -cr * 0.3), (cr * 0.65, cr * 0.1), (0.01, cr * 0.5)], (cr * 0.45 * math.cos(an), cr * 0.45 * math.sin(an), h - cr * 0.6 + r.uniform(-0.1, 0.15)), 1, 8))
    P.append(K.lathe("CrownTop", [(0.01, -cr * 0.5), (cr * 0.7, -cr * 0.2), (cr * 0.6, cr * 0.25), (0.01, cr * 0.55)], (0, 0, h - cr * 0.4), 1, 10))
    S = [K.socket("Trunk", (0, -0.15, 1.0))]
    for i in range(fruit):
        an = i * 2.399; rr = cr * 0.95; z = h - cr * 0.9 + 0.5 * cr * ((i * 0.37) % 1)
        p = (rr * math.cos(an), rr * math.sin(an), z); P.append(K.cyl("Fruit%d" % i, "z", 0.045, 0.04, 0.08, p, 2, 6)); S.append(K.socket("Cluster_%d" % i, p))
    return sm(a, g, P, [("bark", BARK), ("leaves (G66 green)", LEAF), ("fruit", fcol)], S, "%.1f m %s" % (h, note), [K.ucx_prism(a, 0, "z", 0.15, h * 0.55, (0, 0, h * 0.275))])


def critter(a, g, L, H, col, legs=4, head=True, note="critter", horns=False, flat=False):
    bw = L * (0.9 if flat else 0.42); bh = H * (0.5 if flat else 0.45); z = H - bh / 2 - (0 if flat else H * 0.15)
    P = [K.cyl("Body", "z", bw * 0.5, bw * 0.4, bh, (0, 0, z), 0, 10)] if flat else [K.lathe("Body", [(0.01, -L / 2), (bh * 0.55, -L * 0.3), (bh * 0.6, L * 0.2), (0.01, L / 2)], (0, 0, z), 0, 10, rot=(90, 0, 0))]
    S = [K.socket("Body", (0, 0, z)), K.socket("Root", (0, 0, 0))]
    if head and flat:
        for s_ in (-1, 1): P.append(K.cyl("Stalk%d" % s_, "z", 0.004, 0.004, 0.025, (s_ * bw * 0.12, -bw * 0.4, z + bh / 2 + 0.012), 1, 4))
        S.append(K.socket("Head", (0, -bw * 0.45, z)))
    elif head:
        hp = (0, -bw * 0.45, z + bh * 0.3) if flat else (0, -L * 0.55, z + bh * 0.55); P.append(K.box("Head", (bh * 0.6, L * 0.3, bh * 0.55), hp, 0)); S.append(K.socket("Head", hp))
        P.append(K.box("EyeL", (0.02, 0.01, 0.02), (-bh * 0.18, hp[1] - L * 0.15, hp[2] + bh * 0.1), 1, bevel=False)); P.append(K.box("EyeR", (0.02, 0.01, 0.02), (bh * 0.18, hp[1] - L * 0.15, hp[2] + bh * 0.1), 1, bevel=False))
        if horns:
            for s in (-1, 1): P.append(K.cyl("Horn%d" % s, "z", 0.02, 0.005, 0.12 * L, (s * bh * 0.2, hp[1] + 0.03, hp[2] + bh * 0.4), 1, 6, rot=(-35, s * 15, 0)))
    leg_h = z - bh / 2 + 0.02
    for i in range(legs):
        side = -1 if i % 2 == 0 else 1; k = i // 2; n = max(1, legs // 2); y = -L * 0.3 + L * 0.6 * k / max(1, n - 1)
        if flat: y = -bw * 0.2 + bw * 0.2 * k; P.append(K.box("Leg%d" % i, (bw * 0.45, 0.012, 0.012), (side * bw * 0.62, y, z - bh * 0.3), 0, rot=(0, side * 35, 0)))
        else: P.append(K.cyl("Leg%d" % i, "z", 0.035 * L, 0.03 * L, leg_h, (side * bw * 0.3, y, leg_h / 2), 0, 6))
    if flat:
        for s in (-1, 1): P.append(K.box("Claw%d" % s, (0.06 * L, 0.18 * L, 0.05 * L), (s * bw * 0.3, -bw * 0.62, z), 0, rot=(0, 0, s * 20))); S.append(K.socket("Claw_%s" % ("L" if s < 0 else "R"), (s * bw * 0.3, -bw * 0.72, z)))
    return sm(a, g, P, [("body (G66)", col), ("eyes / horns", "2A2420")], S, "%.2f m long %s (static; rig via quadruped recipe if animated)" % (L, note), [K.ucx_box(a, 0, (bw, L, H), (0, 0, H / 2))] if L > 0.4 else [])


def line(a, g, L, n, item, icol, sag=0.25, note="line", item_z=-0.08, rope=ROPE, prefix="Item"):
    P = [K.cyl("Rope%d" % i, "x", 0.008, 0.008, L / 8 + 0.01, (-L / 2 + L / 16 + L / 8 * i, 0, -sag * (1 - ((-L / 2 + L / 16 + L / 8 * i) * 2 / L) ** 2)), 0, 5,
               rot=(0, -math.degrees(math.atan(sag * 8 * (-L / 2 + L / 16 + L / 8 * i) / L ** 2)), 0)) for i in range(8)]
    S = [K.socket("EndA", (-L / 2, 0, 0)), K.socket("EndB", (L / 2, 0, 0))]
    for i in range(n):
        x = -L / 2 + L * (i + 0.5) / n; z = -sag * (1 - (2 * x / L) ** 2)
        P.append(item("%s%d" % (prefix, i), (x, 0, z + item_z), 1 + i % 2)); S.append(K.socket("%s_%d" % (prefix, i), (x, 0, z + item_z)))
    return sm(a, g, P, [("line", rope), ("items A (G66)", icol[0]), ("items B (G66)", icol[1 % len(icol)])], S, "%.1f m %s; hang EndA/EndB" % (L, note))


def mat(a, g, w, d, col, stripes=4, note="mat"):
    P = [K.box("Mat", (w, d, 0.015), (0, 0, 0.0075), 0, bevel=False)] + [K.box("Stripe%d" % i, (w, d / (stripes * 3), 0.017), (0, -d / 2 + d * (i + 0.5) / stripes, 0.0085), 1, bevel=False) for i in range(stripes)]
    return sm(a, g, P, [("weave (G66)", col), ("stripes (G66)", CLOTH4[2])], [K.socket("Centre", (0, 0, 0.015))], "%.1f x %.1f m %s" % (w, d, note))


def hut(a, g, w, d, h, stilts=0.0, note="hut"):
    z0 = stilts; P = []
    if stilts:
        for x in (-w / 2 + 0.1, w / 2 - 0.1):
            for y in (-d / 2 + 0.1, d / 2 - 0.1): P.append(K.cyl("Stilt%+.1f%+.1f" % (x, y), "z", 0.08, 0.08, stilts, (x, y, stilts / 2), 0, 8))
        P.append(K.box("Deck", (w + 0.6, d + 0.6, 0.08), (0, 0, z0), 0)); P.append(K.box("Ladder", (0.5, 0.05, stilts), (0, -d / 2 - 0.5, stilts / 2), 0, rot=(-15, 0, 0)))
    P += [K.box("Walls", (w, d, h), (0, 0, z0 + h / 2), 1), K.box("Door", (0.8, 0.04, 1.8), (0, -d / 2 - 0.01, z0 + 0.9), 3),
          K.box("RoofL", (w * 0.62, d + 0.6, 0.08), (-w * 0.254, 0, z0 + h + w * 0.36 - w * 0.178), 2, rot=(0, -35, 0)),
          K.box("RoofR", (w * 0.62, d + 0.6, 0.08), (w * 0.254, 0, z0 + h + w * 0.36 - w * 0.178), 2, rot=(0, 35, 0)),
          K.slab("GableF", [(-w / 2, 0), (w / 2, 0), (0, w * 0.34)], 0.05, (0, -d / 2 + 0.025, z0 + h), 1, rot=(90, 0, 0)),
          K.slab("GableB", [(-w / 2, 0), (w / 2, 0), (0, w * 0.34)], 0.05, (0, d / 2 - 0.025, z0 + h), 1, rot=(90, 0, 0))]
    return sm(a, g, P, [("timber (G66)", TIMBER), ("walls (G66 whitewash)", "E8DCC0"), ("thatch", "B89858"), ("door (G66 cloth)", CLOTH4[0])],
              [K.socket("Door", (0, -d / 2 - 0.3, z0)), K.socket("Inside", (0, 0, z0)), K.socket("Roof", (0, 0, z0 + h + w * 0.36))], "%.1f x %.1f m %s" % (w, d, note),
              [K.ucx_box(a, 0, (w, d, z0 + h), (0, 0, (z0 + h) / 2))])


def drum(a, g, r, h, note="drum"):
    P = [K.cyl("Shell", "z", r * 0.9, r, h, (0, 0, h / 2), 0, 14), K.cyl("Skin", "z", r * 1.02, r * 1.02, 0.01, (0, 0, h + 0.005), 1, 14)] + [K.box("Cord%d" % i, (0.01, 0.01, h), (r * 0.98 * math.cos(i * math.pi / 4), r * 0.98 * math.sin(i * math.pi / 4), h / 2), 2, bevel=False) for i in range(8)]
    return sm(a, g, P, [("shell (G66 timber)", TIMBER), ("hide", FUR), ("cords", ROPE)], [K.socket("Strike", (0, 0, h + 0.01)), hand(h / 2)], "%.2f m dia %s" % (2 * r, note))


def slip(a, g, w, h, col=PAPER, note="slip"):
    return sm(a, g, [K.box("Sheet", (w, 0.003, h), (0, 0, h / 2), 0, bevel=False), K.box("Ink", (w * 0.7, 0.002, h * 0.5), (0, -0.002, h / 2), 1, bevel=False)], [(note, col), ("ink / glyph (MI)", "2A2420")],
              [K.socket("Text", (0, -0.004, h / 2)), hand(h / 2)], "%.2f x %.2f m %s" % (w, h, note))


def mi(m, names, param):
    m["spec"]["mi_set"] = names; m["spec"]["mi_param"] = param; return m


def state(m, s):
    m["spec"]["state"] = s; return m


# ---- shared assets (built once) ---------------------------------------------------------------------------------------------
def grain_sack(g):
    a = "Prop_YTM_GrainSack"
    return sm(a, g, [K.lathe("Sack", [(0.16, 0), (0.22, 0.12), (0.2, 0.4), (0.1, 0.52), (0.05, 0.58)], (0, 0, 0), 0, 12), K.cyl("Tie", "z", 0.055, 0.055, 0.03, (0, 0, 0.53), 1, 8), K.box("Stamp", (0.16, 0.005, 0.12), (0, -0.215, 0.25), 2, bevel=False)],
              [("hessian", "C8B080"), ("tie rope", ROPE), ("stamp (G66 cloth)", CLOTH4[0])], [K.socket("Carry", (0, 0, 0.45)), K.socket("Shoulder", (0, 0.1, 0.3))], "0.44 m dia x 0.6 m sack")


def row_boat(g):
    a = "Prop_YTM_RowBoat"
    return sm(a, g, boat_parts(3.0, 1.2) + [K.box("Thwart%d" % i, (1.0, 0.18, 0.03), (0, -0.5 + 0.9 * i, 0.38), 0) for i in range(2)],
              [("hull (G66 timber)", TIMBER), ("gunwale (G66 sign board)", SIGN)],
              [K.socket("Oar_L", (-0.6, 0.0, 0.48)), K.socket("Oar_R", (0.6, 0.0, 0.48)), K.socket("Seat_0", (0, -0.5, 0.4)), K.socket("Seat_1", (0, 0.4, 0.4)), K.socket("Mooring", (0, -1.5, 0.45))],
              "3.0 x 1.2 m rowing boat; oars at SOCKET_Oar_L/R", [K.ucx_box(a, 0, (1.2, 3.0, 0.5), (0, 0, 0.25))])


def oar(a, g, L):
    return sm(a, g, [K.cyl("Loom", "y", 0.022, 0.022, L * 0.72, (0, -L * 0.14, 0.03), 0, 8), K.box("Blade", (0.14, L * 0.28, 0.015), (0, L * 0.36, 0.03), 0), K.cyl("Grip", "y", 0.026, 0.026, 0.14, (0, -L / 2 + 0.07, 0.03), 1, 8)],
              [("ash (G66 timber)", TIMBER), ("grip", BARK)], [K.socket("Grip", (0, -L / 2 + 0.07, 0.03)), K.socket("Lock", (0, -L * 0.2, 0.03))], "%.1f m oar" % L)


def soup_pot(g):
    m = pot("Prop_YTM_SoupPot", g, 0.25, 0.35, IRON, lid=False, handles=True, note="iron soup pot")
    m["sockets"].append(K.socket("Ladle", (0.15, 0, 0.35))); m["spec"]["sockets"] = [s["name"] for s in m["sockets"]]; return m


def fire_log_seat(g):
    a = "Prop_YTM_FireLogSeat"
    return sm(a, g, [K.cyl("Log", "x", 0.2, 0.18, 1.6, (0, 0, 0.2), 0, 10), K.box("Flat", (1.4, 0.3, 0.02), (0, 0, 0.39), 1, bevel=False)] + [K.box("Chock%d" % s, (0.1, 0.3, 0.1), (s * 0.6, 0, 0.05), 0) for s in (-1, 1)],
              [("bark log", BARK), ("adzed seat", TIMBER)], [K.socket("Sit_%d" % i, (-0.5 + 0.5 * i, -0.05, 0.4)) for i in range(3)], "1.6 m log bench, 3 seats", [K.ucx_box(a, 0, (1.6, 0.4, 0.4), (0, 0, 0.2))])


# ---- gaps -------------------------------------------------------------------------------------------------------------------
def g254():
    g = "G254"; a = "Prop_YTM_Windmill"; H = 6.0
    P = [K.lathe("Tower", [(1.6, 0), (1.3, H * 0.6), (1.05, H)], (0, 0, 0), 0, 12), K.lathe("Cap", [(1.2, 0), (1.0, 0.6), (0.05, 1.2)], (0, 0, H), 1, 12),
         K.box("Door", (0.8, 0.05, 1.7), (0, -1.58, 0.85), 1), K.cyl("Shaft", "y", 0.12, 0.12, 0.8, (0, -1.3, H + 0.4), 1, 8)]
    for i in range(4):
        an = 90 * i + 45; P.append(K.box("Sail%d" % i, (0.7, 0.04, 2.8), (1.6 * math.cos(math.radians(an)), -1.7, H + 0.4 + 1.6 * math.sin(math.radians(an))), 2, rot=(0, 90 - an, 0)))
    wm = sm(a, g, P, [("whitewash stone", "E8DCC0"), ("cap / door (G66 timber)", TIMBER), ("sails (G66 cloth)", CLOTH4[1])],
            [K.socket("SailRotor", (0, -1.7, H + 0.4)), K.socket("Door", (0, -1.7, 0)), K.socket("Hopper", (0, 0, 1.0))], "3.2 m dia x 7.2 m mill; sails are one mesh, rotate about SOCKET_SailRotor (local Y)",
            [K.ucx_prism(a, 0, "z", 1.6, H, (0, 0, H / 2))])
    b = "Prop_YTM_Millstone"
    ms = sm(b, g, [K.cyl("Bed", "z", 0.6, 0.6, 0.25, (0, 0, 0.125), 0, 16), K.cyl("Runner", "z", 0.58, 0.58, 0.22, (0, 0, 0.36), 0, 16), K.cyl("Eye", "z", 0.1, 0.1, 0.03, (0, 0, 0.48), 1, 8), K.box("Rynd", (0.5, 0.06, 0.04), (0, 0, 0.49), 1)],
            [("millstone", STONE), ("iron rynd", IRON)], [K.socket("Spin", (0, 0, 0.36)), K.socket("Spout", (0.62, 0, 0.12))], "1.2 m dia millstone pair (runner spins on SOCKET_Spin)", [K.ucx_prism(b, 0, "z", 0.6, 0.47, (0, 0, 0.235))])
    return [wm, ms, grain_sack(g)]


def g258():
    g = "G258"
    return [tree("Prop_YTM_AppleTree", g, 3.2, 1.0, 10, RED, "apple tree, fruit cluster sockets", 258), basket("Prop_YTM_AppleBasket", g, 0.22, 0.25, True, note="apple basket", fill=("apples", RED)),
            sm("Prop_YTM_Beehive", g, [K.box("Stand", (0.5, 0.5, 0.4), (0, 0, 0.2), 0)] + [K.lathe("Skep", [(0.25, 0), (0.27, 0.15), (0.2, 0.38), (0.02, 0.48)], (0, 0, 0.4), 1, 12), K.box("Entry", (0.08, 0.02, 0.04), (0, -0.25, 0.43), 2, bevel=False)],
               [("stand (G66 timber)", TIMBER), ("straw skep", "C8A858"), ("entrance", "2A2420")], [K.socket("Entrance", (0, -0.27, 0.43)), K.socket("Swarm", (0, -0.4, 0.6))], "0.54 m straw skep on a stand",
               [K.ucx_box("Prop_YTM_Beehive", 0, (0.55, 0.55, 0.9), (0, 0, 0.45))])]


def g262():
    g = "G262"; out = [stone("Prop_YTM_WallStone_H%d" % i, g, 1.2, 0.6, h, 262 + i, note="sea-wall block") for i, h in enumerate((0.3, 0.6, 0.9), 1)]
    a = "Prop_YTM_StormBoard"
    out.append(sm(a, g, [K.box("Board%d" % i, (2.0, 0.04, 0.24), (0, 0, 0.13 + 0.25 * i), 0) for i in range(4)] + [K.box("Batten%d" % s, (0.08, 0.05, 1.0), (s * 0.8, -0.04, 0.5), 1) for s in (-1, 1)],
                  [("planks (G66 timber)", TIMBER), ("battens", BARK)], [K.socket("Slot_L", (-1.0, 0, 0)), K.socket("Slot_R", (1.0, 0, 0)), K.socket("Lift", (0, -0.06, 0.8))],
                  "2.0 x 1.0 m storm board; scalable along X (planks tile), drops into wall slots", [K.ucx_box(a, 0, (2.0, 0.1, 1.0), (0, 0, 0.5))]))
    out[-1]["spec"]["scalable"] = "X 0.5..3.0 (non-uniform ok; UVs world-aligned)"
    return out


def g266():
    g = "G266"; out = [stone("Prop_YTM_RockShelf_H%d" % h, g, 1.2, 1.0, max(0.05, 0.1 * h), 266 + h, "6E6A60", "tide rock shelf %d/9 high" % h) for h in range(10)]
    a = "Prop_YTM_PoolWater"
    out.append(sm(a, g, [K.box("Water", (2.0, 2.0, 0.01), (0, 0, 0.005), 0, bevel=False)], [("tide pool water (translucent MI)", WATER, 0.05)], [K.socket("Centre", (0, 0, 0.01))], "2 x 2 m water plane, scale freely in XY"))
    out[-1]["spec"]["scalable"] = "XY"
    out.append(critter("Prop_YTM_Crab", g, 0.18, 0.08, "D05A38", 6, True, "shore crab", flat=True))
    return out


def g269():
    g = "G269"
    rb = board("Prop_YTM_RotaBoard", g, 1.0, 0.8, 0.8, 6, "Crew", note="6 crew rota slots")
    return [rb, row_boat(g), oar("Prop_YTM_Oar", g, 2.4)]


def g272():
    g = "G272"; out = []
    for v, bow in (("Straight", 0.0), ("Bowed", 0.12)):
        a = "Prop_YTM_SmokeRack_" + v; P = [K.box("Post%d" % s, (0.08, 0.08, 1.8), (s * 1.0, 0, 0.9), 0) for s in (-1, 1)]
        for j in range(3):
            for k in range(4): P.append(K.box("Rail%d_%d" % (j, k), (0.5, 0.04, 0.04), (-0.75 + 0.5 * k, 0, 1.7 - 0.45 * j - bow * math.sin(math.pi * (k + 0.5) / 4)), 0, rot=(0, (-1 if k < 2 else 1) * bow * 40 * (1 if k in (0, 3) else 0.4), 0)))
        S = [K.socket("Hook_%d_%d" % (j, k), (-0.75 + 0.5 * k, 0, 1.68 - 0.45 * j)) for j in range(3) for k in range(4)]
        out.append(state(sm(a, g, P, [("rack poles (G66 timber)", TIMBER)], S, "2.1 x 1.8 m smoke rack (%s); bow = shape-key pair Straight/Bowed" % v.lower(), [K.ucx_box(a, 0, (2.1, 0.1, 1.8), (0, 0, 0.9))]), v))
    out.append(sm("Prop_YTM_FishSide", g, [K.slab("Fillet", [(-0.25, 0), (0.0, -0.07), (0.25, 0), (0.0, 0.07)], 0.02, (0, 0, 0.01), 0), K.slab("Tail", [(0.25, 0), (0.33, -0.05), (0.33, 0.05)], 0.01, (0, 0, 0.01), 0)],
                  [("smoked fish (G66 amber)", "C07838")], [K.socket("Hook", (-0.24, 0, 0.01)), hand(0.01)], "0.58 m split fish side"))
    a = "Prop_YTM_SmokeFire"; P = [K.box("Stone%d" % i, (0.14, 0.1, 0.1), (0.3 * math.cos(i * 0.785), 0.3 * math.sin(i * 0.785), 0.05), 0, rot=(0, 0, i * 45)) for i in range(8)]
    P += [K.cyl("Embers", "z", 0.2, 0.2, 0.03, (0, 0, 0.02), 1, 10), K.cyl("Chips", "z", 0.15, 0.1, 0.06, (0, 0, 0.06), 2, 8)]
    out.append(sm(a, g, P, [("stones", STONE), ("embers (emissive)", EMBER, 0.8, 0, True), ("wood chips", BARK)], [K.socket("Smoke", (0, 0, 0.2)), K.socket("Fire", (0, 0, 0.08))], "0.7 m smoulder pit", [K.ucx_prism(a, 0, "z", 0.36, 0.12, (0, 0, 0.06))]))
    return out


def g275():
    g = "G275"; a = "Prop_YTM_Trestles"; P = []
    for x in (-1.2, 1.2):
        P += [K.box("Beam%+.0f" % x, (0.1, 1.2, 0.1), (x, 0, 0.75), 0)] + [K.box("Leg%+.0f%d" % (x, s), (0.08, 0.08, 0.8), (x, s * 0.45, 0.38), 0, rot=(s * 12, 0, 0)) for s in (-1, 1)]
    out = [sm(a, g, P, [("trestles (G66 timber)", TIMBER)], [K.socket("Keel", (0, 0, 0.8)), K.socket("Worker_L", (0, -1.0, 0)), K.socket("Worker_R", (0, 1.0, 0))], "pair of 1.2 m trestles 2.4 m apart", [K.ucx_box(a, 0, (2.6, 1.2, 0.8), (0, 0, 0.4))])]
    for i, st in enumerate(("Keel", "Ribs", "Planks")):
        b = "Prop_YTM_HullStage_" + st; P = [K.box("Keel", (0.1, 4.0, 0.12), (0, 0, 0.06), 0), K.cyl("Stem", "z", 0.05, 0.04, 0.8, (0, -2.0, 0.4), 0, 8)]
        if i >= 1: P += [K.box("Rib%d%d" % (k, s), (0.04, 0.05, 0.75), (s * 0.45, -1.6 + 0.4 * k, 0.4), 1, rot=(0, s * -22, 0)) for k in range(9) for s in (-1, 1)]
        if i >= 2: P += [K.box("Strake%d%d" % (j, s), (0.03, 3.6, 0.16), (s * (0.36 + 0.06 * j), 0, 0.15 + 0.17 * j), 2, rot=(0, s * -22, 0)) for j in range(4) for s in (-1, 1)]
        out.append(state(sm(b, g, P, [("keel (G66 timber)", TIMBER), ("ribs", BARK), ("planks (G66 sign board)", SIGN)], [K.socket("Trestle", (0, 0, 0)), K.socket("Work", (0.6, 0, 0.4))],
                             "4.0 m hull, stage %d/3 %s (sit on Trestles SOCKET_Keel)" % (i + 1, st.lower())), st))
    out.append(board("Prop_YTM_JobBoard", g, 1.0, 0.8, 0.8, 5, "Job", note="5 job pegs"))
    return out


def g278():
    g = "G278"; a = "Prop_YTM_TideAlmanac"
    al = sm(a, g, [K.box("Cover", (0.24, 0.32, 0.04), (0, 0, 0.02), 0), K.box("Pages", (0.22, 0.3, 0.032), (0.005, 0, 0.022), 1), K.box("Tab", (0.03, 0.04, 0.03), (0.12, 0.08, 0.02), 2)],
            [("oilskin cover (G66 cloth)", CLOTH4[2]), ("pages", PAPER), ("ribbon tab", RED)], [K.socket("Text", (0, 0, 0.041)), hand(0.02)], "0.24 x 0.32 m almanac")
    fp = post("Prop_YTM_FlatsMarkerPole", g, 2.2, 0.035, CLOTH4[0], RED, "flats marker pole with pennant",
              [K.slab("Pennant", [(0, 0), (0.4, 0.1), (0, 0.2)], 0.005, (0.03, 0, 2.0), 2, rot=(90, 0, 0))] + [K.box("Band%d" % i, (0.075, 0.075, 0.1), (0, 0, 0.4 + 0.4 * i), 1, bevel=False) for i in range(4)],
              [K.socket("Depth_%d" % i, (0, -0.04, 0.4 + 0.4 * i)) for i in range(4)])
    return [al, fp, pot("Prop_YTM_PitchBucket", g, 0.16, 0.26, "2A2420", handles=True, note="pitch bucket")]


def g282():
    g = "G282"; out = []
    for v, P in (("Straight", [K.box("Floor", (0.6, 2.0, 0.1), (0, 0, 0.05), 0)] + [K.box("Wall%d" % s, (0.12, 2.0, 0.35), (s * 0.36, 0, 0.175), 0) for s in (-1, 1)]),
                 ("Corner", [K.box("Floor", (0.6, 1.3, 0.1), (0, -0.35, 0.05), 0), K.box("FloorB", (0.7, 0.6, 0.1), (0.35, 0, 0.05), 0), K.box("WallO", (0.12, 1.3, 0.35), (-0.36, -0.35, 0.175), 0), K.box("WallO2", (1.05, 0.12, 0.35), (0.17, 0.36, 0.175), 0)]),
                 ("Split", [K.box("Floor", (1.4, 1.4, 0.1), (0, 0, 0.05), 0), K.box("Divider", (0.12, 0.7, 0.35), (0, 0.35, 0.175), 0), K.box("WallS", (1.4, 0.12, 0.35), (0, -0.76, 0.175), 0)])):
        a = "Prop_YTM_StoneChannel_" + v
        out.append(sm(a, g, P + [K.box("Water", (0.58, 1.0 if v != "Straight" else 1.96, 0.01), (0, 0, 0.2), 1, bevel=False)], [("cut stone", STONE), ("water (MI)", WATER, 0.05)],
                      [K.socket("In", (0, 1.0, 0.1)), K.socket("Out", (0, -1.0, 0.1))] + ([K.socket("Out2", (1.0, 0, 0.1))] if v != "Straight" else []), "modular 2 m stone channel (%s), 0.6 m wide" % v.lower()))
    a = "Prop_YTM_SluiceWheel"; P = [K.cyl("Axle", "x", 0.06, 0.06, 0.9, (0, 0, 0.9), 1, 8)] + [K.cyl("Rim%d" % s, "x", 0.8, 0.8, 0.05, (s * 0.3, 0, 0.9), 0, 16) for s in (-1, 1)]
    P += [K.box("Paddle%d" % i, (0.6, 0.04, 0.3), (0, 0.72 * math.cos(i * math.pi / 6), 0.9 + 0.72 * math.sin(i * math.pi / 6)), 0, rot=(-math.degrees(i * math.pi / 6), 0, 0)) for i in range(12)]
    P += [K.box("Frame%d" % s, (0.1, 0.12, 1.0), (s * 0.45, 0, 0.5), 1) for s in (-1, 1)]
    out.append(sm(a, g, P, [("wheel (G66 timber)", TIMBER), ("frame / axle", BARK)], [K.socket("Spin", (0, 0, 0.9)), K.socket("Gate", (0, -0.9, 0.2))], "1.7 m sluice wheel, spins about SOCKET_Spin X", [K.ucx_box(a, 0, (1.0, 1.7, 1.75), (0, 0, 0.88))]))
    a = "Prop_YTM_Cistern"
    out.append(sm(a, g, [K.lathe("Tank", [(1.0, 0), (1.0, 1.0), (0.9, 1.05)], (0, 0, 0), 0, 16, cap_top=False), K.cyl("Water", "z", 0.92, 0.92, 0.01, (0, 0, 0.8), 1, 16), K.cyl("Spout", "y", 0.06, 0.06, 0.3, (0, -1.1, 0.2), 0, 8)],
                  [("stone cistern", STONE), ("water (MI, level param)", WATER, 0.05)], [K.socket("Level", (0, 0, 0.8)), K.socket("Spout", (0, -1.25, 0.2)), K.socket("Inlet", (0, 1.0, 1.0))], "2 m dia x 1 m cistern",
                  [K.ucx_prism(a, 0, "z", 1.0, 1.05, (0, 0, 0.53))]))
    return out


def g289():
    g = "G289"; a = "Prop_YTM_StoneWell"
    sw = sm(a, g, [K.lathe("Ring", [(0.75, 0), (0.75, 0.8), (0.55, 0.8)], (0, 0, 0), 0, 14, cap_top=False), K.box("PostL", (0.1, 0.1, 1.6), (-0.65, 0, 1.6), 1), K.box("PostR", (0.1, 0.1, 1.6), (0.65, 0, 1.6), 1),
                   K.cyl("Windlass", "x", 0.06, 0.06, 1.4, (0, 0, 2.2), 1, 8), K.box("Roof", (1.8, 1.2, 0.06), (0, 0, 2.5), 2, rot=(0, 0, 0)), K.box("Crank", (0.04, 0.04, 0.3), (0.75, 0, 2.08), 1)],
            [("well stone", STONE), ("windlass (G66 timber)", TIMBER), ("roof (G66 cloth)", CLOTH4[0])], [K.socket("Rope", (0, 0, 2.15)), K.socket("Bucket", (0, 0, 0.8)), K.socket("Crank", (0.75, -0.1, 1.95))], "1.5 m dia stone well with windlass",
            [K.ucx_prism(a, 0, "z", 0.75, 0.8, (0, 0, 0.4))])
    out = [sw]
    for v, P in (("Straight", [K.cyl("Pipe", "y", 0.08, 0.08, 1.0, (0, 0, 0.08), 0, 10), K.cyl("Collar", "y", 0.1, 0.1, 0.1, (0, 0.45, 0.08), 0, 10)]),
                 ("Elbow", [K.cyl("PipeA", "y", 0.08, 0.08, 0.5, (0, -0.25, 0.08), 0, 10), K.cyl("PipeB", "x", 0.08, 0.08, 0.5, (0.25, 0, 0.08), 0, 10)])):
        out.append(sm("Prop_YTM_ClayPipe_" + v, g, P, [("fired clay", CLAY)], [K.socket("In", (0, -0.5, 0.08)), K.socket("Out", (0, 0.5, 0.08) if v == "Straight" else (0.5, 0, 0.08))], "modular clay pipe (%s), 0.16 m bore" % v.lower()))
    wb = basket("Prop_YTM_WellBucket", g, 0.15, 0.25, True, TIMBER, "well bucket")
    return out + [wb]


def g293():
    g = "G293"; out = [hut("Prop_YTM_StiltHut", g, 3.0, 2.6, 2.2, 1.6, "stilt hut")]
    a = "Prop_YTM_PlankWalkway"; P = [K.box("Plank%d" % i, (1.2, 0.18, 0.04), (0, -0.9 + 0.2 * i, 0.6), 0) for i in range(10)] + [K.box("Stringer%d" % s, (0.08, 2.0, 0.1), (s * 0.5, 0, 0.53), 1) for s in (-1, 1)]
    P += [K.cyl("Pile%d%d" % (s, e), "z", 0.06, 0.06, 0.6, (s * 0.5, e * 0.95, 0.3), 1, 8) for s in (-1, 1) for e in (-1, 1)]
    out.append(sm(a, g, P, [("planks (G66 timber)", TIMBER), ("stringers / piles", BARK)], [K.socket("Start", (0, -1.0, 0.62)), K.socket("End", (0, 1.0, 0.62))],
                  "2.0 m walkway segment (spline-friendly: deform along Y, segments chain Start->End)", [K.ucx_box(a, 0, (1.2, 2.0, 0.1), (0, 0, 0.6))]))
    out[-1]["spec"]["spline"] = "segment length 2.0 m along +Y, Start/End sockets"
    b = "Prop_YTM_PlankStack"
    out.append(sm(b, g, [K.box("Plank%d" % i, (2.0, 0.2, 0.04), (0, (-0.24 + 0.21 * (i % 3)), 0.02 + 0.045 * (i // 3)), 0) for i in range(12)], [("planks (G66 timber)", TIMBER)], [K.socket("Take", (0, 0, 0.2))], "2.0 x 0.6 m stack of 12", [K.ucx_box(b, 0, (2.0, 0.64, 0.18), (0, 0, 0.09))]))
    return out


def g297():
    g = "G297"; ns = stone("Prop_YTM_NameStone", g, 0.6, 0.25, 1.0, 297, note="name stone", n=2, socks=[K.socket("LetterDecal", (0, -0.13, 0.65))])
    ns["spec"]["decal"] = "carved name via DBuffer decal at SOCKET_LetterDecal (T_YTM_LetterAtlas)"
    ch = sm("Prop_YTM_Chisel", g, [K.cyl("Shank", "y", 0.012, 0.012, 0.18, (0, 0, 0.012), 0, 6), K.box("Edge", (0.025, 0.03, 0.006), (0, -0.1, 0.012), 0), K.cyl("Head", "y", 0.016, 0.016, 0.03, (0, 0.1, 0.012), 1, 6)],
            [("steel", IRON, 0.4, 0.9), ("struck head", "6A6A70")], [K.socket("Grip", (0, 0.04, 0.012)), K.socket("Tip", (0, -0.115, 0.012))], "0.22 m stone chisel")
    ml = sm("Prop_YTM_Mallet", g, [K.cyl("Handle", "y", 0.015, 0.015, 0.3, (0, 0.1, 0.05), 0, 6), K.cyl("Head", "x", 0.05, 0.05, 0.14, (0, -0.08, 0.05), 1, 10)],
            [("handle (G66 timber)", TIMBER), ("lignum head", BARK)], [K.socket("Grip", (0, 0.2, 0.05)), K.socket("Strike", (0.07, -0.08, 0.05))], "0.33 m carver's mallet")
    return [ns, ch, ml]


def g301():
    g = "G301"; a = "Prop_YTM_BrineTrough"
    bt = sm(a, g, [K.box("Bottom", (1.6, 0.5, 0.06), (0, 0, 0.33), 0)] + [K.box("Side%d" % s, (1.6, 0.05, 0.3), (0, s * 0.25, 0.48), 0) for s in (-1, 1)] + [K.box("End%d" % s, (0.05, 0.5, 0.3), (s * 0.8, 0, 0.48), 0) for s in (-1, 1)] +
            [K.box("Brine", (1.5, 0.45, 0.01), (0, 0, 0.55), 1, bevel=False)] + [K.box("Leg%d" % s, (0.08, 0.5, 0.3), (s * 0.65, 0, 0.15), 0) for s in (-1, 1)],
            [("trough (G66 timber)", TIMBER), ("brine (MI)", "B8C8C0", 0.1)], [K.socket("Dip_%d" % i, (-0.5 + 0.5 * i, -0.3, 0.6)) for i in range(3)], "1.6 m brine trough", [K.ucx_box(a, 0, (1.6, 0.5, 0.63), (0, 0, 0.32))])
    bk = basket("Prop_YTM_Bucket", g, 0.14, 0.26, True, TIMBER, "bucket", fill=("water (fill-level morph 0..1)", WATER))
    bk["spec"]["morph"] = "Fill (shape key 0 = empty, 1 = full; scales Fill part Z)"
    return [bt, bk, pot("Prop_YTM_PickleCrock", g, 0.18, 0.36, "A87850", lid=True, note="pickle crock")]


def g306():
    g = "G306"; out = []
    for v in ("Intact", "Crumbled"):
        a = "Prop_YTM_CliffLedge_" + v; r = K.rng(306, a); P = [K.box("Ledge", (2.0, 1.0, 0.6) if v == "Intact" else (1.3, 1.0, 0.6), (0 if v == "Intact" else -0.35, 0, 0.3), 0)]
        if v == "Crumbled": P += [K.box("Rubble%d" % i, (0.2, 0.18, 0.15), (0.5 + r.uniform(-0.3, 0.4), r.uniform(-0.4, 0.4), -0.3 - 0.1 * i), 0, rot=(r.uniform(0, 40), r.uniform(0, 40), 0)) for i in range(5)]
        out.append(state(sm(a, g, P, [("cliff rock", "7A7266")], [K.socket("Land", (0 if v == "Intact" else -0.35, 0, 0.6)), K.socket("Edge", (1.0 if v == "Intact" else 0.3, 0, 0.6))], "2.0 m cliff ledge (%s)" % v.lower(),
                               [K.ucx_box(a, 0, (2.0 if v == "Intact" else 1.3, 1.0, 0.6), (0 if v == "Intact" else -0.35, 0, 0.3))]), v))
    out.append(critter("Prop_YTM_Goat", g, 1.0, 0.8, FUR, 4, True, "island goat", horns=True))
    out.append(critter("Prop_YTM_Kid", g, 0.55, 0.45, "E8DCC8", 4, True, "goat kid"))
    return out


def g312():
    g = "G312"; out = [oar("Prop_YTM_OarPile_%s" % n, g, L) for n, L in (("Short", 1.8), ("Medium", 2.4), ("Long", 3.0))]
    for m in out: m["spec"]["note"] = "pile = scatter of this oar; lengths Short/Medium/Long"
    mb = sm("Prop_YTM_MeasuringBoard", g, [K.box("Board", (3.2, 0.25, 0.05), (0, 0, 0.025), 0)] + [K.box("Tick%d" % i, (0.01, 0.12, 0.006), (-1.5 + 0.5 * i, -0.06, 0.052), 1, bevel=False) for i in range(7)],
            [("board (G66 timber)", TIMBER), ("tick marks", "2A2420")], [K.socket("Zero", (-1.5, 0, 0.05))] + [K.socket("Mark_%d" % i, (-1.5 + 0.5 * i, 0, 0.05)) for i in range(7)], "3.2 m measuring board, 0.5 m ticks",
            [K.ucx_box("Prop_YTM_MeasuringBoard", 0, (3.2, 0.25, 0.05), (0, 0, 0.025))])
    ol = sm("Prop_YTM_Oarlock", g, [K.cyl("Pin", "z", 0.012, 0.012, 0.1, (0, 0, 0.05), 0, 6), K.box("HornL", (0.012, 0.012, 0.07), (-0.03, 0, 0.12), 0, rot=(0, -20, 0)), K.box("HornR", (0.012, 0.012, 0.07), (0.03, 0, 0.12), 0, rot=(0, 20, 0))],
            [("bronze", BRASS, 0.4, 0.9)], [K.socket("Oar", (0, 0, 0.12)), K.socket("Mount", (0, 0, 0))], "0.16 m bronze oarlock")
    return out + [mb, ol]


def g316():
    g = "G316"; a = "Prop_YTM_PonyCart"
    P = [K.box("Bed", (1.2, 1.8, 0.08), (0, 0, 0.7), 0)] + [K.box("Side%d" % s, (0.04, 1.8, 0.3), (s * 0.6, 0, 0.88), 0) for s in (-1, 1)] + [K.cyl("Wheel%d" % s, "x", 0.45, 0.45, 0.06, (s * 0.7, 0.2, 0.45), 1, 14) for s in (-1, 1)]
    P += [K.cyl("Axle", "x", 0.03, 0.03, 1.5, (0, 0.2, 0.45), 1, 6)] + [K.box("Shaft%d" % s, (0.05, 1.6, 0.05), (s * 0.35, -1.6, 0.6), 0, rot=(-5, 0, 0)) for s in (-1, 1)]
    pc = sm(a, g, P, [("cart (G66 timber)", TIMBER), ("wheels", BARK)], [K.socket("Pony", (0, -1.9, 0)), K.socket("Load", (0, 0, 0.75)), K.socket("Driver", (0, -0.6, 0.8))], "1.2 x 3.4 m pony cart (no pony; hook at SOCKET_Pony)",
            [K.ucx_box(a, 0, (1.5, 1.8, 1.05), (0, 0, 0.52))])
    hl = hut("Prop_YTM_HillLoft", g, 3.0, 2.4, 2.6, 0.0, "hill grain loft")
    hl["sockets"].append(K.socket("LoftDoor", (0, -1.25, 2.3))); hl["spec"]["sockets"] = [s["name"] for s in hl["sockets"]]
    return [pc, hl]   # GrainSack: built in G254, staged again here


def g319():
    g = "G319"; mp = sm("Prop_YTM_MeltPool", g, [K.cyl("Water", "z", 1.0, 1.0, 0.01, (0, 0, 0.005), 0, 16)] + [K.box("Rim%d" % i, (0.25, 0.18, 0.12), (1.0 * math.cos(i * 0.628), 1.0 * math.sin(i * 0.628), 0.05), 1, rot=(0, 0, math.degrees(i * 0.628))) for i in range(10)],
                        [("meltwater (MI)", "9AD0E0", 0.05), ("rim stones", STONE)], [K.socket("Outflow", (1.1, 0, 0.0)), K.socket("Centre", (0, 0, 0.01))], "2 m melt pool")
    pb = sm("Prop_YTM_PaperBoat", g, [K.slab("Hull", [(-0.08, 0), (0.08, 0), (0.05, 0.04), (-0.05, 0.04)], 0.06, (0, 0, 0.0), 0, rot=(90, 0, 0)), K.slab("Sail", [(-0.03, 0), (0.03, 0), (0, 0.06)], 0.002, (0, 0, 0.04), 0, rot=(90, 0, 0))],
            [("folded paper (G66 cloth tint via MI)", PAPER)], [K.socket("Float", (0, 0, 0)), hand(0.03)], "16 cm paper boat")
    mi(pb, ["MI_YTM_PaperBoat_%s" % c for c in ("Red", "Blue", "Yellow", "White")], "Tint (G66 cloth colours)")
    a = "Prop_YTM_StreamFork"; P = [K.box("Bed", (0.8, 2.0, 0.02), (0, -0.5, 0.01), 0, bevel=False), K.box("BedL", (0.6, 1.4, 0.02), (-0.5, 1.0, 0.01), 0, rot=(0, 0, 25), bevel=False), K.box("BedR", (0.6, 1.4, 0.02), (0.5, 1.0, 0.01), 0, rot=(0, 0, -25), bevel=False)]
    sf = sm(a, g, P + [K.box("Bank%d" % i, (0.2, 0.3, 0.1), (s * 0.5, -1.2 + 0.6 * i, 0.05), 1) for i in range(3) for s in (-1, 1)], [("stream water (flow MI)", WATER, 0.05), ("bank stones", STONE)],
            [K.socket("In", (0, -1.5, 0.02)), K.socket("Out_L", (-0.8, 1.6, 0.02)), K.socket("Out_R", (0.8, 1.6, 0.02))], "Y-fork stream piece (spline-friendly: In/Out sockets chain to channel splines)")
    sf["spec"]["spline"] = "In -> Out_L / Out_R"
    return [mp, pb, sf]


def g323():
    g = "G323"; mc = sm("Prop_YTM_MessageConch", g, [K.lathe("Shell", [(0.01, 0), (0.08, 0.04), (0.11, 0.12), (0.07, 0.22), (0.01, 0.3)], (0, 0, 0), 0, 10, rot=(0, 80, 0)), K.box("Lip", (0.12, 0.02, 0.1), (0.05, -0.08, 0.06), 1)],
                        [("conch (G66 shell)", SHELL), ("pink lip", "E8A0A0")], [K.socket("Mouth", (-0.15, 0, 0.06)), hand(0.06), K.socket("Message", (0.05, -0.1, 0.06))], "0.3 m message conch")
    vg = post("Prop_YTM_VillageGreenMarker", g, 1.4, 0.09, CLOTH4[0], SIGN, "village green marker", [K.box("Plaque", (0.4, 0.04, 0.25), (0, -0.1, 1.1), 2)], [K.socket("Text", (0, -0.125, 1.1))])
    return [mc, vg]


def g328():
    g = "G328"; fp = post("Prop_YTM_FencePost", g, 1.2, 0.06, CLOTH4[0], SIGN, "fence post", [K.box("Rail%d" % i, (0.04, 1.0, 0.08), (0, 0.5, 0.4 + 0.5 * i), 1) for i in range(2)], [K.socket("Lamp", (0, 0, 1.3)), K.socket("Rail_Next", (0, 1.0, 0.4))])
    ls = line("Prop_YTM_LampString", g, 4.0, 8, lambda n, p, s: K.cyl(n, "z", 0.05, 0.05, 0.12, p, s, 8), ["FFC870", "FFA858"], 0.3, "lamp string, 8 bulbs", -0.07, prefix="Lamp")
    ls["materials"][1]["glow"] = True if isinstance(ls["materials"][1], dict) else None
    return [fp, ls]   # Prop_YTM_Fiddle: REUSE (already shipped, not rebuilt)


def g333():
    g = "G333"; a = "Prop_YTM_Loom"; P = [K.box("Post%d%d" % (s, e), (0.08, 0.08, 1.5), (s * 0.7, e * 0.5, 0.75), 0) for s in (-1, 1) for e in (-1, 1)]
    P += [K.cyl("Beam%d" % e, "x", 0.05, 0.05, 1.5, (0, e * 0.5, 1.0), 0, 8) for e in (-1, 1)] + [K.box("Warp", (1.2, 1.0, 0.01), (0, 0, 1.0), 1, bevel=False), K.box("Heddle", (1.3, 0.05, 0.4), (0, -0.1, 1.2), 0), K.box("Bench", (1.2, 0.3, 0.05), (0, -0.9, 0.45), 0)]
    lm = sm(a, g, P, [("loom (G66 timber)", TIMBER), ("warp threads (pattern MI)", CLOTH4[1])], [K.socket("Weaver", (0, -0.9, 0.47)), K.socket("Pattern", (0, 0, 1.01)), K.socket("Shuttle", (0, -0.2, 1.0))], "1.5 x 1.1 m floor loom",
            [K.ucx_box(a, 0, (1.5, 1.1, 1.5), (0, 0, 0.75))])
    ts = sm("Prop_YTM_ThreadStrip", g, [K.box("Strip", (0.6, 0.08, 0.004), (0, 0, 0.002), 0, bevel=False)] + [K.box("Band%d" % i, (0.06, 0.081, 0.005), (-0.27 + 0.09 * i, 0, 0.0025), 1, bevel=False) for i in range(7)],
            [("woven strip (pattern MI)", CLOTH4[0]), ("pattern bands", CLOTH4[2])], [K.socket("Pattern", (0, 0, 0.005)), hand(0.003)], "0.6 m woven pattern strip")
    mi(ts, ["MI_YTM_ThreadStrip_P%d" % i for i in range(8)], "Pattern (index into T_YTM_WeaveAtlas)")
    sa = sm("Prop_YTM_Sash", g, [K.slab("Sash", [(-0.05, 0), (0.05, 0), (0.05, 1.2), (-0.05, 1.2)], 0.004, (0, 0, 0), 0, rot=(90, 0, 0)), K.slab("Knot", [(-0.06, -0.04), (0.06, -0.04), (0.06, 0.04), (-0.06, 0.04)], 0.02, (0, -0.01, 0.6), 1, rot=(90, 0, 0))],
            [("sash (G66 cloth, pattern MI)", CLOTH4[1]), ("knot", CLOTH4[0])], [K.socket("Wear", (0, 0, 0.6))], "1.2 m festival sash (character attaches at SOCKET_Wear)")
    return [lm, ts, sa]


def g338():
    g = "G338"
    return [stone("Prop_YTM_TrailStone", g, 0.5, 0.4, 0.12, 338, note="trail stepping stone", n=1), hut("Prop_YTM_HillHut", g, 2.6, 2.2, 2.0, 0.0, "hill hut"),
            lantern_pole("Prop_YTM_HealerLantern", g, 1.8)]


def g342():
    g = "G342"; a = "Prop_YTM_BellTower"; H = 5.0
    P = [K.box("Leg%d%d" % (s, e), (0.16, 0.16, H), (s * 0.8, e * 0.8, H / 2), 0, rot=(e * -4, s * 4, 0)) for s in (-1, 1) for e in (-1, 1)]
    P += [K.box("Brace%d" % i, (1.6, 0.08, 0.08), (0, (-1) ** i * 0.8, 1.5 + 1.5 * (i // 2)), 0) for i in range(4)] + [K.box("Deck", (1.8, 1.8, 0.1), (0, 0, H - 0.6), 0), K.slab("Roof", [(-1.2, 0), (1.2, 0), (0, 1.0)], 1.8, (0, 0, H + 0.1), 1, rot=(90, 0, 0))]
    bt = sm(a, g, P, [("tower (G66 timber)", TIMBER), ("roof (G66 cloth)", CLOTH4[0])], [K.socket("Bell", (0, 0, H - 0.1)), K.socket("Rope", (0, 0, 1.0))], "1.8 x 1.8 x 6 m bell tower", [K.ucx_box(a, 0, (1.8, 1.8, H), (0, 0, H / 2))])
    bl = sm("Prop_YTM_Bell", g, [K.lathe("Bell", [(0.3, 0), (0.28, 0.05), (0.2, 0.25), (0.18, 0.45), (0.06, 0.52), (0.01, 0.53)], (0, 0, -0.53), 0, 14, cap_bottom=False), K.cyl("Clapper", "z", 0.04, 0.04, 0.3, (0, 0, -0.35), 1, 6), K.box("Crown", (0.12, 0.06, 0.08), (0, 0, 0.03), 1)],
            [("bronze bell", BRASS, 0.3, 0.9), ("clapper / crown", IRON)], [K.socket("Hang", (0, 0, 0.07)), K.socket("Strike", (0.28, 0, -0.45)), K.socket("Sound", (0, 0, -0.3))], "0.6 m bell; pivot = hang point (swing about X)")
    br = sm("Prop_YTM_BellRope", g, [K.cyl("Rope", "z", 0.012, 0.012, 4.0, (0, 0, 2.0), 0, 6), K.cyl("Sally", "z", 0.035, 0.035, 0.4, (0, 0, 1.2), 1, 8)], [("rope", ROPE), ("sally (G66 cloth)", CLOTH4[0])], [K.socket("Top", (0, 0, 4.0)), K.socket("Pull", (0, 0, 1.2))], "4 m bell rope with sally")
    return [bt, bl, br]


def g348():
    g = "G348"
    return [mat("Prop_YTM_DryingMat", g, 2.0, 1.2, "C8A868", 3, "fish drying mat"),
            sm("Prop_YTM_SplitFish", g, [K.slab("Fish", [(-0.2, 0), (-0.05, -0.1), (0.15, -0.06), (0.25, -0.1), (0.25, 0.1), (0.15, 0.06), (-0.05, 0.1)], 0.015, (0, 0, 0.008), 0)],
               [("split fish (G66 silver/amber; dry level MI)", "D8C8A8")], [hand(0.01), K.socket("Mat", (0, 0, 0))], "0.45 m split fish"),
            sm("Prop_YTM_PacingStick", g, [K.cyl("Stick", "z", 0.015, 0.012, 1.0, (0, 0, 0.5), 0, 6)] + [K.box("Notch%d" % i, (0.032, 0.032, 0.01), (0, 0, 0.1 + 0.2 * i), 1, bevel=False) for i in range(5)],
               [("stick (G66 timber)", TIMBER), ("notches", "2A2420")], [K.socket("Grip", (0, 0, 0.9)), K.socket("Tip", (0, 0, 0))], "1.0 m pacing stick, 0.2 m notches")]


def g351():
    g = "G351"; cc = sm("Prop_YTM_CurrentChart", g, [K.box("Chart", (0.8, 0.6, 0.004), (0, 0, 0.002), 0, bevel=False)] + [K.cyl("Roll%d" % s, "y", 0.02, 0.02, 0.62, (s * 0.41, 0, 0.02), 1, 8) for s in (-1, 1)],
                        [("current chart (MI per route)", PAPER), ("rollers", TIMBER)], [K.socket("Route_%d" % i, (-0.3 + 0.2 * i, 0, 0.005)) for i in range(4)], "0.8 x 0.6 m chart")
    wb = sm("Prop_YTM_WhirlpoolBuoy", g, [K.lathe("Buoy", [(0.05, 0), (0.35, 0.15), (0.3, 0.45), (0.1, 0.6)], (0, 0, 0), 0, 12), K.box("Band", (0.65, 0.65, 0.08), (0, 0, 0.3), 1, bevel=False), K.cyl("Pole", "z", 0.025, 0.025, 0.8, (0, 0, 1.0), 0, 6), K.box("Flag", (0.3, 0.01, 0.2), (0.16, 0, 1.3), 1)],
            [("buoy (G66 cloth red)", CLOTH4[0]), ("warning band", "F0E8D8")], [K.socket("Anchor", (0, 0, 0)), K.socket("Top", (0, 0, 1.4))], "0.7 m warning buoy")
    return [cc, wb]   # RowBoat: built in G269


def g357():
    g = "G357"; out = [sm("Prop_YTM_RopeLength_%s" % n, g, [K.cyl("Rope", "x", 0.015, 0.015, L, (0, 0, 0.015), 0, 6), K.cyl("WhippingA", "x", 0.018, 0.018, 0.03, (-L / 2 + 0.015, 0, 0.015), 1, 6), K.cyl("WhippingB", "x", 0.018, 0.018, 0.03, (L / 2 - 0.015, 0, 0.015), 1, 6)],
                          [("rope", ROPE), ("whipping", RED)], [K.socket("EndA", (-L / 2, 0, 0.015)), K.socket("EndB", (L / 2, 0, 0.015)), K.socket("Splice", (0, 0, 0.015))], "%.1f m rope length" % L) for n, L in (("Short", 1.0), ("Long", 2.0))]
    out.append(sm("Prop_YTM_SplicingFid", g, [K.cyl("Fid", "y", 0.02, 0.003, 0.25, (0, 0, 0.02), 0, 8)], [("bone fid", "E8DCC0")], [K.socket("Grip", (0, -0.1, 0.02)), K.socket("Tip", (0, 0.125, 0.02))], "0.25 m splicing fid"))
    return out   # RopeCoil: REUSE G212


def g360():
    g = "G360"; bb = tree("Prop_YTM_BerryBush", g, 0.9, 0.45, 8, "6A2A6A", "berry bush", 360)
    ps = sm("Prop_YTM_PlotString", g, [K.cyl("Peg%d" % i, "z", 0.02, 0.005, 0.3, (x, y, 0.1), 0, 6) for i, (x, y) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1)))] +
            [K.cyl("Str%d" % i, "x" if i % 2 == 0 else "y", 0.004, 0.004, 2.0, ((0, -1, 0.2), (1, 0, 0.2), (0, 1, 0.2), (-1, 0, 0.2))[i], 1, 4) for i in range(4)],
            [("pegs (G66 timber)", TIMBER), ("string (G66 cloth)", CLOTH4[0])], [K.socket("Corner_%d" % i, (x, y, 0.2)) for i, (x, y) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1)))], "2 x 2 m plot string, 4 pegs; scale XY")
    return [bb, ps, basket("Prop_YTM_BerryBasket", g, 0.14, 0.14, True, note="berry basket", fill=("berries", "6A2A6A"))]


def g363():
    g = "G363"; rb = board("Prop_YTM_RiteBoard", g, 1.2, 1.0, 0.7, 6, "Rite", note="6 rite card slots")
    rc = slip("Prop_YTM_RiteCard", g, 0.12, 0.18, PAPER, "rite card"); mi(rc, ["MI_YTM_RiteCard_%d" % i for i in range(12)], "Rite (index into T_YTM_RiteAtlas)")
    sb = sm("Prop_YTM_StartBell", g, [K.box("Frame%d" % s, (0.06, 0.06, 0.9), (s * 0.3, 0, 0.45), 0) for s in (-1, 1)] + [K.box("Bar", (0.66, 0.06, 0.06), (0, 0, 0.9), 0), K.lathe("Bell", [(0.15, 0), (0.12, 0.12), (0.08, 0.24), (0.01, 0.27)], (0, 0, 0.55), 1, 12, cap_bottom=False)],
            [("frame (G66 timber)", TIMBER), ("brass bell", BRASS, 0.3, 0.9)], [K.socket("Strike", (0.15, 0, 0.6)), K.socket("Sound", (0, 0, 0.65))], "0.66 x 0.9 m start bell frame", [K.ucx_box("Prop_YTM_StartBell", 0, (0.66, 0.1, 0.93), (0, 0, 0.465))])
    return [rb, rc, sb]


def g368():
    g = "G368"; ts = sm("Prop_YTM_TradeScale", g, [K.cyl("Stand", "z", 0.03, 0.03, 1.0, (0, 0, 0.5), 0, 8), K.cyl("Foot", "z", 0.2, 0.22, 0.05, (0, 0, 0.025), 0, 12), K.box("Beam", (0.9, 0.03, 0.03), (0, 0, 1.0), 1)] +
                        [K.cyl("Pan%d" % s, "z", 0.15, 0.12, 0.03, (s * 0.42, 0, 0.7), 1, 12) for s in (-1, 1)] + [K.cyl("Chain%d%d" % (s, k), "z", 0.003, 0.003, 0.3, (s * 0.42 + 0.08 * (k - 1), 0, 0.85), 1, 4) for s in (-1, 1) for k in range(3)],
                        [("stand (G66 timber)", TIMBER), ("brass beam / pans", BRASS, 0.3, 0.9)], [K.socket("Pan_L", (-0.42, 0, 0.72)), K.socket("Pan_R", (0.42, 0, 0.72)), K.socket("Pivot", (0, 0, 1.0))], "0.9 m trade balance (beam tilts about SOCKET_Pivot X)")
    a = "Prop_YTM_TreasurePile"; r = K.rng(368, a); P = [K.lathe("Heap", [(0.4, 0), (0.3, 0.12), (0.02, 0.25)], (0, 0, 0), 0, 12)] + [K.cyl("Coin%d" % i, "z", 0.03, 0.03, 0.006, (r.uniform(-0.35, 0.35), r.uniform(-0.35, 0.35), 0.003), 0, 8, rot=(r.uniform(0, 30), 0, 0)) for i in range(10)]
    P += [K.box("Gem%d" % i, (0.04, 0.04, 0.04), (r.uniform(-0.2, 0.2), r.uniform(-0.2, 0.2), 0.12 + 0.05 * r.random()), 1, rot=(45, 45, 0)) for i in range(6)]
    tp = sm(a, g, P, [("gold coins", "E0B840", 0.3, 1.0), ("gems (G66 cloth tints)", CLOTH4[1], 0.2)], [K.socket("Top", (0, 0, 0.25)), K.socket("Scoop", (0.3, -0.3, 0.05))], "0.8 m treasure heap")
    sh = sm("Prop_YTM_TraderShip", g, boat_parts(6.0, 2.0, 5.0) + [K.box("Cabin", (1.4, 1.4, 0.8), (0, 2.0, 0.8), 3)] + [K.box("Cargo%d" % i, (0.5, 0.5, 0.4), (-0.35 + 0.7 * (i % 2), -0.8 + 0.6 * (i // 2), 0.3), 3) for i in range(4)],
            [("hull (G66 timber)", TIMBER), ("gunwale (G66 sign)", SIGN), ("sails (G66 cloth)", "EDE6D6"), ("cabin / cargo", BARK)], [K.socket("Gangway", (1.0, 0, 0.5)), K.socket("Helm", (0, 2.6, 0.5)), K.socket("Cargo", (0, -0.5, 0.5)), K.socket("Mooring", (0, -3.0, 0.5))],
            "6 x 2 m trading ketch, sail rig", [K.ucx_box("Prop_YTM_TraderShip", 0, (2.0, 6.0, 0.6), (0, 0, 0.3))])
    return [ts, tp, sh]


def g374():
    g = "G374"; nh = sm("Prop_YTM_NumberedHive", g, [K.box("Stand", (0.5, 0.5, 0.35), (0, 0, 0.175), 0)] + [K.box("Box%d" % i, (0.46, 0.4, 0.2), (0, 0, 0.45 + 0.21 * i), 1) for i in range(2)] + [K.box("Lid", (0.52, 0.46, 0.06), (0, 0, 0.88), 0), K.box("Number", (0.14, 0.005, 0.1), (0, -0.203, 0.66), 2, bevel=False)],
                        [("stand / lid (G66 timber)", TIMBER), ("hive boxes (G66 whitewash)", "E8DCC0"), ("number plate (MI 0-9)", SIGN)], [K.socket("Entrance", (0, -0.21, 0.37)), K.socket("Number", (0, -0.206, 0.66)), K.socket("Ribbon", (0, 0, 0.91))],
                        "0.5 m hive, numbered", [K.ucx_box("Prop_YTM_NumberedHive", 0, (0.52, 0.5, 0.91), (0, 0, 0.455))])
    mi(nh, ["MI_YTM_NumberedHive_%d" % i for i in range(10)], "Number (0..9)")
    hr = sm("Prop_YTM_HiveRibbon", g, [K.cyl("Rosette", "y", 0.06, 0.06, 0.01, (0, 0, 0.0), 0, 10)] + [K.slab("Tail%d" % s, [(-0.02, 0), (0.02, 0), (0.03, -0.15), (0, -0.12), (-0.03, -0.15)], 0.003, (s * 0.025, 0, -0.03), 0, rot=(90, 0, 0)) for s in (-1, 1)],
            [("prize ribbon (G66 cloth; tint MI)", CLOTH4[0])], [K.socket("Pin", (0, 0, 0))], "0.12 m lucky-hive rosette")
    mi(hr, ["MI_YTM_HiveRibbon_%s" % c for c in ("Gold", "Red", "Blue")], "Tint")
    a = "Prop_YTM_BeeSwarm"; r = K.rng(374, a)
    bs = sm(a, g, [K.box("Bee%d" % i, (0.02, 0.012, 0.012), (r.gauss(0, 0.2), r.gauss(0, 0.2), 0.5 + r.gauss(0, 0.15)), 0, rot=(0, 0, r.uniform(0, 360)), bevel=False) for i in range(30)],
            [("bees (amber/black MI)", "D8A020")], [K.socket("Centre", (0, 0, 0.5))], "0.8 m swarm cloud (30 bee cards; Niagara can replace)")
    return [nh, hr, bs]


def g378():
    g = "G378"; a = "Prop_YTM_Palm"; H = 5.0; P = [K.cyl("Seg%d" % i, "z", 0.16 - 0.012 * i, 0.15 - 0.012 * i, H / 8, (0.06 * i * i / 8, 0, H / 16 + H / 8 * i), 0, 8) for i in range(8)]
    for i in range(7):
        an = i * 360 / 7; P.append(K.slab("Frond%d" % i, [(0, -0.05), (1.6, -0.18), (2.0, 0), (1.6, 0.18), (0, 0.05)], 0.01, (0.42, 0, H), 1, rot=(0, 25, an)))
    S = [K.socket("Crown", (0.42, 0, H)), K.socket("ClimbBase", (0, -0.2, 0))] + [K.socket("Coconut_%d" % i, (0.42 + 0.15 * math.cos(i * 2.1), 0.15 * math.sin(i * 2.1), H - 0.15)) for i in range(3)]
    P += [K.cyl("Nut%d" % i, "z", 0.08, 0.08, 0.14, (0.42 + 0.15 * math.cos(i * 2.1), 0.15 * math.sin(i * 2.1), H - 0.15), 2, 8) for i in range(3)]
    pm = sm(a, g, P, [("palm trunk", "8A7050"), ("fronds (G66 green)", LEAF), ("coconuts", "6A4A2A")], S, "5 m coconut palm, slight lean", [K.ucx_prism(a, 0, "z", 0.16, H, (0.2, 0, H / 2))])
    cr = sm("Prop_YTM_ClimbRope", g, [K.cyl("Loop", "z", 0.22, 0.22, 0.04, (0, 0, 0.02), 0, 12), K.cyl("Tail", "x", 0.015, 0.015, 0.6, (0.5, 0, 0.02), 0, 6)], [("rope", ROPE)], [K.socket("Feet", (0, 0, 0.02)), hand(0.02)], "0.45 m climbing loop")
    cn = sm("Prop_YTM_Coconut", g, [K.lathe("Nut", [(0.01, 0), (0.08, 0.04), (0.09, 0.1), (0.06, 0.16), (0.01, 0.18)], (0, 0, 0), 0, 10)], [("husk", "6A4A2A")], [hand(0.09)], "0.18 m coconut")
    return [pm, cr, cn]


def g383():
    g = "G383"; ps = sm("Prop_YTM_PebbleSet", g, [K.box("Pebble%d" % i, (0.05, 0.04, 0.025), (-0.25 + 0.05 * i, 0, 0.0125), i % 2, rot=(0, 0, 15 * i)) for i in range(10)], [("pebbles light", "D8D0C0"), ("pebbles dark", "5A5650")],
                        [K.socket("Pebble_%d" % i, (-0.25 + 0.05 * i, 0, 0.025)) for i in range(10)], "0.5 m line of 10 pebbles")
    tsk = sm("Prop_YTM_TallyStick", g, [K.box("Stick", (0.35, 0.03, 0.03), (0, 0, 0.015), 0)] + [K.box("Cut%d" % i, (0.004, 0.032, 0.012), (-0.15 + 0.03 * i, 0, 0.03), 1, bevel=False) for i in range(10)],
             [("stick (G66 timber)", TIMBER), ("cuts", "2A2420")], [hand(0.015)] + [K.socket("Cut_%d" % i, (-0.15 + 0.03 * i, 0, 0.03)) for i in range(10)], "0.35 m tally stick, 10 cut sockets")
    return [ps, tsk]


def g387():
    g = "G387"; vj = pot("Prop_YTM_VotingJar", g, 0.14, 0.32, "C8D8D8", note="glass-look voting jar")
    vs = sm("Prop_YTM_VoteShell", g, [K.lathe("Shell", [(0.01, 0), (0.03, 0.004), (0.025, 0.012), (0.01, 0.016)], (0, 0, 0), 0, 8)], [("cowrie (tint MI per choice)", SHELL)], [hand(0.008)], "6 cm vote shell")
    mi(vs, ["MI_YTM_VoteShell_%s" % c for c in ("White", "Red", "Blue", "Yellow")], "Choice tint")
    return [vj, vs, mat("Prop_YTM_CountingMat", g, 1.2, 0.8, "C8A868", 5, "counting mat, 5 lanes")]


def g390():
    g = "G390"; tp = post("Prop_YTM_TidePost", g, 3.0, 0.1, CLOTH4[0], "F0E8D8", "tide gauge post", [K.box("Mark%d" % i, (0.21, 0.21, 0.04), (0, 0, 0.5 + 0.5 * i), 1, bevel=False) for i in range(5)], [K.socket("Level_%d" % i, (0, -0.11, 0.5 + 0.5 * i)) for i in range(5)])
    ls = slip("Prop_YTM_LogSlate", g, 0.3, 0.22, "3A3E44", "tide log slate")
    sb = sm("Prop_YTM_StoneBoat", g, [K.lathe("Hull", [(0.01, 0), (0.3, 0.06), (0.36, 0.2)], (0, 0, 0), 0, 12), K.box("Keel", (0.05, 0.6, 0.04), (0, 0, 0.02), 0)], [("stone boat (ballast)", STONE)], [K.socket("Float", (0, 0, 0.1)), hand(0.2)], "0.72 m stone ballast boat")
    return [tp, ls, sb]


def g395():
    g = "G395"; ss = stone("Prop_YTM_SyllableStone", g, 0.4, 0.3, 0.3, 395, note="syllable stone", n=1, socks=[K.socket("Glyph", (0, -0.16, 0.18))])
    mi(ss, ["MI_YTM_SyllableStone_%d" % i for i in range(12)], "Syllable glyph (index into T_YTM_RiteAtlas)")
    wr = sm("Prop_YTM_WellRing", g, [K.lathe("Ring", [(0.9, 0), (0.9, 0.5), (0.7, 0.5), (0.7, 0.01)], (0, 0, 0), 0, 16, cap_top=False)] + [K.box("Seat%d" % i, (0.3, 0.2, 0.03), (0.8 * math.cos(i * math.pi / 3), 0.8 * math.sin(i * math.pi / 3), 0.51), 1, rot=(0, 0, i * 60 + 90)) for i in range(6)],
            [("ring stone", STONE), ("seat stones", "A89C88")], [K.socket("Echo", (0, 0, 0.3))] + [K.socket("Seat_%d" % i, (1.1 * math.cos(i * math.pi / 3), 1.1 * math.sin(i * math.pi / 3), 0)) for i in range(6)], "1.8 m well ring, 6 chant seats",
            [K.ucx_prism("Prop_YTM_WellRing", 0, "z", 0.9, 0.5, (0, 0, 0.25))])
    return [ss, wr]


def g398():
    return [fire_log_seat("G398"), lantern_pole("Prop_YTM_NightLantern", "G398", 1.4)]


def g401():
    g = "G401"; ft = table("Prop_YTM_FishTable", g, 1.8, 0.7, 0.85, 0, [K.box("Board", (0.6, 0.35, 0.03), (-0.4, 0, 0.865), 2)], "gutting table")
    ms = sm("Prop_YTM_MeasureStick", g, [K.box("Stick", (0.6, 0.04, 0.015), (0, 0, 0.0075), 0)] + [K.box("Tick%d" % i, (0.004, 0.02, 0.003), (-0.3 + 0.1 * i, -0.01, 0.016), 1, bevel=False) for i in range(7)],
            [("stick (G66 timber)", TIMBER), ("ticks", "2A2420")], [K.socket("Zero", (-0.3, 0, 0.015)), hand(0.008)], "0.6 m fish measuring stick")
    return [ft, ms, soup_pot(g)]


def g404():
    g = "G404"; sd = drum("Prop_YTM_SignalDrum", g, 0.3, 0.5, "signal drum")
    dl = line("Prop_YTM_DrumLineRope", g, 6.0, 6, lambda n, p, s: K.box(n, (0.05, 0.05, 0.12), p, s), [CLOTH4[0], CLOTH4[2]], 0.4, "drum-line rope with 6 marker tags", -0.06, prefix="Tag")
    return [sd, dl]


def g407():
    g = "G407"; bb = line("Prop_YTM_BeadBraid", g, 0.6, 12, lambda n, p, s: K.cyl(n, "x", 0.008, 0.008, 0.012, p, s, 6), [CLOTH4[0], SHELL], 0.0, "bead braid, 12 bead sockets", 0.0, rope=CLOTH4[1], prefix="Bead")
    bn = sm("Prop_YTM_BraidingBench", g, [K.box("Seat", (1.2, 0.35, 0.05), (0, 0, 0.45), 0)] + [K.box("Leg%d" % s, (0.06, 0.3, 0.42), (s * 0.5, 0, 0.21), 0) for s in (-1, 1)] + [K.box("Hook", (0.04, 0.04, 0.25), (0.55, 0, 0.6), 1)],
            [("bench (G66 timber)", TIMBER), ("braiding hook", BRASS)], [K.socket("Sit_0", (-0.3, 0, 0.47)), K.socket("Sit_1", (0.3, 0, 0.47)), K.socket("Braid", (0.55, 0, 0.72))], "1.2 m braiding bench", [K.ucx_box("Prop_YTM_BraidingBench", 0, (1.2, 0.35, 0.47), (0, 0, 0.235))])
    return [bb, bn]


def g410():
    g = "G410"; oj = post("Prop_YTM_LampPostOilJar", g, 2.4, 0.06, "FFC870", IRON, "lamp post with oil jar", [K.box("Arm", (0.04, 0.4, 0.04), (0, -0.2, 2.3), 1), K.lathe("Jar", [(0.06, 0), (0.09, 0.08), (0.05, 0.16)], (0, -0.38, 2.1), 2, 10)],
                                [K.socket("Flame", (0, -0.38, 2.3)), K.socket("Fill", (0, -0.38, 2.26))])
    oj["materials"][2]["glow"] = True if isinstance(oj["materials"][2], dict) else None
    lc = sm("Prop_YTM_LamplighterCan", g, [K.lathe("Can", [(0.07, 0), (0.08, 0.15), (0.03, 0.22)], (0, 0, 0), 0, 10), K.cyl("Spout", "y", 0.012, 0.006, 0.18, (0, -0.1, 0.17), 0, 6, rot=(-35, 0, 0)), arch("Bail", 0.06, 0.008, (0, 0, 0.21), 1, 8, 0.01)],
            [("tin can", "9A9CA0", 0.4, 0.8), ("bail", IRON)], [hand(0.3), K.socket("Spout", (0, -0.18, 0.22))], "0.22 m oil can")
    return [oj, lc]


def g415():
    g = "G415"; out = []
    for v in ("Sound", "Weak"):
        a = "Prop_YTM_RopeBridge_" + v; P = [K.box("Plank%d" % i, (1.0, 0.18, 0.03), (0, -1.8 + 0.4 * i, -0.15 * math.sin(math.pi * i / 9)), 0, rot=(0, 0, (8 if v == "Weak" and i % 3 == 1 else 0))) for i in range(10) if not (v == "Weak" and i in (4, 7))]
        P += [K.cyl("Hand%d%d" % (s, k), "y", 0.015, 0.015, 1.0, (s * 0.55, -1.5 + 1.0 * k, 0.9 - 0.15 * math.sin(math.pi * (k + 0.5) / 4)), 1, 6) for s in (-1, 1) for k in range(4)]
        P += [K.box("Post%d%d" % (s, e), (0.12, 0.12, 1.4), (s * 0.55, e * 2.0, 0.4), 0) for s in (-1, 1) for e in (-1, 1)]
        out.append(state(sm(a, g, P, [("planks (G66 timber)", TIMBER), ("rope", ROPE)], [K.socket("Start", (0, -2.0, 0)), K.socket("End", (0, 2.0, 0))] + ([K.socket("Gap_%d" % i, (0, -1.8 + 0.4 * k, -0.1)) for i, k in enumerate((4, 7))] if v == "Weak" else []),
                               "4 m rope bridge (%s)" % v.lower(), [K.ucx_box(a, 0, (1.2, 4.0, 0.1), (0, 0, -0.05))]), v))
    return out   # RopeCoil: REUSE G212


def g417():
    g = "G417"; pb = sm("Prop_YTM_PalmBroom", g, [K.cyl("Handle", "z", 0.015, 0.015, 1.2, (0, 0, 0.75), 0, 6), K.cyl("Head", "z", 0.15, 0.04, 0.3, (0, 0, 0.15), 1, 10)], [("handle (G66 timber)", TIMBER), ("palm-rib bristles", "B8A060")],
                        [K.socket("Grip", (0, 0, 1.1)), K.socket("Sweep", (0, 0, 0))], "1.35 m palm broom")
    sp = sm("Prop_YTM_SandPath", g, [K.box("Path", (1.2, 2.0, 0.01), (0, 0, 0.005), 0, bevel=False)] + [K.box("Shell%d" % i, (0.05, 0.04, 0.02), (s * 0.62, -0.9 + 0.45 * i, 0.01), 1) for i in range(5) for s in (-1, 1)],
            [("raked sand (swept/unswept MI)", SAND), ("edge shells", SHELL)], [K.socket("Start", (0, -1.0, 0)), K.socket("End", (0, 1.0, 0))], "2 m sand path tile (chains Start->End)")
    mi(sp, ["MI_YTM_SandPath_Unswept", "MI_YTM_SandPath_Swept"], "Swept 0/1")
    return [pb, sp]


def g420():
    g = "G420"; tk = pot("Prop_YTM_TeaKettle", g, 0.11, 0.18, IRON, lid=True, note="tea kettle")
    tk["objects"][0]["parts"] = tk["objects"][0]["parts"] + [K.cyl("Spout", "y", 0.02, 0.01, 0.12, (0, -0.14, 0.12), 0, 6, rot=(-40, 0, 0)), arch("Bail", 0.08, 0.008, (0, 0, 0.2), 0, 8, 0.01)]
    return [K.finish({k: v for k, v in tk.items() if k != "predicted"})]   # FireLogSeat: built in G398


def g424():
    g = "G424"; out = [sm("Prop_YTM_DriftwoodPlank_%s" % n, g, [K.box("Plank", (L, 0.22, 0.05), (0, 0, 0.025), 0, rot=(0, 0, 2))], [("driftwood (silver grey)", "A89C88")], [K.socket("CutLine", (0, 0, 0.05)), K.socket("Lift_A", (-L / 2 + 0.1, 0, 0.05)), K.socket("Lift_B", (L / 2 - 0.1, 0, 0.05))], "%.1f m driftwood plank" % L)
                       for n, L in (("Uncut", 2.4), ("Half", 1.2))]
    sh = sm("Prop_YTM_Sawhorse", g, [K.box("Beam", (1.0, 0.1, 0.1), (0, 0, 0.7), 0)] + [K.box("Leg%d%d" % (s, e), (0.06, 0.06, 0.75), (s * 0.4, e * 0.12, 0.36), 0, rot=(e * -12, 0, 0)) for s in (-1, 1) for e in (-1, 1)],
            [("sawhorse (G66 timber)", TIMBER)], [K.socket("Work", (0, 0, 0.75)), K.socket("Sawyer", (0, -0.6, 0))], "1.0 m sawhorse", [K.ucx_box("Prop_YTM_Sawhorse", 0, (1.0, 0.4, 0.75), (0, 0, 0.375))])
    return out + [sh]


def g427():
    g = "G427"; ws = stone("Prop_YTM_WashingStone", g, 0.9, 0.6, 0.4, 427, note="washing stone", n=1, socks=[K.socket("Washer", (0, -0.6, 0)), K.socket("Scrub", (0, -0.1, 0.4))])
    return [ws, basket("Prop_YTM_LaundryBasket", g, 0.3, 0.35, False, note="laundry basket", fill=("laundry (G66 cloth)", CLOTH4[1]))]


def g429():
    g = "G429"; sc = sm("Prop_YTM_ShellCrown", g, [K.cyl("Band", "z", 0.1, 0.1, 0.03, (0, 0, 0.015), 0, 12)] + [K.lathe("Shell%d" % i, [(0.01, 0), (0.02, 0.02), (0.005, 0.05)], (0.1 * math.cos(i * 0.785), 0.1 * math.sin(i * 0.785), 0.03), 1, 6) for i in range(8)],
                        [("woven band", WICKER), ("shells", SHELL)], [K.socket("Head", (0, 0, 0))], "0.2 m shell crown")
    fc = sm("Prop_YTM_FeatherCrown", g, [K.cyl("Band", "z", 0.1, 0.1, 0.03, (0, 0, 0.015), 0, 12)] + [K.slab("Feather%d" % i, [(-0.012, 0), (0.012, 0), (0.0, 0.14)], 0.003, (0.1 * math.cos(i * 0.628), 0.1 * math.sin(i * 0.628), 0.02), 1 + i % 2, rot=(90, 0, math.degrees(i * 0.628) + 90)) for i in range(10)],
            [("woven band", WICKER), ("feathers A (G66 cloth)", CLOTH4[0]), ("feathers B (G66 cloth)", CLOTH4[2])], [K.socket("Head", (0, 0, 0))], "0.2 m feather crown")
    dr = sm("Prop_YTM_DanceRibbon", g, [K.cyl("Stick", "z", 0.01, 0.01, 0.4, (0, 0, 0.2), 0, 6), K.slab("Ribbon", [(0, 0), (0.04, 0), (0.06, -0.8), (0.02, -0.8)], 0.002, (0.01, 0, 0.4), 1, rot=(90, 0, 0))],
            [("stick (G66 timber)", TIMBER), ("ribbon (G66 cloth; cloth sim optional)", CLOTH4[0])], [K.socket("Grip", (0, 0, 0.05)), K.socket("RibbonRoot", (0, 0, 0.4))], "0.4 m stick, 0.8 m ribbon")
    return [sc, fc, dr]


def g434():
    g = "G434"; a = "Prop_YTM_CrabPen"; P = [K.box("Post%d%d" % (s, e), (0.06, 0.06, 0.6), (s * 0.7, e * 0.5, 0.3), 0) for s in (-1, 1) for e in (-1, 1)]
    P += [K.box("Slat%d%d" % (s, k), (0.02, 1.0, 0.06), (s * 0.7, 0, 0.1 + 0.15 * k), 0) for s in (-1, 1) for k in range(4)] + [K.box("SlatE%d%d" % (e, k), (1.4, 0.02, 0.06), (0, e * 0.5, 0.1 + 0.15 * k), 0) for e in (-1, 1) for k in range(4)]
    P += [K.box("Water", (1.36, 0.96, 0.01), (0, 0, 0.12), 1, bevel=False)]
    cp = sm(a, g, P, [("pen slats (G66 timber)", TIMBER), ("shallow water (MI)", WATER, 0.05)], [K.socket("Crab_%d" % i, (-0.4 + 0.4 * (i % 3), -0.2 + 0.4 * (i // 3), 0.13)) for i in range(6)] + [K.socket("Keeper", (0, -0.9, 0))],
            "1.4 x 1.0 m crab pen, 6 crab spots", [K.ucx_box(a, 0, (1.46, 1.06, 0.6), (0, 0, 0.3))])
    return [cp]   # SoupPot: built in G401


def g437():
    g = "G437"; rm = mat("Prop_YTM_ReedMat", g, 2.0, 1.5, "C8B070", 6, "reed floor mat")
    rb = sm("Prop_YTM_ReedBundle", g, [K.cyl("Reeds", "x", 0.12, 0.1, 1.6, (0, 0, 0.12), 0, 10)] + [K.cyl("Tie%d" % s, "x", 0.125, 0.125, 0.04, (s * 0.5, 0, 0.12), 1, 10) for s in (-1, 1)],
            [("dried reed", "C8B070"), ("ties", ROPE)], [K.socket("Carry", (0, 0, 0.24))], "1.6 m reed bundle")
    return [rm, rb]


def g440():
    g = "G440"; dp = sm("Prop_YTM_DoorNumberPlaque", g, [K.box("Plaque", (0.18, 0.025, 0.14), (0, 0, 0.07), 0), K.box("Num", (0.1, 0.004, 0.09), (0, -0.014, 0.07), 1, bevel=False)], [("plaque (G66 sign board)", SIGN), ("painted number (MI 0-9)", "F0E8D8")],
                        [K.socket("Mount", (0, 0.013, 0.07)), K.socket("Number", (0, -0.017, 0.07))], "0.18 m door plaque")
    mi(dp, ["MI_YTM_DoorNumberPlaque_%d" % i for i in range(10)], "Number (0..9)")
    ps = sm("Prop_YTM_PaintedShell", g, [K.lathe("Shell", [(0.01, 0), (0.05, 0.01), (0.04, 0.025), (0.01, 0.03)], (0, 0, 0), 0, 10)], [("painted shell (G66 cloth tint MI)", CLOTH4[0])], [hand(0.015), K.socket("Mount", (0, 0, 0))], "0.1 m painted shell")
    mi(ps, ["MI_YTM_PaintedShell_%s" % c for c in ("Red", "Blue", "Yellow", "Green", "White")], "Tint (lucky colour)")
    return [dp, ps]


def g443():
    g = "G443"; cr = sm("Prop_YTM_CanoeRoller", g, [K.cyl("Roller", "x", 0.08, 0.08, 1.2, (0, 0, 0.08), 0, 10), K.box("ChockL", (0.1, 0.25, 0.06), (-0.55, 0, 0.03), 1), K.box("ChockR", (0.1, 0.25, 0.06), (0.55, 0, 0.03), 1)],
                        [("log roller", BARK), ("chocks (G66 timber)", TIMBER)], [K.socket("Hull", (0, 0, 0.16)), K.socket("Push", (0, 0.4, 0))], "1.2 m canoe roller log")
    return [cr, drum("Prop_YTM_WorkDrum", g, 0.22, 0.45, "work-song drum")]


def g448():
    g = "G448"; pl = sm("Prop_YTM_PaperLantern", g, [K.lathe("Paper", [(0.08, 0), (0.15, 0.08), (0.15, 0.22), (0.08, 0.3)], (0, 0, 0), 0, 12, cap_bottom=False, cap_top=False), K.cyl("Ring", "z", 0.085, 0.085, 0.02, (0, 0, 0.01), 1, 12), K.cyl("Flame", "z", 0.02, 0.0, 0.05, (0, 0, 0.05), 2, 6)],
                        [("paper (G66 cloth tint, emissive)", "FFD890", 0.6, 0, True), ("bamboo ring", WICKER), ("flame (emissive)", EMBER, 0.8, 0, True)], [K.socket("Hand", (0, 0, 0.3)), K.socket("Wish", (0, -0.15, 0.15)), K.socket("Flame", (0, 0, 0.05))], "0.3 m sky/paper lantern")
    mi(pl, ["MI_YTM_PaperLantern_%s" % c for c in ("Warm", "Red", "Blue")], "Tint")
    ws = slip("Prop_YTM_WishSlip", g, 0.06, 0.15, "F0E0C0", "wish slip"); mi(ws, ["MI_YTM_WishSlip_Blank", "MI_YTM_WishSlip_Written"], "Written 0/1")
    return [pl, ws]


def g453():
    g = "G453"; fb = board("Prop_YTM_FlagBoard", g, 1.2, 0.9, 0.7, 5, "Flag", CLOTH4[0], note="5 flag slots")
    cs = sm("Prop_YTM_ColourShells", g, [K.lathe("Shell%d" % i, [(0.01, 0), (0.035, 0.008), (0.028, 0.02), (0.01, 0.024)], (-0.12 + 0.06 * i, 0, 0), i % 4, 8) for i in range(5)], [("shell %d (G66 cloth)" % k, CLOTH4[k]) for k in range(4)],
            [K.socket("Shell_%d" % i, (-0.12 + 0.06 * i, 0, 0.024)) for i in range(5)], "5 coloured shells (0.3 m row)")
    return [fb, cs]


def g456():
    g = "G456"; a = "Prop_YTM_JettyNetRack"; P = [K.box("Post%d" % i, (0.1, 0.1, 2.0), (-1.2 + 1.2 * i, 0, 1.0), 0) for i in range(3)] + [K.box("Rail", (2.6, 0.06, 0.06), (0, 0, 1.9), 0)]
    P += [K.box("Net%d" % i, (1.1, 0.02, 1.2), (-0.6 + 1.2 * i, 0, 1.3), 1, bevel=False) for i in range(2)]
    nr = sm(a, g, P, [("rack (G66 timber)", TIMBER), ("hung net (opacity MI)", ROPE)], [K.socket("Net_%d" % i, (-0.6 + 1.2 * i, 0, 1.9)) for i in range(2)] + [K.socket("Mender", (0, -0.8, 0))], "2.6 m jetty net rack", [K.ucx_box(a, 0, (2.6, 0.12, 2.0), (0, 0, 1.0))])
    return [nr, hut("Prop_YTM_NetShed", g, 2.4, 2.0, 2.0, 0.0, "net shed")]


def g460():
    g = "G460"; out = [sm("Prop_YTM_ShellCoin_%s" % n, g, [K.cyl("Coin", "z", r, r, r * 0.25, (0, 0, r * 0.125), 0, 10), K.cyl("Hole", "z", r * 0.25, r * 0.25, r * 0.26, (0, 0, r * 0.125), 1, 6)], [("polished shell", SHELL), ("bore", "2A2420")], [hand(r * 0.125)], "%.0f mm shell coin" % (2000 * r))
                       for n, r in (("Small", 0.012), ("Large", 0.02))]
    out.append(basket("Prop_YTM_BreadBasket", g, 0.2, 0.12, False, note="bread basket", fill=("loaves", "C88A48")))
    out.append(sm("Prop_YTM_StallTray", g, [K.box("Base", (0.6, 0.4, 0.02), (0, 0, 0.01), 0)] + [K.box("Lip%d" % i, (0.6 if i < 2 else 0.02, 0.02 if i < 2 else 0.4, 0.05), ((0, 0, -0.29, 0.29)[i], (-0.19, 0.19, 0, 0)[i], 0.035), 0) for i in range(4)],
                  [("tray (G66 timber)", TIMBER)], [K.socket("Item_%d" % i, (-0.2 + 0.2 * (i % 3), -0.1 + 0.2 * (i // 3), 0.02)) for i in range(6)], "0.6 x 0.4 m stall tray, 6 item spots"))
    return out


def g463():
    g = "G463"; out = [basket("Prop_YTM_WovenBasket_%s" % n, g, r, h, n != "Large", note="woven basket %s" % n.lower()) for n, r, h in (("Small", 0.12, 0.12), ("Medium", 0.2, 0.22), ("Large", 0.32, 0.36))]
    a = "Prop_YTM_TwoBasketFerry"
    out.append(sm(a, g, boat_parts(2.4, 1.0) + [K.cyl("Basket%d" % i, "z", 0.22, 0.2, 0.25, (0, -0.4 + 0.8 * i, 0.22), 2, 10) for i in range(2)], [("hull (G66 timber)", TIMBER), ("gunwale (G66 sign)", SIGN), ("baskets", WICKER)],
                  [K.socket("Basket_%d" % i, (0, -0.4 + 0.8 * i, 0.22)) for i in range(2)] + [K.socket("Pole", (0, 0.9, 0.45)), K.socket("Mooring", (0, -1.2, 0.45))], "2.4 m two-basket ferry punt", [K.ucx_box(a, 0, (1.0, 2.4, 0.5), (0, 0, 0.25))]))
    return out


def g466():
    g = "G466"; tm = stone("Prop_YTM_TideMarkStone", g, 0.4, 0.3, 1.2, 466, note="carved tide-mark stone", n=2, socks=[K.socket("Mark_%d" % i, (0, -0.16, 0.3 + 0.25 * i)) for i in range(4)])
    tm["objects"][0]["parts"] += [K.box("Groove%d" % i, (0.3, 0.01, 0.02), (0, -0.155, 0.3 + 0.25 * i), 1, bevel=False) for i in range(4)]
    tm["materials"].append(M("Prop_YTM_TideMarkStone", 1, "carved grooves", "4A4640")); tm = K.finish({k: v for k, v in tm.items() if k != "predicted"})
    return [tm, lantern_pole("Prop_YTM_SeaWallLantern", g, 1.0)]


def g468():
    g = "G468"; cb = board("Prop_YTM_ChoreBoard", g, 1.0, 0.9, 0.8, 7, "Day", note="7 day rows")
    out = [cb] + [sm("Prop_YTM_Broom_%s" % n, g, [K.cyl("Handle", "z", 0.014, 0.014, L, (0, 0, L / 2 + 0.25), 0, 6), K.cyl("Head", "z", w, 0.04, 0.28, (0, 0, 0.14), 1, 8)], [("handle (G66 timber)", TIMBER), ("straw", "C8A858")], [K.socket("Grip", (0, 0, L)), K.socket("Sweep", (0, 0, 0))], "%.1f m broom" % (L + 0.25))
                  for n, L, w in (("Long", 1.1, 0.14), ("Hand", 0.45, 0.1))]
    ul = sm("Prop_YTM_FestivalLantern_Unlit", g, [K.lathe("Paper", [(0.1, 0), (0.18, 0.1), (0.18, 0.3), (0.1, 0.4)], (0, 0, 0), 0, 12, cap_bottom=False, cap_top=False), K.cyl("Ring", "z", 0.105, 0.105, 0.02, (0, 0, 0.4), 1, 12)],
            [("paper (G66 cloth, unlit)", CLOTH4[0]), ("bamboo", WICKER)], [K.socket("Hang", (0, 0, 0.41)), K.socket("Candle", (0, 0, 0.05))], "0.4 m festival lantern, unlit state")
    mi(ul, ["MI_YTM_FestivalLantern_%s" % c for c in ("Red", "Yellow", "Blue")], "Tint")
    return out + [state(ul, "Unlit")]


def g470():
    g = "G470"; out = []
    for i in range(3):
        a = "Prop_YTM_GrassTussock_%d" % (i + 1); r = K.rng(470 + i, a)
        out.append(sm(a, g, [K.slab("Blade%d" % k, [(-0.02, 0), (0.02, 0), (0.0, 0.35 + 0.15 * r.random())], 0.004, (0.06 * math.cos(k), 0.06 * math.sin(k), 0), k % 2, rot=(90 - r.uniform(0, 25), 0, math.degrees(k * 0.9))) for k in range(10)],
                      [("marsh grass (G66 green)", LEAF), ("dry tips", "B8A060")], [K.socket("Root", (0, 0, 0))], "0.5 m grass tussock var %d" % (i + 1)))
    out.append(sm("Prop_YTM_ReedBedClump", g, [K.cyl("Reed%d" % k, "z", 0.008, 0.004, 1.2 + 0.03 * (k % 5), (0.25 * math.cos(k * 2.4) * (k / 16), 0.25 * math.sin(k * 2.4) * (k / 16), 0.6), k % 2, 4) for k in range(16)] + [K.cyl("Head%d" % k, "z", 0.015, 0.015, 0.1, (0.25 * math.cos(k * 2.4) * (k / 16), 0.25 * math.sin(k * 2.4) * (k / 16), 1.25), 2, 6) for k in range(0, 16, 3)],
                  [("reed stems (G66 green)", LEAF), ("dry reed", "B8A060"), ("bulrush heads", BARK)], [K.socket("Root", (0, 0, 0))], "0.5 m reed clump, 1.3 m tall"))
    return out


def g471():
    g = "G471"; bp = post("Prop_YTM_BeaconPost", g, 1.8, 0.08, EMBER, SIGN, "wooden beacon post", [K.cyl("Brazier", "z", 0.12, 0.18, 0.15, (0, 0, 1.95), 2, 10)], [K.socket("Fire", (0, 0, 2.05)), K.socket("Rope_A", (-0.09, 0, 1.0)), K.socket("Rope_B", (0.09, 0, 1.0))])
    rf = line("Prop_YTM_RopeFenceLoop", g, 3.0, 0, None, [ROPE], 0.2, "rope fence loop between beacon posts")
    return [bp, rf]


def g472():
    g = "G472"; a = "Prop_YTM_KinTreePanel"; P = [K.box("Panel", (1.6, 0.08, 1.2), (0, 0, 0.6 + 0.4), 0), K.box("Trunk", (0.12, 0.01, 0.6), (0, -0.045, 0.7), 1, bevel=False)]
    S = []
    for lvl in range(3):
        n = 2 ** lvl
        for k in range(n):
            x = -0.6 + 1.2 * (k + 0.5) / n; z = 1.0 + 0.25 * lvl; P.append(K.box("Leaf%d_%d" % (lvl, k), (0.12, 0.012, 0.08), (x, -0.046, z), 2, bevel=False)); S.append(K.socket("Tag_%d_%d" % (lvl, k), (x, -0.053, z)))
    P += [K.box("Leg%d" % s, (0.1, 0.1, 0.45), (s * 0.7, 0, 0.2), 0) for s in (-1, 1)]
    kt = sm(a, g, P, [("carved panel (G66 timber)", TIMBER), ("carved trunk", BARK), ("leaf plates", LEAF)], S, "1.6 x 1.6 m carved kin tree, 7 name-tag sockets", [K.ucx_box(a, 0, (1.6, 0.1, 1.6), (0, 0, 0.8))])
    nt = sm("Prop_YTM_BrassNameTag", g, [K.box("Tag", (0.1, 0.004, 0.035), (0, 0, 0.0175), 0), K.box("Name", (0.08, 0.002, 0.02), (0, -0.003, 0.0175), 1, bevel=False)], [("brass", BRASS, 0.3, 1.0), ("engraved name (decal)", "4A3A20")],
            [K.socket("Mount", (0, 0.002, 0.0175)), K.socket("Name", (0, -0.004, 0.0175))], "0.1 m brass name tag")
    return [kt, nt]


def g474():
    g = "G474"; out = []
    for v, glow in (("Off", False), ("On", True)):
        a = "Prop_YTM_SignalLantern_" + v
        out.append(state(sm(a, g, [K.box("Body", (0.18, 0.18, 0.26), (0, 0, 0.13), 0), K.box("Glass", (0.14, 0.19, 0.18), (0, 0, 0.14), 1), K.box("Cap", (0.2, 0.2, 0.04), (0, 0, 0.28), 0), K.box("Bail", (0.01, 0.12, 0.08), (0, 0, 0.34), 0)],
                            [("iron body", IRON, 0.5, 0.8), ("lens (%s)" % v.lower(), "FFC870" if glow else "6A6050", 0.2, 0, glow)], [K.socket("Hang", (0, 0, 0.38)), K.socket("Light", (0, 0, 0.14))], "0.38 m signal lantern (%s)" % v.lower()), v))
    a = "Prop_YTM_BrassSwitchBoard"; P = [K.box("Board", (0.8, 0.06, 0.5), (0, 0, 1.2), 0), K.box("Post", (0.1, 0.1, 0.95), (0, 0.05, 0.475), 0)]
    P += [K.box("Lever%d" % i, (0.03, 0.08, 0.14), (-0.3 + 0.15 * i, -0.06, 1.2), 1, rot=(25, 0, 0)) for i in range(5)]
    out.append(sm(a, g, P, [("board (G66 timber)", TIMBER), ("brass levers", BRASS, 0.3, 1.0)], [K.socket("Lever_%d" % i, (-0.3 + 0.15 * i, -0.06, 1.2)) for i in range(5)] + [K.socket("Operator", (0, -0.7, 0))],
                  "0.8 m brass switch board, 5 levers (rotate about local X)", [K.ucx_box(a, 0, (0.8, 0.15, 1.45), (0, 0, 0.725))]))
    return out


def g476():
    g = "G476"; dp = sm("Prop_YTM_DockPlank", g, [K.box("Plank", (2.0, 0.25, 0.05), (0, 0, 0.025), 0)] + [K.box("Nail%d" % i, (0.015, 0.015, 0.004), (s * 0.95, -0.08 + 0.16 * i, 0.051), 1, bevel=False) for i in range(2) for s in (-1, 1)],
                        [("plank (G66 timber)", TIMBER), ("nails", IRON)], [K.socket("Lift_A", (-0.9, 0, 0.05)), K.socket("Lift_B", (0.9, 0, 0.05)), K.socket("Lay", (0, 0, 0))], "2.0 m dock plank", [K.ucx_box("Prop_YTM_DockPlank", 0, (2.0, 0.25, 0.05), (0, 0, 0.025))])
    tp = post("Prop_YTM_PaintedTidePost", g, 2.5, 0.09, CLOTH4[0], "F0E8D8", "painted tide post", [K.box("Paint%d" % i, (0.19, 0.19, 0.25), (0, 0, 0.25 + 0.5 * i), 2, bevel=False) for i in range(5)], [K.socket("Band_%d" % i, (0, -0.1, 0.25 + 0.5 * i)) for i in range(5)])
    return [dp, tp]


def g478():
    g = "G478"; cb = board("Prop_YTM_ChalkBookingBoard", g, 1.2, 0.9, 0.7, 6, "Booking", "3A3E44", note="chalk, 6 booking rows")
    a = "Prop_YTM_CoinChest"; cc = sm(a, g, [K.box("Chest", (0.5, 0.32, 0.26), (0, 0, 0.13), 0), K.cyl("LidDome", "x", 0.16, 0.16, 0.5, (0, 0, 0.26), 0, 10), K.box("BandL", (0.03, 0.34, 0.3), (-0.18, 0, 0.18), 1), K.box("BandR", (0.03, 0.34, 0.3), (0.18, 0, 0.18), 1), K.box("Lock", (0.06, 0.02, 0.07), (0, -0.165, 0.24), 1)],
                                [("chest (G66 timber)", TIMBER), ("iron bands / lock", IRON, 0.5, 0.8)], [K.socket("Lid", (0, 0.16, 0.26)), K.socket("Coins", (0, 0, 0.2)), hand(0.3)], "0.5 x 0.32 x 0.42 m coin chest", [K.ucx_box(a, 0, (0.5, 0.32, 0.42), (0, 0, 0.21))])
    bt = line("Prop_YTM_Bunting", g, 5.0, 12, lambda n, p, s: K.slab(n, [(-0.1, 0), (0.1, 0), (0, -0.2)], 0.003, p, s, rot=(90, 0, 0)), [CLOTH4[0], CLOTH4[2]], 0.3, "bunting, 12 pennants", 0.0, prefix="Flag")
    return [cb, cc, bt]


def g479():
    g = "G479"; out = [stone("Prop_YTM_CausewayStone_%d" % (i + 1), g, w, d, 0.35, 479 + i, "8A8478", "causeway stepping stone", n=1) for i, (w, d) in enumerate(((0.6, 0.5), (0.8, 0.6), (0.5, 0.45)))]
    pd = sm("Prop_YTM_ShallowPoolDecal", g, [K.box("Decal", (2.0, 2.0, 0.002), (0, 0, 0.001), 0, bevel=False)], [("shallow pool decal (DBuffer, normal + roughness, opacity mask)", WATER, 0.05)], [K.socket("Centre", (0, 0, 0))], "2 x 2 m decal projector card")
    mi(pd, ["MI_YTM_ShallowPool_%d" % i for i in range(3)], "Mask variant 0..2 (T_YTM_PoolMask atlas)"); pd["spec"]["decal"] = True
    return out + [pd]


def g481():
    g = "G481"; out = []
    for i in range(3):
        a = "Prop_YTM_BlessingBanner_%d" % (i + 1)
        out.append(sm(a, g, [K.cyl("Rod", "x", 0.012, 0.012, 0.6, (0, 0, 0), 0, 6), K.slab("Banner", [(-0.25, 0), (0.25, 0), (0.25, -1.0 + 0.1 * i), (0, -1.15 + 0.1 * i), (-0.25, -1.0 + 0.1 * i)], 0.003, (0, 0, -0.02), 1, rot=(90, 0, 0)),
                          K.cyl("Cord", "z", 0.004, 0.004, 0.3, (0, 0, 0.15), 0, 4)], [("rod / cord (G66 timber)", TIMBER), ("banner (G66 cloth; chant word MI)", CLOTH4[i % 4])], [K.socket("Hang", (0, 0, 0.3)), K.socket("Word", (0, -0.005, -0.5))], "0.5 x 1.1 m hanging blessing banner %d" % (i + 1)))
    a = "Prop_YTM_FireRing"
    out.append(sm(a, g, [K.box("Stone%d" % i, (0.22, 0.16, 0.14), (0.6 * math.cos(i * 0.524), 0.6 * math.sin(i * 0.524), 0.07), 0, rot=(0, 0, i * 30)) for i in range(12)] + [K.cyl("Ash", "z", 0.45, 0.45, 0.02, (0, 0, 0.01), 1, 12), K.cyl("Embers", "z", 0.25, 0.2, 0.06, (0, 0, 0.04), 2, 10)],
                  [("ring stones", STONE), ("ash", "5A5650"), ("embers (emissive)", EMBER, 0.8, 0, True)], [K.socket("Fire", (0, 0, 0.1))] + [K.socket("Chant_%d" % i, (1.2 * math.cos(i * 1.047), 1.2 * math.sin(i * 1.047), 0)) for i in range(6)],
                  "1.4 m chant fire ring", [K.ucx_prism(a, 0, "z", 0.7, 0.15, (0, 0, 0.075))]))
    return out


def g482():
    g = "G482"; nk = line("Prop_YTM_ShellNecklace", g, 0.5, 9, lambda n, p, s: K.lathe(n, [(0.003, 0), (0.012, 0.006), (0.003, 0.018)], p, s, 6), [SHELL, "E8A0A0"], 0.18, "shell necklace strand, 9 shells", -0.01, prefix="Shell")
    out = [nk]
    for n, r in (("Small", 0.03), ("Medium", 0.035)):
        a = "Prop_YTM_ShellBracelet_" + n
        out.append(sm(a, g, [K.cyl("Cord", "z", r, r, 0.006, (0, 0, 0.003), 0, 12)] + [K.lathe("Shell%d" % i, [(0.002, 0), (0.007, 0.004), (0.002, 0.012)], (r * math.cos(i * 0.898), r * math.sin(i * 0.898), 0.004), 1, 6) for i in range(7)],
                      [("cord", ROPE), ("shells", SHELL)], [K.socket("Wrist", (0, 0, 0.003))], "%.0f mm shell bracelet" % (2000 * r)))
    return out


def g484():
    g = "G484"; jar = pot("Prop_YTM_NumberedJar", g, 0.1, 0.22, CLAY, lid=True, note="numbered clay jar")
    jar["objects"][0]["parts"].append(K.box("Number", (0.06, 0.004, 0.05), (0, -0.098, 0.1), 1, bevel=False)); jar["materials"].append(M("Prop_YTM_NumberedJar", 1, "painted number (MI 0-9)", "F0E8D8"))
    jar["sockets"].append(K.socket("Number", (0, -0.102, 0.1))); jar = K.finish({k: v for k, v in jar.items() if k != "predicted"}); jar["spec"]["sockets"] = [s["name"] for s in jar["sockets"]]
    mi(jar, ["MI_YTM_NumberedJar_%d" % i for i in range(10)], "Number (0..9)")
    a = "Prop_YTM_PantryShelf"; P = [K.box("Side%d" % s, (0.04, 0.35, 1.6), (s * 0.6, 0, 0.8), 0) for s in (-1, 1)] + [K.box("Shelf%d" % i, (1.2, 0.35, 0.03), (0, 0, 0.1 + 0.5 * i), 0) for i in range(4)]
    ps = sm(a, g, P, [("shelf (G66 timber)", TIMBER)], [K.socket("Jar_%d_%d" % (i, k), (-0.45 + 0.3 * k, 0, 0.115 + 0.5 * i)) for i in range(4) for k in range(4)], "1.24 x 0.35 x 1.6 m pantry shelf, 16 jar spots", [K.ucx_box(a, 0, (1.24, 0.35, 1.6), (0, 0, 0.8))])
    return [jar, ps]


def g486():
    g = "G486"; out = [crate("Prop_YTM_CargoCrate_%s" % n, g, s, s * 0.8, s * 0.7, note="cargo crate %s" % n.lower()) for n, s in (("Small", 0.4), ("Medium", 0.7), ("Large", 1.0))]
    a = "Prop_YTM_HarbourScale"; P = [K.box("Post%d" % s, (0.12, 0.12, 2.4), (s * 0.8, 0, 1.2), 0) for s in (-1, 1)] + [K.box("Beam", (1.8, 0.14, 0.14), (0, 0, 2.4), 0), K.lathe("Dial", [(0.01, 0), (0.15, 0.0), (0.15, 0.04)], (0, -0.02, 2.1), 1, 14, rot=(90, 0, 0)), K.cyl("Hook", "z", 0.015, 0.015, 0.4, (0, 0, 1.8), 1, 6), K.box("Platform", (0.6, 0.6, 0.04), (0, 0, 1.58), 0)]
    out.append(sm(a, g, P, [("frame (G66 timber)", TIMBER), ("brass dial / hook", BRASS, 0.3, 1.0)], [K.socket("Hook", (0, 0, 1.6)), K.socket("Needle", (0, -0.07, 2.1)), K.socket("Reader", (0, -0.9, 0))], "1.8 x 2.5 m hanging harbour scale (platform hangs from SOCKET_Hook)",
                  [K.ucx_box(a, 0, (1.85, 0.2, 2.5), (0, 0, 1.25))]))
    return out


def g487():
    g = "G487"; sb = sm("Prop_YTM_RegattaBoat", g, boat_parts(3.0, 1.0, 3.0) + [K.box("SailNumber", (0.3, 0.005, 0.3), (0, -0.45, 1.6), 3, bevel=False, rot=(0, 0, 90))], [("hull (G66 timber)", TIMBER), ("gunwale (G66 sign)", SIGN), ("sail", "EDE6D6"), ("sail number (MI 1-9)", "2A2420")],
                        [K.socket("Helm", (0, 1.1, 0.4)), K.socket("Number", (0.01, -0.45, 1.6)), K.socket("Mooring", (0, -1.5, 0.45))], "3 m numbered regatta dinghy, sail rig", [K.ucx_box("Prop_YTM_RegattaBoat", 0, (1.0, 3.0, 0.5), (0, 0, 0.25))])
    mi(sb, ["MI_YTM_RegattaBoat_%d" % i for i in range(1, 10)], "Sail number (1..9)")
    fb = sm("Prop_YTM_FinishBuoy", g, [K.lathe("Buoy", [(0.05, 0), (0.3, 0.12), (0.25, 0.4), (0.03, 0.55)], (0, 0, 0), 0, 12), K.cyl("Pole", "z", 0.02, 0.02, 0.6, (0, 0, 0.85), 1, 6), K.slab("Flag", [(0, 0), (0.25, 0), (0.25, 0.18), (0, 0.18)], 0.004, (0.02, 0, 1.0), 2, rot=(90, 0, 0))],
            [("buoy (G66 cloth yellow)", CLOTH4[2]), ("pole", TIMBER), ("finish flag (chequer MI)", "F0E8D8")], [K.socket("Anchor", (0, 0, 0)), K.socket("Line", (0.3, 0, 0.3))], "0.6 m finish buoy with flag")
    return [sb, fb]


def g489():
    g = "G489"; out = []
    for n in range(1, 4):
        a = "Prop_YTM_StoneCairn_%d" % n; r = K.rng(489 + n, a); P = []
        for i in range(3 + n):
            s = 0.5 - 0.06 * i; P.append(K.box("Stone%d" % i, (s, s * 0.85, 0.15), (r.uniform(-0.03, 0.03), r.uniform(-0.03, 0.03), 0.075 + 0.15 * i), 0, rot=(0, 0, r.uniform(0, 90))))
        h = 0.15 * (3 + n); P.append(K.box("Number", (0.12, 0.01, 0.1), (0, -0.2, 0.25), 1, bevel=False))
        m = sm(a, g, P, [("cairn stone", STONE), ("painted number (MI 0-9)", "F0E8D8")], [K.socket("Top", (0, 0, h)), K.socket("Number", (0, -0.21, 0.25))], "%.2f m numbered cairn (%d stones)" % (h, 3 + n), [K.ucx_box(a, 0, (0.5, 0.45, h), (0, 0, h / 2))])
        out.append(mi(m, ["MI_YTM_StoneCairn_%d" % i for i in range(10)], "Number (0..9)"))
        b = "Prop_YTM_ToppledStones_%d" % n; r2 = K.rng(4890 + n, b)
        out.append(sm(b, g, [K.box("Stone%d" % i, (0.5 - 0.06 * i, 0.4, 0.15), (r2.uniform(-0.5, 0.5), r2.uniform(-0.4, 0.4), 0.075), 0, rot=(r2.uniform(-10, 10), r2.uniform(-10, 10), r2.uniform(0, 180))) for i in range(3 + n)], [("cairn stone", STONE)], [K.socket("Restack", (0, 0, 0))], "toppled cairn %d (fallen state)" % n))
        out[-1]["spec"]["state"] = "Toppled (pair of %s)" % a
    return out


def g490():
    g = "G490"; out = []
    for n, s in (("Small", 0.15), ("Medium", 0.25), ("Tall", 0.2)):
        a = "Prop_YTM_WrappedGift_" + n; h = s * (1.6 if n == "Tall" else 0.8)
        out.append(mi(sm(a, g, [K.box("Box", (s, s, h), (0, 0, h / 2), 0), K.box("RibbonX", (s + 0.004, 0.025, h + 0.004), (0, 0, h / 2), 1, bevel=False), K.box("RibbonY", (0.025, s + 0.004, h + 0.004), (0, 0, h / 2), 1, bevel=False), K.box("Bow", (0.06, 0.04, 0.03), (0, 0, h + 0.015), 1)],
                            [("leaf/cloth wrap (G66 cloth)", CLOTH4[1]), ("ribbon (G66 cloth)", CLOTH4[0])], [hand(h / 2), K.socket("Tag", (0, -s / 2 - 0.003, h * 0.6))], "%.2f m wrapped gift" % s), ["MI_YTM_WrappedGift_%s" % c for c in ("Red", "Blue", "Green", "Yellow")], "Wrap tint"))
    out.append(basket("Prop_YTM_GiftBasket", g, 0.25, 0.22, True, note="woven gift basket"))
    return out


def g492():
    g = "G492"; out = [basket("Prop_YTM_WickerBasket_%s" % n, g, r, h, True, note="wicker apple basket %s" % n.lower(), fill=("apples", RED) if n == "Full" else None) for n, r, h in (("Empty", 0.22, 0.25), ("Full", 0.22, 0.25))]
    out.append(sm("Prop_YTM_RedApple", g, [K.lathe("Apple", [(0.01, 0), (0.035, 0.01), (0.04, 0.04), (0.03, 0.07), (0.01, 0.072)], (0, 0, 0), 0, 10), K.cyl("Stalk", "z", 0.003, 0.002, 0.02, (0, 0, 0.08), 1, 4)], [("red apple", RED, 0.4), ("stalk", BARK)], [hand(0.04)], "8 cm red apple"))
    return out


GAPS = {k: globals()["g" + k[1:]] for k in ASK}
STAGE = {}
for _l in open(os.path.join(HERE, "ytm_wave_d_stage.txt"), encoding="utf-8"):
    if "|" in _l: _g, _s = _l.strip().split("|"); STAGE[_g] = _s
# also staged in these folders (shared assets, built once elsewhere)
ALSO = {"G316": ["Prop_YTM_GrainSack"], "G351": ["Prop_YTM_RowBoat"], "G420": ["Prop_YTM_FireLogSeat"], "G434": ["Prop_YTM_SoupPot"], "G357": ["Prop_YTM_RopeCoil"], "G415": ["Prop_YTM_RopeCoil"], "G328": ["Prop_YTM_Fiddle"]}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--gap", required=True); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = GAPS[o.gap](); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
