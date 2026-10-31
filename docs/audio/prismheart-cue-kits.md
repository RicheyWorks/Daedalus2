# Prismheart cue kits (audio lane, slice 1)

Engine-free C++17 core: `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusCueKitCore.h`.
Tests: `engines/unreal/core-test/cue_kit_core_test.cpp` with `cue_kit_golden.txt`; CI `.github/workflows/cue-kit-core.yml`
(g++ and clang++ with ASan/UBSan and `-ffp-contract=off`, MSVC `/W4 /WX /fp:strict`). Source only; not yet wired to any
cabinet or Unreal sound.

## What it does

Every Prismheart cabinet gets its own short, recognisable cue kit, seeded by `KitSeed(gameId, tokenId)` (FNV-1a 64 of
the game id mixed with the island token, then SplitMix64), so a cabinet sounds the same on every platform and each
island's copy has its own flavour.

| cue | rule |
|---|---|
| start | three notes from the kit's scale |
| good | two or three notes stepping up the scale |
| miss | two notes falling one to three scale steps, held longer (gentle, never harsh) |
| win | four notes ending on the octave of the root |
| streak | one quick rising note per streak day (up to 8), then the win cue (idea PROM-2) |

Scale: a root of 165, 175, 196, 220, 247 or 262 Hz and just-ratio major pentatonic degrees 1, 9/8, 5/4, 3/2, 5/3 plus
the octave, so the top note is at most 524 Hz. Notes are 90-150 ms with 20-40 ms gaps; every cue is under 2 s.

## Ear rule

Each note becomes an `earrule::CallSpec` through `EarSafePeak` (`DaedalusEarRuleCore.h`): base and peak under 800 Hz,
two soft harmonics, brightness 0.15, no sweep or vibrato. Tests check this for every note of 50,000 random kits.

## Originality

Cues are generated from seeds and a fixed scale; no existing tunes, samples, real-person names or trademarks.

## Tests

Golden vectors for 20 cabinet ids x 30 tokens (every cue, plus streak cues for 3 and 8 days); property tests over
50,000 kits (in scale, under 800 Hz, soft, good rises, miss falls gently, win ends on the octave, streak length and
clamping, no leap past an octave); every listed cabinet gets a different kit; roots spread evenly over tokens; FNV-1a
and SplitMix64 reference values.

## Ruleset V2 (team PRNG, slice 2)

PLAN.md asks every Prismheart lane to draw randomness from `DaedalusPyRandomCore.h` (CPython-compatible
`random.Random`). V2 does that: `MakeKitV2(gameId, tokenId)` seeds `PyRandom("cuekit|<game>|<token>")` and runs the same
musical rules (`BuildKit`) as V1, so the ear-rule limits and cue shapes are unchanged. The rules reference is
`tools/minigames/cue_kit.py`, which writes `cue_kit_golden_v2.txt`; CI regenerates it from Python and checks the C++ core
matches it line for line. V1 (`MakeKit(KitSeed(...))`, `cue_kit_golden.txt`) is kept frozen and unchanged for anything
already pinned to it; new cabinet wiring should use V2.
