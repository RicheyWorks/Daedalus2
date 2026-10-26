# Daedalus: How the World Works (STORY v0)

**Status:** Draft v0, by Prometheus. Sections for Art Master Flex and Hephaestus are marked. Needs Richey's review.
**Matches what is built in:** ADR-018 (seeded islands), ADR-019/020 (arks, docks, voyages), ADR-021/022/023 (species canon, island ecology, arks carry life), ADR-027/028 (island deeds, `RealmIslands.sol`), ADR-029/031 (many worlds, sky gates), `rd-music-nft/packages/rd-coat/DAEDALUS.md` (token coat), and the 23 maze generators in `daedalus-core` (TuringGenerator among them). The crafting loop is specified in `ECONOMY.md`.

> **The asteroid ended the old world. The arks carry what's left.**

---

## 1. The Impact

One rock. The sky caught fire, and the ground broke apart and rose. The world is now a lane of floating islands, pieces of the old crust held up in a sky that never fully cleared. On the islands the soil, water and stone survived. Most animal life did not.

**The biology underneath.** Earth's real impacts (the end-Cretaceous one is the best studied) work like this: a short, violent kill, then a long, patchy recovery. The survivors are mostly small, fast-breeding generalists (r-selected). Large specialists come back slowly, if at all. Recovery happens island by island, with chance colonists, founder effects and local extinctions. Daedalus runs that same process. The ecology stepper (ADR-022) uses MacArthur–Wilson island biogeography: colonization falls off with distance, extinction rises as area shrinks, and populations grow logistically up to a guild's carrying capacity. A single founder usually fails.

## 2. The Arks

Arks fly where the ground can't hold: two of every kind, and then some. Every island grows a pier and launches one ark, named from its seed (ADR-019). The arks are the world's main colonization route. In island-biogeography terms, an island's immigration rate is set mostly by ark traffic, not wind (ADR-020, ADR-023). Individuals move between islands; they are not copied. An island loses exactly what the hold gains. A pond kind headed for a dry island stays aboard until the next stop.

Like Noah's ark, an ark is a promise that a lineage gets another chance. Unlike Noah's ark, it guarantees nothing. Whether the founders take hold is up to the island.

The pool of kinds is the species canon: 221 kinds, each with a guild, a size class and a breeding strategy (ADR-021).

## 3. The Coats

No two pets wear the same skin. Nature draws the stripes, math describes them, life wears them.

**The science.** In 1952 Alan Turing showed that two chemicals can paint a pattern on a uniform tissue. One is an activator that makes more of itself. The other is an inhibitor that diffuses faster and shuts the activator down. A source makes the molecules and a sink removes them. That is enough to give spots, stripes and labyrinths. Zebra stripes, leopard rosettes, the spots on pufferfish and the ridges in our own fingerprints are all at least partly explained this way.

**In Daedalus.** Every Reaction/Diffusion/Song token carries a Gray-Scott genome: feed rate **F**, kill rate **k**, diffusion, scale, palette and seed layout. All of it is derived from the token's hash (`rd-coat`). Grown on a torus, that genome becomes a seamless coat, and the coat becomes the pet's skin.

| Coat kind | Patterns |
|---|---|
| Stripes | Labyrinth, Fingerprint, Worms, Coral |
| Spots | Mitosis, Solitons, Honeycomb, Wanderers |

The token's fingerprint and the animal's coat are the same thing, grown by the same equation.

## 4. The Bloodlines

**From one seed.** Holders breed pets. A child takes its F, k and diffusion from a blend of both parents plus a small mutation, always inside the stable ranges (F 0.029–0.078, k 0.057–0.0649). Its palette is 40% parent A, 40% parent B and 20% a brightness-aligned mix. The child's seed is a keccak hash of the lineage, so the same parents always give the same child.

**Does it live or die?** Not every line lasts. A mutation can push a pattern toward a regime where spots die out or stripes melt, and some lines simply aren't carried forward. That is selection: whatever persists, persists because it held. Every birth is recorded, so the lineage is a traceable tree of life, with sisters, brothers and cousins.

**Who are the ancestors?** Any pet's coat and song can be traced back through every breeding to the founder tokens it came from.

## 5. The Song

A pet's song is inherited too. The same genome that grows the coat also sets the music: rhythm, intervals, scale, style and timbre, composed by a Turing-machine composer. Breeding blends the music the same way it blends the coat. Two pets from one line sound related, the way siblings resemble each other.

**Jukeboxes.** Jukeboxes stand in Daedalus and play seed music on real, sampled instruments, warm, as if played off a record. Genre conversion (rock, jazz, reggae, orchestral) changes the arrangement, never the genome. When a seed has never been played, the jukebox enters its **record presser** state: you watch a new record being pressed from the seed, and then it plays.

## 6. The Islands

There is one island per token, yours to plant, keep and defend.

**What an island is.** An island is a surviving fragment of the old crust that an ark settled. Its shape (ground, trees, ponds, streams, waterfalls, crystals) is a pure function of its seed (ADR-018). The same seed always grows the same island, so the deed carries the land itself, not a pointer to it. The `RealmIslands` contract stores each slot's seed and radius on chain (ADR-027/028). From that seed come:
- **Biome and habitat:** canopy, pond, meadow, soil and starborn crystal cells, which set which guilds can live there (ADR-022).
- **Ambience and song:** the island's soundscape grows from the same seed.
- **Flora and ores:** see section 7 and `ECONOMY.md`.
- **A maze:** each island can hold a maze grown by one of the 23 generators. A generator is picked from the seed; Turing islands grow the reaction-diffusion maze. Mazes stand for the broken ground and the old ruins, and they exist in every world (ADR-029).

*Open item:* how a Reaction/Diffusion/Song token id maps to an island slot (see Open Questions).

## 7. Living off the land (the crafting loop)

The impact scattered seeds and sowed metal. Survival takes both.

1. **Gather.** Plants on each island (the flora assets) are harvested sustainably. Overharvesting lowers regrowth, the same way real wild-harvest populations crash.
2. **Process.** Plants are cooked, dried, fermented, distilled or pressed into food, medicine, dyes and fuel. The model is real ethnobotany: willow bark for pain (salicin), woad and indigo for blue, madder for red, resinous wood and oilseed for fuel.
3. **Prospect and mine.** Islands carry ores from the old crust: copper, tin, iron, lead and zinc.
4. **Smelt and refine.** Ore becomes metal at a smelter. The rare metals (iridium, platinum, nickel-iron) come from **asteroid fragments**. That is real geology: the iridium layer at the end-Cretaceous boundary is the impactor's fingerprint. They are found mostly on starborn (crystal) islands.
5. **Craft.** Metals, fibers, resins and dyes become tools, ark parts (hull, rigging, lift crystal housings) and pet gear (harness, bedding, medicine).

What spawns on an island is set by its seed. The full tiers, recipes and data schema are in **`ECONOMY.md`**.

## 8. Many worlds

The islands are the first world, not the only one. Sky gates past the rainbow lead to other worlds, each with its own mount (ADR-029/031). A pet, its coat and its song travel with its holder.

## 9. The Hook

The world was wiped clean. What grows back is up to you.

---

## [ART MASTER FLEX] Companion and Jukebox
*Reserved for Art Master Flex: the Cane Corso companion (its role, its origin on the arks, how it guards an island), the 1/1 jukebox, and the record presser on the web page.*

## [HEPHAESTUS] Posts and Voice
*Reserved for Hephaestus: the teaser series (one post per section, 1–6 and 9), the voice guide, and which lines are already live on X. Nothing gets posted without Richey's go.*

---

## Open questions for Richey
1. **Token to island:** With up to 50,000 R/D/S tokens, does each token mint or unlock a `RealmIslands` slot, or is an island's seed derived from the token hash?
2. **Death:** Can a pet die in the game, or does "lines die out" only mean lineages that stop being bred?
3. **Breeding costs:** Cooldown, whether you must own both parents, and the split (the breeding fee is 25% of mint price). Can crafted pet gear or medicine affect breeding?
4. **Fast Food Punks:** Buffffff's broadcast asks to tie them in. Who or what are they in the world (survivor faction, traders, ark crews)?
5. **Defend:** "Plant, keep and defend." Defend against what: foes (ADR-044), weather, invasive kinds, raids?
6. **Rare metals:** Is it OK to source them from asteroid fragments on starborn islands?
7. **Islands per world:** Are all token islands in World Zero, or spread across worlds?
