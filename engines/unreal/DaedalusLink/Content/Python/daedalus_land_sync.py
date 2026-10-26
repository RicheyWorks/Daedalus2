# SPDX-License-Identifier: MIT
"""Keep the editor's lands in step with the server's land registry (Sol's REALM-LAND-API.md, BASE-LAYER row 11).

    import daedalus_land_sync as S
    S.sync("WORLD-ZERO")                 # fetch every hub district (44,45,54,55), reconcile, move/tag, save
    S.sync("GALLERY-CITY", districts=[55], apply=False)   # dry run: the report only

For each district: GET {server}/api/v1/realms/{REALM}/lands?district=d (bearer token from the daedalus.Token
cvar or DAEDALUS_TOKEN), read it with the same rules as DaedalusLandRegistryCore.h (schema 1, size 1..4,
int64 seeds as text), then against the plots daedalus_plots laid down (labels Land_<n> / Land_<Realm>_<n>):
  agree       -> tag Registry:rev=<r>
  moved       -> the editor follows the server: the plot moves to the server's cell, tagged
  only server -> a plot is laid for it (the server knows a land we never plotted)
  only editor -> left alone, tagged Registry:unlisted (the server has no row; nothing is deleted)
  reserved    -> left alone, tagged Registry:reserved (a plot on a cell the server reserves)
No ownership is implied by any of this (Sol 29151). Pure parts (read, reconcile) are testable headless.
"""
import json
import os

import daedalus_land_grid as G

SERVER = "http://localhost:8088"


def read_district(text):
    """The DTO as a dict with the same refusals as the C++ reader: returns (district, why)."""
    try:
        d = json.loads(text)
    except ValueError as e:
        return None, "json: %s" % e
    if not isinstance(d, dict):
        return None, "not an object"
    if d.get("schemaVersion") != 1:
        return None, "schemaVersion %r (want 1)" % d.get("schemaVersion")
    if not d.get("realm") or not (0 <= int(d.get("district", -1)) <= 99):
        return None, "realm/district missing"
    lands = d.get("lands")
    if not isinstance(lands, list):
        return None, "no lands array"
    out = []
    for l in lands:
        try:
            row = {"n": int(l["landNumber"]), "x": int(l["cellX"]), "y": int(l["cellY"]), "size": int(l.get("size", 1)),
                   "seed": str(l.get("seed", "")), "east_m": float(l.get("originEastMetres", 0.0)), "north_m": float(l.get("originNorthMetres", 0.0))}
        except (KeyError, TypeError, ValueError):
            return None, "bad land row"
        if row["n"] < 0 or row["x"] < 0 or row["y"] < 0 or not 1 <= row["size"] <= 4:
            return None, "bad land row"
        out.append(row)
    return {"realm": d["realm"], "revision": int(d.get("revision", 0)), "district": int(d["district"]),
            "pitch_m": float(d.get("pitchMetres", G.PITCH_M)), "reserved": [int(c) for c in d.get("reservedCells", [])], "lands": out}, ""


def in_district(district, x, y):
    return x // 10 == district % 10 and y // 10 == district // 10


def reconcile(district, plots):
    """plots: {n: (x, y, size)} the editor's. Returns the report dict (same five buckets as the C++ Report)."""
    server = {l["n"]: l for l in district["lands"]}
    editor = {n: p for n, p in plots.items() if in_district(district["district"], p[0], p[1])}
    reserved = set(district["reserved"])
    r = {"revision": district["revision"], "district": district["district"], "agree": [], "moved": [], "only_server": [], "only_editor": [], "reserved_plotted": []}
    for n, l in sorted(server.items()):
        p = editor.get(n)
        if p is None:
            r["only_server"].append(l)
        elif p == (l["x"], l["y"], l["size"]):
            r["agree"].append(n)
        else:
            r["moved"].append((n, l))
    for n, p in sorted(editor.items()):
        if n not in server:
            r["only_editor"].append(n)
        if G.number(p[0], p[1]) in reserved:
            r["reserved_plotted"].append(n)
    return r


def describe(r):
    return "rev=%d district=%d agree=%d moved=%d only_server=%d only_editor=%d reserved_plotted=%d" % (
        r["revision"], r["district"], len(r["agree"]), len(r["moved"]), len(r["only_server"]), len(r["only_editor"]), len(r["reserved_plotted"]))


# ---- editor side ----------------------------------------------------------------------------------------------

def _server():
    import unreal
    s = unreal.SystemLibrary.get_console_variable_string_value("daedalus.Server") or SERVER
    return s.rstrip("/")


def _token():
    import unreal
    try:
        t = unreal.SystemLibrary.get_console_variable_string_value("daedalus.Token")
    except Exception:
        t = ""
    return t or os.environ.get("DAEDALUS_TOKEN", "")


def fetch(realm, district, timeout=10):
    """(district dict, why): one GET; a 404 means the server has no layout for this realm (not an error)."""
    import urllib.request
    import urllib.error
    url = "%s/api/v1/realms/%s/lands?district=%d" % (_server(), realm, district)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + _token()} if _token() else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return read_district(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return None, "http %d" % e.code
    except (OSError, ValueError) as e:
        return None, "unreachable: %s" % e


def _plots(realm):
    """{n: (x, y, size, actor)} from the level: plots by label, estates (World Zero islands) by the spiral plan."""
    import unreal
    import daedalus_plots as P
    out = {}
    for label, a in P._existing(realm).items():
        if label.endswith("_Sign"):
            continue
        n = int(label.split("_")[-1])
        x, y = G.cell(n)
        out[n] = (x, y, 1, a)
    if realm == "WORLD-ZERO":
        import daedalus_layout as L
        for r in L.spiral_plan()["plan"]:
            out[r["deed"]] = (r["cell"][0], r["cell"][1], r["estate"], None)
    return out


def hub_districts():
    """The four districts the hub rings 1..6 touch."""
    return sorted({G.district(n) for n in range(0, 169)})


def sync(realm, districts=None, apply=True):
    import unreal
    import daedalus_plots as P
    import daedalus_realm_ground as R
    plots = _plots(realm)
    origin = R.ORIGINS[realm]
    ground = R.GROUND_Z
    reports, actions = [], {"tagged": 0, "moved": 0, "laid": 0, "unlisted": 0, "reserved": 0}
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for d in (districts or hub_districts()):
        dist, why = fetch(realm, d)
        if not dist:
            reports.append({"district": d, "error": why})
            continue
        r = reconcile(dist, {n: p[:3] for n, p in plots.items()})
        reports.append(describe(r))
        if not apply:
            continue
        rev = unreal.Name("Registry:rev=%d" % r["revision"])
        for n in r["agree"]:
            a = plots[n][3]
            if a:
                a.tags = [t for t in a.tags if not str(t).startswith("Registry:")] + [rev]
                actions["tagged"] += 1
        for n, l in r["moved"]:
            a = plots[n][3]
            if a:
                mx, my = (l["x"] - G.HUB) * dist["pitch_m"], (l["y"] - G.HUB) * dist["pitch_m"]
                a.modify(True)
                a.set_actor_location(unreal.Vector(origin[0] + mx * 100.0, origin[1] + my * 100.0, a.get_actor_location().z), False, False)
                a.tags = [t for t in a.tags if not str(t).startswith(("Registry:", "Deed:"))] + [rev, unreal.Name("Deed:%d" % n)]
                actions["moved"] += 1
        for l in r["only_server"]:
            mx, my = (l["x"] - G.HUB) * dist["pitch_m"], (l["y"] - G.HUB) * dist["pitch_m"]
            P.lay_one(realm, l["n"], (origin[0] + mx * 100.0, origin[1] + my * 100.0, ground), G.district(l["n"]), size=l["size"])
            actions["laid"] += 1
        for n in r["only_editor"]:
            a = plots[n][3]
            if a and not any(str(t) == "Registry:unlisted" for t in a.tags):
                a.tags = list(a.tags) + [unreal.Name("Registry:unlisted")]
                actions["unlisted"] += 1
        for n in r["reserved_plotted"]:
            a = plots[n][3]
            if a and not any(str(t) == "Registry:reserved" for t in a.tags):
                a.tags = list(a.tags) + [unreal.Name("Registry:reserved")]
                actions["reserved"] += 1
    if apply and any(actions.values()):
        P.save_world()
    return {"realm": realm, "server": _server(), "reports": reports, "actions": actions}
