# Prometheus Island

Builder: prometheus (Team Grok). Only prometheus edits this island.
Sublevel: `/Game/Prometheus/Maps/PrometheusIsland`. Assets: `/Game/Prometheus/*`.
Sources: `bot-team/art/prometheus_island/` (terrain_gs.py, blender_items.py, audio_pi.py, pi_place.py, pi_shot.py, manifest_*.json).

## Lore blurb (for the mint)
When the asteroid broke the world, one shard kept humming. Prometheus Island is a 480 m sky-island whose
hills were grown by a reaction-diffusion pattern, the same Gray-Scott math that paints every Reaction /
Diffusion / Song coat. A spring rises under the peak, and the stream it feeds plays the island's song as
it falls to the sea of cloud. Arks dock here to trade seeds and records. Herbs grow in a ring tuned like
a circle of fifths, the herds wear coats grown from their own genomes, and at the heart a jukebox and a
record presser cut each visitor's genome into vinyl.

## Terrain (seeded)
- `terrain_gs.py <seed>`: Gray-Scott, F=0.0545, k=0.062 (Coral regime, inside the stable ranges),
  128x128 grid, 6000 steps, on a dome falloff. Seed for the flagship: token e00015 (15).
- 480 m across (double the planned 240 m), 38 m peak. A stream valley is carved from the spring (NE, near the peak) to
  the SW shore. Same code makes any token's island: a different seed gives different hills.

## Fresh water (HARD RULE): spring + stream + rain catch + cistern + still
| Stage | In-world actors (`PI_Water_*`, tag `water`) | Role |
|---|---|---|
| Spring basin | `PI_Water_SpringBasin` (+3 rim stones) | Groundwater rises under the peak: the primary source, flows all year |
| Stream | `PI_Water_Stream_00..39` (40 segments on the carved valley) | Carries spring water downhill; people drink upstream of the pens |
| Rain catch | `PI_Water_RainCatcher_00..11` (funnel + downpipe + jar, ring around the cistern) | Roof and funnel harvest in storms; first-flush runs to waste |
| Cistern | `PI_Water_Cistern_0..5` | Settling storage fed by the stream offtake and the rain catchers; sand/charcoal layer as a slow filter |
| Pipes | `PI_Water_Pipe_00..15` | Gravity line from the cistern to the pens |
| Troughs | `PI_Water_Trough_00..11` (two rows at the pens) | Livestock drink here, never from the stream itself (keeps the source clean) |
| Solar still | `PI_Water_Still_00..09` (basin + sloped glass) | Shore backup: makes clean drinking water from brackish or dirty water in drought |
Sound: stream emitters `PI_Snd_Stream_*` loop `SW_PI_Stream` (low-passed, soft); the heart plays `SW_PI_Song`.
Water is the island's song: the stream bed and the song come from the same seed.
Budget per day: a person needs about 3 L to drink (more with cooking); a goat or sheep needs about 4 to 8 L. The spring is the base supply,
rain fills the cistern buffer, and the still covers drought for drinking only.

## Harmonic herbs (Prometheus's herb mechanic)
Each herb carries a **pitch class**. A preparation (tea, poultice or salve) of 2 to 4 herbs is read as an **interval or chord**, and
the harmony decides the effect. Potency follows **consonance**, and **rhythm** (how many doses and how they are timed) adds a second axis.
This is different from Kennel Isle's trough tonics (pet + coat scaling) and DiskSaver's compression herbs: here the
combination rule is music theory, so the same herbs give different effects depending on which notes they make together.

| PC | Herb (real use) | | PC | Herb (real use) |
|---|---|---|---|---|
| C | Yarrow (*Achillea*): styptic, wound wash | | F# | Elderflower (*Sambucus*): fever tea |
| C# | Plantain (*Plantago*): drawing poultice | | G | Sage (*Salvia*): antiseptic gargle |
| D | Chamomile (*Matricaria*): calming, gut | | G# | Comfrey (*Symphytum*): external bruise salve only |
| D# | Valerian: sedative root | | A | Willow bark (*Salix*, salicin): pain, fever |
| E | Feverfew (*Tanacetum parthenium*): headache | | A# | Hypericum: wound oil |
| F | Mint (*Mentha*): digestion, cooling | | B | Nettle (*Urtica*): iron-rich food, tonic |

Rules (an interval is counted in semitones between pitch classes):
- **Major triad** (root, +4, +7; for example C-E-G Yarrow+Feverfew+Sage) = **Heal** over time. Minor triad = a weaker heal plus calm (lower aggro).
- **Perfect fifth** (+7; for example D-A Chamomile+Willow) = **Shield** (damage reduction). An octave doubling (two doses of the same herb) = it lasts longer.
- **Triplet**: the same chord taken as 3 doses at even spacing = **Speed**. A dotted rhythm = stamina.
- **Fourth** (+5) = cleanse (removes a debuff).
- **Dissonance**: a tritone (+6) or minor second (+1) = **Poison/debuff**. These are the brew for traps and arrows,
  and they are a lesson in real dose danger: Comfrey is never taken internally, and Valerian + Hypericum stacks sedation and drug interactions.
- Consonance score (unison/octave 1.0, fifth 0.9, fourth 0.8, major third 0.7, minor third 0.6, sixths 0.5, seconds 0.2, tritone 0) sets potency.
- **Genome tie**: a player's token seed sets their **tonic**. Chords built on your own tonic get +25%.
In-world: the herb garden of 12 beds is laid out on the **circle of fifths** (`PI_Herb_*`, `PI_Label_Herb_*`), so neighbouring beds
are a fifth apart and make shields, and beds across the circle are a tritone apart and make poisons. 60 tone stones (`PI_ToneStone_*`) ring the garden;
a lower note means a taller stone.

## Livestock + survival loop
- Herds: coat-skinned livestock in the pens (`PI_Stock_*`, tag `livestock`), wearing the coats8 Turing coats
  (Worms, Solitons, Mitosis, Labyrinth, Coral, Fingerprint, Honeycomb, Wanderers + bred children).
  A herd's call is synthesized from its coat genome (the same pipeline as the Wild Biomes `SW_Call_*`).
- **Food growth**: 12 crops x 3 stages (`PI_Crop_*`): barley, oat, buckwheat, millet (grain); pea, bean (protein);
  turnip, kale, squash (vegetables); flax (fibre + oil); clover and lucerne (fodder, nitrogen fixers).
  The rotation is grain -> legume -> fodder -> roots, so the fixers restore the soil.
- **What animals eat**: grazing clover/lucerne, hay bales (`PI_Farm_HayBale_*`) in winter, grain tailings, and a salt lick for minerals.
  They drink at the troughs.
- **What people eat**: grain porridge and flatbread, pea/bean pottage, roots, kale, milk and eggs (from the nest boxes), and nettle greens;
  meat only from culled surplus. Herb teas from the garden.
- **The loop**: spring water -> crops + troughs -> fodder -> livestock -> manure back onto the crop beds -> food for people.
  Rain refills the cistern; the still covers drought. Pests and illness are answered with harmonic herbs.

## NFT tie
- Island seed = token id: `terrain_gs.py <tokenId>` makes that token's terrain; a token's Gray-Scott F/k sets its hills.
- The island song (`SW_PI_Song`) and stream bed come from the Turing-machine composer, so the island sounds like its token.
- Livestock coats = token coats; a bred pet's coat is the blended parent F/k (the breeding rules in STORY.md).
- Herb tonic = the holder's token tonic (+25% on their own key).
- The record presser cuts a holder's seed song to vinyl (the waiting state AMF puts on the web page).

## Items (Blender, hidden headless, 4 parallel jobs)
500 meshes, 114,972 tris total, one FBX each: 108 herbs (12 x 3 stages x 3 variants), 100 water-system parts, 60 livestock/farm props,
36 crops, 60 tone stones, 60 basalt rocks, 30 spruce, 20 shelf fungi, 26 music props (vinyl, press plates, speakers, lanterns).

## Audio rules
Everything is low-passed and soft (peaks at -18 dBFS; the song stays under ~1.1 kHz and the stream has <1% of its energy above 2 kHz).
There are no bright or piercing tones, and passing notes are played at a lower velocity. Forest and spacey beds are untouched.
