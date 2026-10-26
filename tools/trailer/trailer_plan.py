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


# ---- Part 2: past the rainbows (ADR-031 sky gates, ADR-052 portal realm). Cameras are relative to live positions
# (the gate row and each realm's bounds), so they are computed in trailer_realms_ue.py from these specs.
# (name, seconds, caption). The order is the order the player meets them.
REALM_SEGMENTS = [
    ("rainbows", 5.0, "PAST THE RAINBOWS"),
    ("through", 5.0, "GATES IN THE CLOUDS"),
    ("realm:0", 5.0, None),          # caption = the far world's title
    ("realm:1", 5.0, None),
    ("realm:2", 5.0, None),
    ("pixel", 7.0, "THROUGH THE PORTAL, AN 8-BIT REALM"),
    ("heal", 4.0, "HEAL THE SHATTERED PLANET"),
]


def seg_frames(name, fps=FPS, segments=REALM_SEGMENTS):
    for n, secs, _ in segments:
        if n == name:
            return max(1, int(round(secs * fps)))
    raise KeyError(name)


def gate_row_shots(gates):
    """Wide and fly-through cameras for a row of gate centres [(x, y, z)] (Unreal cm, sorted by gate).
    Gates stand far out from the islands on -Y; the rainbow is ~40 m in front of each ring (toward the islands)."""
    xs = [g[0] for g in gates]
    cx = sum(xs) / len(xs)
    gy = sum(g[1] for g in gates) / len(gates)
    gz = sum(g[2] for g in gates) / len(gates)
    span = max(xs) - min(xs) + 6000.0
    wide = {"e0": (cx - span * 0.2, gy + span * 0.9, gz + 2500), "e1": (cx + span * 0.2, gy + span * 0.7, gz + 1500),
            "t0": (cx, gy, gz), "t1": (cx, gy, gz)}
    g0 = gates[0]
    through = {"e0": (g0[0] + 600, g0[1] + 9000, g0[2] - 300), "e1": (g0[0], g0[1] + 900, g0[2]),
               "t0": g0, "t1": (g0[0], g0[1] - 2000, g0[2])}
    heal = {"e0": (cx, gy + span * 0.6, gz + 1200), "e1": (cx, gy + span * 2.2, gz + span * 1.4),
            "t0": (cx, gy, gz), "t1": (cx, gy - span, gz - span * 0.3)}
    return {"rainbows": wide, "through": through, "heal": heal}


def realm_orbit(origin, extent):
    """An orbit that frames a whole realm from its bounds (origin, half-extent), Unreal cm."""
    ox, oy, oz = origin
    ex, ey, ez = extent
    r = max(ex, ey, 2000.0) * 1.25
    return {"c": (ox, oy, oz), "r": r, "h": max(ez, 1500.0) + r * 0.35, "a0": 210, "a1": 260, "lz": oz}
