from world_census import config, model
def test_mapping():
    cfg = config.load()
    src = dict(queue=[{"name": "Prop_BUF_Chest", "kind": "prop", "status": "READY", "notes": ""}],
               art_files=["art/Prop/Prop_Lantern.blend", "art/Mob/Mob_Realm_Slime.blend", "art/x/weird.glb"],
               uassets=["Content/Daedalus/Art/Prop/Prop_Lantern/Prop_Lantern.uasset"],
               competition={"grid": {"buffffff": "6000000,0,0"}, "island_tracker": []},
               realms=[], island_docs=[], registries=[])
    c = model.build(src, cfg); a = {r["name"]: r for r in c["assets"]}
    assert a["Prop_BUF_Chest"]["world"] == "Buffffff Island" and a["Prop_BUF_Chest"]["category"] == "chests/containers"
    assert a["Prop_Lantern"]["status"] == "in_unreal"
    assert a["Mob_Realm_Slime"]["world"] == "Portal Realm (8-bit)"
    assert a["weird"]["world"] == "Unassigned"
