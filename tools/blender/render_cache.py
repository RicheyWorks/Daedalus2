# SPDX-License-Identifier: MIT
"""Which finished render may be reused, and how its sidecar is written. Pure Python (no bpy), so it is unit-tested.

A shot is reusable only when everything that decides its pixels matches what produced it:
  * the source GLBs, by size and sha256;
  * samples, resolution, view, focus and frame (the camera);
  * the scene adjustment identity: whatever adjust() changes (a tide offset, say), as a JSON-serialisable value.
    A shot rendered with an adjust() hook but no identity is never reused, because nothing says what it changed.
  * the PNG itself, by sha256 (a half-written or edited image is a miss).
All of these go into one canonical cache_key stored in the sidecar. A sidecar that is missing, unreadable, truncated
or from before cache keys existed is a miss, never an error. The sidecar is written atomically (temp file, then
os.replace) and only after the PNG exists, so a crash mid-write leaves the previous evidence, or nothing, but never a
half-written sidecar that claims a new state.
"""
import hashlib
import json
import os

KEY_VERSION = 1


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _num(v):
    return None if v is None else [round(float(x), 6) for x in v]


def inputs(glbs, view, focus, frame, res, samples, identity, adjusted):
    """Everything that decides the shot's pixels, as one plain dict."""
    return {"v": KEY_VERSION, "view": view, "focus": _num(focus), "frame": _num(frame), "res": [int(r) for r in res],
            "samples": int(samples), "sources": {os.path.basename(g): [os.path.getsize(g), sha(g)] for g in glbs},
            "adjusted": bool(adjusted), "identity": identity}


def cache_key(inp):
    return hashlib.sha256(json.dumps(inp, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def reusable(stem, inp):
    """The stored sidecar meta if STEM.png + STEM.json are a finished shot of exactly these inputs, else None."""
    if inp["adjusted"] and inp["identity"] is None:
        return None                                        # an adjustment nobody named cannot be matched
    png, side = stem + ".png", stem + ".json"
    if not (os.path.exists(png) and os.path.exists(side)):
        return None
    try:
        with open(side, encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return None                                        # unreadable or truncated sidecar: render again
    if not isinstance(meta, dict) or meta.get("cache_key") != cache_key(inp) or meta.get("sha256") != sha(png):
        return None
    return meta


def write_json_atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_sidecar(stem, meta, inp):
    """Atomically write STEM.json with the cache key, after the PNG is complete."""
    meta = dict(meta, cache_key=cache_key(inp), cache_inputs=inp)
    write_json_atomic(stem + ".json", meta)
    return meta
