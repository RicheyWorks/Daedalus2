# Youtube Master Island (youtube-master, Team Grok) — island contest entry
Claim: `CLAIM island:youtube-master` (team link, 15:08 PT). Sublevel: `/Game/YTM/Maps/YTM_Island` only. Site: 26 km south of origin (clear of the Wild Biomes rings 4.5-16 km).
Size: **double, 240 m across** (R = 120 m). Built only from my `_YTM_` assets (500 shipped via QUEUE.md), plus one engine cylinder as the ground base.

## Layout
| Zone | Where | Contents |
|---|---|---|
| Spawn + water | centre | `YTM_Island_Spawn`, clean Spring 15 m away (drinkable water within 40 m, mandatory) |
| Water chain | ring 20-45 m | Well, HandPump, Fountain (drinkable); RainBarrel, Cistern, Pool (raw); Filter, Boiler (treat) |
| Herb garden | east 60 m | spiral of 12 note-herbs x 4 stages around a Brewbench |
| Farm | west 60 m | 8 pens (fence, trough, Calf/Adult/Elder), feed crops, Barn, Coop, Silo |
| Kitchen | north 50 m | Stove, Mill, Churn, Press, Smokehouse, Loom, Smelter |
| Rim | 105-118 m | 120 cliffs/rocks + 80 scattered rocks |

## Original mechanic: Melody Brewing (herbs)
Prometheus's Harmonic Herbs reads herbs as a chord. To keep the two distinct, mine reads them as a tune:
- **What counts:** the order you drop 3 to 5 note-herbs into the kettle. The herbs use the same pitch classes as Prometheus, so the islands teach harmony and melody side by side.
- **Contour sets the effect:**

| Contour | Effect |
|---|---|
| Rise | haste |
| Fall | cures sickness |
| Arch | regenerates health |
| Valley | restores hunger |
| Dance (zig-zag) | stamina |

- **Steps and leaps:** if every step is 2 semitones or less, the effect lasts twice as long; any leap of 5 or more doubles its strength.
- **Cadence:** ending on the note you started with also purifies water, which ties into the mandatory water loop.
- **Noise:** a repeated note or fewer than 3 herbs gives a mild poison.
- **The same herbs can give different tonics** depending on their order.
- **Code:** `herbcombo.py` (tests pass; `herb_combos.json` has 901 recipes) and `ADaedalusBrewBench` in C++. The bench plays the tune through the audio hook `OnMelodyBrewed(notes)`.

## Livestock and food loop (`food_water.json`)
- 8 species, each with a feed crop and a product: Mooncalf gives milk, ReefSheep wool, BubbleHen eggs, Kelpig bacon, DriftGoat cheese, StormDuck feathers, Hornox hide, Glowllama glow fleece.
- An animal that is fed and has a trough within 15 m grows from calf to adult in 20 min, then produces on a timer.
- Breeding takes 2 adults plus a Chordberry.
- Products and crops are combined at the Stove into 8 dishes, first Raw then Cooked. A dish that uses a note-herb also gives the tonic buff.

## Drinkable water (mandatory)
- Thirst drains 2 per min; at 0, health drains 1 per s.
- Clean water gives +30, raw +20 with a 25% chance of sickness, and salt water -10.
- A Filter or Boiler turns raw water clean; a Seventh tonic purifies a container.
- Containers: Cup, Flask, Canteen, Jug, Bucket (1 to 10 drinks).

## Files (bot-team\art\NOTES\youtube-master)
`ytm_items.py` (Blender batch, 500), `batch1.json`, `ytm_island_ue.py` (island placement), `ytm_flythrough_ue.py` (Wild Biomes cameras), `herbcombo.py` and `herb_combos.json`, `food_water.json`, `SHOTLIST.md`.
The Blueprint and C++ gameplay hooks (thirst component, brew interaction, pen tick) go to unreal-team; the data stays JSON for codex.

## found tunes (v2, seed-song records)
Each of the 16 seed-song records on the island carries a 4-5 note motif. Play a record at the jukebox
(Prop_YTM_Jukebox) to learn its tune; brewing exactly that herb ORDER at the bench makes a named tonic
(Item_YTM_Tonic_Found_*) with a unique bonus on top of the normal contour effect. 12 tunes so far, data in
engines/unreal/ytm-island/found_tunes.csv (DataTable-ready). Harmonic Herbs (prometheus) is order-free chords,
so this stays an order-only, song-tied hook. Balance (brew_data.py): 3-herb tunes split Rise/Arch/Valley/Fall
~17-25% each; 5-herb tunes skew Dance 35% / Noise 29% / Fall 3%, so cure-sickness is an early 3-herb recipe.

## hero props
12 lowercase signposts (face spawn, >=6 m apart), record shrine + jukebox + record rack by spawn,
16 seed-song records (4 by the shrine, 12 in a 3.2 m arc behind it). Placed by ytm_hero_ue.py (tag YTM_Hero).