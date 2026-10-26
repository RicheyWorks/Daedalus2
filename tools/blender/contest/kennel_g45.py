# SPDX-License-Identifier: MIT
"""G45 Kennel Isle: The Ark Glass Cellar (art-master-flex 49039, amf-g45-bottle-meshes-20261019; PR #242,
docs/islands/KENNEL-THE-ARK-GLASS-CELLAR.md, code companion.TonicBottler), blender-kit/v1.
One modular generator, bottle(name, cork, wax, ark), gives the four tier bottles of TonicBottler:
  Item_TonicBottle_AMF_T1  plain bottle                          (materials: bottle)
  Item_TonicBottle_AMF_T2  corked                                (bottle, cork)
  Item_TonicBottle_AMF_T3  corked + wax seal                     (bottle, cork, wax)
  Item_TonicBottle_AMF_T4  thick blue-green ark glass, cork + wax (ark glass, cork, wax): squatter, heavier walls, a raised
                           band where the melted hull-port rim was.
Kennel pipeline match (tools/islands/kennel-isle/amf_items.py): Item_<Family>_AMF_<Name>_T# naming, origin bottom centre,
<= 3 materials named from the shared Kennel palette (M_AMF_glass, M_AMF_wood for cork, M_AMF_red for wax; new M_AMF_arkglass),
same linear colours as the palette. Hand props: SOCKET_Grip is an attach socket (+X up the bottle, like the rod/bat grips).
UCX prism each. Staged outside art\\glb\\amf (art-master-flex's watched output).
REUSE check: Item_Tonic_AMF_*_T1..T4 are 36-tri effect-colour placeholders without cork/wax/ark glass or sockets -> new.
Usage: python kennel_g45.py --out data/contest/kennel_g45.kit.json"""
import argparse, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 4545
PRE = "Item_TonicBottle_AMF_"
TIERS = {"T1": dict(cork=False, wax=False, ark=False), "T2": dict(cork=True, wax=False, ark=False),
         "T3": dict(cork=True, wax=True, ark=False), "T4": dict(cork=True, wax=True, ark=True)}
CAPS = {PRE + t: 1500 for t in TIERS}
SOCKETS = {PRE + t: ["SOCKET_Grip"] for t in TIERS}
PALETTE = {"glass": (0.7, 0.9, 1.0), "wood": (0.55, 0.36, 0.2), "red": (0.8, 0.2, 0.2), "arkglass": (0.12, 0.42, 0.36)}   # linear, = amf_items.P (+ arkglass)


def l2s_hex(c):
    out = ""
    for v in c:
        s = v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
        out += "%02X" % max(0, min(255, int(round(s * 255))))
    return out


def amf_mat(slot, key, label, rough, metal=0.0):
    return dict(K.material("x", slot, label, l2s_hex(PALETTE[key]), rough, metal), name="M_AMF_" + key)


# (radius, z) outer profiles. Standard bottle 0.22 m; ark glass is squat and thick-walled.
STD = [(0.038, 0.0), (0.044, 0.006), (0.045, 0.02), (0.045, 0.12), (0.041, 0.142), (0.026, 0.16), (0.0145, 0.172), (0.0145, 0.196), (0.0175, 0.199), (0.0175, 0.207), (0.012, 0.208)]
ARK = [(0.046, 0.0), (0.052, 0.008), (0.053, 0.025), (0.053, 0.105), (0.048, 0.128), (0.03, 0.146), (0.0175, 0.156), (0.0175, 0.18), (0.022, 0.184), (0.022, 0.194), (0.0145, 0.195)]


def bottle(name, cork=False, wax=False, ark=False, seed=SEED):
    """The generator. cork/wax/ark are independent toggles (wax needs cork: it seals over it)."""
    if wax and not cork:
        raise ValueError("wax seals over a cork")
    a = PRE + name; prof = ARK if ark else STD; top = prof[-1][1]; neck_r = prof[-4][0]; lip_r = prof[-2][0]
    mats = [amf_mat(0, "arkglass" if ark else "glass", "ark glass (blue-green, from hull ports)" if ark else "bottle glass", 0.08 if ark else 0.05)]
    P = [K.lathe("Bottle", prof, (0, 0, 0), 0, 20 if ark else 16, cap_bottom=True, cap_top=True, lod1={"segments": 10 if ark else 8})]
    if ark:   # melted hull-port rim: a raised band around the body
        P.append(K.lathe("PortBand", [(0.053, 0.058), (0.0565, 0.064), (0.0565, 0.072), (0.053, 0.078)], (0, 0, 0), 0, 20, cap_bottom=False, cap_top=False, lod1={"segments": 10}))
    if cork:
        mats.append(amf_mat(len(mats), "wood", "cork", 0.9)); cs = len(mats) - 1
        P.append(K.cyl("Cork", "z", neck_r - 0.002, neck_r + 0.0005, 0.03, (0, 0, round(top + 0.003, 5)), cs, 12, lod1={"segments": 6}))
    if wax:
        mats.append(amf_mat(len(mats), "red", "sealing wax", 0.45)); ws = len(mats) - 1; ct = top + 0.018
        P.append(K.lathe("WaxCap", [(lip_r + 0.002, top - 0.014), (lip_r + 0.003, top - 0.004), (neck_r + 0.003, ct - 0.002), (neck_r - 0.004, ct + 0.003)], (0, 0, 0), ws, 14,
                         cap_bottom=False, cap_top=True, lod1={"segments": 7}))
        r = K.rng(seed, a)
        for i in range(3):                                        # drips down the neck
            ang = 70 + 120 * i + r.uniform(-20, 20); L = r.uniform(0.012, 0.022)
            x, y = (lip_r + 0.0015) * math.cos(math.radians(ang)), (lip_r + 0.0015) * math.sin(math.radians(ang))
            P.append(K.box("Drip%d" % i, (0.004, 0.004, round(L, 4)), (round(x, 5), round(y, 5), round(top - 0.014 - L / 2 + 0.002, 5)), ws, rot=(0, 0, round(ang, 3)), bevel=False, lod1={"drop": True}))
        P.append(K.cyl("Seal", "z", neck_r + 0.001, neck_r + 0.001, 0.003, (0, 0, round(ct + 0.0045, 5)), ws, 12, lod1={"drop": True}))   # stamped medallion on top
    body_r = max(p[0] for p in prof)
    m = {"asset": a, "kind": "Item", "seed": seed, "tier": name, "toggles": {"cork": cork, "wax": wax, "ark_glass": ark},
         "spec": {"gap": "G45", "ask": "art-master-flex 49039", "size_m": "hand prop, ~0.2-0.24 m tall", "tri_cap": 1500, "lod": "LOD0/1", "collision": "UCX prism",
                  "sockets": ["Grip"], "held": "attach socket +X up the bottle (rod/bat convention)", "pipeline": "Kennel amf_items naming + M_AMF_ palette"},
         "materials": mats, "objects": [K.obj(a, P)],
         "sockets": [K.socket("Grip", (0, 0, round(0.42 * top, 4)), forward=(0, 0, 1), attach=((0, 0, 1), (0, 1, 0)))], "nanite": True}
    K.finish(m); h = m["predicted"]["dimensions"][2]
    m["collision"] = [K.ucx_prism(a, 0, "z", round(body_r + (0.004 if ark else 0), 4), round(h, 4), (0, 0, round(h / 2, 4)), 10)]
    return K.finish(m)


def assets(seed=SEED):
    return [bottle(t, seed=seed, **TIERS[t]) for t in TIERS]


def extra_checks(A):
    B = [A[PRE + t] for t in TIERS]
    mats = [[x["name"] for x in m["materials"]] for m in B]
    return [("T1 plain, T2 cork, T3 cork + wax, T4 ark glass + cork + wax", [m["toggles"] for m in B] == [{"cork": c, "wax": w, "ark_glass": k} for c, w, k in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1))]),
            ("materials follow the tier table (bottle/cork/wax/ark glass)", mats == [["M_AMF_glass"], ["M_AMF_glass", "M_AMF_wood"], ["M_AMF_glass", "M_AMF_wood", "M_AMF_red"], ["M_AMF_arkglass", "M_AMF_wood", "M_AMF_red"]], mats),
            ("Kennel palette colours (linear = amf_items.P)", all(x["hex"] == l2s_hex(PALETTE[x["name"][6:]]) for m in B for x in m["materials"])),
            ("ark glass reads blue-green", PALETTE["arkglass"][1] > PALETTE["arkglass"][0] and PALETTE["arkglass"][2] > PALETTE["arkglass"][0]),
            ("ark glass is thicker and squatter than standard glass", B[3]["predicted"]["dimensions"][0] > B[0]["predicted"]["dimensions"][0] + 0.01 and B[3]["predicted"]["dimensions"][2] < B[2]["predicted"]["dimensions"][2]),
            ("hand-prop size (0.15-0.26 m tall, <= 0.12 m wide)", all(0.15 <= m["predicted"]["dimensions"][2] <= 0.26 and m["predicted"]["dimensions"][0] <= 0.12 for m in B), [m["predicted"]["dimensions"] for m in B]),
            ("every bottle has a Grip attach socket on the body", all(m["sockets"][0]["name"] == "SOCKET_Grip" and m["sockets"][0].get("attach") and 0.04 < m["sockets"][0]["location"][2] < 0.12 for m in B)),
            ("wax without cork is refused", _refuses())]


def _refuses():
    try:
        bottle("X", cork=False, wax=True)
    except ValueError:
        return True
    return False


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], [x["name"] for x in m["materials"]])
