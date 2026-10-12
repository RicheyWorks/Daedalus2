# SPDX-License-Identifier: MIT
"""Claude Island, The Orrery Reach (island contest, 2026-10-12): 500 original items, built headless in Blender.

    blender --background --factory-startup --python orr_build.py -- <art folder> [--only N] [--rows]

Every item is its own .blend at <art>/<Kind>/<Asset>.blend, holding one collection named after the asset, with low
poly, at most 3 materials, and the bottom at z = 0 and the front toward +Y (the art queue's rules, BRIEF.md). With
--rows, a READY row for each item is appended to <art>/QUEUE.md (skipping names already there), so the queue watcher
ships them. Names all carry the realm tag "Orr". The whole set is original: no names or designs from other games.

The catalogue is a list of (asset, kind, builder, params). Builders put together a few primitives; a per-name random
stream varies the proportions, so no two items share a shape.
"""
import hashlib
import math
import os
import random
import sys

import bpy
import bmesh

# --------------------------------------------------------------------------------------------- the catalogue

HERBS = ["Dawnthistle", "Noonspire", "Duskmallow", "Midnightmint", "Cometcress", "Moonvetch", "Starsedge",
         "Nebulawort", "Eclipsebell", "Auroraleaf", "Polarisroot", "Meteorsage", "Orbitfern", "Solsticerue",
         "Equinoxbalm", "Zenithclover", "Nadirmoss", "Twilightsorrel", "Galaxygrass", "Quasarthyme",
         "Lunarlily", "Sunsprig", "Driftfennel", "Heartstonebloom"]
STAGES = ["Sprout", "Bud", "Bloom", "Harvested"]
CONSTELLATIONS = ["Keeper", "Lantern", "Ark", "Shard", "Wanderer", "Hearth", "Spindle", "Crown", "Tide", "Forge",
                  "Kite", "Loom"]
ECLIPSES = ["Umbra", "Penumbra", "Corona", "Diamondring", "Baileybeads", "Totality", "Annular", "Hybrid"]
LIVESTOCK = [("Lumewool", "sheep"), ("CometHen", "hen"), ("OrbitGoat", "goat"), ("NebulaBee", "bee")]
WILD = ["StarMoth", "DewNewt", "LensOwl", "GearFox"]
GOODS = ["Lumewool_Fleece", "Lumewool_Yarn", "Lumewool_Blanket", "CometEgg", "CometEgg_Basket", "OrbitMilk_Pail",
         "OrbitMilk_Bottle", "OrbitCheese_Wheel", "OrbitCheese_Wedge", "NebulaHoney_Jar", "NebulaHoney_Comb",
         "NebulaWax_Candle", "Starbread_Loaf", "Starbread_Slice", "Dewcake", "Moonpie", "Comet_Omelette",
         "Herb_Porridge", "Eclipse_Stew", "Lumen_Soup", "Sunfruit", "Moonmelon", "Driftberry_Bowl", "Orbit_Butter",
         "Honey_Glazed_Roots", "Stargazer_Pie", "Feed_Sack", "Hay_Bale", "Seed_Pouch", "Water_Flask"]
BUILDINGS = ["Observatory_Dome", "Observatory_Tower", "Keeper_Cottage_A", "Keeper_Cottage_B", "Keeper_Cottage_C",
             "Chart_Hall", "Lens_Workshop", "Clock_Tower", "Lumewool_Barn", "Comet_Coop", "Goat_Shed",
             "Nebula_Apiary", "Steeping_House", "Herb_Drying_Shed", "Cistern_House", "Well_House", "Pump_House",
             "Filter_House", "Dew_Tower", "Granary", "Bakery", "Dairy", "Market_Stall_A", "Market_Stall_B",
             "Ark_Dock_House", "Dock_Crane", "Lighthouse_Star", "Gate_Arch", "Plaza_Pavilion", "Bell_Tower",
             "Schoolhouse_Stars", "Tea_House", "Bathhouse", "Greenhouse_Night", "Greenhouse_Day", "Windmill",
             "Water_Mill", "Bridge_Stone", "Bridge_Rope", "Watch_Post"]
WATER = ["Dew_Net_Small", "Dew_Net_Large", "Dew_Net_Frame", "Dew_Funnel", "Dew_Collector_Bowl", "Dew_Pipe_Run",
         "Summit_Spring", "Spring_Basin", "Aqueduct_Straight", "Aqueduct_Corner", "Aqueduct_Arch",
         "Aqueduct_Pillar", "Aqueduct_End", "Aqueduct_Sluice", "Aqueduct_Ramp", "Aqueduct_Junction",
         "Sand_Filter", "Charcoal_Filter", "Filter_Bed", "Cistern_Round", "Cistern_Square", "Cistern_Lid",
         "Well_Stone", "Well_Bucket", "Well_Crank", "Trough_Long", "Trough_Round", "Trough_Stone", "Trough_Wood",
         "Trough_Double", "Trough_Corner", "Rain_Barrel", "Rain_Gutter", "Water_Pipe_Straight", "Water_Pipe_Elbow",
         "Water_Valve", "Drinking_Fountain", "Ladle_Post", "Water_Jug", "Hand_Pump"]
ASTRO = (["Armillary_%s" % c for c in ("Brass", "Silver", "Copper", "Gold", "Iron", "Glass", "Bone", "Jade",
                                       "Obsidian", "Heartstone")]
         + ["Orrery_%dPlanet" % n for n in range(2, 12)]
         + ["Telescope_%s" % c for c in ("Brass", "Tripod", "Refractor", "Reflector", "Pocket", "Giant", "Twin",
                                          "Rooftop", "Periscope", "Ark")]
         + ["StarChart_Stand_%s" % c for c in CONSTELLATIONS[:10]]
         + ["Sundial_%s" % c for c in ("Garden", "Pillar", "Ring", "Pocket", "Plaza", "Wall", "Equatorial", "Moon")]
         + ["MoonPhase_Lamp_%s" % c for c in ("New", "Crescent", "Quarter", "Gibbous", "Full", "Waning", "Blue",
                                               "Blood")]
         + ["Meteorite_%s" % c for c in ("Iron", "Stony", "Glass", "Starmetal", "Ember", "Frost", "Twin", "Split",
                                          "Hollow", "Ringed")]
         + ["Lens_%s" % c for c in ("Clear", "Amber", "Violet", "Rose", "Sea", "Smoke", "Prism", "Moon")])
DECOR = (["Lantern_%s" % c for c in ("Star", "Moon", "Comet", "Ring", "Orb", "Hanging", "Post", "Floor", "Wall",
                                      "Path")]
         + ["Bench_%s" % c for c in ("Stone", "Wood", "Curved", "Stargazer", "Double", "Swing")]
         + ["Fence_%s" % c for c in ("Picket", "Rail", "Stone", "Wattle", "Brass", "Corner", "Gate", "Post",
                                      "Low", "Tall")]
         + ["Path_Tile_%s" % c for c in ("Star", "Moon", "Hex", "Round", "Square", "Cobble", "Slab", "Step",
                                          "Mosaic", "Edge")]
         + ["Planter_%s" % c for c in ("Square", "Round", "Long", "Tiered", "Hanging", "Window", "Barrel", "Urn",
                                        "Trough", "Spiral")]
         + ["Sign_%s" % c for c in ("Arrow", "Board", "Hanging", "Post", "Star", "Shop", "Dock", "Welcome")]
         + ["Banner_%s" % c for c in CONSTELLATIONS[:8]])
TOOLS = ["Star_Trowel", "Dew_Scoop", "Lens_Wrench", "Gear_Key", "Chart_Compass", "Sky_Sextant", "Herb_Sickle",
         "Steeping_Ladle", "Wool_Shears", "Egg_Basket_Hook", "Milk_Stool", "Bee_Smoker", "Hive_Tool", "Water_Bucket",
         "Pruning_Hook", "Seed_Dibber", "Hoe_Brass", "Rake_Brass", "Shovel_Brass", "Watering_Can"]
WEAPONS = ["Comet_Pike", "Meridian_Blade", "Orbit_Chakram", "Eclipse_Mace", "Lens_Bow", "Gear_Hammer",
           "Starshard_Dagger", "Nebula_Staff", "Tidecaller_Spear", "Heartstone_Axe", "Aurora_Saber", "Zenith_Glaive"]
VEHICLES = ["Star_Skiff", "Cloud_Rowboat", "Ark_Dinghy", "Dew_Glider", "Orrery_Balloon", "Comet_Sled"]
SKY = ["Moonlet_Small", "Moonlet_Ringed", "Fragment_Drift_A", "Fragment_Drift_B", "Debris_Field_Chunk",
       "Cloud_Bank_Star", "Star_Cluster_Marker", "Comet_Tail_Wisp", "Aurora_Ribbon", "Meteor_Streak"]
INTERIOR = ["Chart_Desk", "Astrolabe_Table", "Globe_Fragments", "Bookshelf_Stars", "Lens_Cabinet", "Keeper_Bed",
            "Keeper_Chair", "Tea_Table", "Steeping_Kettle", "Herb_Rack", "Map_Chest", "Brass_Clock", "Candle_Stand",
            "Star_Rug", "Telescope_Mount", "Gear_Workbench", "Wool_Loom", "Honey_Press", "Cheese_Press",
            "Butter_Churn"]
CROPS = ["Sunfruit", "Moonmelon", "Driftberry", "Starbarley", "Cometcorn", "Dewroot"]
ITEMS_EXTRA = (["Constellation_Chart_%s" % c for c in CONSTELLATIONS]
               + ["Keeper_Key_%s" % c for c in ("Dome", "Vault", "Cistern", "Gate")])


def catalogue():
    out = []
    for h in HERBS:
        for s in STAGES:
            out.append(("Prop_Orr_Herb_%s_%s" % (h, s), "Prop", "herb", {"stage": s}))
    for h in HERBS:
        out.append(("Item_Orr_Tea_%s" % h, "Item", "tea", {}))
    for c in CONSTELLATIONS:
        out.append(("Item_Orr_Brew_%s" % c, "Item", "brew", {}))
    for e in ECLIPSES:
        out.append(("Item_Orr_EclipseBrew_%s" % e, "Item", "brew", {"dark": True}))
    for n, body in LIVESTOCK:
        out.append(("Mob_Orr_%s" % n, "Mob", "beast", {"body": body}))
        out.append(("Mob_Orr_%s_Young" % n, "Mob", "beast", {"body": body, "young": True}))
    for n in WILD:
        out.append(("Mob_Orr_%s" % n, "Mob", "beast", {"body": "wild"}))
    for g in GOODS:
        out.append(("Item_Orr_%s" % g, "Item", "goods", {}))
    for b in BUILDINGS:
        out.append(("Bld_Orr_%s" % b, "Bld", "building", {}))
    for w in WATER:
        out.append(("Prop_Orr_%s" % w, "Prop", "water", {}))
    for a in ASTRO:
        out.append(("Prop_Orr_%s" % a, "Prop", "astro", {}))
    for d in DECOR:
        out.append(("Prop_Orr_%s" % d, "Prop", "decor", {}))
    for t in TOOLS:
        out.append(("Tool_Orr_%s" % t, "Tool", "tool", {}))
    for w in WEAPONS:
        out.append(("Wpn_Orr_%s" % w, "Wpn", "weapon", {}))
    for v in VEHICLES:
        out.append(("Veh_Orr_%s" % v, "Veh", "vehicle", {}))
    for s in SKY:
        out.append(("Sky_Orr_%s" % s, "Sky", "sky", {}))
    for i in INTERIOR:
        out.append(("Prop_Orr_Interior_%s" % i, "Prop", "interior", {}))
    for c in CROPS:
        for s in ("Seedling", "Growing", "Ripe"):
            out.append(("Prop_Orr_Crop_%s_%s" % (c, s), "Prop", "crop", {"stage": s}))
    for i in ITEMS_EXTRA:
        out.append(("Item_Orr_%s" % i, "Item", "goods", {}))
    return out


# ------------------------------------------------------------------------------------------------ geometry

def rng_for(name):
    return random.Random(int(hashlib.sha256(name.encode()).hexdigest()[:12], 16))


def mat(name, rgb, emit=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = 0.6
    if emit > 0:
        bsdf.inputs["Emission Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit
    return m


class Part:
    """Primitives merged into one mesh object per asset, each tagged with one of up to three materials."""

    def __init__(self, name, mats):
        self.bm = bmesh.new()
        self.name = name
        self.mats = mats[:3]

    def _tag(self, geom, mi):
        for f in geom:
            f.material_index = mi

    def _place(self, verts, loc, rot=(0, 0, 0), scale=(1, 1, 1)):
        bmesh.ops.scale(self.bm, vec=scale, verts=verts)
        for ax, ang in zip("XYZ", rot):
            if ang:
                from mathutils import Matrix
                bmesh.ops.rotate(self.bm, verts=verts, cent=(0, 0, 0), matrix=Matrix.Rotation(ang, 3, ax))
        bmesh.ops.translate(self.bm, vec=loc, verts=verts)

    def box(self, loc, size, mi=0, rot=(0, 0, 0)):
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        self._place(r["verts"], loc, rot, size)
        self.bm.faces.ensure_lookup_table()
        self._tag(self.bm.faces[-6:], mi)

    def cyl(self, loc, r, h, mi=0, seg=8, r2=None, rot=(0, 0, 0)):
        before = len(self.bm.faces)
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                                    radius2=r if r2 is None else r2, depth=h)
        self._place(res["verts"], loc, rot)
        self.bm.faces.ensure_lookup_table()
        self._tag(self.bm.faces[before:], mi)

    def ball(self, loc, r, mi=0, sub=1, scale=(1, 1, 1)):
        before = len(self.bm.faces)
        res = bmesh.ops.create_icosphere(self.bm, subdivisions=sub, radius=r)
        self._place(res["verts"], loc, (0, 0, 0), scale)
        self.bm.faces.ensure_lookup_table()
        self._tag(self.bm.faces[before:], mi)

    def ring(self, loc, R, r, mi=0, seg=16, rot=(0, 0, 0)):
        for i in range(seg):
            a = 2 * math.pi * i / seg
            a2 = 2 * math.pi * (i + 1) / seg
            mid = ((math.cos(a) + math.cos(a2)) / 2 * R, (math.sin(a) + math.sin(a2)) / 2 * R)
            ln = 2 * math.pi * R / seg * 1.05
            ang = (a + a2) / 2 + math.pi / 2
            before = len(self.bm.verts)
            res = bmesh.ops.create_cube(self.bm, size=1.0)
            self._place(res["verts"], (mid[0], mid[1], 0), (0, 0, ang), (ln, r, r))
            from mathutils import Matrix, Vector
            for ax, angr in zip("XYZ", rot):
                if angr:
                    bmesh.ops.rotate(self.bm, verts=res["verts"], cent=(0, 0, 0), matrix=Matrix.Rotation(angr, 3, ax))
            bmesh.ops.translate(self.bm, vec=loc, verts=res["verts"])
            self.bm.faces.ensure_lookup_table()
            self._tag(self.bm.faces[-6:], mi)

    def finish(self, coll):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me)
        coll.objects.link(ob)
        # bottom at z = 0, centred on x/y
        zs = [v.co.z for v in me.vertices]
        xs = [v.co.x for v in me.vertices]
        ys = [v.co.y for v in me.vertices]
        dz, dx, dy = -min(zs), -(min(xs) + max(xs)) / 2, -(min(ys) + max(ys)) / 2
        for v in me.vertices:
            v.co.x += dx
            v.co.y += dy
            v.co.z += dz
        return ob


PAL = {
    "brass": (0.78, 0.6, 0.25), "night": (0.08, 0.1, 0.28), "star": (1.0, 0.92, 0.55), "stone": (0.55, 0.55, 0.6),
    "wood": (0.45, 0.3, 0.18), "leaf": (0.25, 0.6, 0.3), "glow": (0.55, 0.85, 1.0), "water": (0.2, 0.5, 0.85),
    "wool": (0.9, 0.92, 1.0), "roof": (0.25, 0.22, 0.5), "clay": (0.7, 0.42, 0.3), "heart": (1.0, 0.4, 0.3),
}


def hue(rng):
    import colorsys
    return colorsys.hsv_to_rgb(rng.random(), 0.55 + rng.random() * 0.35, 0.65 + rng.random() * 0.35)


def build(asset, kind, family, p):
    rng = rng_for(asset)
    coll = bpy.data.collections.new(asset)
    bpy.context.scene.collection.children.link(coll)
    k = rng.uniform(0.85, 1.2)
    if family == "herb":
        c = hue(rng)
        part = Part(asset, [mat("leaf", PAL["leaf"]), mat(asset + "_petal", c, 1.5 if p["stage"] == "Bloom" else 0),
                            mat("soil", PAL["wood"])])
        st = STAGES.index(p["stage"])
        h = [0.12, 0.25, 0.4, 0.15][st] * k
        if p["stage"] == "Harvested":
            for i in range(rng.randint(3, 6)):
                part.cyl((rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04), h / 2), 0.008, h, 0, 5, rot=(rng.uniform(-0.4, 0.4), 0, 0))
            part.cyl((0, 0, h * 0.4), 0.03, 0.03, 2, 6)
            part.ball((0, 0, h), 0.03 * k, 1, 1)
        else:
            part.cyl((0, 0, 0.01), 0.07, 0.02, 2, 8)
            leaves = rng.randint(3, 7)
            for i in range(leaves):
                a = 2 * math.pi * i / leaves
                part.box((math.cos(a) * 0.04, math.sin(a) * 0.04, h * 0.3), (0.06, 0.02, 0.005), 0, rot=(0.5, 0, a))
            part.cyl((0, 0, h / 2), 0.006, h, 0, 5)
            if st >= 1:
                part.ball((0, 0, h), (0.02 if st == 1 else 0.045) * k, 1, 1, (1, 1, rng.uniform(0.5, 1.4)))
            if st == 2:
                petals = rng.randint(5, 8)
                for i in range(petals):
                    a = 2 * math.pi * i / petals
                    part.box((math.cos(a) * 0.05, math.sin(a) * 0.05, h), (0.05, 0.022, 0.006), 1, rot=(0, 0.3, a))
        part.finish(coll)
    elif family in ("tea", "brew"):
        c = hue(rng)
        dark = p.get("dark")
        part = Part(asset, [mat("glass", PAL["glow"]), mat(asset + "_liquid", (c[0] * 0.4, c[1] * 0.4, c[2] * 0.5) if dark else c, 0.8),
                            mat("cork", PAL["wood"])])
        h = rng.uniform(0.12, 0.22)
        shape = rng.randint(0, 2)
        if shape == 0:
            part.cyl((0, 0, h / 2), 0.05 * k, h, 0, 10)
        elif shape == 1:
            part.ball((0, 0, 0.06), 0.06 * k, 0, 2)
            part.cyl((0, 0, 0.13), 0.015, 0.08, 0, 6)
        else:
            part.cyl((0, 0, h / 2), 0.06 * k, h, 0, 6, r2=0.03)
        part.cyl((0, 0, h * 0.35), 0.042 * k, h * 0.5, 1, 10)
        part.cyl((0, 0, h + 0.02), 0.018, 0.04, 2, 6)
        if family == "brew":
            part.ring((0, 0, h * 0.6), 0.065 * k, 0.006, 1, 12)
        part.finish(coll)
    elif family == "beast":
        body = p["body"]
        s = 0.55 if p.get("young") else 1.0
        c = hue(rng)
        base = {"sheep": PAL["wool"], "hen": (0.95, 0.8, 0.5), "goat": (0.6, 0.5, 0.42), "bee": (0.95, 0.75, 0.2),
                "wild": c}[body]
        part = Part(asset, [mat(asset + "_coat", base), mat(asset + "_glow", c, 2.0), mat("hoof", (0.15, 0.12, 0.12))])
        if body in ("sheep", "goat", "wild"):
            L = {"sheep": 0.9, "goat": 0.8, "wild": rng.uniform(0.35, 0.7)}[body] * s
            H = L * 0.5
            part.ball((0, 0, H), L * 0.5, 0, 2, (0.75, 1.1, 0.75))
            part.ball((0, L * 0.55, H * 1.3), L * 0.2, 0, 1)
            for x in (-1, 1):
                for y in (-1, 1):
                    part.cyl((x * L * 0.18, y * L * 0.3, H * 0.35), L * 0.05, H * 0.7, 2, 6)
            part.ball((0, L * 0.72, H * 1.35), L * 0.05, 1, 1)
            if body == "goat":
                for x in (-1, 1):
                    part.cyl((x * L * 0.08, L * 0.5, H * 1.6), L * 0.025, L * 0.25, 2, 5, r2=0.002, rot=(-0.6, 0, 0))
            if body == "sheep":
                part.ring((0, 0, H * 1.45), L * 0.3, L * 0.03, 1, 12)
        elif body == "hen":
            part.ball((0, 0, 0.22 * s), 0.18 * s, 0, 2, (0.8, 1.1, 0.9))
            part.ball((0, 0.17 * s, 0.38 * s), 0.08 * s, 0, 1)
            part.cyl((0, 0.27 * s, 0.38 * s), 0.025 * s, 0.07 * s, 2, 5, r2=0.002, rot=(-1.57, 0, 0))
            part.cyl((0, -0.12 * s, 0.35 * s), 0.07 * s, 0.25 * s, 1, 6, r2=0.0, rot=(0.9, 0, 0))
            for x in (-1, 1):
                part.cyl((x * 0.06 * s, 0, 0.05 * s), 0.012 * s, 0.1 * s, 2, 5)
        else:  # bee
            part.ball((0, 0, 0.12 * s), 0.1 * s, 0, 2, (0.8, 1.3, 0.8))
            part.ball((0, 0.14 * s, 0.14 * s), 0.06 * s, 2, 1)
            for x in (-1, 1):
                part.box((x * 0.1 * s, 0, 0.22 * s), (0.16 * s, 0.08 * s, 0.01), 1, rot=(0, 0.3 * x, 0))
            for i in range(3):
                part.ring((0, -0.04 * s + i * 0.05 * s, 0.12 * s), 0.09 * s, 0.01, 2, 10, rot=(1.57, 0, 0))
        part.finish(coll)
    elif family == "building":
        W, D, H = rng.uniform(4, 9) * k, rng.uniform(4, 8) * k, rng.uniform(3, 6) * k
        part = Part(asset, [mat("stone", PAL["stone"]), mat(asset + "_roof", hue(rng) if rng.random() < 0.4 else PAL["roof"]),
                            mat("starglass", PAL["star"], 1.5)])
        tall = any(t in asset for t in ("Tower", "Lighthouse", "Clock", "Bell", "Dew_Tower", "Watch", "Windmill"))
        if tall:
            W = D = rng.uniform(3, 4.5)
            H = rng.uniform(9, 15)
        part.box((0, 0, H / 2), (W, D, H), 0)
        if "Dome" in asset or "Observatory" in asset or "Greenhouse" in asset or "Pavilion" in asset:
            part.ball((0, 0, H), min(W, D) * 0.55, 1 if "Green" not in asset else 2, 2, (1, 1, 0.8))
            part.cyl((0, min(W, D) * 0.3, H + min(W, D) * 0.4), 0.3, min(W, D) * 0.6, 0, 8, rot=(0.6, 0, 0))
        elif "Bridge" in asset:
            part.box((0, 0, 0.3), (2.0, 10, 0.4), 1)
        else:
            part.cyl((0, 0, H + 1.2), max(W, D) * 0.72, 2.4, 1, 4, r2=0.05, rot=(0, 0, 0.785))
        for i in range(rng.randint(2, 5)):
            part.box((rng.uniform(-W / 3, W / 3), D / 2 + 0.05, rng.uniform(1.2, H - 0.8)), (0.7, 0.1, 0.9), 2)
        part.box((0, D / 2 + 0.06, 1.0), (1.1, 0.12, 2.0), 1)
        if "Windmill" in asset or "Water_Mill" in asset:
            for i in range(4):
                part.box((0, D / 2 + 0.5, H * 0.8), (0.4, 0.1, 5.0), 1, rot=(0, 1.5708 * i + 0.4, 0))
        if "Crane" in asset:
            part.box((0, D, H + 2), (0.4, D * 2, 0.4), 1)
        part.finish(coll)
    elif family in ("water", "astro", "decor", "interior", "tool", "weapon", "vehicle", "sky", "goods", "crop"):
        prop(asset, family, p, rng, k, coll)
    return coll


def prop(asset, family, p, rng, k, coll):
    c = hue(rng)
    if family == "water":
        part = Part(asset, [mat("stone", PAL["stone"]), mat("water", PAL["water"], 0.3), mat("wood", PAL["wood"])])
        n = asset
        if "Net" in n or "Frame" in n:
            w = rng.uniform(1.5, 3.5)
            for x in (-1, 1):
                part.cyl((x * w / 2, 0, 1.2), 0.06, 2.4, 2, 6)
            part.box((0, 0, 1.6), (w, 0.03, 1.4), 1)
        elif "Aqueduct" in n:
            L = 4.0 if "Straight" in n else 2.5
            part.box((0, 0, 3.2), (0.9, L, 0.5), 0)
            part.box((0, 0, 3.5), (0.5, L, 0.12), 1)
            if "Pillar" in n or "Arch" in n or "Straight" in n:
                part.box((0, 0, 1.5), (0.7, 0.7, 3.0), 0)
            if "Arch" in n:
                part.ring((0, 0, 1.6), 1.2, 0.25, 0, 10, rot=(0, 1.5708, 0))
            if "Corner" in n or "Junction" in n:
                part.box((L / 3, 0, 3.2), (L / 1.5, 0.9, 0.5), 0)
            if "Sluice" in n:
                part.box((0, 0, 3.9), (1.0, 0.15, 0.8), 2)
            if "Ramp" in n:
                part.box((0, L / 2, 2.4), (0.9, 1.0, 1.6), 0)
        elif "Trough" in n:
            L = rng.uniform(1.2, 2.6)
            if "Round" in n:
                part.cyl((0, 0, 0.3), 0.6 * k, 0.6, 0 if "Stone" in n else 2, 12)
            else:
                part.box((0, 0, 0.3), (0.6, L, 0.6), 0 if "Stone" in n else 2)
            part.box((0, 0, 0.55), (0.45, L * 0.9 if "Round" not in n else 0.8, 0.05), 1)
            if "Double" in n:
                part.box((0.8, 0, 0.3), (0.6, L, 0.6), 2)
        elif "Cistern" in n:
            if "Square" in n:
                part.box((0, 0, 1.2), (3, 3, 2.4), 0)
            else:
                part.cyl((0, 0, 1.2), 1.6 * k, 2.4, 0, 14)
            part.cyl((0, 0, 2.45), 1.3 * k, 0.1, 1 if "Lid" not in n else 2, 14)
        elif "Well" in n or "Pump" in n or "Fountain" in n or "Post" in n:
            part.cyl((0, 0, 0.45), 0.8 * k, 0.9, 0, 12)
            part.cyl((0, 0, 0.85), 0.62 * k, 0.05, 1, 12)
            if "Crank" in n or "Stone" in n:
                for x in (-1, 1):
                    part.box((x * 0.75, 0, 1.4), (0.12, 0.12, 1.9), 2)
                part.cyl((0, 0, 2.2), 0.06, 1.6, 2, 6, rot=(0, 1.5708, 0))
            if "Bucket" in n:
                part.cyl((0, 0, 1.4), 0.15, 0.25, 2, 8)
            if "Fountain" in n:
                part.cyl((0, 0, 1.2), 0.12, 1.0, 0, 8)
                part.ball((0, 0, 1.8), 0.18, 1, 1)
            if "Pump" in n:
                part.box((0, 0, 1.3), (0.2, 0.2, 1.0), 2)
                part.box((0.3, 0, 1.7), (0.6, 0.06, 0.06), 2)
        else:
            h = rng.uniform(0.4, 1.4)
            part.cyl((0, 0, h / 2), rng.uniform(0.2, 0.6), h, 2 if "Barrel" in n else 0, 10)
            part.cyl((0, 0, h * 0.92), rng.uniform(0.15, 0.4), 0.05, 1, 10)
            if "Pipe" in n or "Valve" in n or "Gutter" in n:
                part.cyl((0.6, 0, h * 0.5), 0.08, 1.2, 0, 8, rot=(0, 1.5708, 0))
        part.finish(coll)
        return
    if family == "astro":
        part = Part(asset, [mat("brass", PAL["brass"]), mat(asset + "_c", c, 1.2), mat("night", PAL["night"])])
        n = asset
        if "Armillary" in n:
            part.cyl((0, 0, 0.5), 0.08, 1.0, 0, 8)
            for i in range(rng.randint(3, 5)):
                part.ring((0, 0, 1.4), 0.5 * k - i * 0.04, 0.025, 0 if i % 2 else 1, 16, rot=(i * 0.6, i * 0.4, 0))
            part.ball((0, 0, 1.4), 0.1, 1, 1)
        elif "Orrery" in n:
            planets = int(n.split("_")[-1].replace("Orrery", "").replace("Planet", "") or 3)
            part.cyl((0, 0, 0.05), 0.5, 0.1, 2, 12)
            part.cyl((0, 0, 0.4), 0.05, 0.7, 0, 6)
            part.ball((0, 0, 0.8), 0.12, 1, 2)
            for i in range(planets):
                a = rng.uniform(0, 6.28)
                R = 0.2 + i * 0.07
                part.cyl((math.cos(a) * R / 2, math.sin(a) * R / 2, 0.75), 0.008, R, 0, 4, rot=(0, 1.5708, a))
                part.ball((math.cos(a) * R, math.sin(a) * R, 0.75), 0.025 + rng.random() * 0.03, 1, 1)
        elif "Telescope" in n:
            L = rng.uniform(1.0, 2.2) * (2 if "Giant" in n else (0.4 if "Pocket" in n else 1))
            for i in range(3):
                a = i * 2.094
                part.cyl((math.cos(a) * 0.3, math.sin(a) * 0.3, 0.55), 0.03, 1.2, 2, 5, rot=(math.sin(a) * 0.25, -math.cos(a) * 0.25, 0))
            part.cyl((0, 0, 1.2 + L * 0.3), 0.08 * k, L, 0, 10, r2=0.05, rot=(0.9, 0, 0))
            if "Twin" in n:
                part.cyl((0.2, 0, 1.2 + L * 0.3), 0.06, L, 0, 8, rot=(0.9, 0, 0))
        elif "StarChart" in n:
            part.cyl((0, 0, 0.6), 0.05, 1.2, 0, 6)
            part.box((0, 0, 1.25), (0.8, 0.05, 0.6), 2, rot=(-0.4, 0, 0))
            for i in range(rng.randint(5, 9)):
                part.ball((rng.uniform(-0.3, 0.3), 0.05, 1.25 + rng.uniform(-0.2, 0.2)), 0.025, 1, 0)
        elif "Sundial" in n:
            part.cyl((0, 0, 0.5 if "Pillar" in n else 0.1), 0.35 * k, 1.0 if "Pillar" in n else 0.2, 2, 12)
            part.box((0, 0, 1.1 if "Pillar" in n else 0.35), (0.04, 0.3, 0.25), 0, rot=(0.6, 0, 0))
            part.ring((0, 0, 1.01 if "Pillar" in n else 0.21), 0.3 * k, 0.015, 1, 16)
        elif "MoonPhase" in n:
            part.cyl((0, 0, 0.9), 0.04, 1.8, 0, 6)
            part.ball((0, 0, 1.9), 0.2, 1, 2)
            part.ball((0.08 * (1 + rng.random()), 0, 1.9), 0.19, 2, 2, (0.8, 1.05, 1.05))
        elif "Meteorite" in n:
            for i in range(2 if ("Twin" in n or "Split" in n) else 1):
                part.ball((i * 0.6, 0, 0.35), 0.4 * k, 2 if "Ember" not in n else 1, 1, (1.2, 0.9, 0.75))
            part.ball((0.1, 0.25, 0.5), 0.12, 1, 1)
            if "Ringed" in n:
                part.ring((0, 0, 0.35), 0.6, 0.03, 0, 14, rot=(0.4, 0, 0))
        else:  # lens
            part.cyl((0, 0, 0.45), 0.04, 0.9, 0, 6)
            part.ring((0, 0, 1.1), 0.25, 0.03, 0, 14, rot=(1.5708, 0, 0))
            part.cyl((0, 0, 1.1), 0.24, 0.02, 1, 14, rot=(1.5708, 0, 0))
        part.finish(coll)
        return
    if family == "decor":
        part = Part(asset, [mat("wood", PAL["wood"]), mat(asset + "_c", c, 1.0), mat("stone", PAL["stone"])])
        n = asset
        if "Lantern" in n:
            h = rng.uniform(0.4, 2.4)
            if "Hanging" not in n and "Wall" not in n:
                part.cyl((0, 0, h / 2), 0.05, h, 0, 6)
            part.box((0, 0, h + 0.15), (0.22, 0.22, 0.3), 1)
            part.cyl((0, 0, h + 0.35), 0.16, 0.1, 0, 4, r2=0.02)
        elif "Bench" in n:
            L = rng.uniform(1.2, 2.2)
            part.box((0, 0, 0.45), (L, 0.45, 0.08), 0 if "Stone" not in n else 2)
            for x in (-1, 1):
                part.box((x * L * 0.4, 0, 0.22), (0.1, 0.4, 0.45), 2)
            if "Stargazer" in n or "Double" in n:
                part.box((0, -0.25, 0.75), (L, 0.06, 0.5), 0, rot=(-0.4, 0, 0))
        elif "Fence" in n:
            L = 2.0
            h = rng.uniform(0.6, 1.6) * (1.6 if "Tall" in n else (0.6 if "Low" in n else 1))
            for x in (-1, 0, 1):
                part.box((x * L / 2, 0, h / 2), (0.1, 0.1, h), 2 if "Stone" in n else 0)
            for z in (0.35, 0.75):
                part.box((0, 0, h * z), (L, 0.05, 0.08), 1 if "Brass" in n else 0)
        elif "Path_Tile" in n:
            if "Round" in n or "Star" in n or "Moon" in n:
                part.cyl((0, 0, 0.04), 0.5 * k, 0.08, 2, 5 if "Star" in n else 12)
            else:
                part.box((0, 0, 0.04), (1.0 * k, 1.0, 0.08), 2)
            part.cyl((0, 0, 0.085), 0.12, 0.01, 1, 6)
        elif "Planter" in n:
            h = rng.uniform(0.3, 0.8)
            if "Round" in n or "Urn" in n or "Barrel" in n:
                part.cyl((0, 0, h / 2), 0.35 * k, h, 2, 10, r2=0.25 if "Urn" in n else None)
            else:
                part.box((0, 0, h / 2), (0.9 * k, 0.4, h), 0)
            for i in range(rng.randint(3, 6)):
                part.ball((rng.uniform(-0.2, 0.2), rng.uniform(-0.1, 0.1), h + 0.08), 0.08, 1, 1)
        elif "Sign" in n:
            part.box((0, 0, 0.7), (0.1, 0.1, 1.4), 0)
            part.box((0, 0.06, 1.25), (0.8 * k, 0.05, 0.4), 1, rot=(0, 0, 0.3 if "Arrow" in n else 0))
        else:  # banner
            part.cyl((0, 0, 1.5), 0.04, 3.0, 0, 6)
            part.box((0.35, 0, 2.4), (0.6, 0.02, 1.0), 1)
            part.ball((0.35, 0.02, 2.4), 0.08, 2, 0)
        part.finish(coll)
        return
    if family == "interior":
        part = Part(asset, [mat("wood", PAL["wood"]), mat(asset + "_c", c, 0.6), mat("brass", PAL["brass"])])
        W, D, H = rng.uniform(0.6, 1.8), rng.uniform(0.4, 1.0), rng.uniform(0.5, 2.0)
        if any(t in asset for t in ("Rug",)):
            part.box((0, 0, 0.01), (W * 1.5, D * 2, 0.02), 1)
        elif any(t in asset for t in ("Globe", "Clock", "Candle", "Kettle", "Astrolabe")):
            part.cyl((0, 0, H * 0.35), 0.08, H * 0.7, 2, 6)
            part.ball((0, 0, H * 0.8), 0.25 * k, 1, 2)
            part.ring((0, 0, H * 0.8), 0.3 * k, 0.015, 2, 14, rot=(0.4, 0, 0))
        else:
            part.box((0, 0, H), (W, D, 0.06), 0)
            for x in (-1, 1):
                for y in (-1, 1):
                    part.box((x * W * 0.45, y * D * 0.4, H / 2), (0.06, 0.06, H), 0)
            for i in range(rng.randint(1, 4)):
                part.box((rng.uniform(-W / 3, W / 3), 0, H + 0.08), (0.15, 0.12, 0.12), 1)
            part.box((0, -D / 2, H * 0.6), (W * 0.9, 0.03, H * 0.4), 2)
        part.finish(coll)
        return
    if family in ("tool", "weapon"):
        part = Part(asset, [mat("wood", PAL["wood"]), mat("brass", PAL["brass"]), mat(asset + "_c", c, 1.5 if family == "weapon" else 0.3)])
        L = rng.uniform(0.5, 1.1) * (1.8 if any(t in asset for t in ("Pike", "Spear", "Glaive", "Staff")) else 1)
        part.cyl((0, 0, L / 2), 0.02, L, 0, 6)
        head = rng.randint(0, 3)
        if any(t in asset for t in ("Blade", "Saber", "Dagger")):
            part.box((0, 0, L * 0.9), (0.06, 0.012, L * 0.9), 2)
            part.box((0, 0, L * 0.45), (0.2, 0.04, 0.03), 1)
        elif "Chakram" in asset or "Orbit" in asset:
            part.ring((0, 0, L + 0.2), 0.2, 0.025, 2, 14, rot=(1.5708, 0, 0))
        elif "Bow" in asset:
            part.ring((0, 0, L / 2), L / 2, 0.02, 1, 12, rot=(1.5708, 0, 0))
            part.cyl((0, 0, L / 2), 0.003, L, 2, 4)
        else:
            if head == 0:
                part.box((0, 0, L), (0.18, 0.05, 0.1), 1)
            elif head == 1:
                part.cyl((0, 0, L + 0.08), 0.05, 0.18, 2, 6, r2=0.0)
            elif head == 2:
                part.ball((0, 0, L), 0.07, 2, 1)
            else:
                part.box((0.06, 0, L - 0.04), (0.16, 0.02, 0.12), 1, rot=(0, 0.4, 0))
        part.finish(coll)
        return
    if family == "vehicle":
        part = Part(asset, [mat("wood", PAL["wood"]), mat(asset + "_sail", c), mat("brass", PAL["brass"])])
        L = rng.uniform(3.5, 6.0)
        part.ball((0, 0, 0.5), L / 2, 0, 1, (0.35, 1.0, 0.25))
        if "Balloon" in asset:
            part.ball((0, 0, 4.0), 2.0, 1, 2, (1, 1, 1.15))
            for x in (-1, 1):
                part.cyl((x * 0.8, 0, 2.2), 0.02, 2.6, 2, 4)
        elif "Sled" in asset:
            for x in (-1, 1):
                part.box((x * 0.6, 0, 0.1), (0.08, L, 0.08), 2)
        else:
            part.cyl((0, 0, 2.2), 0.06, 3.4, 0, 6)
            part.box((0, 0.1, 2.4), (0.04, 1.6, 2.2), 1)
            if "Glider" in asset or "Skiff" in asset:
                for x in (-1, 1):
                    part.box((x * 1.4, 0, 0.9), (2.0, 0.8, 0.05), 1)
        part.finish(coll)
        return
    if family == "sky":
        part = Part(asset, [mat("stone", PAL["stone"]), mat(asset + "_c", c, 2.0), mat("night", PAL["night"])])
        R = rng.uniform(3, 9)
        if "Moonlet" in asset:
            part.ball((0, 0, R), R, 0, 2)
            if "Ringed" in asset:
                part.ring((0, 0, R), R * 1.6, R * 0.08, 1, 20, rot=(0.3, 0, 0))
        elif "Fragment" in asset or "Debris" in asset:
            for i in range(rng.randint(3, 7)):
                part.ball((rng.uniform(-R, R), rng.uniform(-R, R), R + rng.uniform(-R, R) * 0.4), rng.uniform(0.5, 2.5), 0, 1,
                          (1.2, 0.8, 0.7))
            part.ball((0, 0, R), 0.6, 1, 1)
        elif "Cloud" in asset:
            for i in range(6):
                part.ball((rng.uniform(-R, R), rng.uniform(-R / 2, R / 2), R * 0.3), rng.uniform(1.5, 3.5), 2, 1, (1.3, 1, 0.6))
            part.ball((0, 0, R * 0.5), 0.5, 1, 0)
        else:
            for i in range(rng.randint(6, 12)):
                part.ball((rng.uniform(-R, R), rng.uniform(-R, R), rng.uniform(0, R)), rng.uniform(0.15, 0.5), 1, 0)
            part.box((0, 0, R / 2), (0.05, R * 2, 0.05), 2)
        part.finish(coll)
        return
    if family == "crop":
        part = Part(asset, [mat("leaf", PAL["leaf"]), mat(asset.rsplit("_", 1)[0] + "_fruit", c, 0.4), mat("soil", PAL["wood"])])
        st = ["Seedling", "Growing", "Ripe"].index(p["stage"])
        h = [0.15, 0.5, 0.9][st] * k
        part.box((0, 0, 0.04), (0.6, 0.6, 0.08), 2)
        part.cyl((0, 0, h / 2), 0.015, h, 0, 5)
        for i in range(2 + st * 2):
            a = i * 2.4
            part.box((math.cos(a) * 0.08, math.sin(a) * 0.08, h * (0.3 + 0.12 * i)), (0.16, 0.05, 0.01), 0, rot=(0.4, 0, a))
        if st == 2:
            for i in range(rng.randint(2, 5)):
                part.ball((rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), h * rng.uniform(0.5, 1.0)), 0.06 * k, 1, 1)
        part.finish(coll)
        return
    # goods
    part = Part(asset, [mat("wood", PAL["wood"]), mat(asset + "_c", c, 0.3), mat("clay", PAL["clay"])])
    n = asset
    s = rng.uniform(0.15, 0.4)
    if any(t in n for t in ("Jar", "Bottle", "Flask", "Pail", "Jug")):
        part.cyl((0, 0, s / 2), s * 0.4, s, 2, 10)
        part.cyl((0, 0, s + 0.02), s * 0.2, 0.05, 0, 8)
        part.cyl((0, 0, s * 0.4), s * 0.38, s * 0.5, 1, 10)
    elif any(t in n for t in ("Wheel", "Pie", "Cake", "Loaf", "Bowl", "Soup", "Stew", "Porridge", "Omelette", "Butter", "Roots")):
        part.cyl((0, 0, 0.02), s * 0.8, 0.04, 2, 12)
        part.ball((0, 0, 0.06), s * 0.6, 1, 2, (1, 1, 0.45))
    elif any(t in n for t in ("Chart", "Key")):
        if "Key" in n:
            part.ring((0, 0, 0.1), 0.06, 0.012, 1, 10, rot=(1.5708, 0, 0))
            part.box((0, 0, 0.0 + 0.012), (0.012, 0.012, 0.18), 1, rot=(1.5708, 0, 0))
            part.box((0.02, 0.09, 0.012), (0.04, 0.012, 0.03), 1)
        else:
            part.cyl((0, 0, 0.04), 0.04, 0.5, 2, 8, rot=(0, 1.5708, 0))
            part.box((0, 0.15, 0.005), (0.48, 0.3, 0.01), 1)
            for i in range(rng.randint(4, 8)):
                part.ball((rng.uniform(-0.2, 0.2), rng.uniform(0.02, 0.28), 0.012), 0.012, 0, 0)
    elif any(t in n for t in ("Sack", "Bale", "Pouch", "Basket", "Fleece", "Yarn", "Blanket", "Comb", "Candle")):
        part.box((0, 0, s / 2), (s * 1.4, s, s), 1 if "Bale" not in n else 0)
        part.cyl((0, 0, s + 0.03), s * 0.2, 0.06, 0, 6)
    else:
        part.ball((0, 0, s / 2), s / 2, 1, 2, (1, 1, rng.uniform(0.8, 1.3)))
        part.cyl((0, 0, s + 0.02), 0.01, 0.05, 0, 4)
    part.finish(coll)


# -------------------------------------------------------------------------------------------------- main

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    art = argv[0]
    only = int(argv[argv.index("--only") + 1]) if "--only" in argv else None
    items = catalogue()
    names = [a for a, *_ in items]
    assert len(names) == len(set(names)), "duplicate names in the catalogue"
    if only:
        items = items[:only]
    made = 0
    for asset, kind, family, p in items:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        build(asset, kind, family, p)
        out = os.path.join(art, kind, asset + ".blend")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
        made += 1
    print("ORR built %d of %d (catalogue %d)" % (made, len(items), len(names)))


if __name__ == "__main__":
    main()
