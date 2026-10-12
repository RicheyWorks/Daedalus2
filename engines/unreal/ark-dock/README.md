# Ark Dock (Team Grok, 2Hot2Trot)

Reusable builder for an ark landing dock on an island edge in DaedalusWorld.
Writes only to the streaming sublevel `/Game/Grok/Maps/ArkDock_2hot2trot` and saves only that
(plus the persistent map's sublevel entry when the map was clean before the run).

What it places (all actors tagged `GROK_ArkDock`, so a rerun replaces them):
- landing pad, a 40 m pier past the island lip, posts and lanterns with warm point lights
- a docked ark from shipped art `/Game/Daedalus/Art/Veh/Veh_Ark` (hull, wings, claw) plus the bone anchor; primitive fallback
- game basic #7 crafting bench (`Prop_Workbench`, station `workbench`) and #8 smelter (`Prop_Smelter_Lit`, station `smelter`)
  wired to codex's `data/economy` stations/recipes: tags `DAEDALUS_Station`, `Station_<id>`, `StationTier_<n>`, `Recipe_<id>` and a recipe sign
- pad spotlight, smelter glow, a title label; viewport framed for a screenshot

Run only during a Grok editor turn (one editor, never launch one):

    python ue_send.py ark_dock_ue.py 600 [ARK_ECON=C:\path\to\data\economy]

Edge finder: rays out from PlayerStart in 24 directions, prefers the shore with no Wild Biomes plants.
