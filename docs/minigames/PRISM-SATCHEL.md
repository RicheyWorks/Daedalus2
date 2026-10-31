# Prism Satchel and Warden Trials

One shard wallet and one mastery ladder shared by all 11 Prismheart games (Progression lane of the Prismheart round).

- Rules authority: `tools/minigames/prism_satchel.py` (Python).
- Native core: `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusPrismSatchelCore.h` (header-only C++17,
  integer only, no RNG, no I/O).
- Parity: `tools/minigames/prism_satchel_parity.py` writes `engines/unreal/core-test/prism_satchel_parity.txt`;
  `prism_satchel_core_test.cpp` must reproduce it byte for byte (CI: engines.yml, gcc ASan/UBSan and clang; the
  fixture check runs in desktop-games.yml). Tests: `tools/minigames/test_prism_satchel.py`.

## Prism Shards

A finished game pays shards of the game's home hue (ember, tide, verdant, gale or umbra):

| Result | Shards |
| --- | --- |
| Win | 1 / 2 / 3 (easy / normal / hard) + min(4, score // divisor) |
| Loss | min(2, (score // divisor) // 2) |
| Perfect run (a win the game marks perfect) | +2 |
| Each new Warden seal level the run reaches for that game | +1 |

Spending names one or more hues and a whole number of shards per hue; a short satchel refuses the whole spend and
nothing is taken. Bad results (unknown game or difficulty, negative or non-integer score, a perfect loss) are refused.

## Warden Trials

Each game keeps its best seal, in order:

1. Ember: finish a game (any result).
2. Tide: win.
3. Verdant: win on normal or hard.
4. Gale: win on hard.
5. Umbra: win on hard with score >= the game's umbra par.
6. Heartglass: win on hard with score >= the heartglass par, or a perfect run where the game has one (Glowmoss).

`heartglass()` counts Heartglass games (for Spirit Boons later).

## Payout table

Pars come from the Fair Par table (pythagoras; `engines/unreal/core-test/prism_fair_par_parity.txt`, docs/mechanics/FAIRPAR02)
on hard: umbra par = silver, heartglass par = gold. Prismcairn hard has no par (the bot never wins), so it uses normal.
Glowmoss keeps Heartglass for a perfect run. `test_prism_satchel.py` pins the table against the Fair Par file. Changing a
par or divisor changes the parity fixture, so regenerate it in the same PR and keep the C++ table in sync.

| Game | Home hue | Score divisor | Umbra par | Heartglass par |
| --- | --- | --- | --- | --- |
| facetlock | gale | 40 | 130 | 160 |
| glimmerloom | tide | 50 | 120 | 135 |
| glowmoss | verdant | 12 | 29 | perfect |
| lumenpath | ember | 50 | 140 | 180 |
| prismcairn | verdant | 35 | 105 | 105 |
| prismvault | umbra | 40 | 100 | 200 |
| shadewatch | umbra | 40 | 148 | 163 |
| shardfall | ember | 12 | 34 | 38 |
| shardring | tide | 60 | 188 | 215 |
| spiritkite | gale | 8 | 22 | 25 |
| wardens_accord | tide | 15 | 60 | 65 |

## Save

One text line, strictly parsed: `PRISMSATCHEL1;<ember>,<tide>,<verdant>,<gale>,<umbra>;<runs>;<game>:<seal>,...`
(seals sorted by game id, at most 4096 characters, counts up to 9 digits). A load is refused on:

- a wrong tag or part count;
- a non-digit or overlong count;
- an unknown or duplicate game;
- a seal outside 1-6;
- anything that is not in canonical form (leading zeros, wrong order, stray separators).

Seal levels and shard counts are wallet facts, not replays. A hand-edited but well-formed save loads, the same as any
local save file.
