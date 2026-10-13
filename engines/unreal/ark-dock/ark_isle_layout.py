# SPDX-License-Identifier: MIT
"""Ark Dock Isle (2Hot2Trot, Team Grok) layout: pure Python, no unreal import, so it is testable offline.
layout(radius_m) -> list of placements {pack, kind, x, y (m, island-local, centre 0,0), yaw, h (target height m), zone, tags}
All meshes are SHIPPED art under /Game/Daedalus/Art/<kind>/<pack>. Deterministic (seeded), so reruns match."""
import math, random

HERBS = ["Prop_Herb_Mint", "Prop_Herb_Chamomile", "Prop_Herb_Ginger", "Prop_Herb_Lavender", "Prop_Herb_Sage",
         "Prop_Herb_Basil", "Prop_Herb_Rosemary", "Prop_Herb_Nettle", "Prop_Herb_Aloe", "Prop_Herb_Angelica",
         "Prop_Herb_Moonpetal", "Prop_Herb_Lemongrass", "Prop_Herb_Clover", "Prop_Herb_Dandelion", "Prop_Herb_Marshmallow"]
FLOWERS = ["Prop_Flower_Bluebell", "Prop_Flower_Poppy", "Prop_Flower_Foxglove", "Prop_Flower_Gentian", "Prop_Flower_Orchid",
           "Prop_Flower_Sunflower", "Prop_Bloom_Cornflower", "Prop_Flower_Edelweiss"]
ROCKS = ["Prop_ForgeLavaRock_Basalt", "Prop_ForgeLavaRock_Stone", "Prop_ForgeLavaRock_Iron", "Prop_ForgeLavaRock_Obsidian"]
POND = ["Prop_Aqua_Cattail", "Prop_Aqua_WaterLily", "Prop_Flower_Lotus", "Prop_Flower_WaterLily"]
LIVESTOCK = {"cattle": ["Mob_Cow"], "sheep_goats": ["Mob_Sheep", "Mob_Goat", "Mob_PygmyGoat"],
             "poultry": ["Mob_Chicken", "Mob_Duck"], "pigs": ["Mob_Pig"], "stable": ["Mob_Horse", "Mob_Horse_Pony"]}
MOB_H = {"Mob_Cow": 1.5, "Mob_Sheep": 1.0, "Mob_Goat": 1.0, "Mob_PygmyGoat": 0.7, "Mob_Chicken": 0.45, "Mob_Duck": 0.45,
         "Mob_Pig": 0.9, "Mob_Horse": 1.7, "Mob_Horse_Pony": 1.3}

def _p(out, pack, kind, x, y, h, zone, yaw=0.0, tags=()):
    out.append(dict(pack=pack, kind=kind, x=round(x, 2), y=round(y, 2), yaw=round(yaw, 1), h=h, zone=zone, tags=list(tags)))

def layout(R=120.0, seed=2026):
    rnd = random.Random(seed); out = []
    # zones (island-local metres). Dock faces +X; pond west; pens north; herb gardens south; town centre.
    POND_C, POND_R = (-55.0, 0.0), 18.0
    # 1) herb gardens: 15 herbs x 14 = 210, in rows south
    for i, herb in enumerate(HERBS):
        bx, by = -60 + (i % 5) * 24, -40 - (i // 5) * 16
        for k in range(14):
            _p(out, herb, "Prop", bx + (k % 7) * 2.2 + rnd.uniform(-.3, .3), by + (k // 7) * 2.5, 0.6 * rnd.uniform(.8, 1.2),
               "herb_garden", rnd.uniform(0, 360), ["Herb", "Harvest_" + herb.replace("Prop_Herb_", "")])
    # 2) wildflower meadow ring: 96
    for k in range(96):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(.55, .85) * R
        x, y = r * math.cos(a), r * math.sin(a)
        if x > 40 and abs(y) < 25: continue   # keep dock approach clear
        _p(out, rnd.choice(FLOWERS), "Prop", x, y, 0.5 * rnd.uniform(.7, 1.3), "meadow", rnd.uniform(0, 360))
    # 3) shoreline rocks: 90 around the rim (gap at the dock)
    for k in range(90):
        a = 2 * math.pi * k / 90 + rnd.uniform(-.02, .02)
        if math.cos(a) > .97: continue
        r = R * rnd.uniform(.93, .99)
        _p(out, rnd.choice(ROCKS), "Prop", r * math.cos(a), r * math.sin(a), rnd.uniform(1.0, 3.0), "shoreline", rnd.uniform(0, 360), ["Shoreline"])
    # 4) pond edge plants: 56 (cattails on rim, lilies on water)
    for k in range(56):
        a = 2 * math.pi * k / 56
        if k % 2:
            r = POND_R * rnd.uniform(1.0, 1.15); pack = "Prop_Aqua_Cattail"; h = 1.4
        else:
            r = POND_R * rnd.uniform(.3, .85); pack = rnd.choice(POND[1:]); h = 0.3
        _p(out, pack, "Prop", POND_C[0] + r * math.cos(a), POND_C[1] + r * math.sin(a), h, "pond", rnd.uniform(0, 360), ["Pond"])
    # 5) livestock pens north: 5 pens, fences + trough + animals
    pens = []
    for i, (pen, mobs) in enumerate(LIVESTOCK.items()):
        cx, cy, half = -50 + i * 25, 55, 9.0
        pens.append((pen, cx, cy, half))
        for side in range(4):
            for j in range(5):
                t = -half + (j + .5) * (2 * half / 5)
                x, y, yaw = [(cx + t, cy - half, 0), (cx + half, cy + t, 90), (cx + t, cy + half, 0), (cx - half, cy + t, 90)][side]
                pack = "Prop_Fence_Gate" if side == 0 and j == 2 else "Prop_Fence"
                _p(out, pack, "Prop", x, y, 1.1, "pen_" + pen, yaw, ["Pen_" + pen])
        _p(out, "Prop_Barrel", "Prop", cx + half - 1.5, cy + half - 1.5, 0.9, "pen_" + pen, 0, ["Trough", "Pen_" + pen])
        for k in range(6):
            m = mobs[k % len(mobs)]
            _p(out, m, "Mob", cx + rnd.uniform(-half + 2, half - 2), cy + rnd.uniform(-half + 2, half - 2), MOB_H.get(m, 1.0),
               "pen_" + pen, rnd.uniform(0, 360), ["Livestock", "Pen_" + pen, "Species_" + m[4:]])
    # 6) village / ark camp centre: lanterns, crates, stalls
    camp = [("Prop_Town_Lamppost", 3.5), ("Prop_Town_CrateStack", 1.6), ("Prop_Town_Barrel", 1.0), ("Prop_Town_MarketStall", 3.0),
            ("Prop_Lantern", 0.6), ("Prop_Crate", 0.9), ("Prop_Town_Bench", 0.9)]
    for k in range(28):
        a = 2 * math.pi * k / 28; r = 14 + (k % 3) * 4
        pk, h = camp[k % len(camp)]
        _p(out, pk, "Prop", 5 + r * math.cos(a), r * math.sin(a), h, "camp", math.degrees(a) + 180)
    # 7) trees on the shoulder: 30 moonbark
    for k in range(30):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(.35, .8) * R
        x, y = r * math.cos(a), r * math.sin(a)
        if (x > 30 and abs(y) < 30) or math.hypot(x - POND_C[0], y - POND_C[1]) < POND_R + 6 or (y > 40 and abs(x + 0) < 70): continue
        _p(out, rnd.choice(["Prop_Tree_Moonbark_Mature", "Prop_Tree_Moonbark_Young"]), "Prop", x, y, rnd.uniform(6, 12), "grove", rnd.uniform(0, 360))
    meta = dict(radius_m=R, pond=dict(c=POND_C, r=POND_R), pens=pens, dock_dir_deg=0.0)
    return out, meta

if __name__ == "__main__":
    import collections
    pl, meta = layout()
    print(len(pl), collections.Counter(p["zone"].split("_")[0] for p in pl))
