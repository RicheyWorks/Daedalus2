# SPDX-License-Identifier: MIT
"""island:pythagoras verifier (read-only): ground fit, drinkable-water chain, livestock + food loop, herb combo, biomes.
python ue_send.py pyth_verify_ue.py 300"""
import unreal
TAG = "PYT_Island"
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
ew = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
acts = [a for a in eas.get_all_level_actors() if a.actor_has_tag(TAG)]
lab = {a.get_actor_label(): a for a in acts}
def has(prefix, n=1): return sum(1 for k in lab if k.startswith(prefix)) >= n
# ground fit: every placed StaticMesh (not ground/rock/habitat/labels) has ground within 10 cm below its pivot
ground = lab.get("PYT_Island_Ground"); flo = sunk = checked = 0; worst = 0.0
skip = ("PYT_Island_", "PYT_Habitat_", "PYT_Label_", "HerbBed_", "PYT_FoodTable")
for a in acts:
    if not isinstance(a, unreal.StaticMeshActor) or a.get_actor_label().startswith(skip): continue
    if "Mob_Bee" in a.get_actor_label() or a.get_actor_label().startswith("Item_"): continue
    L = a.get_actor_location()
    h = unreal.SystemLibrary.line_trace_single(ew, unreal.Vector(L.x, L.y, L.z + 500), unreal.Vector(L.x, L.y, L.z - 3000),
        unreal.TraceTypeQuery.ECC_VISIBILITY, False, [a], unreal.DrawDebugTrace.NONE, True)
    t = h.to_tuple(); checked += 1
    if not t[0]: flo += 1; continue
    d = L.z - t[4].z; worst = max(worst, abs(d))
    if d > 10: flo += 1
    elif d < -10: sunk += 1
water = {"W1_spring": has("W1_Spring"), "W2_stream>=6": has("W2_Stream_", 6), "W3_pond": has("W3_Pond"),
         "W4_filter": has("W4_ReedFilter"), "W5_well": has("W5_Well"), "W6_cistern": has("W6_Cistern"),
         "W7_rain>=2": has("W7_RainBarrel_", 2), "W8_troughs>=1": has("W8_Trough_")}
drink = sum(1 for a in acts if a.actor_has_tag("Water_Drinkable"))
live = {}
for a in acts:
    if a.actor_has_tag("PYT_Livestock"):
        k = a.static_mesh_component.static_mesh.get_name() if a.static_mesh_component.static_mesh else "?"; live[k] = live.get(k, 0) + 1
food = sorted({k.split("_PYT_")[1].split("_")[0] for k in lab if k.startswith("PYT_Item_Food_PYT_")} | {a.static_mesh_component.static_mesh.get_name().split("_PYT_")[1].split("_")[0] for a in acts if isinstance(a, unreal.StaticMeshActor) and a.static_mesh_component.static_mesh and "Item_Food_PYT_" in a.static_mesh_component.static_mesh.get_name()})
herbs = sorted({str(t)[5:] for a in acts for t in a.tags if str(t).startswith("Herb_")})
biomes = {}
for a in acts:
    for t in a.tags:
        if str(t).startswith("PYT_Biome_"): biomes[str(t)[10:]] = biomes.get(str(t)[10:], 0) + 1
loop = {"feed_present": has("PYT_Prop_Live_PYT_HayRack") or any("HayRack" in k for k in lab), "shelter": any("SheepShelter" in k for k in lab),
        "coops": any("HenCoop" in k for k in lab), "hives": any("Beehive" in k for k in lab), "troughs_for_pen": water["W8_troughs>=1"]}
result = {"actors": len(acts), "ground_fit": {"checked": checked, "floating": flo, "sunk": sunk, "worst_cm": round(worst, 1)},
          "water_chain_ok": all(water.values()), "water": water, "drinkable_sources": drink,
          "livestock": live, "livestock_ok": sum(live.values()) >= 10 and all(loop.values()), "food_loop": loop, "foods": food,
          "herb_species": len(herbs), "herb_stages_ok": len(herbs) == 12, "biomes": biomes}
