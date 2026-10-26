# SPDX-License-Identifier: MIT
"""G91 Lichen Clock survey tool (pythagoras 49650, pyth-g91-assets-20261019; code main 1d8ebbe9 LichenClock.measure(event, boulder, n)
is "the calipers interaction"), blender-kit/v1. Surveyor Tamsin Coire's 0.2 m vernier calipers, lying flat (beam along +X, jaws -Y).
  Prop_Survey_Calipers         frame: 200 mm steel beam with a 0-150 mm engraved scale, fixed outside jaw + small inside jaw.
                               SOCKET_Grip (held-prop attach, +X along the beam, +Z up the face), SOCKET_Slide (jaw mover origin, closed),
                               SOCKET_JawTip (measuring point, fixed jaw tip). Root UCX only (UEB 48812).
  Prop_Survey_Calipers_Jaw     mover: slider with vernier window, moving jaw, thumb wheel, lock screw. Origin = SOCKET_Slide.
                               Hinge motion "slide": translate along +X (UE +X), travel 0-0.15 m; jaw gap mm = offset m x 1000,
                               so the UE side can show LichenClock.measure()'s largest diameter directly. Own UCX.
  Prop_Survey_Calipers_Static  assembled single mesh, jaw open 60 mm (a Decal_Rock_Lichen_L thallus), for placement / pickups.
REUSE check: no calipers or measuring tool in the catalog. Boulders reuse the rock kits (not built).
Usage: python survey_g91.py --out data/contest/survey_g91.kit.json"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import kitlib as K

SEED = 9192
CAL, JAW, STATIC = "Prop_Survey_Calipers", "Prop_Survey_Calipers_Jaw", "Prop_Survey_Calipers_Static"
CAPS = {CAL: 1500, JAW: 600, STATIC: 2000}
SOCKETS = {CAL: ["SOCKET_Grip", "SOCKET_JawTip", "SOCKET_Slide"], JAW: ["SOCKET_Slide"], STATIC: ["SOCKET_Grip", "SOCKET_JawTip"]}
SPEC = {"gap": "G91", "ask": "pythagoras 49650", "lod": "LOD0/1"}
T, BEAM_L, BEAM_W = 0.0035, 0.2, 0.016
XF = -0.088                     # fixed jaw inner face = slider zero
TRAVEL, OPEN_STATIC = 0.15, 0.06
TIP_Y = -0.056
SLIDE_HINGE = {"socket": "SOCKET_Slide", "mover": JAW, "pivot_m": [XF, 0.0, 0.0], "motion": "slide", "slide_axis_blender": [1, 0, 0], "slide_axis_ue": [1, 0, 0],
               "travel_m": [0.0, TRAVEL], "reading": "jaw gap mm = slide offset (m) x 1000; LichenClock.measure() diameter", "open_blender_euler_deg": None, "open_ue_rotator": None}


def mats(a):
    return [K.material(a, 0, "stainless steel", "B9BFC6", 0.32, metallic=0.9), K.material(a, 1, "engraved marks", "1E2124", 0.6), K.material(a, 2, "brass wheel / screw", "B08D57", 0.4, metallic=0.85)]


def bx(name, x0, x1, y0, y1, z0, z1, slot, lod1=None, bevel=False):
    return K.box(name, (x1 - x0, y1 - y0, z1 - z0), ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), slot, bevel=bevel, lod1=lod1)


def frame_parts():
    P = [bx("Beam", -BEAM_L / 2, BEAM_L / 2, -BEAM_W / 2, BEAM_W / 2, 0, T, 0),
         bx("FixedJaw", -BEAM_L / 2, XF, -0.05, -BEAM_W / 2, 0, T, 0), bx("FixedJawTip", XF - 0.004, XF, -0.062, -0.05, 0, T, 0),
         bx("FixedInnerJaw", XF - 0.006, XF, BEAM_W / 2, 0.024, 0, T, 0)]
    for i in range(31):                                   # main scale 0-150 mm: cm marks long, half-cm short
        x = XF + 0.005 * i; ln = 0.006 if i % 2 == 0 else 0.0035
        P.append(bx("Tick%02d" % i, x - 0.0003, x + 0.0003, BEAM_W / 2 - 0.0005 - ln, BEAM_W / 2 - 0.0005, T, T + 0.0003, 1, lod1=None if i % 2 == 0 else {"drop": True}))
    return P


def jaw_parts(dx=0.0):
    """Moving jaw parts in frame coordinates at slide offset dx (0 = closed)."""
    x = XF + dx; H = T + 0.0035
    return [bx("Slider", x, x + 0.038, -0.012, 0.012, 0, H, 0),
            bx("MovingJaw", x, x + 0.012, -0.05, -0.012, 0, T, 0), bx("MovingJawTip", x, x + 0.004, -0.062, -0.05, 0, T, 0),
            bx("MovingInnerJaw", x, x + 0.006, 0.012, 0.024, 0, T, 0),
            bx("VernierWindow", x + 0.008, x + 0.032, 0.002, 0.009, H, H + 0.0004, 1, lod1={"drop": True}),
            K.cyl("ThumbWheel", "y", 0.0052, 0.0052, 0.004, (x + 0.031, -0.0145, 0.0052), 2, 12, lod1={"segments": 6}),
            K.cyl("LockScrew", "z", 0.003, 0.003, 0.004, (x + 0.019, -0.006, H + 0.002), 2, 8, lod1={"drop": True})]


def shift(parts, d):
    return [dict(q, centre=[round(q["centre"][i] - d[i], 5) + 0.0 for i in range(3)]) for q in parts]


def frame_sockets():
    return [K.socket("Grip", (0.05, 0, T / 2), forward=(1, 0, 0), attach=((1, 0, 0), (0, 0, 1))), K.socket("Slide", (XF, 0, 0), forward=(1, 0, 0)),
            K.socket("JawTip", (XF, TIP_Y, T / 2), forward=(1, 0, 0))]


def frame(seed=SEED):
    a = CAL
    m = {"asset": a, "kind": "Prop", "seed": seed, "frame_of": [JAW], "hinges": [SLIDE_HINGE],
         "spec": dict(SPEC, size_m="200 mm calipers (scale 0-150 mm)", tri_cap=CAPS[a], collision="UCX beam + jaw", sockets=["Grip", "Slide", "JawTip"],
                      held="attach socket +X along the beam, +Z up the scale face", split="frame glb (UEB 48812): jaw mover at SOCKET_Slide, slides +X"),
         "materials": mats(a), "objects": [K.obj(a, frame_parts())], "sockets": frame_sockets(),
         "collision": [K.ucx_box(a, 0, (BEAM_L, BEAM_W, T), (0, 0, T / 2)), K.ucx_box(a, 1, (BEAM_L / 2 + XF, 0.054, T), ((-BEAM_L / 2 + XF) / 2, -0.035, T / 2))], "nanite": False}
    return K.finish(m)


def jaw(seed=SEED):
    a = JAW
    m = {"asset": a, "kind": "Prop", "seed": seed, "mover_of": CAL, "hinge": SLIDE_HINGE,
         "spec": dict(SPEC, split="mover glb (UEB 48812): origin = SOCKET_Slide (closed); translate +X 0-0.15 m"), "materials": mats(a),
         "objects": [K.obj(a, shift(jaw_parts(), (XF, 0, 0)), role="mover; origin at the slide zero (frame SOCKET_Slide); slides +X")],
         "sockets": [K.socket("Slide", (0, 0, 0), forward=(1, 0, 0))],
         "collision": [K.ucx_box(a, 0, (0.038, 0.086, T + 0.0035), (0.019, -0.019, (T + 0.0035) / 2))],
         "off_centre_ok": "origin is the slide zero at the jaw face (attach at %s SOCKET_Slide)" % CAL, "nanite": False}
    return K.finish(m)


def static(seed=SEED):
    a = STATIC
    m = {"asset": a, "kind": "Prop", "seed": seed, "jaw_open_mm": round(OPEN_STATIC * 1000),
         "spec": dict(SPEC, size_m="200 mm calipers, jaw open 60 mm", tri_cap=CAPS[a], collision="UCX box", sockets=["Grip", "JawTip"], state="assembled single mesh; ship frame + jaw for gameplay"),
         "materials": mats(a), "objects": [K.obj(a, frame_parts() + jaw_parts(OPEN_STATIC))], "sockets": [s for s in frame_sockets() if s["name"] != "SOCKET_Slide"],
         "collision": [K.ucx_box(a, 0, (BEAM_L, 0.086, T + 0.0035), (0, -0.019, (T + 0.0035) / 2))], "nanite": False}
    return K.finish(m)


def assets(seed=SEED):
    return [frame(seed), jaw(seed), static(seed)]


def extra_checks(A):
    F, J, S = A[CAL], A[JAW], A[STATIC]; fs = {s["name"]: s["location"] for s in F["sockets"]}
    jp = {q["name"]: q for q in J["objects"][0]["parts"]}
    return [("calipers ~0.2 m long", abs(F["predicted"]["dimensions"][0] - 0.2) < 1e-6, F["predicted"]["dimensions"]),
            ("closed: moving jaw face meets the fixed jaw face (zero)", abs(jp["MovingJaw"]["centre"][0] - jp["MovingJaw"]["size"][0] / 2) < 1e-9),
            ("full travel keeps the slider on the beam", XF + TRAVEL + 0.038 <= BEAM_L / 2 + 1e-9),
            ("slide hinge on frame socket, +X, 0-150 mm", F["hinges"][0]["socket"] == "SOCKET_Slide" and fs["SOCKET_Slide"] == [XF, 0, 0] and F["hinges"][0]["travel_m"] == [0.0, 0.15]
             and F["hinges"][0]["slide_axis_ue"] == [1, 0, 0]),
            ("scale has 31 marks 0-150 mm", sum(1 for q in F["objects"][0]["parts"] if q["name"].startswith("Tick")) == 31),
            ("static jaw gap 60 mm", abs(next(q for q in S["objects"][0]["parts"] if q["name"] == "MovingJaw")["centre"][0] - 0.006 - XF - 0.06) < 1e-9),
            ("Grip is a held-prop attach socket", "attach" in next(s for s in F["sockets"] if s["name"] == "SOCKET_Grip"))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=SEED); ap.add_argument("--out", required=True); o = ap.parse_args()
    A = assets(o.seed); K.write(A, o.out)
    for m in A: print(m["asset"], m["predicted"]["triangles"], m["predicted"]["lod1_triangles"], m["predicted"]["lod1_ratio"], m["predicted"]["dimensions"], m["predicted"]["bounds_min"])
