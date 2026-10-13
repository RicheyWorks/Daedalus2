# SPDX-License-Identifier: MIT
"""Read-only quest hook: derive Climax Seed flags from the live island (placed props, livestock, water) and report
which chapters are unlocked via succession_depth.quest_progress. Sim-only flags (teas, burn rate) come from quest_flags.json."""
import unreal
import sys; sys.path.insert(0, r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology")
import json, importlib, succession_depth as SD, succession_sim as SS; importlib.reload(SD)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
flags = json.load(open(r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\quest_flags.json", encoding="utf-8-sig"))
import quest_hook; importlib.reload(quest_hook)
pairs = [(a.static_mesh_component.static_mesh.get_name() if a.static_mesh_component.static_mesh else "", [str(t) for t in a.tags])
         for a in eas.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor)]
flags = quest_hook.flags_from_actors(pairs, flags)
I = SS.Island(12, flags.pop("island_years", 0)) if hasattr(SS, "Island") else None
triggers = sorted(a.get_actor_label() for a in eas.get_all_level_actors() if a.actor_has_tag("PYT_Quest"))
result = {"progress": SD.quest_progress(I, flags), "triggers": triggers, "placed_ch7": {k: flags.get(k, 0) for k in ("Prop_Live_PYT_JayFeeder", "Prop_Veh_PYT_ArkRaft")},
          "placed_ch8": flags.get("Prop_Quest_PYT_FireAltar", 0)}


