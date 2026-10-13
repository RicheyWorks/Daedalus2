"""Hephaestus Island preflight (runs outside the editor, no Unreal calls).

Checks every asset in data/islands/hephaestus/layout.json against the Unreal project's Content folder
(/Game/Daedalus/Art/<Kind>/<name> -> Content/Daedalus/Art/<Kind>/<name>/**.uasset) and the art GLB drop,
so a turn never burns editor minutes on meshes that are missing. Also counts the living-check categories
(water / livestock / herbs) the in-editor turn enforces. Writes preflight.json next to the layout.

usage: python tools/islands/hephaestus/heph_preflight.py [--content C:/Unreal/DaedalusRealm/Content] [--glb DIR]
"""
import argparse, collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LAYOUT = os.path.join(REPO, "data", "islands", "hephaestus", "layout.json")
KIND = {"Prop", "Item", "Tool", "Bld", "Mob", "Veh", "Wpn"}
ENGINE = {"WaterPlane_HotSpring"}  # placed from /Engine/BasicShapes, always available


def kind_of(name):
    k = name.split("_", 1)[0]
    return k if k in KIND else "Prop"


def category(name):
    if name.startswith("WaterPlane") or name.startswith("Prop_Water"): return "water"
    if name.startswith("Mob_"): return "livestock"
    if name.startswith("Item_Herb_"): return "herbs"
    return "other"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", default=os.environ.get("HEPH_CONTENT", r"C:\Unreal\DaedalusRealm\Content"))
    ap.add_argument("--glb", default=os.environ.get("HEPH_GLB", r"C:\Users\730ri\projects\bot-team\art\glb"))
    ap.add_argument("--layout", default=LAYOUT)
    a = ap.parse_args(argv)
    lay = json.load(open(a.layout, encoding="utf-8"))
    uses = collections.Counter(p["asset"] for p in lay["placements"])
    glbs = {os.path.splitext(f)[0].lower() for f in os.listdir(a.glb)} if os.path.isdir(a.glb) else set()
    rows, living = [], collections.Counter()
    lod1_ready = []
    for name, n in sorted(uses.items()):
        living[category(name)] += n
        has_lod1 = (name + "_lod1").lower() in glbs
        if has_lod1:
            lod1_ready.append(name)
        if name in ENGINE:
            status = "engine"
        else:
            d = os.path.join(a.content, "Daedalus", "Art", kind_of(name), name)
            in_ue = os.path.isdir(d) and any(f.endswith(".uasset") for _, _, fs in os.walk(d) for f in fs)
            status = "in_unreal" if in_ue else ("glb_only" if name.lower() in glbs else "missing")
        rows.append({"asset": name, "uses": n, "category": category(name), "status": status, "lod1": has_lod1})
    by = collections.Counter(r["status"] for r in rows)
    out = {"island": lay.get("island", "hephaestus"), "placements": sum(uses.values()), "unique_assets": len(rows),
           "status": dict(by), "living": {k: living[k] for k in ("water", "livestock", "herbs")},
           "living_ok": all(living[k] > 0 for k in ("water", "livestock", "herbs")),
           "blocking": [r["asset"] for r in rows if r["status"] == "missing"],
           "needs_import": [r["asset"] for r in rows if r["status"] == "glb_only"],
           "lod1_ready": lod1_ready, "lod1_count": len(lod1_ready), "assets": rows}
    path = os.path.join(os.path.dirname(a.layout), "preflight.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "assets"}, indent=1))
    return 0 if out["living_ok"] and not out["blocking"] else 1


if __name__ == "__main__":
    sys.exit(main())
