# SPDX-License-Identifier: MIT
"""The hype-train trailer's shots and per-frame cameras, engine-free (tested offline by test_trailer.py).

Each shot is a camera move over real places in DaedalusWorld (coordinates read live on 2026-10-13). frames() turns
the shot list into one (eye, look-at, caption) per frame at the chosen fps; trailer_ue.py renders them in Play."""
import math

FPS = 30

# (name, seconds, kind, params, caption). Unreal cm. Orbits: centre, radius, height, from/to degrees, look height.
SHOTS = [
    ("sky", 6.0, "orbit", {"c": (20000, -9000, 5000), "r": 32000, "h": 16000, "a0": 200, "a1": 250, "lz": 4800},
     "ONE SHATTERED PLANET"),
    # "follow": an orbit around a live herd animal, picked when the shot starts (trailer_ue.py); c is the fallback.
    ("herd_cows", 5.0, "follow", {"c": (1179, -9108, 5400), "r": 900, "h": 320, "a0": 200, "a1": 250, "lz": 5400},
     "LIVING HERDS"),
    ("herd_ranch", 5.0, "follow", {"c": (37500, -8000, 4900), "r": 1300, "h": 450, "a0": 120, "a1": 170, "lz": 4900},
     "EVERY CREATURE WANDERS ITS OWN WAY"),
    ("orrery_reach", 6.0, "orbit", {"c": (402000, 0, 5800), "r": 14000, "h": 6000, "a0": 300, "a1": 360, "lz": 5600},
     "THE ORRERY REACH"),
    ("star_creatures", 5.0, "dolly", {"e0": (404500, 1500, 6700), "e1": (406200, 3600, 6500), "t0": (407829, 4988, 6063),
                                      "t1": (407500, 4800, 6050)}, "STARLIGHT CREATURES"),
    ("squad", 6.0, "orbit", {"c": (800, -8800, 5450), "r": 1800, "h": 700, "a0": 30, "a1": 100, "lz": 5450},
     "SQUADS THAT THINK"),
    ("pull_away", 5.0, "dolly", {"e0": (2500, -10500, 6500), "e1": (60000, -60000, 45000), "t0": (800, -8800, 5400),
                                 "t1": (20000, -9000, 5000)}, "DAEDALUS"),
]


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def camera(kind, p, t):
    """(eye, target) at shot progress t in 0..1, eased."""
    s = smooth(t)
    if kind in ("orbit", "follow"):
        a = math.radians(p["a0"] + (p["a1"] - p["a0"]) * s)
        cx, cy, cz = p["c"]
        eye = (cx + p["r"] * math.cos(a), cy + p["r"] * math.sin(a), cz + p["h"])
        return eye, (cx, cy, p["lz"])
    if kind == "dolly":
        return lerp(p["e0"], p["e1"], s), lerp(p["t0"], p["t1"], s)
    raise ValueError("unknown shot kind " + kind)


def rotation(eye, target):
    """Unreal (pitch, yaw) degrees looking from eye to target."""
    dx, dy, dz = (target[i] - eye[i] for i in range(3))
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return pitch, yaw


def frames(shots=SHOTS, fps=FPS):
    """[(index, shot name, eye, (pitch, yaw), caption)] for every frame, shots back to back."""
    out = []
    for name, secs, kind, p, caption in shots:
        n = max(1, int(round(secs * fps)))
        for k in range(n):
            eye, tgt = camera(kind, p, k / max(1, n - 1))
            out.append((len(out), name, eye, rotation(eye, tgt), caption))
    return out


def shot_starts(shots=SHOTS, fps=FPS):
    """{name: (first frame, frame count, caption)} for the edit (captions burn in over each shot)."""
    out, i = {}, 0
    for name, secs, _, _, caption in shots:
        n = max(1, int(round(secs * fps)))
        out[name] = (i, n, caption)
        i += n
    return out
