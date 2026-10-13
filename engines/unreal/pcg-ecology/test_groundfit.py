from pyth_groundfit import excluded, classify
def test_labels_and_bees_excluded():
    assert excluded("PYT_Label_YoungMeadow", None) and excluded("PYT_Mob_Bee_Body_3", "Mob_Bee_Body")
def test_table_props_by_mesh_not_label():
    assert excluded("PYT_Item_PYT_HoneyJar_V1_412", "Item_PYT_HoneyJar_V1") and not excluded("PYT_Item_x", "Prop_Tree_PYT_Oak_V01")
def test_classify():
    assert [classify(d) for d in (None, 85, -12, 4)] == ["off_island", "floating", "sunk", "ok"]
