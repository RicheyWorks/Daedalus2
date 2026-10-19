# Melody Brewing vs Prometheus Harmonic Herbs: proposed split

Status (Oct 18 2026, youtube-master): PROPOSED to prometheus on the team link, no reply yet. Not agreed. If prometheus answers differently, edit this file and the ARCHITECTURE.md row.

| | Melody Brewing (youtube-master) | Harmonic Herbs / HerbChord (prometheus) |
|---|---|---|
| Input | an ORDERED sequence of 3-5 herbs at the brew bench | UNORDERED set of herbs played as a chord |
| Output | a consumable: drink / food / purified water for the survival loop; found tunes tie to seed-song records | audio: chord voicing for the Island Audio record (HRB 1 endpoint, jukebox cue) |
| Owns | herbcombo.py, found_tunes.csv, balance.json, ADaedalusBrewBench (DaedalusLink) | HerbChord, /api/v1/audio/herb-chord, AUD 1 |
| Shared, not duplicated | one pitch class per herb. Melody Brewing reads prometheus's herb-to-pitch table and never defines its own | same table is the source of truth |

Rules: no second herb-to-pitch mapping; ordered melody = brew bench, unordered chord = audio; the brew bench may call the herb-chord endpoint to play a result, never the reverse.