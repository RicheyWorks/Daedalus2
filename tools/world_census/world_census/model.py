"""Merge sources into one census: assets, worlds, totals."""
import re, os, datetime
from collections import defaultdict, Counter

BUCKETS = ["in_unreal", "ready", "in_progress", "blender_only", "rejected"]
SUPPORT_RX = re.compile(r"(^|/)(materials|textures)/|^(m|mi|t|mat)_|^chunk_|^pcg_|^sw_|^bp_|^wbp_", re.I)


def stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def kind_of(name, cfg):
    k = name.split("_")[0]
    return k if k in cfg["kinds"] else ""


def world_of(name, path, notes, cfg):
    toks = name.split("_")
    for t in toks[1:3]:
        if t in cfg["tags"]:
            return cfg["tags"][t]
    lp = (path or "").lower()
    for frag, w, o in cfg["folders"]:
        if frag in lp:
            return [w, o]
    for t, (w, o) in cfg["tags"].items():
        if re.search(r"\b" + re.escape(t) + r"\b", notes or ""):
            return [w, o]
    if name.lower().startswith("poot"):
        return cfg["tags"]["Poot"]
    if kind_of(name, cfg):
        return [cfg["default_world"], "shared"]
    return [cfg["unassigned"], "unknown"]


def category_of(name, kind, cfg):
    s = (kind + "_ " + name).lower()
    for cat, kws in cfg["categories"]:
        if any(k in s for k in kws):
            return cat
    return "other"


def build(src, cfg):
    assets = {}
    support = Counter()

    def get(name):
        key = name.lower()
        if key not in assets:
            assets[key] = {"name": name, "queue_status": "", "queue_kind": "", "notes": "",
                           "blender_paths": [], "unreal_paths": []}
        return assets[key]

    for r in src["queue"]:
        if not r["name"]:
            continue
        a = get(r["name"]); a.update(queue_status=r["status"], queue_kind=r["kind"], notes=r["notes"])
    for p in src["art_files"]:
        get(stem(p))["blender_paths"].append(p)
    for p in src["uassets"]:
        if SUPPORT_RX.search(p.split("/")[-1]) or SUPPORT_RX.search(p):
            support[p.split("/")[1] if "/" in p else p] += 1
            continue
        get(stem(p))["unreal_paths"].append(p)

    rows = []
    for a in assets.values():
        n = a["name"]; kind = kind_of(n, cfg) or a["queue_kind"]
        path = (a["unreal_paths"] or a["blender_paths"] or [""])[0]
        world, owner = world_of(n, " ".join(a["blender_paths"] + a["unreal_paths"]), a["notes"], cfg)
        qs = a["queue_status"]
        if qs == "SHIPPED" or a["unreal_paths"]:
            b = "in_unreal"
        elif qs in ("READY", "SHIPPING"):
            b = "ready"
        elif qs in ("TODO", "DOING", "BLOCKED"):
            b = "in_progress"
        elif qs == "REJECTED":
            b = "rejected"
        else:
            b = "blender_only"
        if b == "in_unreal" and not a["unreal_paths"] and "in Unreal:" in a["notes"]:
            path = a["notes"].split("in Unreal:")[-1].strip()
        rows.append({"name": n, "kind": kind, "category": category_of(n, kind, cfg), "world": world,
                     "owner": owner, "status": b, "queue_status": qs or "-",
                     "blender_files": len(a["blender_paths"]), "uassets": len(a["unreal_paths"]), "path": path})
    rows.sort(key=lambda r: (r["world"], r["category"], r["name"]))

    inv = defaultdict(Counter)
    for r in rows:
        inv[(r["world"], r["category"])][r["status"]] += 1
    inventory = [dict(world=w, category=c, **{b: cnt[b] for b in BUCKETS}, total=sum(cnt.values()))
                 for (w, c), cnt in sorted(inv.items())]

    def tot(key):
        t = defaultdict(Counter)
        for r in rows:
            t[r[key]][r["status"]] += 1
        return [dict(**{key: k}, **{b: c[b] for b in BUCKETS}, total=sum(c.values())) for k, c in sorted(t.items())]

    tw = tot("world"); have = {r["world"] for r in tw}
    tw += [dict(world=w, **{b: 0 for b in BUCKETS}, total=0) for w in cfg.get("worlds", []) if w not in have]
    tw.sort(key=lambda r: r["world"])
    grand = Counter(r["status"] for r in rows)
    comp = src["competition"]; grid = comp["grid"]
    tracker = {t.get("Bot", ""): t for t in comp["island_tracker"]}
    owner_world = {}
    for r in rows:
        owner_world.setdefault(r["owner"], r["world"])
    islands = []
    for bot in sorted(set(grid) | set(tracker)):
        t = tracker.get(bot, {})
        islands.append({"bot": bot, "island": t.get("Island", owner_world.get(bot, "")), "ark_origin": grid.get(bot, ""),
                        "items_reported": t.get("Items n/500", ""), "herb_mechanic": t.get("Herb combo", ""),
                        "livestock_food": t.get("Livestock + food", ""), "water": t.get("Drinkable water", ""),
                        "in_unreal_reported": t.get("In Unreal", ""),
                        "assets_counted": sum(1 for r in rows if r["owner"] == bot)})
    return {
        "generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "grand_total": dict(**{b: grand[b] for b in BUCKETS}, total=len(rows)),
        "totals_by_world": tw, "totals_by_owner": tot("owner"), "totals_by_category": tot("category"),
        "inventory": inventory, "islands": islands, "realms": src["realms"], "island_docs": src["island_docs"],
        "registries": src["registries"], "unreal_support_files": dict(support),
        "source_counts": {"queue_rows": len(src["queue"]), "art_files": len(src["art_files"]),
                          "uassets": len(src["uassets"])},
        "assets": rows,
    }
