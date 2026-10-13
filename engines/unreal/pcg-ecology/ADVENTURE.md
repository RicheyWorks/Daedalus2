# The Climax Seed - adventure guide (island:pythagoras)

Mechanic: SUCCESSION - every tile ages bare -> meadow -> scrub -> pine -> oak; players steer it with grazing, digging, burning and seed carrying. Quest progress is computed by succession_depth.quest_progress; in Unreal each chapter has a hidden trigger PYT_QuestTrigger_<id> (tags PYT_Quest, Quest_<id>) and pyth_quest_ue.py reports progress from placed props.

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

Sim modules: succession_sim.py, succession_depth.py (biogeography, seed rain, windthrow, nurse pines, colonise), fire_keeper.py (intermediate disturbance), succession_metrics.py (Shannon H, seral stage).
Tests: run python succession_sim.py, python succession_depth.py, python -m pytest -q.
