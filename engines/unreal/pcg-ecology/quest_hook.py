# SPDX-License-Identifier: MIT
"""Pure quest-flag derivation for pyth_quest_ue.py: (mesh_name, tags) pairs -> counts keyed by mesh base name and tag."""
def flags_from_actors(pairs, base=None):
    f = dict(base or {})
    for mesh, tags in pairs:
        if mesh:
            b = mesh.rsplit("_V", 1)[0] if "_V" in mesh else mesh
            f[b] = f.get(b, 0) + 1
        for t in tags: f[t] = f.get(t, 0) + 1
    return f

# --- live island -> sim Island (fixes quest progress stalling at ch.2: graze/dig/stage goals had no live source) ---
import ecology_rules as _er
from succession_sim import Island
HALF_CM, N = 6000.0, 12
# design seral stage per biome (pyth_island_ue CENT layout); the sim grid takes it per 10 m cell by nearest biome centre
BIOME_STAGE = {"YoungMeadow": ((-3200, -3200), 0), "BrambleScrub": ((3200, -3200), 1), "PineStand": ((3200, 3200), 2),
               "OldGrowthOak": ((-3200, 3200), 3), "WillowRiverbank": ((0, 0), 2)}
def cell(x, y):
    """Island-local cm -> 12x12 grid cell (10 m cells)."""
    c = lambda v: min(N - 1, max(0, int((v + HALF_CM) / (2 * HALF_CM / N))))
    return c(x), c(y)
def years_for_stage(s):
    t = 0.0
    while _er._stage_from_years(t) < s and t < 500: t += 0.5
    return t
def build_island(livestock_xy=(), water_xy=(), save=None):
    save = save or {}; I = Island(N, 0)
    for j in range(N):
        for i in range(N):
            x, y = (i + 0.5) * 2 * HALF_CM / N - HALF_CM, (j + 0.5) * 2 * HALF_CM / N - HALF_CM
            st = min(BIOME_STAGE.values(), key=lambda v: (v[0][0] - x) ** 2 + (v[0][1] - y) ** 2)[1]
            I.t[j][i] = years_for_stage(st)
    for x, y in livestock_xy:   # animals graze their cell and its neighbours
        ci, cj = cell(x, y); I.graze([(a, b) for a in range(ci - 1, ci + 2) for b in range(cj - 1, cj + 2) if 0 <= a < N and 0 <= b < N])
    I.dig([cell(x, y) for x, y in water_xy])
    for cx, cy in save.get("burn_cells", ()): I.burn(cx, cy, 0)
    return I
