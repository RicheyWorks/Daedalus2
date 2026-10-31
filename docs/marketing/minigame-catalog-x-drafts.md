# Minigame catalog: X post drafts (DRAFT, for Richey's review)

Status: draft only. Nothing here has been posted or scheduled. No posting tools were used.
Prepared by Prometheus on 2026-10-29 from what is in the repo on main (`c836c3ba8`):
`tools/minigames/minigame_catalog.py`, `docs/minigames/CATALOG.md`, the contest board Results and the
`daedalus-core` audio game sources. Character counts are in brackets; every post is under 280.

Grounding rules used: no player counts, no release dates, no "play now" (the catalog says native status is
source only until the batched rebuild), no real-person names, no trademarked game names, light on the
Daedalus world. Ecology numbers in the games are illustrative and the posts say so where it matters.

## Single posts

**1. The catalog** [245 chars]
> Fifteen small arcade cabinets now live in one catalog. Each has one plain line on how to play, easy/normal/hard, and a seed, so the same start comes back every time. Next step is the rebuild that puts them in their corners of the Daedalus world.

**2. Gloam Latch** [156 chars]
> Gloam Latch: flip a lamp and its neighbors flip with it. The goal is a dark board. Small rule, lots of thinking. One of the quieter cabinets in the catalog.

**3. Reedbeat** [184 chars]
> Reedbeat has a one-line rule: strike while the reed is bright. As a musician I like games that are really about timing and listening. This one sits on a reed bench in the Orrery Reach.

**4. Lumenpath Refraction** [178 chars]
> Lumenpath Refraction: toggle mirrors in a little lattice to bend a beam through every crystal before your moves run out. Seeded, so a puzzle you liked can be dealt again exactly.

**5. Cricket thermometer** [259 chars]
> Snowy tree crickets chirp faster when it's warmer. An old rule of thumb for that one species: degrees F is about 40 plus the chirps in 15 seconds. One of our sound puzzles has you pick out the steady cricket and count. A field estimate, not a lab thermometer.

**6. Brook Babble** [227 chars]
> Why does a brook babble? Partly because newly trapped air bubbles ring as they form, and bigger bubbles ring lower. In Brook Babble you size bubbles by pitch. The "aeration" score is an illustrative index, not dissolved oxygen.

**7. Reed Hum** [244 chars]
> Wind past a thin stem sheds little vortices from side to side, and the stem hums. Pitch rises with wind and falls with thickness. Reed Hum asks you to read the wind from the hum. Real reeds flex and wind gusts, so treat the numbers as a sketch.

**8. Bat Ranging** [243 chars]
> A hunting bat calls faster as it closes on a moth, and the echo delay tells it the range. Bat Ranging slows the calls way down so you can hear them. Real calls are ultrasonic; our playback is compressed far more than a real bat detector would.

**9. Brood Cycles** [214 chars]
> Some periodical cicadas emerge every 13 or 17 years. One idea, still a hypothesis, is that prime cycles rarely line up with predator booms. Brood Cycles lets you test that with made-up predators and pick the cycle.

**10. The ear rule** [244 chars]
> A rule I keep for the island's sound puzzles: no piercing tones. Fundamentals stay under 800 Hz, and a test sweeps hundreds of seeds to check it. Real bats, crickets and bubbles go much higher, so the games say plainly when pitch is compressed.

**11. Seeds** [177 chars]
> Every game here is seeded. Same seed, same puzzle, same sound, byte for byte. That makes bugs easy to repeat, and it means you can hand a friend the exact board you just played.

## Thread (5 posts)

**T1** [83 chars]
> A short tour of the minigame catalog: small cabinets, plain rules, seeded starts. 🧵

**T2** [202 chars]
> Fifteen arcade cabinets, each with one line of rules. A few: "Flip a lamp and its neighbors until the board is dark." "Strike while the reed is bright." "Slide the falling stone and clear a full layer."

**T3** [200 chars]
> Each cabinet has easy, normal and hard, and a seed, so you can replay the exact same game. Each one also has a home spot picked out in the Daedalus world: a lamp corner, a reed bench, a stacking yard.

**T4** [214 chars]
> Beside the cabinets there are sound puzzles from the regrown island: count crickets for the temperature, size brook bubbles by pitch, read the wind from humming reeds. Numbers are illustrative and the games say so.

**T5** [124 chars]
> They're built and tested in source now; the next step is the rebuild that puts them in place. I'll share clips as they land.

## Notes for Richey

Facts to verify before posting:
- 1, T2, T3: "fifteen cabinets" is the count in `docs/minigames/CATALOG.md` today (plus 2 Python and 2 Java cabinets not counted). Recount if the catalog changes.
- 1, T3, T5: the catalog says native status is "source only until the batched rebuild". Don't say "play now" until that changes.
- T3: 14 of the 15 cabinets have a spot in the spots table; `cairnwell` is listed under `bricks` ("the stacking yard"). Check that the realm names are fine to say in public.
- 5: Dolbear's rule (F = 40 + chirps in 15 s) applies to the snowy tree cricket only; the game's pitches are compressed.
- 6: Minnaert bubble resonance is real physics; the aeration score is the game's illustrative index.
- 7: aeolian tone f = St U / D is textbook; the bumblebee forage line in the game is illustrative, so the post leaves it out.
- 8: the replay compression is much larger than real time-expansion detectors (about 10x); the post says so.
- 9: the prime-cycle idea is a hypothesis; the predators are invented.
- 10: the 800 Hz rule is enforced in the core audio pieces and by EarRuleSweepTest. I have not checked every cabinet's sound effects, so keep the post scoped to the island's sound puzzles, or verify the cabinets first.
- 5 to 9: these are contest pieces in `daedalus-core` with tests. Confirm how players reach them in game before implying they're playable.
- 11: true for the cabinets (`StartGame(id, seed)`), the Python games and the core audio (G502 regression test). "Hand a friend the board" assumes seeds are shown to players; verify.

Clip pairings (suggestions only; I found no clip files in the repo or on the board, so these are by game name for Hephaestus to pick from):
- 1, T1, T2: a montage of cabinet title screens (Ironwake has a title screen; others start straight in).
- 2: Gloam Latch board going dark.
- 3: Reedbeat timing strikes.
- 4: Lumenpath beam bending through crystals (terminal render works if no 3D clip exists).
- T3: Cairnwell layer clear, or Hephaestus island's rock yard / terrace grid (Driftstone, Emberstep, Ironwake live there).
- 5 to 9: audio-first, so a waveform or spectrogram clip of the in-game sound with a still of the marsh or brook.
- 10, 11: no clip needed, or a short screen capture of the sweep test passing.

Left out on purpose: the Java card-table and number-grid cabinets (third-party names), player counts, dates, and anything about tokens.
