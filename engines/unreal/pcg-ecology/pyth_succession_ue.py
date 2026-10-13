# SPDX-License-Identifier: MIT
"""Read-only: per-biome species counts, Shannon H and seral stage on the live island (editor turn, no saves)."""
import unreal, importlib, succession_metrics as SM; importlib.reload(SM)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out = {}
for a in eas.get_all_level_actors():
    for t in a.tags:
        t = str(t)
        if t.startswith("PYT_Biome_") and isinstance(a, unreal.StaticMeshActor):
            sm = a.static_mesh_component.static_mesh; sp = SM.species_of(sm.get_name() if sm else "")
            if sp: out.setdefault(t[10:], {}).setdefault(sp, 0); out[t[10:]][sp] += 1
result = {b: {"species": c, "shannon": round(SM.shannon(c), 3), "stage": round(SM.stage_of(c), 2)} for b, c in out.items()}
