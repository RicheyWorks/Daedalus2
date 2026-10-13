# SPDX-License-Identifier: MIT
"""Shared ground-fit rules for island:pythagoras (used by pyth_fix_ue + pyth_verify_ue, testable outside Unreal).
Intentionally elevated actors are excluded: structure/helper labels, flying bees, and table-top Item_/Tool_ props
(decided by MESH name, since actor labels are PYT_<mesh>_<n>). Tolerance is 10 cm either way; no ground hit = off_island."""
SKIP_LABELS = ("PYT_Island_", "PYT_Habitat_", "PYT_Label_", "HerbBed_", "PYT_FoodTable", "PYT_SimTile_", "PYT_SimReadout")
ELEVATED_MESH = ("Mob_Bee", "Item_", "Tool_")
TOL_CM = 10.0

def excluded(label, mesh_name):
    return label.startswith(SKIP_LABELS) or (mesh_name or "").startswith(ELEVATED_MESH)

def classify(dz, tol=TOL_CM):
    """dz = actor pivot z - ground hit z (cm); None means the trace found no ground."""
    if dz is None: return "off_island"
    if dz > tol: return "floating"
    if dz < -tol: return "sunk"
    return "ok"

