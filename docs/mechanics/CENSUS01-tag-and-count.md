# CENSUS01 — Tag and Count (contest G156)

*Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/MarkRecapture.java` (tests: `MarkRecaptureTest`, 12).*

## Story

The thistle hares came to the Ark Refuge on the third raft (ISLES01), and now they are everywhere and nowhere: you never
see more than a dozen at once. The ark kitchens want a harvest. Census-keeper Orrin Vale won't set a quota until he
knows how many hares there are, and you can't count animals that hide. So Vale counts them the old way: **catch some,
tag them, let them go, then catch again and see how many tags come back.** If a quarter of the second catch carries
tags, the tagged hares are about a quarter of the refuge.

## Quest `q_tag_and_count`: "Every Ear Tells"

1. Vale has **60 trap-nights**. Split them between session 1 (tagging) and session 2 (checking): `plan(t1, t2)`.
2. Run the census (`run()`). Vale's board shows M (tagged), C (second catch), R (tags seen again), the Chapman count
   and its 95% band.
3. Vale sets the harvest at 10% of the hares. You choose whether he works from the band's **lower end**
   (`quota(0.1)`) or from the **point estimate** (`greedyQuota(0.1)`).
   - A quota no larger than 10% of the true population keeps the refuge MEADOW (`band(0.1)`).
   - Overharvest lets it scrub over.
4. Side quests break the assumptions on purpose: ear tags that fall off (`tagLoss`), hares that learn the traps mean
   free food (trap-happy, `trapResponse` > 1) or a fright (trap-shy, < 1), and a long wait between sessions so that
   young hares replace old ones (`turnover`). The player has to work out which way each one bends the count.

Results with the defaults (240 hares, 60 trap-nights) over 200 seeds:

| Census | Mean Chapman | ACCURATE (within 15%) | Band holds the truth | Mean band width |
|---|---|---|---|---|
| 30 / 30, honest | 241.6 | 133 | 178 | 139 |
| 10 / 50 | 243.7 | 91 | 176 | 189 |
| 50 / 10 | 233.0 | 113 | 170 | 171 |
| 30% tag loss | 345.1 | 31 | 171 | 267 |
| 30% turnover | 342.6 | 34 | 177 | 265 |
| trap-shy (×0.5) | 401.1 | 15 | 180 | 381 |
| trap-happy (×2) | 156.2 | 0 | 0 | 42 |

With the honest 30/30 census, the lower-bound quota was safe in 200 of 200 seeds; the point-estimate quota overharvested
in 77. Trap-happy hares are the nasty one: a tight, confident band that never holds the truth.

## Rules (seeded)

1. Each hare is caught in a session of t trap-nights with chance `1 − (1 − 0.012)^t` (30 nights ≈ 0.30).
2. Session 1 tags every hare caught.
3. Between sessions, a hare is replaced by an untagged young one with chance `turnover`, and a tag falls off with chance
   `tagLoss`.
4. Session 2: a hare caught in session 1 (and still alive) is caught with its chance × `trapResponse`; others as usual.
   Tagged hares in the catch are the recaptures R.
5. Estimates: Lincoln-Petersen `M·C/R` (infinite with R = 0), Chapman `(M+1)(C+1)/(R+1) − 1`, Seber variance
   `(M+1)(C+1)(M−R)(C−R) / ((R+1)²(R+2))`, band `Chapman ± 1.96·√var`, with the lower end never below the M + C − R hares
   actually handled.

Every roll is a splitmix hash of (seed, session, hare, salt). `Settings.DEFAULT = (240, 60, 0.012, 0, 1, 0)`.

## What the tests pin

- The formulas match the textbook (M = 50, C = 40, R = 10 gives 200 and 189.09). With no recaptures, Lincoln-Petersen is
  infinite but Chapman stays finite.
- Chapman beats Lincoln-Petersen on bias when recaptures are few: with 12 + 12 trap-nights over 400 seeds, among censuses
  with R ≥ 1, Lincoln-Petersen averages 279 (+16%) and Chapman 221 (−8%); two censuses saw no recaptures at all.
- The honest census is nearly unbiased (mean within 5% over 200 seeds) and ACCURATE in at least 110 of 200.
- The 95% band holds the truth in at least 165 of 200 seeds.
- An even split gives a narrower band than 10/50 or 50/10. Sixty trap-nights give less than half the band width of twenty.
- Tag loss and turnover inflate the count by more than 25%. Trap-shy hares inflate it by more than 40%, and trap-happy
  hares shrink it below 75%, with a band that holds the truth in at most 20 seeds.
- The lower-bound quota never exceeds the true 10% surplus in any of 200 seeds, at 60 or at 20 trap-nights, while the
  point-estimate quota overharvests in at least 50. `band(rate)` is MEADOW exactly when the quota is safe.
- R never exceeds M or C, and the band never drops below the hares handled.
- The same seed and plan give the same census, and bad plans and settings are refused.

## Host seam

- `MarkRecapture.refuge(Settings, seed)`, then `plan(t1, t2)` from Vale's trap-night slider, then `run()`.
- `Census` fields drive the tally board: M, C and R pegs, the Chapman count, and the band as a bracket. `quota(rate)`
  versus `greedyQuota(rate)` is the player's choice, and `band(rate)` paints the refuge meadow. `truth` is for the
  judge and replay only, never shown on the board.
- Ties: the hares arrived through ISLES01's rafts, and Vale's board is G119's `Prop_Census_Board`. The harvest feeds the
  arks' kitchens. Cover uses the battlefield `Vegetation` bands.
- Assets: `Mob_Thistle_Hare` (Idle/Hop/Freeze; tagged-ear variant), `Prop_Live_Trap` (box trap with a drop door),
  `Prop_Ear_Tag` (small numbered tag), and reuse of the refuge tiles and the G119 census board (see UNREAL-QUEUE /
  BLENDER-ASKS).
- The G119 board is staged (see ISLES01): use `SOCKET_Peg_00`..`39` with `Prop_Census_Peg` as the M / C / R tally and
  `SOCKET_Text` for the Chapman count and band.

## Native C++ core (G615)

`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusMarshMarkRecaptureCore.h` (namespace
`daedalus::marsh`) is a header-only C++17 port of this core: `MarkRecapture::Plan`, `CatchChance` and the seeded
two-session `Run`; the `Census` estimates (Lincoln-Petersen, Chapman, Seber variance, 95% band, error, verdict, quota,
greedy quota, MEADOW/SCRUB band); and `MarkRecaptureSettings::Valid`. It uses the standard library only (no Unreal
headers). Where Java throws on impossible counts, the C++ estimators return NaN. The Java class stays the rules
authority. `MarshCoresParityTest.markRecapture` writes 24 golden vectors (8 tunings x {unplanned even split, a
quarter/three-quarter split, an over-budget plan that is refused}) to
`engines/unreal/core-test/marsh_mark_recapture_parity.txt`, and `marsh_mark_recapture_core_test.cpp` replays them.
From the same counts every estimate matches exactly (only + - * / and sqrt). The catch chance calls `pow`, so at
least 22 of 24 censuses must replay exactly (24 of 24 do with g++/glibc). CI runs this in
`.github/workflows/marsh-cores.yml`. See [NATIVE-PORT-PATTERN.md](NATIVE-PORT-PATTERN.md). No Fair Par cabinet reads
this core, so the par guard is unchanged.
