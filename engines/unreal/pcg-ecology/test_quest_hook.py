from quest_hook import flags_from_actors
def test_counts_by_base_and_tag():
    f = flags_from_actors([("Prop_Live_PYT_JayFeeder_V1", ["PYT_Chapter"]), ("Prop_Live_PYT_JayFeeder_V2", ["PYT_Chapter"]), ("Prop_Veh_PYT_ArkRaft_V1", [])], {"teas": ["ladder"]})
    assert f["Prop_Live_PYT_JayFeeder"] == 2 and f["Prop_Veh_PYT_ArkRaft"] == 1 and f["PYT_Chapter"] == 2 and f["teas"] == ["ladder"]
def test_base_flags_not_mutated():
    b = {"x": 1}; flags_from_actors([("M_V1", [])], b); assert b == {"x": 1}

def test_live_island_unlocks_past_chapter2():
    import succession_depth as SD
    from quest_hook import build_island
    sheep = [(-3200 + dx, -400 + dy) for dx in (-700, 700) for dy in (-500, 500)]
    water = [(-5000, 0), (1800, 0), (3300, 900), (3500, -200), (-3000, 500), (0, 0), (2500, 1500)]
    I = build_island(sheep, water)
    f = {"teas": ["ladder", "climax"], "PYT_Livestock": 18, "Prop_Live_PYT_Beehive": 4, "bramble_choice": "goats", "survived": ["windthrow"],
         "oaks": 21, "Water_Drinkable": 19, "Prop_Live_PYT_JayFeeder": 2, "Prop_Veh_PYT_ArkRaft": 1, "islet_species": ["Grass", "Pine", "Willow", "Oak"],
         "Prop_Quest_PYT_FireAltar": 1, "burn_rate": 0.03}
    done = SD.quest_progress(I, f)
    assert len(I.grazed) >= 16 and len(I.water) >= 6
    assert [c for c, ok in done if ok] == ["ash_field", "meadow_keepers", "bramble_wall", "pine_shield", "riverbank", "climax", "seed_rain", "fire_keeper"]
