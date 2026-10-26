# SPDX-License-Identifier: MIT
"""Read-only quest hook: live island -> Climax Seed progress. Placed props/tags give counts; livestock and drinkable-water
positions give grazed/dug sim cells (quest_hook.build_island); player-only facts (teas brewed, events survived, choices,
islet species, burn rate) come from the save file quest_flags.json (a demo playthrough save for now)."""
import unreal
import sys; sys.path.insert(0, r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology")
import json, importlib, quest_hook, succession_depth as SD
for m in (quest_hook, SD): importlib.reload(m)
ORIGIN = (-60000.0, 60000.0)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
save = json.load(open(r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\quest_flags.json", encoding="utf-8-sig"))
acts = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.StaticMeshActor)]
pairs = [(a.static_mesh_component.static_mesh.get_name() if a.static_mesh_component.static_mesh else "", [str(t) for t in a.tags]) for a in acts]
flags = quest_hook.flags_from_actors(pairs, {k: v for k, v in save.items() if k != "burn_cells"})
def xy(a): L = a.get_actor_location(); return (L.x - ORIGIN[0], L.y - ORIGIN[1])
live = [xy(a) for a in acts if a.actor_has_tag("PYT_Livestock") and "Bee" not in a.get_actor_label()]
water = [xy(a) for a in acts if a.actor_has_tag("Water_Drinkable")]
flags["oaks"] = flags.get("Prop_Tree_PYT_Oak", 0) + flags.get("Prop_Tree_PYT_GreatOak", 0)
dams = [quest_hook.cell(*xy(a)) for a in acts if a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_name().startswith("Prop_Water_PYT_BeaverDam")]
if dams: flags["dam_cells"] = dams   # live dams override the save
I = quest_hook.build_island(live, water, save)
triggers = sorted(a.get_actor_label() for a in eas.get_all_level_actors() if a.actor_has_tag("PYT_Quest"))
result = {"progress": SD.quest_progress(I, flags), "grazed_cells": len(I.grazed), "dug_cells": len(I.water), "stages": I.stages(),
          "oaks": flags["oaks"], "hives": flags.get("Prop_Live_PYT_Beehive", 0), "triggers": len(triggers), "dam_cells": flags.get("dam_cells")}

