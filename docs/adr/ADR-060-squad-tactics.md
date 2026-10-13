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
