# G19 Anvil and Quench (contest 2026-10-19)

Owner: hephaestus. Core: `daedalus-core/src/main/java/com/daedalus/world/forge/TemperForge.java`, tests in `TemperForgeTest.java`. Source only; the Unreal binding waits in BOARD\UNREAL-QUEUE.md.

## Story tie-in
On Hephaestus Island the planet's shattered core became the Great Forge, and the keepers carved one rule into the quench tub: **"Heat alone breaks. Water alone softens. Temper both, or the ark dies in the void."** (data/islands/hephaestus/ISLAND.md). Anvil and Quench is that rule as a minigame. Its temper score (0-100) feeds **Forge Weapon Grades** (`ForgeGrades.grade`) for swords and blasters. A **DUAL** quench at temper 60 or more stamps an ark plate, the last step of quest `q_forge_temper`.

## Play
All times are milliseconds since the blank went into the forge.

1. **Heat:** the blank warms at its metal's rate. Pull it in the target band. Each degree outside the band costs 10 per-mille, and the blank burns at target + 300 C.
2. **Hammer:** the anvil beat starts 1 s after the pull, with 5-8 strikes at 520-780 ms (seeded). Strikes are judged PERFECT or GOOD by the metal's window, otherwise MISS. The blank cools 25 C/s, and a strike below target - 250 C is a CRACK, capping temper at 30. A strike after the quench is WASTED, and each strike past the beat count costs 100 per-mille.
3. **Quench:** dip at the quench heat, which the blank reaches about one beat after the last strike. The window is +/-30 C for MAGMA (strength) and SPRING (duration), and +/-15 C for DUAL (both).

Temper = 30% heat + 45% hammer + 25% quench.

| Metal | Target C | Band | Heat C/s | Perfect ms | Good ms |
|---|---|---|---|---|---|
| Copper | 700 | 45 | 140 | 80 | 170 |
| Bronze | 760 | 40 | 130 | 75 | 160 |
| Iron | 850 | 40 | 120 | 70 | 150 |
| Steel | 900 | 35 | 110 | 60 | 135 |
| Starmetal | 1100 | 25 | 100 | 45 | 110 |

Wood, stone and obsidian are shaped, not tempered (`forgeable` is false).

`judge(blank, run)` is pure, so the host replays any submitted run (pull, strikes, quench, medium) and gets the same result. `idealRun` is the master smith's reference.

## Tests
`TemperForgeTest` has 11 tests:
- Blanks are seeded and in range.
- Only metals are tempered.
- The ideal run reaches temper 98 or more for 5 metals, 100 seeds and 3 quench paths.
- Mistiming never raises temper.
- Harder metals judge tighter.
- The heat bands hold, and the blank burns at the cap.
- A cold strike cracks the blank and caps temper.
- Wasted and overwork strikes are scored as above.
- DUAL has half the quench window.
- Temper feeds ForgeGrades unchanged.
- Judging is pure.

## Unreal later (UNREAL-QUEUE)
- At the Great Forge, show the glow colour from `heatAt`.
- Add an anvil beat cue and a strike input.
- Add a quench tub with magma, spring and dual dips.
- Show the result and the ForgeGrades sheet in the HUD, and play an ark-plate stamp effect.
