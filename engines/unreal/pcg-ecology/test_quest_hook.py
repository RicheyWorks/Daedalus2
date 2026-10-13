from quest_hook import flags_from_actors
def test_counts_by_base_and_tag():
    f = flags_from_actors([("Prop_Live_PYT_JayFeeder_V1", ["PYT_Chapter"]), ("Prop_Live_PYT_JayFeeder_V2", ["PYT_Chapter"]), ("Prop_Veh_PYT_ArkRaft_V1", [])], {"teas": ["ladder"]})
    assert f["Prop_Live_PYT_JayFeeder"] == 2 and f["Prop_Veh_PYT_ArkRaft"] == 1 and f["PYT_Chapter"] == 2 and f["teas"] == ["ladder"]
def test_base_flags_not_mutated():
    b = {"x": 1}; flags_from_actors([("M_V1", [])], b); assert b == {"x": 1}
