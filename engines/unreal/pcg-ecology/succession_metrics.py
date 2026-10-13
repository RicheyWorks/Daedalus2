# SPDX-License-Identifier: MIT
"""Shannon diversity + seral stage for island:pythagoras biomes. Pure part (shannon, stage_of) is testable;
pyth_succession_ue.py feeds it the live species counts from actors tagged PYT_Biome_<name>."""
import math, re
SERAL = {"Grass": 0, "Sedge": 0, "Fern": 1, "Bramble": 1, "Pine": 2, "Willow": 2, "Oak": 3}
def species_of(mesh_name):
    m = re.match(r"Prop_\w+?_PYT_([A-Za-z]+?)(Grass)?_V\d+", mesh_name or "")
    if not m: return None
    s = m.group(1) + (m.group(2) or "")
    return "Grass" if s == "MeadowGrass" else s
def shannon(counts):
    n = sum(counts.values())
    return 0.0 if n == 0 else -sum(c / n * math.log(c / n) for c in counts.values() if c)
def stage_of(counts):
    """Abundance-weighted seral stage, 0 (pioneer) .. 3 (climax)."""
    n = sum(c for s, c in counts.items() if s in SERAL)
    return 0.0 if n == 0 else sum(SERAL[s] * c for s, c in counts.items() if s in SERAL) / n
