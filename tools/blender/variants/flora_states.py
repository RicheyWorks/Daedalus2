# SPDX-License-Identifier: MIT
"""G48 Bee Bloom flora states (pythagoras 49144, pyth-g48-assets-20261019; code main c5a738b1 battlefield.BeeBloom).
G28/G33 approach: no mesh per state. Each flora clump keeps its own base colours (bloom), and the frost-killed state
is an MI swap on the clump's slots (FrostAmount 0 -> 1, FrostTint, FrostRoughness, RimeAmount). So the reused
pcg-ecology meshes (pythagoras) stay untouched.
  Flora (= BeeBloom.Flora)  clump meshes                              slots
  WILLOW_CATKIN             Prop_Bee_Flora_WillowCatkin (new, G48)     M0 twig, M1 catkin, M2 fuzz
  CROCUS                    Prop_Bee_Flora_Crocus (new, G48)           M0 leaf, M1 bloom, M2 stamen
  CLOVER                    Prop_Ground_PYT_Clover_V01..V10 (REUSE)    M_PYT_leaf
  BRAMBLE                   Prop_Bee_Flora_Bramble (new, G48)          M0 cane, M1 bloom, M2 leaf
  HEATHER                   Prop_Ground_PYT_Wildflower_V01..V10 (REUSE) M_PYT_flower
State rule: BLOOM normally; FROST once a frost day (Day.frost, temp < 0) hits a bed whose flora is open (its seed is lost).
Bed: Prop_Bee_FlowerBed has SOCKET_Plant_00..07; one flora per bed, clump pick + yaw per socket below (seeded, stable).
Usage: python flora_states.py --kit data/contest/bee_g48.kit.json --out <dir> [--mesh-sha Asset=sha ...]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coat_variants import lin

SCHEMA = "bb-material-variants/1"
FLORA = ["WILLOW_CATKIN", "CROCUS", "CLOVER", "BRAMBLE", "HEATHER"]          # = BeeBloom.Flora (c5a738b1), checked by the test
BAND = {"WILLOW_CATKIN": "WETLAND", "CROCUS": "MEADOW", "CLOVER": "MEADOW", "BRAMBLE": "SCRUB", "HEATHER": "MEADOW"}
STATES = ["BLOOM", "FROST"]
ROLE = {"petal": {"FrostTint": "6B4A3A", "FrostAmount": 0.9, "FrostRoughness": 0.95, "RimeAmount": 0.35},
        "leaf": {"FrostTint": "6E6A45", "FrostAmount": 0.85, "FrostRoughness": 0.9, "RimeAmount": 0.45},
        "wood": {"FrostTint": "4A3A2E", "FrostAmount": 0.25, "FrostRoughness": 0.85, "RimeAmount": 0.3}}
NEW = {"WILLOW_CATKIN": ("Prop_Bee_Flora_WillowCatkin", ["wood", "petal", "petal"]), "CROCUS": ("Prop_Bee_Flora_Crocus", ["leaf", "petal", "petal"]),
       "BRAMBLE": ("Prop_Bee_Flora_Bramble", ["wood", "petal", "leaf"])}
REUSE = {"CLOVER": ("Prop_Ground_PYT_Clover_V%02d", "M_PYT_leaf", "leaf"), "HEATHER": ("Prop_Ground_PYT_Wildflower_V%02d", "M_PYT_flower", "petal")}
BED = "Prop_Bee_FlowerBed"
SEED = 4848


def mi(role, state):
    return "MI_BeeFlora_%s_%s" % (role.capitalize(), state.capitalize())


def build(kit, mesh_sha=None):
    mesh_sha = mesh_sha or {}
    A = {a["asset"]: a for a in kit["assets"]}
    variants = []
    for role, R in ROLE.items():
        for st in STATES:
            amt = R["FrostAmount"] if st == "FROST" else 0.0
            variants.append({"name": mi(role, st), "role": role, "state": st, "params": {
                "FrostAmount": {"type": "scalar", "value": amt}, "FrostTint": {"type": "vector", "srgb_hex": R["FrostTint"], "linear_rgba": lin(R["FrostTint"]) + [1.0]},
                "FrostRoughness": {"type": "scalar", "value": R["FrostRoughness"]}, "RimeAmount": {"type": "scalar", "value": R["RimeAmount"] if st == "FROST" else 0.0}}})
    flora = {}
    for f in FLORA:
        if f in NEW:
            a, roles = NEW[f]; mats = A[a]["materials"]
            meshes = [{"mesh": a, "mesh_path": "staging/g48-bee-bloom-20261019/%s/%s.glb" % (a, a), "mesh_sha256": mesh_sha.get(a), "owner": "blender-team (G48, new)"}]
            slots = [{"slot": m["name"], "slot_index": i, "base_srgb": m.get("base_srgb") or m.get("hex"), "role": roles[i], "mi": {st: mi(roles[i], st) for st in STATES}} for i, m in enumerate(mats)]
        else:
            pat, slot, role = REUSE[f]
            meshes = [{"mesh": pat % v, "mesh_path": "art/glb/pythagoras/%s.glb" % (pat % v), "mesh_sha256": mesh_sha.get(pat % v), "owner": "pythagoras (pcg-ecology, REUSED untouched)"} for v in range(1, 11)]
            slots = [{"slot": slot, "slot_index": 0, "base_srgb": "mesh's own", "role": role, "mi": {st: mi(role, st) for st in STATES}}]
        plants = []
        for i, s in enumerate(A[BED]["sockets"]):
            pick = (SEED + 7 * i + 3 * FLORA.index(f)) % len(meshes)
            plants.append({"socket": s["name"], "mesh": meshes[pick]["mesh"], "yaw_deg": (47 * i + 29 * FLORA.index(f)) % 360, "location_m": s["location"]})
        flora[f] = {"band": BAND[f], "meshes": meshes, "slots": slots, "plants": plants}
    lookup = {"%s/%s/%s" % (f, s["slot"], st): s["mi"][st] for f in flora for s in flora[f]["slots"] for st in STATES}
    return {"schema": SCHEMA, "kit": "G48_BeeFlora", "gap": "G48 (pythagoras 49144, code c5a738b1 com.daedalus.world.battlefield.BeeBloom)",
            "rule": "state = FROST once Day.frost (tempC < 0) falls while the bed's flora is open (BeeBloom: open blooms lose their seed); else BLOOM. "
                    "Optional: fade FrostAmount 0 -> value over the frost morning",
            "meshes": "new clumps for WILLOW_CATKIN / CROCUS / BRAMBLE; CLOVER and HEATHER REUSE pythagoras pcg-ecology glbs untouched (only the MI changes)",
            "bed": {"mesh": BED, "sockets": [s["name"] for s in A[BED]["sockets"]], "one_flora_per_bed": True, "note": "6 beds in BeeBloom; spawn the flora's plants list on the bed's sockets"},
            "parent_material": {"name": "M_BeeFlora (UE side, not built yet)",
                                "graph": "colour = lerp(BaseColor, FrostTint, FrostAmount), then lerp toward white by RimeAmount x Fresnel (edge rime); roughness = lerp(Roughness, FrostRoughness, FrostAmount). BLOOM MIs (FrostAmount 0) = the mesh's own colours"},
            "params": {"FrostAmount": "scalar 0..1", "FrostTint": "vector, linear", "FrostRoughness": "scalar 0..1", "RimeAmount": "scalar 0..1"},
            "states": STATES, "roles": list(ROLE), "variants": variants, "flora": flora, "flora_order": FLORA, "lookup": lookup,
            "status": "STAGED NOT READY (MI params only; parent material and bed spawning are UE editor steps)"}


def write(kit_path, out, mesh_sha=None):
    os.makedirs(out, exist_ok=True)
    m = build(json.load(open(kit_path, encoding="utf-8")), mesh_sha)
    p = os.path.join(out, "G48_BeeFlora.flora_variants.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    return p, m


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--kit", required=True); ap.add_argument("--out", required=True); ap.add_argument("--mesh-sha", nargs="*", default=[])
    o = ap.parse_args(); p, m = write(o.kit, o.out, dict(kv.split("=", 1) for kv in o.mesh_sha))
    print(p, len(m["variants"]), "MIs", len(m["flora"]), "flora", len(m["lookup"]), "lookup keys")
