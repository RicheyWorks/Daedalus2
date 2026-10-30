# Shardsong Crossing (G587)

Engine-free C++17 core: `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusShardsongCore.h`.
Tests: `engines/unreal/core-test/shardsong_core_test.cpp` with `shardsong_golden.txt` (CI: `.github/workflows/shardsong-core.yml`,
g++ and clang++ with sanitizers, plus MSVC). Native status: source only, not yet in a cabinet or the catalog script.

| id | title | portable tests |
|---|---|---|
| `shardsong_crossing` | Shardsong Crossing | 1 (golden vectors + properties) |

## How to play

| id | line |
|---|---|
| `shardsong_crossing` | HOW Pick a pitch and a tone or trill so the song carries to the mate across the strips. |

When the planet shattered, songbird pairs were split across the drifting fragments that became the Daedalus islands.
Each of five rounds shows the path between the two birds: one to four strips of forest, grass, open water or scrub,
10 to 120 m each, and the habitat the mate sits in. The player picks one of six call bands (200, 250, 315, 400, 500
or 630 Hz) and a form: a steady tone or a fast trill. The mate hears the call if it arrives at least 3 dB above the
noise where the mate sits. A round scores 100 for the best possible choice and one point less for every 0.1 dB short
of it (0 if unheard). A game is 0 to 500.

## Difficulty

| id | default | easy | normal | hard |
|---|---|---|---|---|
| `shardsong_crossing` | normal | 1-2 strips | 2-3 strips | 3-4 strips |

## Ruleset V2 (opt-in; V1 stays the default and is frozen)

`Game::Begin(seed, difficulty, Ruleset::V2)`. V1 (`shardsong_golden.txt`) is unchanged line for line. V2
(`shardsong_golden_v2.txt`) adds:

- **Marsh and rock strips.** Reed stems scatter the upper bands hardest and a frog chorus fills the middle bands at a
  marsh mate; bare rock is quiet and open but echoes off its faces smear trills a little.
- **Wind and a singing flock each round.** Wind (calm half the time, else breeze or gusty) adds low-pitched noise at the
  mate (halved in forest shelter) and doubles the blur on steady tones over open ground when gusty. Most rounds another
  flock sings in one band at the mate's fragment, masking it (and half its neighbours), so the call must find a free
  band: the acoustic niche idea, illustrative.
- **Gentle first round and a difficulty ramp.** Round 1 is always one 20-60 m strip in still air with no flock. Later
  rounds use the difficulty's base strip count, one more strip in rounds 4-5, and the longest strip allowed grows from
  60 m to 120 m. Every crossing is solvable both with the best call and with a tone alone.

Why: in V1 one answer (315 Hz tone) was best in 35% of rounds and two bands carried most of the game. Over 45,000 V2
rounds no single answer is best in more than 25% (the top is 315 Hz tone at about 23%), every band is the answer at
least 5% of the time, and trills win about 37%.

## Feedback (free, after any call)

`Advise(crossing, band, form)` says how far the call fell short of the best one (in 0.1 dB), whether the mate heard
it, whether to try a lower or higher pitch or the other form, and the main cause: soaked up by the habitats on the
way, smeared (a trill in forest echo, a tone in open wind), or masked by noise where the mate sits. `Explain` gives
the full breakdown: spreading, absorption, smearing and noise, which add up to the SNR exactly.

## Daedalus tie-in

The seed for a fragment pair comes from a Daedalus token id (`TokenSeed(tokenId)`, SplitMix64 defined in the header),
so every island token has its own five crossings, identical on every platform.

## Ecology (illustrative)

Levels are integer tables in tenths of dB: spreading loss (20 log10 d), excess attenuation per habitat that rises with
pitch in foliage, a low-band ground dip over grass, reverberation that smears trills in forest, wind that blurs steady
tones over open ground, and ambient noise that differs by habitat (low wind roar, high insects, low surf). The trend
follows the acoustic adaptation hypothesis: dense habitats favour lower, tonal songs and open ones higher, modulated
songs. The hypothesis holds for some bird groups and not others, and real songs mostly sit well above 800 Hz. The
numbers here are illustrative, chosen for play, not measured.

## Sound

Every call is built through `DaedalusEarRuleCore.h` (`EarSafePeak`): the fundamental and its peak with vibrato stay
under 800 Hz, with soft two-harmonic tones and no piercing sounds.

## Iteration log

| # | PR | change | behavior |
|---|---|---|---|
| 1 | iter PR 1 | `Explain` / `Advise` no-cost feedback (cause: absorbed, smeared, masked; pitch and form hints) | unchanged, golden v1 identical |
| 2 | iter PR 1 | property, boundary and fuzz tests: 10 m more path lowers every call; 10 m and 400 m edges; 30,000 raw seeds solvable | unchanged |
| 3 | iter PR 1 | ear-rule checks (base and peak < 800 Hz, 2 harmonics, low brightness, no extra drop) and a no-heap check over 500 full games | unchanged |
| 4 | iter PR 2 | Ruleset V2: marsh and rock strips (V1 frozen and default) | V2 only; new golden v2 |
| 5 | iter PR 2 | V2: per-round wind and a singing flock masking one band (balance: no answer above 25%) | V2 only |
| 6 | iter PR 2 | V2: gentle first round and a difficulty ramp; tone-solvable guarantee | V2 only |
