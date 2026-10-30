# SPDX-License-Identifier: MIT
"""Prismheart arcade batch e: 10 reviewed iterations on batch d (blender-team, 2026-10-30, Richey "iterate 10 times" via buffffff 58915).
Every change is a NEW suffixed asset; batch d originals are untouched. Sockets keep the batch d names and positions (same sidecar shape).
  it1  Prop_Arcade_CeilingLightRig_C_v2   true hexagon: edges on the apothem at side length, corner hub blocks, cans under the hubs
                                          (d: arcs on the wrong radius left corner gaps and cans off the truss)
  it2  Prop_Arcade_CeilingLightRig_A_v2 / _B_v2 / _C_v3   light hotspots read in renders: wider lens + emissive colour band on each can
  it3  Prop_Arcade_Cab_DancePad_v2        thick raised arrows (2 cm, 2.2x larger), P1 magenta / P2 cyan, chrome frame per player stage
  it4  Prop_Arcade_Cab_Pinball_v2         chrome side rails, lockdown bar, coin door on the front
  it5  Prop_Arcade_Plush_Pebblepup_v2     paws tucked under the body (d: paws floated in front)
  it6  Prop_Arcade_Plush_Lumenfish_v2     pectoral fins swept back against the body (d: flat planks sticking out)
  it7  Prop_Arcade_HighScoreBoard_v2      marquee bulb border on the panel face (5 cm bulbs, proud of the face)
  it8  Prop_Arcade_TicketCounter_v2       ticket ribbon from ReceiptOut + beacon on the hood
  it9  Prop_Arcade_PhotoBooth_v2          bulb row across the header sign + flash panel
  it10 Prop_Arcade_Cab_DancePad_v3        v2 + emissive stage edge strip and front step nosing
Usage: python arcade_prism_props_e.py --kit data/contest/arcade_prism_e.kit.json"""
import argparse, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arcade_prism_props_b as AB
import arcade_prism_props_c as AC
import arcade_prism_props_d as AD
K, A = AB.K, AB.A
CAB, CHROME, PRISM, GOLD, BLACK = AB.CAB, AB.CHROME, AB.PRISM, AB.GOLD, AB.BLACK
ball, GLASSC, SCREEN = AC.ball, AC.GLASSC, AD.SCREEN
MAG, CYAN, BULB = "FF4AD0", "6AE8FF", "FFF0B0"


def _rename(m, new):
    """Asset copy under a new name: object, sockets' parents, UCX names."""
    old = m["asset"]
    def fix(v):
        if isinstance(v, str): return v.replace(old, new) if v.startswith(old) or v.startswith("UCX_" + old) or v.startswith("MI_" + old) or v.startswith("M_" + old) else v
        if isinstance(v, list): return [fix(x) for x in v]
        if isinstance(v, dict): return {k: fix(x) for k, x in v.items()}
        return v
    return fix(m)


def can(name, c, slot_body, slot_lens, hot):
    x, y, z = c
    P = [K.cyl(name + "Yoke", "z", 0.015, 0.015, 0.12, (x, y, z - 0.06), slot_body, 6), K.cyl(name, "z", 0.06, 0.08, 0.2, (x, y, z - 0.22), slot_body, 10)]
    if hot:   # it2: lens wider than the can mouth + a lit colour band that reads from any angle
        P += [K.cyl(name + "Lens", "z", 0.088, 0.088, 0.012, (x, y, z - 0.326), slot_lens, 12), K.cyl(name + "Band", "z", 0.074, 0.076, 0.035, (x, y, z - 0.2), slot_lens, 10)]
    else:
        P.append(K.cyl(name + "Lens", "z", 0.072, 0.072, 0.01, (x, y, z - 0.325), slot_lens, 10))
    return P


def light_rig(v, name, hot, hexfix):
    P = []; S = []; zt = -0.6
    if v == "A":
        P.append(K.box("Truss", (3.0, 0.2, 0.2), (0, 0, zt), 0)); pts = [(-1.2 + 0.8 * i, 0) for i in range(4)]; hangs = [(-1.3, 0), (1.3, 0)]
        P += [K.box("Lace%d" % i, (0.02, 0.21, 0.21), (-1.4 + 0.2 * i, 0, zt), 0, rot=(45, 0, 0), bevel=False) for i in range(15)]
    elif v == "B":
        P += [K.box("TrussX", (2.4, 0.2, 0.2), (0, 0, zt), 0), K.box("TrussY", (0.2, 2.4, 0.2), (0, 0, zt), 0)]; pts = [(1.0, 0), (-1.0, 0), (0, 1.0), (0, -1.0)]; hangs = [(0.6, 0.0), (-0.6, 0.0), (0, 0.6), (0, -0.6)]
    else:
        R = 1.2
        if hexfix:   # it1: edge k joins vertex k and k+1: centre on the apothem, length = side; hubs close the corners
            ap = R * math.cos(math.pi / 6)
            for i in range(6):
                an = i * math.pi / 3 + math.pi / 6
                P.append(K.box("Arc%d" % i, (0.2, R - 0.1, 0.2), (ap * math.cos(an), ap * math.sin(an), zt), 0, rot=(0, 0, math.degrees(an))))
                vx, vy = R * math.cos(i * math.pi / 3), R * math.sin(i * math.pi / 3)
                P.append(K.box("Hub%d" % i, (0.26, 0.26, 0.24), (vx, vy, zt), 0, rot=(0, 0, math.degrees(i * math.pi / 3))))
        else:
            P += [K.box("Arc%d" % i, (0.2, 1.3, 0.2), (1.2 * math.cos(i * math.pi / 3 + math.pi / 6) * 0.98, 1.2 * math.sin(i * math.pi / 3 + math.pi / 6) * 0.98, zt), 0, rot=(0, 0, math.degrees(i * math.pi / 3 + math.pi / 6))) for i in range(6)]
        pts = [(R * math.cos(i * math.pi / 3), R * math.sin(i * math.pi / 3)) for i in range(6)]; hangs = pts[::2]
    for i, (x, y) in enumerate(hangs):
        P.append(K.cyl("Cable%d" % i, "z", 0.006, 0.006, -zt - 0.1, (x, y, zt / 2 + 0.05), 1, 4)); P.append(K.cyl("Plate%d" % i, "z", 0.06, 0.06, 0.02, (x, y, -0.01), 1, 8)); S.append(K.socket("Hang_%d" % i, (x, y, 0)))
    dz = 0.12 if (v == "C" and hexfix) else 0.1   # under the 0.24 m hub instead of the 0.2 m truss
    for i, (x, y) in enumerate(pts):
        P += can("Can%d" % i, (x, y, zt - dz), 1, 2 + i % 2, hot); S.append(K.socket("Light_%d" % i, (x, y, zt - dz - 0.23), forward=(0, 0, -1)))
    return A(name, P, [("truss (chrome)", CHROME, 0.35, 0.9), ("cans / cables (black)", BLACK, 0.5, 0.6), ("lens magenta (emissive)", MAG, 0.2, 0.0, True), ("lens cyan (emissive)", CYAN, 0.2, 0.0, True)],
             S, [], "ceiling light rig %s; origin = ceiling plane, hangs %.2f m" % (v, 0.95 + (0.02 if dz > 0.1 else 0)))


ARROW = [(0, 0.09), (0.07, 0), (0.03, 0), (0.03, -0.08), (-0.03, -0.08), (-0.03, 0), (-0.07, 0)]


def dance_pad(name, v3):
    P = []; S = []
    P += [K.box("Tower", (1.6, 0.6, 2.2), (0, 0.9, 1.1), 0), K.box("Screen", (1.0, 0.03, 0.62), (0, 0.585, 1.6), 3, bevel=False), K.box("Marquee", (1.6, 0.4, 0.35), (0, 0.8, 2.37), 2)]
    P += [K.cyl("Speaker%d" % s, "y", 0.16, 0.16, 0.04, (s * 0.62, 0.585, 1.6), 4, 12) for s in (-1, 1)]
    P += [K.box("Stage", (2.4, 1.2, 0.18), (0, -0.1, 0.09), 1), K.box("RailBack", (2.4, 0.05, 0.05), (0, 0.45, 1.0), 1)] + [K.cyl("RailPost%d" % s, "z", 0.025, 0.025, 0.82, (s * 1.15, 0.45, 0.59), 1, 8) for s in (-1, 1)]
    sc = 2.2
    for p, px in (("P1", -0.6), ("P2", 0.6)):
        slot = 6 if p == "P1" else 7
        for nm, (dx, dy) in (("Up", (0, 0.32)), ("Down", (0, -0.32)), ("Left", (-0.32, 0)), ("Right", (0.32, 0))):
            c = (px + dx, -0.1 + dy, 0.185); P.append(K.box("Pad%s%s" % (p, nm), (0.28, 0.28, 0.012), c, 5, bevel=False))
            P.append(K.slab("Arrow%s%s" % (p, nm), [(x * sc, y * sc) for x, y in ARROW], 0.02, (c[0], c[1] - (0.0), 0.201), slot,
                            rot=(0, 0, {"Up": 0, "Down": 180, "Left": 90, "Right": -90}[nm]))); S.append(K.socket("Pad_%s_%s" % (p, nm), (c[0], c[1], 0.196)))
        for k, (sx, sy, cx, cy) in enumerate(((0.98, 0.03, px, -0.1 + 0.48), (0.98, 0.03, px, -0.1 - 0.48), (0.03, 0.98, px - 0.48, -0.1), (0.03, 0.98, px + 0.48, -0.1))):
            P.append(K.box("Frame%s%d" % (p, k), (sx, sy, 0.02), (cx, cy, 0.19), 1, bevel=False))
        S.append(K.socket("Player%s" % p[1], (px, -0.1, 0.18)))
    if v3:   # it10: lit stage edge + front step nosing
        P += [K.box("EdgeFront", (2.4, 0.03, 0.04), (0, -0.715, 0.12), 6, bevel=False), K.box("EdgeL", (0.03, 1.2, 0.04), (-1.215, -0.1, 0.12), 7, bevel=False),
              K.box("EdgeR", (0.03, 1.2, 0.04), (1.215, -0.1, 0.12), 7, bevel=False), K.box("Nosing", (2.4, 0.06, 0.02), (0, -0.7, 0.19), 1)]
    S += [K.socket("Screen", (0, 0.57, 1.6)), K.socket("CoinSlot", (0.5, 0.59, 0.9))]
    return A(name, P, [("cab body", CAB, 0.5), ("stage / rails (chrome)", CHROME, 0.3, 0.9), ("marquee (emissive)", PRISM, 0.4, 0.0, True), ("screen", SCREEN, 0.1), ("speakers", BLACK, 0.5),
                       ("pad panels (pressed = MI param)", "D0D8F0", 0.3), ("P1 arrows (emissive)", MAG, 0.3, 0.0, True), ("P2 arrows (emissive)", CYAN, 0.3, 0.0, True)],
             S, [K.ucx_box(name, 0, (1.6, 0.6, 2.55), (0, 0.9, 1.27)), K.ucx_box(name, 1, (2.4, 1.2, 0.18), (0, -0.1, 0.09))], "2.4 x 1.8 x 2.55 m dance cab, 2 players, 8 arrow pads")


def pinball_v2():
    m = AD.pinball(); a = "Prop_Arcade_Cab_Pinball_v2"; m = _rename(m, a)
    L, W, tilt = 1.3, 0.7, 6.5; zf, zb = 0.82, 0.82 + L * math.tan(math.radians(tilt)); zm = (zf + zb) / 2
    P = m["objects"][0]["parts"]
    P += [K.box("Rail%d" % s, (0.035, L, 0.035), (s * (W / 2 - 0.0175), 0, zm + 0.165), 1, rot=(tilt, 0, 0)) for s in (-1, 1)]
    P += [K.box("Lockdown", (W, 0.07, 0.035), (0, -L / 2 + 0.035, zf + 0.165), 1), K.box("CoinDoor", (0.26, 0.015, 0.16), (0, -L / 2 - 0.008, zf - 0.03), 1),
          K.box("CoinSlotL", (0.02, 0.006, 0.05), (-0.05, -L / 2 - 0.018, zf - 0.0), 0, bevel=False), K.box("CoinSlotR", (0.02, 0.006, 0.05), (0.05, -L / 2 - 0.018, zf - 0.0), 0, bevel=False)]
    return K.finish(m)


def plush(kind):
    if kind == "Pebblepup":
        a = "Prop_Arcade_Plush_Pebblepup_v2"
        P = [ball("Body", (0, 0.02, 0.1), 0.1, 0), ball("Head", (0, -0.09, 0.18), 0.08, 0), ball("Snout", (0, -0.16, 0.16), 0.035, 1, 6), ball("Nose", (0, -0.19, 0.17), 0.012, 3, 6),
             ball("EyeL", (0.035, -0.155, 0.21), 0.014, 3, 6), ball("EyeR", (-0.035, -0.155, 0.21), 0.014, 3, 6), K.cyl("Collar", "z", 0.07, 0.07, 0.02, (0, -0.06, 0.13), 2, 10), ball("Gem", (0, -0.13, 0.12), 0.015, 2, 6)]
        P += [K.box("Ear%d" % s, (0.03, 0.05, 0.08), (s * 0.075, -0.08, 0.2), 1, rot=(0, s * 25, 0)) for s in (-1, 1)]
        P += [ball("Paw%d" % i, (0.055 * (1 if i % 2 else -1), 0.02 + 0.055 * (1 if i > 1 else -1), 0.028), 0.03, 0, 6) for i in range(4)]   # it5: under the body
        P.append(K.cyl("Tail", "y", 0.02, 0.01, 0.06, (0, 0.13, 0.12), 1, 6, rot=(-30, 0, 0)))
        mats = [("plush pebble grey", "A8A0B8", 0.95), ("plush ears / snout", "D8C8E8", 0.95), ("prism gem collar", PRISM, 0.5), ("eyes / nose", BLACK, 0.4)]
    else:
        a = "Prop_Arcade_Plush_Lumenfish_v2"
        P = [ball("Body", (0, 0, 0.12), 0.11, 0), K.slab("Tail", [(0, 0), (0.08, 0.07), (0.1, 0.0), (0.08, -0.07)], 0.025, (0, 0.1, 0.12), 1, rot=(0, -90, 90)),
             K.slab("FinTop", [(0, 0), (0.05, 0.07), (0.09, 0)], 0.02, (0, -0.03, 0.21), 1, rot=(90, 0, 90)), ball("Lure", (0, -0.12, 0.27), 0.022, 2, 6), K.cyl("Stalk", "z", 0.005, 0.005, 0.07, (0, -0.1, 0.235), 1, 4, rot=(-25, 0, 0)),
             ball("EyeL", (0.05, -0.09, 0.15), 0.02, 3, 6), ball("EyeR", (-0.05, -0.09, 0.15), 0.02, 3, 6)]
        # it6: pectoral fins hug the flank, swept back (+Y) and tilted down, instead of flat planks
        P += [K.slab("Side%d" % s, [(0, -0.01), (0.02, 0.06), (-0.025, 0.055)], 0.015, (s * 0.118, 0.0, 0.11), 1, rot=(0, s * 60, 0)) for s in (-1, 1)]
        mats = [("plush teal", "4AC8C0", 0.95), ("fins coral", "F08A6A", 0.95), ("glow lure (emissive)", "FFF0A0", 0.4, 0.0, True), ("eyes", BLACK, 0.4)]
    return A(a, P, mats, [K.socket("Shelf", (0, 0, 0)), K.socket("Hand", (0, 0, 0.12)), K.socket("Grab", (0, 0, 0.22))], [], "~25 cm plush prize")


def _add(m, new, parts, mats=()):
    m = _rename(m, new); m["objects"][0]["parts"] += parts
    for i, mt in enumerate(mats): m["materials"].append(K.material(new, len(m["materials"]), *mt))
    return K.finish(m)


def high_score_v2():
    m = AD.high_score_board(); W, H, z0 = 1.6, 2.0, 0.8; slot = len(m["materials"]); P = []; k = 0; yb, r = -0.06, 0.026   # bulbs proud of the 4 cm panel face
    xs = [-W / 2 + 0.02 + i * (W - 0.04) / 10 for i in range(11)]; zs = [z0 + 0.02 + i * (H - 0.04) / 12 for i in range(13)]
    for x in xs: P += [K.cyl("BulbT%d" % k, "y", r, r, 0.03, (x, yb, z0 + H - 0.02), slot, 6), K.cyl("BulbB%d" % k, "y", r, r, 0.03, (x, yb, z0 + 0.02), slot, 6)]; k += 1
    for z in zs[1:-1]: P += [K.cyl("BulbL%d" % k, "y", r, r, 0.03, (-W / 2 + 0.02, yb, z), slot, 6), K.cyl("BulbR%d" % k, "y", r, r, 0.03, (W / 2 - 0.02, yb, z), slot, 6)]; k += 1
    return _add(m, "Prop_Arcade_HighScoreBoard_v2", P, [("marquee bulbs (emissive, chase = MI)", BULB, 0.3, 0.0, True)])


def ticket_v2():
    m = AD.ticket_counter(); slot = len(m["materials"]); P = []
    for i in range(6):   # folded ticket ribbon hanging from the printer mouth
        P.append(K.box("Ticket%d" % i, (0.05, 0.004, 0.07), (0.18, -0.30 - (0.008 if i % 2 else 0), 0.71 - 0.068 * i), slot, rot=(12 if i % 2 else -12, 0, 0), bevel=False))
    P += [K.cyl("BeaconBase", "z", 0.05, 0.05, 0.02, (0, 0.08, 1.455), 1, 10), K.cyl("Beacon", "z", 0.04, 0.03, 0.07, (0, 0.08, 1.5), slot + 1, 10)]
    return _add(m, "Prop_Arcade_TicketCounter_v2", P, [("tickets", "F2A23A", 0.8), ("beacon (emissive)", "FF6A3A", 0.3, 0.0, True)])


def photo_v2():
    m = AD.photo_booth(); W, D, H = 1.4, 1.0, 2.1; slot = len(m["materials"])
    P = [K.cyl("HdrBulb%d" % i, "y", 0.032, 0.032, 0.03, (-0.6 + 0.12 * i, -D / 2 - 0.015, H - 0.175), slot, 8) for i in range(11)]
    P += [K.box("Flash", (0.18, 0.02, 0.12), (W / 2 - 0.05, -D / 2 - 0.004, H - 0.6), slot, bevel=False), K.box("FlashRim", (0.22, 0.015, 0.16), (W / 2 - 0.05, -D / 2 + 0.006, H - 0.6), 1)]
    return _add(m, "Prop_Arcade_PhotoBooth_v2", P, [("header bulbs / flash (emissive)", BULB, 0.3, 0.0, True)])


def assets():
    return [light_rig("C", "Prop_Arcade_CeilingLightRig_C_v2", False, True),
            light_rig("A", "Prop_Arcade_CeilingLightRig_A_v2", True, False), light_rig("B", "Prop_Arcade_CeilingLightRig_B_v2", True, False), light_rig("C", "Prop_Arcade_CeilingLightRig_C_v3", True, True),
            dance_pad("Prop_Arcade_Cab_DancePad_v2", False), pinball_v2(), plush("Pebblepup"), plush("Lumenfish"), high_score_v2(), ticket_v2(), photo_v2(),
            dance_pad("Prop_Arcade_Cab_DancePad_v3", True)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--kit", required=True); o = ap.parse_args()
    M_ = assets(); K.write(M_, o.kit)
    for m in M_: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["dimensions"])
