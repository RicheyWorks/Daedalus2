# G24 Ark Drydock launch (contest 2026-10-19)

Owner: hephaestus. Core: `daedalus-core/src/main/java/com/daedalus/world/forge/ArkDrydock.java`, tests in `ArkDrydockTest.java`. Source only; the Unreal binding waits in BOARD\UNREAL-QUEUE.md.

## Story tie-in: what the forge is for
When the planet Daedalus shattered, Hephaestus Island became the shard whose heart took the asteroid. The ark crews built the Great Forge there because "every hull that would ever fly had to be tempered here first" (data/islands/hephaestus/ISLAND.md). The drydock turns stamped plates and tempered rivets into arks that carry life to the other shards. This piece closes the forge loop:

**G19 Anvil and Quench** (temper a plate) -> **ForgeGrades** (weapons) / **ArkDrydock** (hulls) -> launch to another shard.

### Quest q_ark_launch
The quest has five steps: `forge_plates` -> `rivet_seams` -> `load_life` -> `water_hold` -> `launch`. `questStep(inspection)` names the current step from the first blocker.

NPCs:
- **Drydock Master Brannoc Slagg** inspects the ark. He has one line per blocker, plus the send-off.
- **Quartermaster Hesper Coalhand** keeps the hold.

| Blocker | Brannoc says |
|---|---|
| HULL_INCOMPLETE | "A ring with a gap is a funnel, not a hull. Every plate, every seam." |
| UNSTAMPED_PLATE | "No stamp, no trust. Take that plate back to the anvil and earn your mark." |
| BRITTLE | "All fire, no water. She'd shatter on the first cold gust. Heat alone breaks." |
| SOFT | "All spring, no fire. She'd sag like wet bread in the void. Water alone softens." |
| WEAK_SEAM | "One weak seam and the void finds it. Better plates there, or more rivets." |
| OVER_CAPACITY | "Hesper says the hold is bursting. Leave some for the next ark." |
| UNPAIRED | "Two by two, or the herd ends where it lands. Find that one a mate." |
| THIRSTY_HOLD | "Count the days, count the mouths. You're short of water for that run." |
| OVER_HOLD | "More water than tank. The rest will be ballast on the slipway floor." |
| (ready) | "Tempered both ways. Knock the chocks out. N days to <shard>, and the forge goes with you." |

## Rules
- **Hull classes:**

  | Class | Plates | Crew | Berths | Hold water |
  |---|---|---|---|---|
  | SKIFF | 6 | 2 | 12 | 200 L |
  | BARGE | 10 | 4 | 24 | 600 L |
  | LONGARK | 14 | 6 | 40 | 1,200 L |

- **Plates:** `Plate.of(TemperForge.Result)` turns a forge result into a plate. A plate is stamped only if it is uncracked and has temper 60 or more.
- **Seams:** seam i joins plate i to plate i+1 around the ring. Its strength is the mean temper of the two plates, minus 10 for each missing rivet (4 per seam). The hull's integrity is its weakest seam and must be 60 or more.
- **Temper both:** a hull with no spring or dual plate is BRITTLE. A hull with no magma or dual plate is SOFT.
- **Life manifest:**
  - Livestock travel in pairs: emberhen, ashgoat, forgeox, lavaboar, cinderwool.
  - Vent bee hives, pets (Kennel Turing-coat pups, G21) and seed crates do not need to be paired.
  - Each one takes a berth.
- **Water:** the crew needs 2 L/day each, and every animal needs its own figure from `livestock.json`. `ArkDrydockTest` reads that file to keep the numbers in step. Loaded water must cover the voyage's days and fit in the hold.
- **Voyage:** `voyage(seed)` posts one of the other shards (Kennel Isle, Glass Reef, Sky Orchard, Storm Anchorage, Cinder Shoal, Whistle Atoll), 3 to 9 days out.

`inspect(ark, voyage)` is pure. It reports every blocker, the integrity, the water needed, the berths used, and Brannoc's line.

## Tests
`ArkDrydockTest` has 10 tests:
- The water figures match livestock.json.
- A good ark launches, with exact water and berth sums.
- The temper-both rule gives BRITTLE, SOFT, or passes on all DUAL plates.
- Seam maths, including the ring closing and the 60 boundary.
- The hull must be complete and stamped.
- Pairs and berths are enforced.
- The hold must have enough water but not overflow.
- Each blocker has a distinct line and quest step.
- Voyages are seeded across every shard.
- A LONGARK built from 14 G19 ideal-run plates launches, and a cracked blank makes an unstamped plate.

## Unreal later (UNREAL-QUEUE)
- The drydock slip shows the plate ring filling up, with rivet sockets on each seam.
- Quartermaster Hesper has a manifest panel.
- Brannoc's inspection bark comes from `line`.
- A launch cinematic plays when `ready`.
