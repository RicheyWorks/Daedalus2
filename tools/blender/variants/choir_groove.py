# SPDX-License-Identifier: MIT
"""G53 Choir Stones state manifests (youtube-master 49161, ytm-g53-assets-20261019; code main 77814390 brew.stones).
G28/G33 approach for the hum: one mesh, the groove slot (Prop_YTM_ChoirStone_M1) gets an MI per state:
  Quiet    blank stone set on a fragment, nothing carved yet (or the record not mended)   EmissiveStrength 0
  Humming  ChoirStones.carve(...) == CARVED; glows while humming                           EmissiveStrength x RangeScale[range]
range = ChoirStones.range(tier): T1 1, T2-T3 2, T4 3 bridges; RangeScale brightens the stronger brews.
Rope bridge strength is a mesh swap (BridgeLedger.strength 3/2/1/0 -> Seg_S3/S2/S1/Snapped), all chained by SOCKET_Anchor_A/B.
Usage: python choir_groove.py --kit data/contest/ytm_g53.kit.json --out <dir> [--mesh-sha Asset=sha ...]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from coat_variants import lin

SCHEMA = "bb-material-variants/1"
STONE, SLOT, SLOT_INDEX = "Prop_YTM_ChoirStone", "Prop_YTM_ChoirStone_M1", 1
STATES = ["Quiet", "Humming"]
GROOVE = {"Quiet": {"GrooveBase": "2A2A30", "EmissiveColour": "FFD27A", "EmissiveStrength": 0.0, "PulseRate": 0.0, "PulseDepth": 0.0, "Roughness": 0.6},
          "Humming": {"GrooveBase": "3A3428", "EmissiveColour": "FFD27A", "EmissiveStrength": 8.0, "PulseRate": 0.75, "PulseDepth": 0.35, "Roughness": 0.4}}
RANGE_SCALE = {1: 1.0, 2: 1.4, 3: 1.8}                      # ChoirStones.range(tier) -> EmissiveStrength multiplier
TIER_RANGE = {1: 1, 2: 2, 3: 2, 4: 3}                       # = ChoirStones.range (77814390), checked by the test
BRIDGE = {3: "Prop_YTM_RopeBridge_Seg_S3", 2: "Prop_YTM_RopeBridge_Seg_S2", 1: "Prop_YTM_RopeBridge_Seg_S1", 0: "Prop_YTM_RopeBridge_Seg_Snapped"}
ANCHOR = "Prop_YTM_RopeBridge_Anchor"


def mi(st):
    return "MI_ChoirStone_Groove_" + st


def build(kit, mesh_sha=None):
    mesh_sha = mesh_sha or {}; A = {a["asset"]: a for a in kit["assets"]}
    assert A[STONE]["materials"][SLOT_INDEX]["name"] == SLOT
    variants = []
    for st in STATES:
        G = GROOVE[st]; P = {}
        for k in ("GrooveBase", "EmissiveColour"):
            P[k] = {"type": "vector", "srgb_hex": G[k], "linear_rgba": lin(G[k]) + [1.0]}
        for k in ("EmissiveStrength", "PulseRate", "PulseDepth", "Roughness"):
            P[k] = {"type": "scalar", "value": G[k]}
        variants.append({"name": mi(st), "state": st, "params": P})
    def sk(a, n):
        return next(s["location"] for s in A[a]["sockets"] if s["name"] == n)
    bridge = {str(s): {"mesh": m, "mesh_sha256": mesh_sha.get(m), "crossable": s > 0, "socket_A": sk(m, "SOCKET_Anchor_A"), "socket_B": sk(m, "SOCKET_Anchor_B"),
                       "collision": bool(A[m]["collision"])} for s, m in BRIDGE.items()}
    return {"schema": SCHEMA, "kit": "G53_ChoirStones", "gap": "G53 (youtube-master 49161, code 77814390 com.daedalus.world.brew.stones)",
            "stone": {"mesh": STONE, "mesh_sha256": mesh_sha.get(STONE), "groove_slot": SLOT, "groove_slot_index": SLOT_INDEX,
                      "sockets": {"SOCKET_Hum": "hum VFX / audio emitter (top)", "SOCKET_Carve": "carve interaction (front, on the groove)"}},
            "rule": "Humming once ChoirStones.carve(...) returns CARVED for this fragment, else Quiet. Humming EmissiveStrength x RangeScale[range]; "
                    "emissive = EmissiveColour x EmissiveStrength x (1 - PulseDepth + PulseDepth x sin(2pi PulseRate t)). Fade Quiet -> Humming over ~1 s on carve",
            "parent_material": {"name": "M_ChoirGroove (UE side, not built yet: UNREAL-QUEUE G53)", "graph": "base = GrooveBase, roughness = Roughness, emissive as in rule"},
            "params": {"GrooveBase": "vector, linear", "EmissiveColour": "vector, linear", "EmissiveStrength": "scalar (nits-ish, 0 = off)", "PulseRate": "scalar Hz",
                       "PulseDepth": "scalar 0..1", "Roughness": "scalar 0..1"},
            "states": STATES, "variants": variants, "range_scale": {str(k): v for k, v in RANGE_SCALE.items()}, "tier_range": {str(k): v for k, v in TIER_RANGE.items()},
            "lookup": {"%s/range%d" % (st, r): {"mi": mi(st), "emissive_strength": round(GROOVE[st]["EmissiveStrength"] * (RANGE_SCALE[r] if st == "Humming" else 1), 3)} for st in STATES for r in (1, 2, 3)},
            "bridge": {"rule": "mesh = bridge_states[BridgeLedger.strength(b)]; swap in place (S3/S2/S1 share socket positions); strength 0 = Snapped, no collision, refuse crossing",
                       "segment_length_m": 2.0, "chain": "seg n SOCKET_Anchor_B -> seg n+1 SOCKET_Anchor_A; both bridge ends on %s SOCKET_Segment (far end yawed 180)" % ANCHOR,
                       "anchor": {"mesh": ANCHOR, "mesh_sha256": mesh_sha.get(ANCHOR), "socket": sk(ANCHOR, "SOCKET_Segment")}, "states": bridge,
                       "humming": "a humming bridge (ChoirStones.humming) never frays: keep its current mesh"},
            "status": "STAGED NOT READY (MI params + state lookup only; parent material and actors are UE editor steps)"}


def write(kit_path, out, mesh_sha=None):
    os.makedirs(out, exist_ok=True)
    m = build(json.load(open(kit_path, encoding="utf-8")), mesh_sha)
    p = os.path.join(out, "G53_ChoirStones.choir_variants.json")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, indent=1); f.write("\n")
    return p, m


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--kit", required=True); ap.add_argument("--out", required=True); ap.add_argument("--mesh-sha", nargs="*", default=[])
    o = ap.parse_args(); p, m = write(o.kit, o.out, dict(kv.split("=", 1) for kv in o.mesh_sha))
    print(p, len(m["variants"]), "MIs", len(m["lookup"]), "lookup keys", len(m["bridge"]["states"]), "bridge states")
