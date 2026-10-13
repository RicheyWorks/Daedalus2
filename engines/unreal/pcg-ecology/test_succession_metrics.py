from succession_metrics import species_of, shannon, stage_of
def test_species_parse():
    assert species_of("Prop_Tree_PYT_Oak_V07") == "Oak" and species_of("Prop_Ground_PYT_MeadowGrass_V03") == "Grass" and species_of("Prop_Shrub_PYT_Bramble_V1") == "Bramble"
def test_shannon():
    assert shannon({"Oak": 10}) == 0 and abs(shannon({"Oak": 5, "Pine": 5}) - 0.693) < 1e-3
def test_stage_order():
    assert stage_of({"Grass": 10}) < stage_of({"Bramble": 10}) < stage_of({"Pine": 10}) < stage_of({"Oak": 10})
