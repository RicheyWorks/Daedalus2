# ADR-060: Squad tactics, with Java deciding and Unreal executing (DTO 1)

**Status:** accepted, 2026-10-13. **Author:** unreal-team (Claude). **For:** team-codex (Java Living World / combat
director), Richey.

## Why

Richey wants Halo-style encounters: foes that coordinate, react to how you fight, and are remembered by a persistent
world. The split is:
- **Java** decides at squad timescale, about once a second: who flanks, who holds, who falls back. It also holds
  the persistent memory: factions, what you did here last time.
- **Unreal** executes at frame timescale: movement, attacks, hits and animation in `ADaedalusTarget`.

Nothing inside a frame waits on Java. A missing or slow director only means foes fight alone, which is how they
fought before this ADR.

## Decision

1. **The contract is DTO 1** (Daedalus Tactical Orders), a versioned plain-text spec like DRR 1:
   ```
   DTO 1
   squad <id> tick <n>
   order <unit> <HOLD|ATTACK|FLANK|DEFEND|RETREAT|REINFORCE> <LEFT|RIGHT|-> <x> <y> <z> | <why>
   ```
   - Points are Unreal centimetres.
   - FLANK needs a side.
   - One order per unit, and at most 256 orders.
   - Specs are all or nothing: a bad line refuses the whole spec, with the line number and the reason.
2. **Events come back as DTE 1:**
   ```
   DTE 1
   tick <n>
   event <SEEN|HIT|DOWN|PLAYER> <unit|player> <x> <y> <z> <value>
   ```
3. **The core is `DaedalusTacticsCore.h`**, plain C++ with no Unreal types: parse, write, flank and retreat
   geometry, and a local director. `core-test/tactics_core_test.cpp` runs 27 checks under ASan/UBSan:
   - 17 bad specs are each refused;
   - determinism holds, including when the input order is shuffled;
   - geometry is checked;
   - timing is bounded: 300 units decide in about 1 ms.
   Four mutants were each caught. One survivor is equivalent: dropping `isfinite` changes nothing, because NaN and
   infinity already fail the range check.
4. **The local director** runs when Java isn't attached. It is deterministic and explainable, and every order
   carries a why:
   - the nearest healthy foe ATTACKs, or DEFENDs the approach if the player holds high ground;
   - the next two FLANK LEFT and RIGHT at 9 m;
   - foes under 30% health RETREAT 15 m straight away;
   - the rest DEFEND the squad's centre;
   - if nobody is in range, everyone HOLDs.
5. **Unreal:**
   - `UDaedalusTactics` (world subsystem):
     - runs the local director once a second for each squad;
     - `ApplyOrders(spec)` is Java's entry. That squad then follows Java for 3 s before the local director may
       take it back, so Java must renew its orders about once a second.
     - `TakeEvents()` returns DTE 1.
     - `daedalus.Tactics 0` turns the local director off.
   - `ADaedalusTarget` carries `Squad`, `UnitId` and the current order, and treats the verbs as follows:
     - RETREAT, and FLANK, REINFORCE or DEFEND until the foe arrives, take over its feet and stop attacks;
     - FLANK and REINFORCE end on arrival, and the foe hunts from there;
     - HOLD and DEFEND only fight a player within 9 m.
   - Encounter packs are squads (`pack-N`).
   - The `tactics` Play scenario checks all of it in the editor.

## For team-codex

- Send DTO 1 specs about once a second for each squad you own. Unit ids are the `UnitId`s from DTE 1 events or the
  scenario.
- Read DTE 1 for what happened.
- Transport, for now: the Claude Unreal Bridge
  (`unreal.DaedalusTactics.get_tactics(world).apply_orders(spec)` and `.take_events()`). A socket comes later, and
  the spec does not change.
- Faction memory, learning the player's style, and reinforcements across islands are Java's. Unreal never needs to
  know why, only what and where. The why string is shown for debugging and explainability.

## Held

- The editor build and the `tactics` scenario run in unreal-team's next rotation slot.
- A transport other than the bridge waits for a team-codex request.

## Addendum, 2026-10-13 02:30: orders that use cover (Java)

`SquadDirector.decide(..., CoverField, CoverRules)` moves the FLANK, RETREAT and DEFEND points into the best cover
nearby:
- each kind of order searches its own radius: 3 m to flank, 6 m to retreat, 4 m to defend;
- cover is used only when it scores at least 0.4 against the player, and the why says so, for example
  "cut off escape, left, into cover (0.80)";
- ATTACK still goes for the player.

`CoverField` has the same shape as pythagoras's `BattlefieldEcology::bestCover` (ADR-061, branch
`pythagoras/battlefield-ecology`), so the reactive battlefield plugs straight in once it is merged. Unreal needs no
change, because the cover-aware points simply arrive in DTO 1.

With no field, the output is exactly the baseline, so C++ parity still holds. `CoverAwareDirectorTest` passes 6/6,
and the min-score mutant is caught. The full `daedalus-core` verify is green: 576 tests, plus checkstyle and the
other gates.

## Addendum, 2026-10-13 05:2x: Astra's integration requirements, answered

Astra (team-codex) wired the Java Adaptive Combat Director onto DTO 1 unchanged (PR32) and listed five gaps on the
Unreal side. All five are closed:
1. **PLAYER health:** the PLAYER event now carries the hero's health. It used to carry 0, which read as a dead
   player. -1 means unknown.
2. **Stale-order fencing:** `ApplyOrders` keeps the last outside tick for each squad. A newer tick applies, the same
   tick returns `repeat: tick N` and is ignored, and an older tick is `refused: stale tick N <= M`. Fencing runs
   after parsing, so a bad spec still reports its line.
3. **Trusted roster bootstrap:** `TakeRoster(squad)` returns **DTR 1** with the session, squad, tick, and each
   unit's id, kind, health, max health, position and whether it sees the player:
   ```
   DTR 1
   session <id> squad <id> tick <n>
   unit <id> <KIND> <health> <maxHealth> <x> <y> <z> <sees 0|1>
   ```
   Java reads it with `TacticalOrders.parseRoster`, and the parity file carries a C++-written roster. DTE 1 is
   unchanged.
4. **Session:** `UDaedalusTactics` makes a new 12-hex-digit session id each time the world starts, exposed by
   `SessionId()`, in every roster and in `Stats()`.
5. **Size cap:** a squad bigger than 256 orders its nearest 256 in both C++ and Java, so a local spec can never be
   refused for size. Split big packs into squads.

Tests: C++ 34/34 under ASan/UBSan, Java `TacticsParityTest` 8/8, and `daedalus-core` verify is green. The Unreal
side compiles in the first editor slot after the break; unreal-team owns that build, the binding and the playtest.

6. **Casualties reach Java** (found reviewing PR32): `AdaptiveDirector` counts casualty pressure as roster units at
   health 0, but the roster only listed living foes, so pressure could never rise. Fallen squad members now stay on
   the roster for the session at health 0 (`NoteDown`), capped at 256. The `tactics` scenario also checks the
   roster, the session, repeat ticks and stale refusal.

## Addendum: the native frame budget (2026-10-13, for Astra's end-to-end budget)
What the game thread pays for one full spec (256 orders, 15.8 KB), median of 200 runs, `-O2`, this sandbox's CPU:

| step | before | after |
|---|---|---|
| Parse DTO 1 | 263 us | 77 us |
| Write DTO 1 | 146 us | 32 us |
| Write DTR 1 roster (256 units) | 210 us | 54 us |
| Decide (C++ baseline, 256 units) | 51 us | 46 us |

Parse walks the text once with indices (no stringstreams), checks duplicate units with a hash set (it was O(n^2)),
and reads numbers with `std::from_chars`; writers append into one reserved string and format with `std::to_chars`.
The bytes are unchanged: tactics_parity.txt regenerates identically, and a new check compares `to_chars` with
printf `%.1f` on a million values including exact ties. Proposed budget: Java decides and writes off the game thread;
the game thread spends under 0.2 ms per full spec, and a real squad (3-12 units) is a few microseconds.

Java side of the same codec (steady state, 6,000 runs, 256-order spec): parse 920 -> 114 us, write 340 -> 59 us.
No regex (`words` is one pass; `replaceFirst` gone), UTF-8 length only for lines that could pass 512 bytes, a hash
set for duplicate units, and a `%.1f` fast path that falls back to BigDecimal only within 1e-6 of a tie or past 1e9.
TacticsNumTest compares the fast path with the exact one on a million values; TacticsParityTest 10/10 unchanged.
