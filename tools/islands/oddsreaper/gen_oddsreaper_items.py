# SPDX-License-Identifier: MIT
"""OddsReaper Island: 500 low-poly items, deterministic, headless.
blender -b --factory-startup -P gen_oddsreaper_items.py -- <out_dir> [limit]
Writes <out_dir>/<Name>.glb (metres; Unreal imports as cm x100) and manifest.json. Same seed -> same 500 items.
"""
import bpy, json, math, os, random, sys

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else os.path.join(os.getcwd(), "oddsreaper_glb")
LIMIT = int(argv[1]) if len(argv) > 1 else 10**9
os.makedirs(OUT, exist_ok=True)

PAL = {"bone": (0.88, 0.85, 0.76), "gold": (0.95, 0.72, 0.2), "green": (0.05, 0.45, 0.2), "felt": (0.04, 0.3, 0.15),
       "red": (0.7, 0.05, 0.06), "black": (0.04, 0.04, 0.05), "violet": (0.35, 0.12, 0.6), "storm": (0.25, 0.3, 0.42),
       "silver": (0.75, 0.77, 0.8), "copper": (0.72, 0.4, 0.22), "ivory": (0.95, 0.93, 0.86), "teal": (0.1, 0.55, 0.55),
       "burlap": (0.55, 0.42, 0.25), "stone": (0.38, 0.36, 0.38), "wood": (0.35, 0.22, 0.12), "cyan": (0.3, 0.85, 1.0)}
MATS = {}


def mat(name):
    if name not in MATS:
        m = bpy.data.materials.new("M_OR_" + name); m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*PAL[name], 1)
        b.inputs["Metallic"].default_value = 1.0 if name in ("gold", "silver", "copper") else 0.0
        b.inputs["Roughness"].default_value = 0.3 if name in ("gold", "silver", "copper", "cyan") else 0.7
        if name == "cyan":
            b.inputs["Emission Color"].default_value = (*PAL[name], 1); b.inputs["Emission Strength"].default_value = 4.0
        MATS[name] = m
    return MATS[name]


def clear():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()


def put(op, color, loc=(0, 0, 0), scale=(1, 1, 1), rot=(0, 0, 0), **kw):
    op(location=loc, rotation=rot, **kw)
    o = bpy.context.active_object; o.scale = scale; o.data.materials.append(mat(color)); return o


cube = lambda c, l, s, r=(0, 0, 0): put(bpy.ops.mesh.primitive_cube_add, c, l, s, r, size=1)
cyl = lambda c, l, s, v=12, r=(0, 0, 0): put(bpy.ops.mesh.primitive_cylinder_add, c, l, s, r, vertices=v, radius=0.5, depth=1)
ball = lambda c, l, s, n=1: put(bpy.ops.mesh.primitive_ico_sphere_add, c, l, s, subdivisions=n, radius=0.5)
cone = lambda c, l, s, v=8, r=(0, 0, 0): put(bpy.ops.mesh.primitive_cone_add, c, l, s, r, vertices=v, radius1=0.5, depth=1)


def skull(c, z, k):
    ball(c, (0, 0, z + 0.55 * k), (0.5 * k, 0.55 * k, 0.5 * k))
    cube(c, (0, -0.05 * k, z + 0.2 * k), (0.32 * k, 0.35 * k, 0.2 * k))
    for x in (-0.12, 0.12): ball("black", (x * k, -0.25 * k, z + 0.52 * k), (0.13 * k, 0.06 * k, 0.13 * k))


def moneybag(c, k):
    ball(c, (0, 0, 0.4 * k), (0.8 * k, 0.8 * k, 0.75 * k), 2); cone(c, (0, 0, 0.85 * k), (0.35 * k, 0.35 * k, 0.3 * k))
    cyl("gold", (0, 0, 0.75 * k), (0.32 * k, 0.32 * k, 0.05 * k)); cyl("gold", (0, -0.4 * k, 0.4 * k), (0.25 * k, 0.25 * k, 0.03 * k), 16, (math.pi / 2, 0, 0))


# ---- families: (prefix, count, builder(rng, i) -> description) ----
def f_chip(r, i):
    c = list(PAL)[i % 10]; cyl(c, (0, 0, 0.005), (0.04, 0.04, 0.008), 24); cyl("ivory", (0, 0, 0.0095), (0.026, 0.026, 0.001), 24)
    return f"{c} wager chip"
def f_die(r, i):
    s = 0.02 + 0.01 * (i % 4); c = ["ivory", "red", "black", "green", "violet", "gold", "bone", "teal"][i % 8]
    (cube if i % 3 else ball)(c, (0, 0, s / 2), (s, s, s)); return f"{c} die"
def f_coin(r, i):
    c = ["gold", "silver", "copper"][i % 3]; k = 0.02 + 0.006 * (i % 5)
    cyl(c, (0, 0, k / 8), (k, k, k / 4), 20); return f"{c} reaper coin"
def f_bag(r, i):
    moneybag(["burlap", "green", "black", "red", "violet"][i % 5], 0.3 + 0.08 * (i % 6)); return "money bag"
def f_skulltotem(r, i):
    h = 1.5 + 0.25 * (i % 8); cyl("stone", (0, 0, h / 2), (0.5, 0.5, h), 8)
    skull(["bone", "gold", "silver"][i % 3], h, 0.9); cyl("gold", (0, 0, h * 0.5), (0.56, 0.56, 0.12), 8)
    return "skull totem"
def f_oddsboard(r, i):
    w, h = 2 + (i % 4), 1.5 + 0.5 * (i % 3)
    for x in (-w / 2, w / 2): cube("wood", (x, 0, h / 2 + 0.5), (0.15, 0.15, h + 1))
    cube("black", (0, 0, h / 2 + 1), (w, 0.1, h))
    cols, rows = 3 + i % 3, 2 + i % 3
    for cx in range(cols):
        for ry in range(rows):
            cube(r.choice(["cyan", "gold", "red", "green"]), (-w / 2 + (cx + 0.5) * w / cols, -0.07, 1 + (ry + 0.5) * h / rows),
                 (w / cols * 0.7, 0.02, h / rows * 0.5))
    skull("bone", h + 1.5, 0.6); return "odds board"
def f_roulette(r, i):
    d = 1.2 + 0.3 * (i % 4); cyl("wood", (0, 0, 0.45), (d, d, 0.9), 24); cyl("felt", (0, 0, 0.92), (d * 0.9, d * 0.9, 0.05), 24)
    for k in range(12): cube("red" if k % 2 else "black", (math.cos(k * math.pi / 6) * d * 0.35, math.sin(k * math.pi / 6) * d * 0.35, 0.96),
                             (d * 0.12, d * 0.06, 0.02), (0, 0, k * math.pi / 6))
    cone("gold", (0, 0, 1.05), (0.12, 0.12, 0.2)); return "roulette wheel"
def f_pillar(r, i):
    h = 3 + i % 6; cyl("stone", (0, 0, h / 2), (0.7, 0.7, h), 8); cube("gold", (0, 0, h + 0.15), (0.9, 0.9, 0.3))
    if i % 2: skull("bone", h + 0.3, 0.6)
    return "casino pillar"
def f_cards(r, i):
    n = 3 + i % 12
    for k in range(n): cube(r.choice(["ivory", "red", "black"]), (r.uniform(-0.01, 0.01), r.uniform(-0.01, 0.01), 0.001 * k + 0.0005),
                             (0.063, 0.088, 0.0008), (0, 0, r.uniform(-0.2, 0.2)))
    return "card stack"
def f_lantern(r, i):
    h = 1.6 + 0.3 * (i % 4); cyl("black", (0, 0, h / 2), (0.08, 0.08, h), 6); cube("cyan" if i % 2 else "gold", (0, 0, h + 0.15), (0.25, 0.25, 0.3))
    cone("black", (0, 0, h + 0.38), (0.3, 0.3, 0.16), 4); return "storm lantern"
def f_crystal(r, i):
    for k in range(3 + i % 4): cone(["cyan", "violet", "teal"][k % 3], (r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), 0.4),
                                     (0.25, 0.25, r.uniform(0.6, 1.6)), 6, (r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), 0))
    return "oracle crystal"
HERBS = ["Luckroot", "Hedgeleaf", "Bluffmoss", "Longshot", "Parlayvine", "Stormbloom", "Vigweed", "Oddsthistle"]
HC = ["green", "teal", "violet", "gold", "red", "cyan", "copper", "silver"]
def f_herb(r, i):
    s, g = i % 8, i // 8 % 4; k = 0.15 + 0.12 * g
    for j in range(4 + g * 2):
        a = j * 2.4; cone("green", (math.cos(a) * k * 0.3, math.sin(a) * k * 0.3, k / 2), (k * 0.25, k * 0.08, k), 4, (0.3 * math.cos(a), 0.3 * math.sin(a), a))
    if g >= 2: ball(HC[s], (0, 0, k * 1.1), (k * 0.35, k * 0.35, k * 0.35))
    return f"{HERBS[s]} growth {g}"
def f_herbitem(r, i):
    ball(HC[i % 8], (0, 0, 0.05), (0.1, 0.1, 0.1)); cone("green", (0, 0, 0.12), (0.06, 0.02, 0.1), 4); return HERBS[i % 8] + " sprig"
def f_tonic(r, i):
    a, b = divmod(i, 8); cyl("ivory", (0, 0, 0.08), (0.08, 0.08, 0.16), 10); cyl(HC[a % 8], (0, 0, 0.06), (0.075, 0.075, 0.1), 10)
    ball(HC[b % 8], (0, 0, 0.18), (0.05, 0.05, 0.05)); skull("bone", 0.2, 0.06); return f"tonic {HERBS[a % 8]}+{HERBS[b % 8]}"
def f_goat(r, i):
    c = ["ivory", "black", "copper", "storm"][i % 4]; cube(c, (0, 0, 0.7), (0.9, 0.4, 0.45)); ball(c, (0.55, 0, 0.95), (0.3, 0.25, 0.28))
    for x in (-0.35, 0.35):
        for y in (-0.15, 0.15): cyl(c, (x, y, 0.25), (0.1, 0.1, 0.5), 6)
    for y in (-0.08, 0.08): cone("bone", (0.55, y, 1.15), (0.06, 0.06, 0.25), 6, (0, -0.6, 0))
    for k in range(5): cyl("gold", (-0.3 + k * 0.15, 0, 0.94), (0.1, 0.1, 0.02), 12)  # coin-scale back ridge
    return "Coinback goat"
def f_hen(r, i):
    c = ["ivory", "black", "red", "copper"][i % 4]; ball(c, (0, 0, 0.25), (0.35, 0.25, 0.28)); ball(c, (0.15, 0, 0.45), (0.15, 0.13, 0.15))
    cube("ivory", (0.25, 0, 0.45), (0.06, 0.06, 0.06)); cube("gold", (0.15, 0, 0.55), (0.05, 0.02, 0.06))
    for y in (-0.06, 0.06): cyl("gold", (0, y, 0.06), (0.03, 0.03, 0.12), 4)
    return "Dicebeak hen"
def f_dicerock(r, i):
    s = 1 + r.uniform(0, 3)
    for k in range(1 + i % 4): cube("stone", (r.uniform(-s, s) * 0.4, r.uniform(-s, s) * 0.4, s * 0.4 * (k + 0.5)), (s, s, s) if k == 0 else (s * 0.6,) * 3,
                                    (r.uniform(0, 1), r.uniform(0, 1), r.uniform(0, 1)))
    return "dice-stone rock"
def f_tree(r, i):
    h = 2 + i % 6; cyl("wood", (0, 0, h / 2), (0.3, 0.3, h), 6)
    for k in range(3): cone("green" if i % 3 else "violet", (0, 0, h * 0.6 + k * 0.8), (2.2 - k * 0.5, 2.2 - k * 0.5, 1.4), 7)
    for k in range(i % 5): cyl("gold", (r.uniform(-0.8, 0.8), r.uniform(-0.8, 0.8), h * 0.6 + r.uniform(0, 1.5)), (0.15, 0.15, 0.02), 10, (math.pi / 2, 0, 0))
    return "ledger tree (coin fruit)"
def f_arch(r, i):
    w, h = 3 + i % 4, 4 + i % 3
    for x in (-w / 2, w / 2): cube("stone", (x, 0, h / 2), (0.6, 0.6, h))
    cube("stone", (0, 0, h + 0.3), (w + 0.8, 0.7, 0.6)); skull("gold" if i % 2 else "bone", h + 0.6, 0.8); return "skull arch"
def f_table(r, i):
    w = 1.5 + 0.3 * (i % 4); cube("felt", (0, 0, 0.85), (w, w * 0.6, 0.08)); cube("wood", (0, 0, 0.8), (w + 0.1, w * 0.6 + 0.1, 0.06))
    for x in (-1, 1):
        for y in (-1, 1): cyl("wood", (x * w * 0.42, y * w * 0.25, 0.4), (0.08, 0.08, 0.8), 6)
    return "felt table"
def f_food(r, i):
    kinds = [("egg", "ivory", ball, (0.05, 0.05, 0.065)), ("cheese", "gold", cube, (0.1, 0.08, 0.06)), ("milk", "ivory", cyl, (0.08, 0.08, 0.15)),
             ("coinfruit", "gold", ball, (0.09, 0.09, 0.09)), ("bread", "copper", ball, (0.18, 0.1, 0.08))]
    n, c, f, s = kinds[i % 5]; f(c, (0, 0, s[2] / 2), s); return n
def f_shard(r, i):
    cone("cyan", (0, 0, 1), (0.6, 0.6, 2 + i % 3), 5); cone("storm", (0, 0, -0.5), (0.6, 0.6, 1), 5, (math.pi, 0, 0)); return "storm shard"
def f_sigil(r, i):
    skull("bone", 0, 1.0 + 0.2 * (i % 4)); bpy.context.view_layer.objects.active = None
    moneybag("gold" if i % 2 else "green", 0.5); return "skull + money bag sigil"
def f_core(r, i):  # island landmass, 2x planned size
    s = 250 + 10 * i; cyl("stone", (0, 0, -s * 0.08), (s, s, s * 0.16), 16); cone("stone", (0, 0, -s * 0.31), (s, s, s * 0.3), 16, (math.pi, 0, 0))
    cyl("felt", (0, 0, 0.05), (s * 0.95, s * 0.95, 0.4), 16); return "island core"

FAMILIES = [("Item_OR_Chip", 50, f_chip), ("Item_OR_Die", 40, f_die), ("Item_OR_Coin", 30, f_coin), ("Item_OR_MoneyBag", 30, f_bag),
            ("Prop_OR_SkullTotem", 16, f_skulltotem), ("Prop_OR_OddsBoard", 24, f_oddsboard), ("Prop_OR_Roulette", 8, f_roulette),
            ("Bld_OR_Pillar", 16, f_pillar), ("Item_OR_Cards", 20, f_cards), ("Prop_OR_Lantern", 16, f_lantern),
            ("Prop_OR_Crystal", 24, f_crystal), ("Prop_OR_Herb", 32, f_herb), ("Item_OR_Herb", 8, f_herbitem), ("Item_OR_Tonic", 64, f_tonic),
            ("Mob_OR_CoinbackGoat", 4, f_goat), ("Mob_OR_DicebeakHen", 4, f_hen), ("Prop_OR_DiceRock", 40, f_dicerock),
            ("Prop_OR_LedgerTree", 24, f_tree), ("Bld_OR_SkullArch", 12, f_arch), ("Prop_OR_FeltTable", 8, f_table),
            ("Item_OR_Food", 10, f_food), ("Sky_OR_StormShard", 12, f_shard), ("Prop_OR_Sigil", 6, f_sigil), ("Bld_OR_IslandCore", 2, f_core)]
assert sum(n for _, n, _ in FAMILIES) == 500, sum(n for _, n, _ in FAMILIES)

manifest = []
for prefix, n, build in FAMILIES:
    for i in range(n):
        if len(manifest) >= LIMIT: break
        name = f"{prefix}_{i:02d}"; r = random.Random(f"oddsreaper:{name}")
        clear(); desc = build(r, i)
        objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        if len(objs) > 1: bpy.ops.object.join()
        o = bpy.context.active_object; o.name = name
        tris = sum(len(p.vertices) - 2 for p in o.data.polygons)
        dims = [round(d, 3) for d in o.dimensions]
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".glb"), export_format="GLB", use_selection=True, export_apply=True)
        manifest.append({"name": name, "desc": desc, "tris": tris, "size_m": dims})
json.dump({"island": "OddsReaper", "count": len(manifest), "items": manifest}, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
print(f"ODDSREAPER_ITEMS {len(manifest)} -> {OUT}")
