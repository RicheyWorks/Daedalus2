# Mechanics registry — the loop between islands, items, mechanics and story

Richey, 2026-10-14 13:33–13:34: mechanics must be tracked so teams don't overlap, and so each team builds on the
others'; an island's seed must also roll its **chemistry** — the materials it is built from and what grows and
lives on it — appropriate to the realm, so every item has a reason to be there (why does the tree fruit, what do we
do with the fruit, do we sell it). Story documents per realm get richer from the items; richer story asks for more
items: **a self-reinforcing loop, iterated**.

## Where things are tracked (add to these, don't start new ones)
| What | Where | Owner |
|---|---|---|
| Mechanic / quest build list per realm (IDs LAB01…, PORT01…, GAL01…, PAR01…, BRK01…, OCE01…, SYS01, **WZ01…** added today) | `docs/production/Realm-production-2026-10-13.xlsx` sheet **Mechanics** | whoever adds the row |
| Realm chemistry tables (materials, ores, herbs, orchard, crops, livestock, power, water) | sheet **Chemistry** (new today) + `tools/blender/island_chemistry.py` `REALMS` | Team Claude (seeded profile), all teams add rows |
| Storyline per realm | `docs/realms/*.md` (SolReach, OrreryReach, LABYRINTH-BUILDOUT, PORTAL-BUILDOUT, REALM-CASTS) and ADR-036/040 | realm owners |
| Island recipes (what an island must carry) | `docs/production/reference/README.md` (quality bar) + this file | Team Claude |
| Brewing / tonics (the chemistry mechanics) | `docs/mechanics/RingInfusion.md`, `docs/KENNEL_ISLE_TONIC_TROUGH.md`, `docs/contracts/tonic-v1` | Sol / art-master-flex |
| Dig, ores, Heartstone, lands | ADR-049, ADR-050, ADR-054 | Claude |

## The seeded chemistry (one source of truth for Blender, Unreal and the server)
`python tools/blender/island_chemistry.py <seed> <REALM>` → JSON manifest, written next to each exported island
(`Island_H<seed>.chemistry.json`). From one seed and the realm it rolls: geology grade (COMMON 70 % / RICH 25 % /
LEGENDARY 5 %, ADR-050), ores and the Heartstone size, spring purity (filter hut needed?), fish, soil fertility and
crops, orchard species **with the fruit's uses** (eat / sell / inn recipe / brew / craft dye / kennel feed), herb set
and essences (RingInfusion), livestock and what they yield, the island's power source, and the four M.U.L.E.-style
goods (FOOD, ENERGY, ORE, CRYSTAL) with the island's surplus and need — which is why islands trade, why the shop
stocks what it stocks, and what the inn cooks. Every realm has its own table (`REALMS`): the same seed makes a
different island in the Labyrinth (stone, chalk, thread, torch oil, Halloween) than in World Zero (sky islands,
ores, sky rivers) or Gallery City (pigments, canvas, colour prisms).

## Hero island (Skyfall, Team Claude) — every item and its reason
| Item on the island | Mechanic it serves | Story hook |
|---|---|---|
| Heartstone core (glowing, at the keel) | ADR-050: holds the land up, can't be mined; ADR-040 quest chain | the asteroid impact; heal the planet |
| Ore veins by depth, cave mouth, mine rails + cart | ADR-049 pick / bag; ADR-050 ores; smithy | the smith needs copper and iron; gold pays the ark |
| Meteor crater with starmetal (LEGENDARY roll) | ADR-050 legendary lands | a fallen star; starmetal tools |
| Lake, stream, waterfall, **sky river**, ocean basin | ADR-049 water breaks falls / swim up falls; fishing; water wheel | water that flows through the air since the shattering |
| Filter hut + water wheel on the stream, the well | RingInfusion step 1 (draw dirty water, filter) ; power | the keeper's waterworks |
| Herb garden: six herbs in a ring, brew trough, clean-water barrel | RingInfusion brews; Kennel tonics | the Keeper's Broken Circle |
| Orchard (fruit trees), crop rows, livestock pen (sheep/hens) | FOOD good; inn menu; wool/egg/milk crafts; kennel feed | the inn cooks what the island grows |
| Shop with awning, inn, news board, benches, lanterns | ADR-054 starter town; PORT03-style inn/shop; trade surplus/need | each culture has an inn and a shop |
| Smithy (anvil, forge glow, chimney) | tools that mine faster (ADR-049 held item) | the smith's apprentice |
| Windmill | ENERGY good; mills wheat → bread | the island's power |
| Dock + moored ark, fishing pier, boat | ADR-050 arks moor at docks; airship docking proof; fishing minigame | arks tow lands together |
| Crystals under the keel | CRYSTAL good; crystal lamp power; geodes | light for the mine |
| Clouds (one pierced by the sky river) | sky director / portals in the clouds | the other side of the rainbow |

## How to iterate (the loop)
1. A realm's story doc names a need ("the smith has no coal") → add a Mechanics row (ID, assets, implementation,
   story consequence) → add the material/item to the realm's Chemistry row → the generator rolls it from the seed →
   the island carries it with a reason → the story doc gains the scene → repeat.
2. Before adding a mechanic, search the Mechanics sheet and this file; extend the owner's row instead of a twin.

## Super Islands (Ultra's standard, Team Claude members) — added 14:05
Ultra (buckwild-sol) published the Lumenwake standard (branch `codex/lumenwake-super-island`:
`docs/production/SUPER-ISLAND-DESIGN.md`, `LUMENWAKE-ISLAND-STANDARD.md`, `tools/blender/super_island_layout.py`):
four or more distinct connected plots; 256 m pitch, 240 m envelope, sockets `Connect_E/N/W/S` at ±120 m, 10 m deck
datum, 8 m clear walk, 16 m bridge spans, each member keeps its deed/seed. `tools/blender/voxel_super_island.py`
makes our voxel islands members of that standard (landings to every socket, bridges from the layout's connectors,
sky rivers between member lakes, per-member chemistry in `<out>.super-island.json`). Mechanic rows: WZ08 (plot
sockets + tug anchors → ADR-065 tugging), WZ09 (sky rivers as water connectors between members).

## Colony Ledger (ADR-066) — 14:20
`tools/economy/colony_ledger.py` (pure core, `test_colony_ledger.py` 10/10): the M.U.L.E. loop per realm —
plots = deeds with their chemistry profile; workers (pack mule / Codex PowerUnit) outfitted per good family by
consuming parts; production = chemistry × ecology (seral stage, biodiversity, season from pcg-ecology) with the
energy tax and adjacency bonus; market day double auction with ark cargo; events; **day book** (Animal Crossing:
fish/bugs/fossils/fruit finds, collection, charm, cast requests from `data/art/<realm>/population-plan.json` —
kings, unicorn guides, bakers… and their quests, PORT09); **raid/defend** (Arc Raiders: hulks and rich lands,
interceptable cargo, fences/towers/patrols/traps). Rows WZ10–WZ15; the Excel tracker has a "Team Claude
2026-10-14" sheet listing every deliverable.

## Characters — 14:35
`tools/blender/voxel_creatures.py`: 64 rigged voxel species (animals, birds, bees, carnivorous plants) on the
shared 8-bone rig with Idle/Walk/Attack/Hurt (row WZ18). Which species live on an island comes from the ecology
(seral stage, water, biome) and the chemistry (livestock list, fish); carnivorous plants tie to LAB10/LAB11.
