"""capture/v1: engine-free job schema for in-game proof captures (youtube-master).

A job names one island sublevel, its origin and a list of views (eye/target offsets in cm from the origin),
plus an optional short Movie Render Queue clip. This module validates jobs, turns views into camera
rotations, and builds the manifest.json that a registry row links to as IN-GAME-DEMO evidence.
No Unreal import here, so it runs and is tested anywhere (python -m unittest)."""
import json, math, re, datetime

SCHEMA = "capture/v1"
NAME_RE = re.compile(r"^[a-z0-9_]{1,40}$")
DEFAULTS = {"width": 1600, "height": 900, "fov": 70.0, "ev100": 9.0, "basecolor": True,
            "out_dir": r"C:\Users\730ri\projects\bot-team\art\NOTES\captures"}

class JobError(ValueError):
    pass

def _vec(v, what):
    if not (isinstance(v, (list, tuple)) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v)):
        raise JobError("%s must be [x, y, z] numbers" % what)
    return [float(x) for x in v]

def load(text_or_dict):
    """Parse + validate a job; returns a normalised dict (defaults filled). Raises JobError."""
    j = json.loads(text_or_dict) if isinstance(text_or_dict, str) else dict(text_or_dict)
    if j.get("schema") != SCHEMA: raise JobError("schema must be %r" % SCHEMA)
    for k in ("component", "sublevel"):
        if not isinstance(j.get(k), str) or not j[k]: raise JobError("%s is required" % k)
    if not NAME_RE.match(j.get("name", "")): raise JobError("name must match %s" % NAME_RE.pattern)
    j["origin"] = _vec(j.get("origin"), "origin")
    views = j.get("views")
    if not isinstance(views, list) or not 1 <= len(views) <= 24: raise JobError("views must be a list of 1-24")
    seen = set(); out = []
    for i, v in enumerate(views):
        n = v.get("name", "")
        if not NAME_RE.match(n): raise JobError("view %d name invalid" % i)
        if n in seen: raise JobError("duplicate view %s" % n)
        seen.add(n); e = _vec(v.get("eye"), n + ".eye"); t = _vec(v.get("target"), n + ".target")
        if e == t: raise JobError("view %s eye == target" % n)
        out.append({"name": n, "eye": e, "target": t})
    j["views"] = out
    for k, d in DEFAULTS.items(): j.setdefault(k, d)
    if not (64 <= j["width"] <= 3840 and 64 <= j["height"] <= 2160): raise JobError("width/height out of range")
    c = j.get("clip")
    if c is not None:
        if not isinstance(c.get("sequence"), str) or not c["sequence"].startswith("/Game/"): raise JobError("clip.sequence must be a /Game/ path")
        c.setdefault("start", 0); c.setdefault("frames", 180); c.setdefault("fps", 30); c.setdefault("min_free_gb", 2.0)
        if not 1 <= c["frames"] <= 900: raise JobError("clip.frames must be 1-900 (keep it short: 10-min editor turns)")
        j["clip"] = c
    return j

def rotation(eye, target):
    """(pitch, yaw) in degrees so a camera at eye looks at target (Unreal: X forward, Z up)."""
    dx, dy, dz = (target[i] - eye[i] for i in range(3))
    return math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx))

def plan(job):
    """World-space camera plan: [{name, eye(world), pitch, yaw, file}]."""
    o = job["origin"]; p = []
    for v in job["views"]:
        e = [o[i] + v["eye"][i] for i in range(3)]; t = [o[i] + v["target"][i] for i in range(3)]
        pitch, yaw = rotation(e, t)
        p.append({"name": v["name"], "eye": e, "pitch": pitch, "yaw": yaw, "file": "%s_%s.png" % (job["name"], v["name"])})
    return p

def manifest(job, written, commit="unknown", errors=(), now=None, clip=None):
    """Evidence record. `written` = list of file names actually exported. Times are PT-labelled local time."""
    now = now or datetime.datetime.now()
    return {"schema": SCHEMA + "/manifest", "component": job["component"], "job": job["name"], "sublevel": job["sublevel"],
            "commit": commit, "captured_at": now.strftime("%Y-%m-%d %H:%M PT"), "files": list(written),
            "expected": [p["file"] for p in plan(job)], "complete": all(p["file"] in written for p in plan(job)),
            "errors": list(errors), "clip": clip}
