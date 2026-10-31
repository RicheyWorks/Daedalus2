# Prism Looks: Refraction Skins palette table and cabinet art notes

Owner: art-master-flex (Prismheart Looks lane). Source: `tools/minigames/prism_looks.py` (authority); native core
`DaedalusPrismLooksCore.h`; parity `engines/unreal/core-test/prism_looks_parity.txt`. Cosmetic data only: skins never change
rules, scores or balance. House skin is always worn; Verdant and Heartglass skins unlock from the game's best Warden seal
(Prism Satchel). A locked or unknown wanted skin falls back to the house skin. Accent is at least 60 luma (Rec.601, 0..255)
from base so trim text stays readable. All names are original.

| game | skin id | name | base | accent | glow | unlock | luma gap |
|---|---|---|---|---|---|---|---|
| facetlock | `facetlock_house` | Lattice Dawn | #1B2440 | #E8D7A0 | #7FD4FF | none | 177 |
| facetlock | `facetlock_verdant` | Copper Hinge | #2E1A12 | #F0B27A | #FF8A3D | verdant | 159 |
| facetlock | `facetlock_heart` | Glassbound Key | #0E1E2A | #D9F7FF | #B48CFF | heartglass | 212 |
| glimmerloom | `glimmerloom_house` | Warp and Weft | #2A1B3D | #F2D6E8 | #FF7AC8 | none | 189 |
| glimmerloom | `glimmerloom_verdant` | Indigo Bolt | #101A3A | #A9C4FF | #4F7BFF | verdant | 168 |
| glimmerloom | `glimmerloom_heart` | Spun Starlight | #15121F | #FFF4C2 | #FFE066 | heartglass | 221 |
| glowmoss | `glowmoss_house` | Mossbed Lantern | #13261A | #C8F0A0 | #6BFF8E | none | 188 |
| glowmoss | `glowmoss_verdant` | Fernshade | #0F1F14 | #9FE3B8 | #2EE6A6 | verdant | 177 |
| glowmoss | `glowmoss_heart` | Sporelight Crown | #1C1430 | #E6FFB3 | #D2FF4D | heartglass | 213 |
| lumenpath | `lumenpath_house` | Beamwright | #2B1608 | #FFD9A0 | #FFB000 | none | 195 |
| lumenpath | `lumenpath_verdant` | Kiln Mirror | #331010 | #FFC2B0 | #FF5A36 | verdant | 184 |
| lumenpath | `lumenpath_heart` | Noon Refractor | #1A1A2E | #FFFBE6 | #FFF06A | heartglass | 221 |
| prismcairn | `prismcairn_house` | Stacked Slate | #22262B | #D8DEE6 | #8FD18B | none | 184 |
| prismcairn | `prismcairn_verdant` | Lichen Cairn | #1B2617 | #D6E8B0 | #A6E05A | verdant | 187 |
| prismcairn | `prismcairn_heart` | Summit Geode | #241032 | #F0D9FF | #C77DFF | heartglass | 203 |
| prismvault | `prismvault_house` | Strongroom Umber | #1E1612 | #E0C9A6 | #C9A14A | none | 180 |
| prismvault | `prismvault_verdant` | Tumbler Teal | #0D2426 | #A8E6E0 | #2BC4B4 | verdant | 181 |
| prismvault | `prismvault_heart` | Sealed Sunburst | #14100A | #FFE9B0 | #FFC93C | heartglass | 217 |
| shadewatch | `shadewatch_house` | Night Sentry | #0C0E1A | #B8C2E6 | #6A7BFF | none | 181 |
| shadewatch | `shadewatch_verdant` | Owl Ember | #1A0E0C | #E6B8A8 | #FF6B4A | verdant | 178 |
| shadewatch | `shadewatch_heart` | Eclipse Watch | #07070C | #E8E8FF | #FFFFFF | heartglass | 227 |
| shardfall | `shardfall_house` | Falling Ember | #2A0F0A | #FFC7A8 | #FF6A2B | none | 190 |
| shardfall | `shardfall_verdant` | Cinder Rain | #1A1A1A | #E6E6E6 | #FF9E40 | verdant | 204 |
| shardfall | `shardfall_heart` | Meteor Choir | #100A24 | #FFE0F0 | #FF4FD8 | heartglass | 221 |
| shardring | `shardring_house` | Tidal Ring | #0A1E2E | #BFE6FF | #3FB8FF | none | 196 |
| shardring | `shardring_verdant` | Kelp Halo | #0E2418 | #BEEBC8 | #46D98A | verdant | 189 |
| shardring | `shardring_heart` | Moonwater Crown | #0B0B22 | #E0E8FF | #9FB4FF | heartglass | 219 |
| spiritkite | `spiritkite_house` | Gale Ribbon | #14263A | #DDF0FF | #8AE0FF | none | 202 |
| spiritkite | `spiritkite_verdant` | Thistle Draft | #2A1530 | #F0D0F5 | #D27BFF | verdant | 191 |
| spiritkite | `spiritkite_heart` | Aurora Tail | #061A1A | #D8FFF4 | #5CFFD0 | heartglass | 222 |
| wardens_accord | `wardens_accord_house` | Oathstone Blue | #14203A | #D6DCF0 | #5C8CFF | none | 189 |
| wardens_accord | `wardens_accord_verdant` | Grove Pact | #182614 | #DCEBC4 | #8CCF4E | verdant | 195 |
| wardens_accord | `wardens_accord_heart` | Heartglass Charter | #1E0F1E | #FFE3F2 | #FF7AB6 | heartglass | 216 |

## Cabinet art notes (one per Prismheart cabinet)

- **facetlock:** Brass lattice frame with a hinged glass marquee; facets catch a cold key light from upper left. Keep the lock glyph central.
- **glimmerloom:** Loom-frame silhouette, thread lines running across the bezel; glow pulses along the weft on a woven row clear.
- **glowmoss:** Rounded, overgrown cabinet edges with moss in the corners; low warm-green underglow, the screen reads like a lantern in a hollow.
- **lumenpath:** Mirror-panel sides with a single beam line etched across the marquee; glow follows the beam path left to right.
- **prismcairn:** Stacked-stone cabinet top (three slabs), matte slate body; accent only on the cairn stones, glow from the peak.
- **prismvault:** Heavy strongroom door motif on the front panel with tumbler dials as buttons; brass accents, glow only inside the dial rings.
- **shadewatch:** Tall narrow tower cabinet, a single watch-eye in the marquee; dark body, accent on the eye rim, cool glow.
- **shardfall:** Marquee shaped like a falling shard trail; ember sparks decal on the sides, glow drips downward.
- **shardring:** Circular ring bezel around the screen; tidal wave band on the base, glow chases around the ring.
- **spiritkite:** Kite-diamond marquee with a ribbon tail running down one side; light, airy body, glow on the ribbon.
- **wardens_accord:** Charter-stone slab front with two warden crests facing each other; accent on the crest inlay, glow under the oath line.

Blender staging: cabinet skins are material variants only (base, accent, glow slots); stage NOT READY.
