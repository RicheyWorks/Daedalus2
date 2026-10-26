# SPDX-License-Identifier: MIT
"""Contest row 11 (G14 mail route; buffffff 48312), blender-kit/v1.
Prop_Par_MailBag      0.5 m courier satchel with flap, buckle and shoulder strap; SOCKET_Carry at the strap top. UCX box.
Prop_Par_Letter       0.2 m sealed envelope (lies flat); SOCKET_Carry at its centre. UCX box.
Prop_Par_PlotMailbox  1.2 m post mailbox with a rounded top, front slot and side flag; SOCKET_Slot at the slot. UCX box.
REUSE check: no Parcels (Par) props exist in catalog.bba or art\\glb; catalog Prop_Mailbox is 1.42 m with no sockets or slot,
so it can't serve the drop point -> new.
Usage: python par_mail.py --out data/contest/par_mail.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 1414
BAG, LET, BOX = "Prop_Par_MailBag", "Prop_Par_Letter", "Prop_Par_PlotMailbox"
CAPS = {BAG: 1500, LET: 1500, BOX: 1500}
SOCKETS = {BAG: ["SOCKET_Carry"], LET: ["SOCKET_Carry"], BOX: ["SOCKET_Slot"]}
SPEC = {"row": 11, "gap": "G14", "tri_cap": 1500, "lod": "LOD0/1", "collision": "UCX box"}


def bag(seed=SEED):
    a = BAG
    mats = [K.material(a, 0, "canvas", "8C6B3F", 0.9), K.material(a, 1, "leather strap", "5A3A22", 0.8), K.material(a, 2, "brass", "B08D3C", 0.5, 0.6)]
    P = K.plain_lod1(K.box("Body", (0.45, 0.15, 0.32), (0, 0, 0.16), 0)) + K.plain_lod1(K.box("Flap", (0.46, 0.03, 0.17), (0, -0.085, 0.24), 0)) + \
        [K.box("Buckle", (0.05, 0.02, 0.05), (0, -0.105, 0.17), 2, bevel=False)]
    for i in range(7):                                   # strap arch over the bag, radius 0.21 about (0, 0, 0.32)
        t = math.pi * (i + 0.5) / 7
        P.append(K.box("Strap%d" % i, (0.1, 0.04, 0.012), (round(0.21 * math.cos(t), 5), 0, round(0.32 + 0.21 * math.sin(t), 5)), 1,
                       rot=(0, round(90 - math.degrees(t), 4), 0), bevel=False, lod1={"drop": i % 2 == 1}))
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="bag 0.5 m", sockets=["Carry"]), "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Carry", (0, 0, 0.53))], "collision": [K.ucx_box(a, 0, (0.46, 0.18, 0.33), (0, -0.01, 0.165))], "nanite": True}
    return K.finish(m)


def letter(seed=SEED):
    a = LET
    mats = [K.material(a, 0, "paper", "E8DDC0", 0.95), K.material(a, 1, "wax seal", "A12A2A", 0.5)]
    P = [K.box("Envelope", (0.2, 0.12, 0.004), (0, 0, 0.002), 0, bevel=False),
         K.box("FlapL", (0.115, 0.004, 0.0012), (-0.045, -0.025, 0.0046), 0, rot=(0, 0, 28), bevel=False),
         K.box("FlapR", (0.115, 0.004, 0.0012), (0.045, -0.025, 0.0046), 0, rot=(0, 0, -28), bevel=False),
         K.cyl("Seal", "z", 0.013, 0.013, 0.003, (0, -0.005, 0.0055), 1, 12, lod1={"segments": 6})]
    m = {"asset": a, "kind": "Prop", "seed": seed, "lod1": False, "spec": dict(SPEC, size_m="letter 0.2 m", sockets=["Carry"], lod="LOD0 only (80 tris)"), "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Carry", (0, 0, 0.004))], "collision": [K.ucx_box(a, 0, (0.2, 0.12, 0.008), (0, 0, 0.004))], "nanite": True}
    return K.finish(m)


def mailbox(seed=SEED):
    a = BOX
    mats = [K.material(a, 0, "post wood", "7A5232", 0.9), K.material(a, 1, "painted tin", "3E6E8E", 0.6, 0.4), K.material(a, 2, "flag red", "C0392B", 0.6)]
    P = K.plain_lod1(K.box("Post", (0.09, 0.09, 0.95), (0, 0, 0.475), 0)) + K.plain_lod1(K.box("Shelf", (0.28, 0.48, 0.03), (0, 0, 0.965), 0)) + \
        [K.box("Box", (0.25, 0.45, 0.13), (0, 0, 1.045), 1), K.cyl("Roof", "y", 0.125, 0.125, 0.45, (0, 0, 1.11), 1, 16, lod1={"segments": 8}),
         K.box("Slot", (0.14, 0.012, 0.02), (0, -0.226, 1.08), 0, bevel=False), K.box("FlagArm", (0.012, 0.03, 0.18), (0.131, 0.08, 1.1), 2, bevel=False),
         K.box("Flag", (0.012, 0.09, 0.06), (0.131, 0.05, 1.17), 2, bevel=False, lod1={"drop": True})]
    m = {"asset": a, "kind": "Prop", "seed": seed, "spec": dict(SPEC, size_m="mailbox 1.2 m", sockets=["Slot"]), "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Slot", (0, -0.23, 1.08))],
         "collision": [K.ucx_box(a, 0, (0.1, 0.1, 0.95), (0, 0, 0.475)), K.ucx_box(a, 1, (0.27, 0.46, 0.27), (0, 0, 1.1))], "nanite": True}
    return K.finish(m)


def assets(seed=SEED):
    return [bag(seed), letter(seed), mailbox(seed)]


def extra_checks(A):
    B, L, M = A[BAG], A[LET], A[BOX]
    return [("bag ~0.5 m", 0.45 <= max(B["predicted"]["dimensions"]) <= 0.55, B["predicted"]["dimensions"]),
            ("letter 0.2 m", abs(L["predicted"]["dimensions"][0] - 0.2) < 0.005, L["predicted"]["dimensions"]),
            ("mailbox 1.2 m (roof top 1.235)", 1.18 <= M["predicted"]["dimensions"][2] <= 1.25, M["predicted"]["dimensions"]),
            ("mailbox slot faces front", M["sockets"][0]["location"][1] < -0.2),
            ("a letter fits the slot", L["predicted"]["dimensions"][0] <= 0.14 + 0.07 and L["predicted"]["dimensions"][2] <= 0.02)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"])
