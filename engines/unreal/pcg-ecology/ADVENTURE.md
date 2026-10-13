# The Climax Seed - adventure guide (island:pythagoras)

Mechanic: SUCCESSION - every tile ages bare -> meadow -> scrub -> pine -> oak; players steer it with grazing, digging, burning, damming and seed carrying. Progress: succession_depth.quest_progress. In Unreal each chapter has a hidden trigger PYT_QuestTrigger_<id> (tags PYT_Quest, Quest_<id>); pyth_quest_ue.py reads live livestock/water/dam positions as sim cells and reports progress.

| # | Chapter | Goals | Reward |
|---|---|---|---|
| 1 | Ash Field | type=stage_tiles, stage=0, n=20; type=brew, tea=ladder, min_rungs=1 | Item_Seed_PYT_MeadowPouch_V1 |
| 2 | Meadow Keepers | type=graze_tiles, n=16; type=actor, tag=PYT_Livestock, n=5; type=place, asset=Prop_Live_PYT_Beehive, n=2 | Item_Food_PYT_HoneyJar_V1 |
| 3 | Bramble Wall | type=stage_tiles, stage=2, n=12; type=choice, options=['goats', 'burn'] | Tool_PYT_FireweedTorch_V1 |
| 4 | Pine Shield | type=survive_event, event=windthrow; type=species, name=Oak, min=5 | Item_Seed_PYT_ForestPouch_V1 |
| 5 | Riverbank | type=dig_tiles, n=6; type=actor, tag=Water_Drinkable, n=3 | Item_Seed_PYT_RiparianPouch_V1 |
| 6 | Climax | type=climax_mosaic; type=brew, tea=climax, at=ADV_OldStump | Prop_Tree_PYT_GreatOak |
| 7 | Seed Rain | type=place, asset=Prop_Live_PYT_JayFeeder, n=2; type=place, asset=Prop_Veh_PYT_ArkRaft, n=1; type=colonised, n=4, need_oak=True | Prop_Quest_PYT_ClimaxSeed, Prop_Dress_PYT_ColonistCairn |
| 8 | Fire Keeper | type=place, asset=Prop_Quest_PYT_FireAltar, n=1; type=fire_rate, min_h=1.2 | Prop_Dress_PYT_FireLookout |
| 9 | Keystone Beaver | type=place, asset=Prop_Water_PYT_BeaverDam, n=2; type=beaver_dams, min_h=1.55, min_old=30 | Prop_Live_PYT_BeaverLodge |

Sim modules: succession_sim, succession_depth (biogeography, seed rain, windthrow, nurse pines, colonise), fire_keeper (intermediate disturbance), keystone_beaver (dams/wetland), succession_metrics (Shannon H, seral stage), rate_dial, quest_hook.
Dialogue: chapter7_seed_rain.json, chapter8_fire_keeper.json, chapter9_keystone_beaver.json. Visual: succession_timelapse.png.
Tests: python succession_sim.py; python succession_depth.py; python -m pytest -q test_*.py
