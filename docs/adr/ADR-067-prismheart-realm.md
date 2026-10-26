# ADR-067: The Prismheart Realm — the 16-bit crystal-era party RPG (original)

Date: 2026-10-14 · Status: Proposed (Blender stage shipped) · Owner: Team Claude

## Why
Richmond (19:48 PT): "i need you to make stuff for the dragon warrior and final fantasy realms." ADR-036 already
asks for "a Final Fantasy type vibe … world map exploration and gaining levels" and ADR-037 for "the team
assembling for a fight". The 8-bit side exists — the **Portal Realm** (ADR-052). The 16-bit side had no realm.
REALMS.md rule 4: we take the genre and the feel, never the names, monsters, music or maps. Square Enix owns
Final Fantasy and Dragon Quest; nothing here uses their names, job names, summons, items or creatures.

## Decision
A new realm, **Prismheart**, reached through a prism gate (like the Portal cubes, ADR-052). Its feel: a party of
four chosen from eight original job classes, a world map opened by an airship, six Prism Shards whose bearers can
call summon spirits, waystones to save, towns with an inn, item shop, arms shop and spell tower.

| Piece | Original design |
|---|---|
| Jobs (PRISM01) | Bladeward (sword + shield knight), Runecaster (offence staff), Lightmender (healer rod), Shadowstep (twin daggers), Beastcaller (bow, tames monsters), Gearwright (wrench, gadgets), Starlancer (lance, leaps), Chronoseer (hourglass staff, haste/slow) |
| Waystones (PRISM02) | Floating teal crystals on a plinth: save, heal at an inn price, fast-travel between found stones |
| Shards + summons (PRISM03) | Fire, Tide, Gale, Stone, Light, Shade shards. Spirits: Aurorawyrm, Tidecoil, Emberforge Titan, Galewing, Glacier Stag, Stormmane, Rootfather, Starfall |
| Airship (PRISM04) | The Skyfarer: a balloon-envelope sky boat with side props; lands on open ground and harbour docks |
| Monsters | 30 types: Glimmer Imp, Frost Puddle, Thornback Boar, Bone Lancer, Cinder Hound, Mirror Moth, Clockwork Sentry, Hollow Armor, Sand Wyrm, Gale Harpy, Bog Lantern, Coral Golem, Ironshell Tortoise, Rat King, Ember Salamander, Storm Roc, Crystal Mantis, Void Eye, Lantern Ghoul, Ash Treant, Mire Hydra, Rune Gargoyle, Quartz Scarab, Shade Panther, Tide Kraken, Thunder Ram, Moss Behemoth, Dune Scorpion, Glass Serpent, Star Jelly |
| Mount | Duneback (a long-tailed desert grazer — not a bird) |
| Items | Mendwater (heal), Mana Draught, Clearwater (status), Ember Plume (revive); chests in wood / iron / gilded |
| Chemistry | `island_chemistry.REALMS["PRISMHEART"]`: ores iron/silver/gold/starmetal, orchard pear/peach/lemon, crops barley/turnip/sunroot (sunroot → Mana Draught at the brew), livestock duneback/hen/goat, power crystal lamp / water wheel / windmill |

## What shipped (Blender stage)
- `tools/blender/realm_rpg_cast.py` — 48 heroes (8 jobs × 6), 150 monsters (30 × 5), 8 summons (2× voxel scale),
  48 townsfolk (12 roles × 4), 4 Duneback mounts, all rigged on the shared 8-bone rig with the 8 standard clips;
  `export_rpg_cast.py` → `engines/unreal/art/claude-prism-cast/Mob_Prism_*`.
- `tools/blender/realm_prism_props.py` — 12 structures (Prism Shrine, Waystone, Skyfarer, Castle Gate, Town House,
  Inn, Item Shop, Arms Shop, Spell Tower, Chapel, Harbour Dock, Crystal Lamp Post) and 24 items (6 chests, 8 job
  weapons, 4 potions, 6 shards); `export_catalog.py prism OUT` → `Bld_Prism_*`, `Prop_Prism_*`.
- Same file also fills the **Portal Realm** population plan: every `art_status: Planned` row (49 enemy types, 50
  friendly types incl. the four unicorn roles, 10 individuals each = 990) plus the 5 proposal bosses →
  `claude-portal-cast/Mob_Portal_<TYPE>_Voxel_NN`, each json carrying its `plan_id` / `variant_seed`.

## Not decided here
Battle rules (real-time Zelda-II style per ADR-036 vs a turn mode for this realm), the shard/summon economy, how the
realm is reached on the island map, music cues (jukebox), and native import (Codex is sole Unreal operator).
