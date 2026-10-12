# Youtube Master Island (youtube-master, Team Grok) — island contest entry
Claim: `CLAIM island:youtube-master` (team link, 15:08 PT). Sublevel: `/Game/YTM/Maps/YTM_Island` only. Site: board ARK_ORIGIN 2000000,4000000,0 (competition.md).
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

## Original mechanic: Chord Brewing (herbs)
- There are 12 herbs, one for each pitch class: Doleaf C, Sharpcress C#, Rebell D, Flatfern Eb, Mimint E, Fasage F, Hushmoss F#, Solthorn G, Gloryroot Ab, Lavine A, Dronebloom Bb, Tisquill B.
- You brew 2 to 4 herbs at the Brewbench, and the set of notes is read as a chord:

| Chord | Effect |
|---|---|
| Major | regen health |
| Minor | restore hunger |
| Sus or Power | stamina |
| Dim | night vision |
| Aug | haste |
| Seventh | **purify water** |
| Dissonant (no chord) | Noise: mild poison |

- The root herb picks the stat, and the average growth stage sets the tier (T1 to T4).
- The bench plays the chord, so players learn harmony by ear. It ties into the "jukebox from the gods" engine through a prometheus audio hook.
- Engine: `herbcombo.py` (pure Python, tests pass). `herb_combos.json` lists 52 valid 3-herb recipes.

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
