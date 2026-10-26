# Trough-Brew Pet Tonics (Kennel Isle, art-master-flex)
Machine-readable: `tonics.json` (100 recipes). Fits `NOTES\companions\companion-rules.schema.json`: every effect is a temporary `{stat, op, value}` mod, the same shape as gear mods, applied by the server.

## How it works
1. Harvest herbs (actors tagged `Herb_Source`, 36 placed, 12 kinds) and steep up to 3 in the brew trough `W9_Trough_3` (tag `Brew_Trough`).
2. **1st herb = base (effect family)**, **2nd = heart (stat)**, **3rd = finish (duration/mode)**. Order matters; a heart or finish herb in slot 1 does nothing.
3. Any pet that drinks gets the brew. The trough goes plain after 3 drinks or 10 min (the water loop refills it).

## The 12 herbs (placed on Kennel Isle as Prop_Herb_AMF_<Name>_V1)
| Herb | Role | Gives | Base value |
|---|---|---|---|
| Barkbalm | base | Heal (burst) | hearts +1.0 |
| Guardthistle | base | Shield (sustained) | blunt +0.15 |
| Wagwort | base | Speed (burst) | speed x1.10 |
| Howlroot | base | Fury (burst) | damage +0.5 |
| Dozeleaf | base | Calm (sustained) | loyalty +5 |
| Pawmint | heart | Stamina | cooldownPct -0.05 |
| Ironfang | heart | Defense | blunt +0.05 |
| Snoutsage | heart | Perception | hazardResist +0.10 |
| Starkibble | heart | Luck | expPct +0.05 |
| Furfern | finish | Long | 240 s |
| Dewclaw | finish | Swim | 120 s + swim, livestock can cross water |
| Coppercap | finish | Instant | one pulse, 0 s |
No finish = 120 s over time.

## Strength formula
`S = clamp(base x coat x drinker x stage, 0, 2 x base)`; `duration = durationSec x charm`
- **coat** (Turing pattern): Spots 1.25 on burst / 1.0 sustained; Stripes 1.0 burst / 1.25 sustained; Labyrinth 1.1 on all + 10% second roll; none 1.0.
- **drinker**: Cane Corso **1.0 (always full strength)**; pack member drinking after the Corso 0.5; other pets 0.75.
- **stage** (companion stages): 1 = 1.0, 2 = 1.1, 3 (Glitch Warden) = 1.2.
- **charm**: wearing a matching `charm` slot item doubles duration.
- `mul` mods scale as `1 + (value-1) x S/base`. Heart mod scales by the same factor.

Example: Corso, Stripes coat, stage 2, Bulwark: blunt 0.15 x 1.25 x 1.0 x 1.1 = **+0.206** (+ Ironfang 0.069) for 240 s.

## Recipe table (5 bases x 5 heart options x 4 finish options = 100)
| Base \ Heart | none | Pawmint | Ironfang | Snoutsage | Starkibble |
|---|---|---|---|---|---|
| Barkbalm | Heal | **Mend** | Heal+Def | Heal+Perc | Heal+Luck |
| Guardthistle | Shield | Shield+Stam | Shield+Def (**Bulwark** w/ Furfern) | Shield+Perc | Shield+Luck |
| Wagwort | Speed | Speed+Stam (**Dash** w/ Coppercap) | Speed+Def | Speed+Perc | Speed+Luck |
| Howlroot | Fury | Fury+Stam | **Fury** | Fury+Perc | Fury+Luck |
| Dozeleaf | Calm | Calm+Stam | Calm+Def | Calm+Perc | **Bond** (+20% breed) |
Each cell x {none, Furfern, Dewclaw, Coppercap}.

Named: Mend (Barkbalm+Pawmint), Bulwark (Guardthistle+Ironfang+Furfern), Dash (Wagwort+Pawmint+Coppercap), Fury (Howlroot+Ironfang), Bond (Dozeleaf+Starkibble).

## Balance pass 1 (00:40 PT)
| Base | base value | Corso max (Spots/Stripes, stage 3) | pack min (no coat, stage 1) | cap 2x |
|---|---|---|---|---|
| Barkbalm | +1.000 | +1.500 | +0.500 | +2.000 |
| Guardthistle | +0.150 | +0.225 | +0.075 | +0.300 |
| Wagwort | x1.100 | x1.150 | x1.050 | x1.200 |
| Howlroot | +0.500 | +0.750 | +0.250 | +1.000 |
| Dozeleaf | +5.000 | +7.500 | +2.500 | +10.000 |
Result: max factor 1.5 (1.25 x 1.2) stays under the 2x cap, so the cap never binds for one drink; Labyrinth second roll (10%) is the only path near 2x. Fury +0.75 dmg at max vs Molosser Bite power 1.0 is the strongest; kept, since it lasts 120 s and costs a trough slot.

## Schema check (00:51 PT)
All 180 mods in the 100 recipes use stats already in corso-rules.json (base + gear mods: blunt, cooldownPct, damage, expPct, hazardResist, hearts, loyalty, speed) and op add/mul. 0 invalid; no new stat fields needed in companion-rules.schema.json.

## Bottled tonics (01:03 PT) - maps the 40 Item_Tonic_AMF_<Name>_T1..T4 items in amf_items.py
Bottling a trough brew (empty bottle + 1 drink of the brew) stores it off-island. The drinker multiplier still applies when it is drunk.
| Item | Recipe |
|---|---|
| Mend | Barkbalm + Pawmint |
| Bulwark | Guardthistle + Ironfang + Furfern |
| Dash | Wagwort + Pawmint + Coppercap |
| Keen | Wagwort + Snoutsage |
| Calm | Dozeleaf |
| Fury | Howlroot + Ironfang |
| Thick | Guardthistle + Pawmint + Furfern |
| Glow | Barkbalm + Starkibble |
| Swim | Wagwort + Pawmint + Dewclaw |
| Bond | Dozeleaf + Starkibble |
Tier = bottled strength: T1 0.5x (1 herb bundle each), T2 0.75x (Bundle2+), T3 1.0x (Bundle3+, steeped while the Corso is at the trough), T4 1.25x (Bundle5 + matching charm worn by the drinker). Tier never pushes past the 2x cap.

## Herb economy (01:13 PT)
- 36 tagged herb plants (12 kinds x 3) on Kennel Isle; each harvest gives 1 bundle and regrows in 1 game day if watered from the trough line (ISLAND.md section 3).
- Supply: 36 bundles/day. A full 3-herb brew uses 3 bundles and serves 3 drinks, so the island supports 12 brews = 36 pet-drinks a day.
- Demand: the pack is the Corso + pup + about 6 pets, so 1 brew per pet per day uses about 8 brews (24 bundles), leaving 12 bundles for bottling (4 T1 bottles or 2 T3).
- Bottleneck: only 3 plants of each kind. Base herbs run out first if everyone wants Fury, which is intended: the pack has to mix tonics.
- Brewing costs no extra water: the brew uses the trough's existing water, and the cistern (2,000 L, about 30 L/day demand) refills it.

## Corso move interactions (01:25 PT) - moves from corso-rules.json
| Tonic | Corso move | Interaction |
|---|---|---|
| Fury (+0.5 dmg) | Molosser Bite (power 1.0), Glitch Lunge (2.2) | damage mod adds before move power, so the Lunge gains the most |
| Bulwark / Thick (blunt) | Stand Guard (0.35, target owner) | Guard shares half the tonic's blunt with the owner while active |
| Mend (hearts) | Never Leaves (passive, life 8) | heal over time keeps running while Never Leaves holds the Corso up |
| Dash / Swim | Curbside Pickup (stage 2) | carry runs at tonic speed; Swim lets it fetch across water between fragments |
| Calm / Bond (loyalty) | Low Growl (debuff, magicCost 1) | no change to the growl; loyalty only affects taming and breeding, to keep PvP clean |
| Pawmint (cooldownPct -0.05) | all moves | stacks with charm_crystal (-0.1), total cooldown floor -0.25 |

## In-world tags (round 5, 01:30 PT, amf_turn5_ue.py -> last_turn5.json)
- Brew trough actors (tag Brew_Trough, 2): Tonic_Data_tonics_json_v1, Tonic_MaxHerbs_3, Tonic_Slot1_base / Slot2_heart / Slot3_finish, Tonic_Decay_3drinks_10min, Tonic_Recipes_100, Tonic_CorsoDrinker_1.0, Tonic_Pack_0.5.
- Herb actors (tag Herb_Source): Tonic_Herb_<Name>, Tonic_Role_<base|heart|finish>, plus Tonic_Family_/Tonic_Shape_/Tonic_Stat_/Tonic_Finish_/Tonic_DurSec_ and Tonic_Mod_<stat>_<op>_<value>.
- Gameplay code reads these with GetAllActorsWithTag and needs no extra lookup.
- Open item: only 12 of the 36 herbs matched Herb_Source in Island_AMF. The other 24 (turn-3 tagged) need a check next turn. Rerunning the script is safe because it skips existing tags.
- Diagnosis (01:52 PT): amf_loop_ue.py:80 tags herbs by actor label (tag_existing), so it reaches only one actor per label. amf_island_ue.py:77 places 3 per kind (V1..V3). Next turn: tag every actor whose label starts with Prop_Herb_AMF_ (as amf_turn3_ue.py:19 does) with Herb_Source plus the tonic tags.
