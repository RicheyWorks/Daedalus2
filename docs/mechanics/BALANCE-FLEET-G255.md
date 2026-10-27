# G255 Balance Fleet: Reedbeat, Beacon Sweep, and a Shardring/Cairnwell re-run

Follows [G192 balance simulator](BALANCE-SIM-G192.md) and [G197 balance tuner](BALANCE-TUNER-G197.md). This adds two
more minigames to `com.daedalus.world.odds.balance` and re-runs the first two against `main`. **Reporting only: no
game source was changed.** Run `FleetReport.main` to reproduce every number below (seed 255; the re-run uses the
G192/G197 seeds 190/195).

Bands (unchanged): easy 60-98%, normal 30-90%, hard 10-75%. A mode is flagged only when its whole 95% Wilson interval
sits outside its band. The tuner requires the whole interval inside the band and strict easy > normal > hard.

## Which games were picked

Read from `origin/main` at 53b52ce8 (Oct 26, 21:10 PT). The 15 desktop cabinets live in
`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DesktopGames/`.

* **Reedbeat** (`DaedalusDesktopReedbeatCore.h`, 84 lines): a rhythm round with a clear win (all notes hit) and loss
  (3 misses), and real per-option constants. Picked.
* **Beacon Sweep** (`DaedalusDesktopBeaconSweepCore.h`): a minesweeper with three real boards and win/loss. Picked.
* **Gloam Latch**: a lights-out puzzle that is always solvable and has no move limit or loss, so a win rate is always
  100%. Not a balance target; skipped.
* Maze/Riftwing, the platformers, shooters and sports cores are 900-1000 line real-time games whose outcome depends on
  continuous movement and enemy AI; a faithful headless model is a larger job than this slot. Skipped (good next step).

**Cabinet difficulty finding (PR #533, `cursor/difficulty-20261026`).** `SetCabinetDifficulty("easy"|"normal"|"hard")`
on every cabinet only stores the name; its own test pins that "option, score, and note stay put". So on all 15
cabinets the easy, normal and hard *labels* currently play identically. The modes that really differ are each game's
`SetOption` values, and those are what this report simulates (mapped softest first).

## Reedbeat

Source: option 1 practice = 4 notes, 18-tick window, gap 40 (mapped "easy"); option 0 = 8 notes, 8-tick window, gap 36
("normal"); no third option ("hard" reported missing). First note at gap + seed mod 5. A press in the window is a hit;
a press outside it is a miss and the note stays scheduled; a window that closes unstruck is a miss. A press on the
closing tick costs two misses, as in the source.

**Player model (assumed):** an anticipating tapper who aims at the window centre with Gaussian timing error, sd 4
ticks (~67 ms at 60 Hz), and re-aims after an early miss. The gap does not affect this player.

| Mode | Shipped (notes, window) | Win (n=2000) | 95% CI | Flag |
|---|---|---|---|---|
| easy | 4, 18 | 97.4% | 96.6-98.0 | none (at the 98% ceiling) |
| normal | 8, 8 | 28.1% | 26.2-30.1 | none (straddles the 30% floor) |
| hard | not in source | - | - | MISSING_MODE |

Tuner suggestion (confirmed on a fresh seed, n=1500):

| Mode | Shipped | Suggested | Win | 95% CI |
|---|---|---|---|---|
| easy | 4, 18 | 4, **14** | 92.5% | 91.0-93.7 |
| normal | 8, 8 | 8, **10** | 54.4% | 51.9-56.9 |
| hard (new) | - | 8, 8 (today's normal) | 28.7% | 26.5-31.1 |

Read: normal is borderline too hard for this player; widening its window to 10 ticks puts it mid-band, and today's
8-tick round becomes a natural hard option.

## Beacon Sweep

Source: option 0 = 9x9/10 mines, 1 = 16x16/40, 2 = 30x16/99 (easy/normal/hard). Mines are planted on the first
reveal, never in that cell's 3x3; zeros flood; a mine loses; all safe cells win.

**Player model (assumed):** a careful logician who opens the centre, applies the single-cell rules and the pairwise
subset rule, never flags wrongly, and when stuck guesses the lowest local-risk cell (ties random). Weaker players will
lose more, so treat these as upper figures.

| Mode | Shipped | Win (n=2000) | 95% CI | Flag |
|---|---|---|---|---|
| easy | 9x9, 10 | 95.8% | 94.8-96.6 | none |
| normal | 16x16, 40 | 80.6% | 78.8-82.2 | none |
| hard | 30x16, 99 | 24.9% | 23.0-26.8 | none |

Tuner keeps 9x9/10 and 16x16/40; for hard it lands on 100 mines (23.9%) only because 99 is off its 5-mine grid. Keep
the shipped 99. **Beacon Sweep is balanced: no change recommended.**

## Shardring and Cairnwell re-run on main

Shardring Resonance landed on `main` (`tools/minigames/prism_shard.py`, PRs #531, #554, #614). Its `DIFFICULTY` table
(12/3/60, 10/4/50, 8/5/40) and rules are byte-identical to the branch G192 used; main only added save/load, demo and
the web/controller front ends. Cairnwell's core on main matches the G192 commit, and PR #533 does not touch its wells.
The re-run reproduces G192/G197 exactly:

* Shardring: easy 52.8%, normal 2.0%, hard 0.0%, all TOO_HARD. Suggested: easy 14 facets, normal 3 hues, hard 3 hues.
* Cairnwell: easy and normal 100%, TOO_EASY; hard missing. Suggested: practice 4 rows; normal 7 rows, drop every 8;
  new hard well 6x5, drop every 8.

## Code

`ReedbeatBalance` and `BeaconSweepBalance` each implement both `BalanceGame` (shipped modes) and `TunableGame` (knobs),
reusing `OddsRng`, Wilson intervals, `BalanceCheck` and `BalanceTuner` unchanged. `FleetReport` wires them up.
`FleetBalanceTest` covers shipped constants vs source, seeded determinism, Reedbeat rules (perfect tapper always wins,
wild tapper loses, wider windows help), Beacon Sweep planting (never in the first 3x3, exact mine count) and solver
soundness (never opens a mine or flags a safe cell on 200 seeded boards), and that every published suggestion's
interval sits in band with strict easy > normal > hard.
