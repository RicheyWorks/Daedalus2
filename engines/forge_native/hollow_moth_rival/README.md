# Hollow Moth rival (Prismheart R2-9, hephaestus)

Header-only, engine-free C++17 core: `DaedalusHollowMothRivalCore.h`. Rules authority: `hollow_moth_rival_ref.py`
(`python hollow_moth_rival_ref.py --check hollow_moth_rival_golden.txt`). The golden is generated, never hand-edited.
Reads Prism Satchel (`DaedalusPrismSatchelCore.h` / `prism_satchel.PAYOUTS`) read-only; seeded with
`DaedalusPyRandomCore.h` (bit-exact with Python `random`).

* **Unlock:** `Unlocked(satchel.Heartglass())`, 3 or more Heartglass seals.
* **Challenge:** `Begin(&state, seed, heartMask)` draws, with `PyRandom("hollow_moth|<seed>|<round>")`, a cabinet
  without Heartglass (any of the 11 once all are sealed). Mark = Heartglass par + 0..max(1, par/10).
  For a perfect-par cabinet (glowmoss): a perfect hard win at or above Umbra par + margin.
* **Tries:** 3 per round. `Attempt(...)` returns BEATEN for a hard win at or above the mark, FELL_SHORT, or FLEW_OFF
  (out of tries; the next `Begin` draws round + 1). Rounds cap at 9999.
* **Reward:** `MothFreed(state)` feeds the `mothFreed` flag of Spirit Boons (`spirit_boons/`), which turns on the
  Hollow Moth boon (shardfall cracked -1, PROPOSED until the owner ACKs).

Statuses: OK, LOCKED, ALREADY_BEATEN, BAD_MASK, NO_CHALLENGE, WRONG_GAME, BAD_DIFFICULTY, BAD_SCORE, BEATEN,
FELL_SHORT, FLEW_OFF, ROUND_LIMIT, NULL_POINTER. Refusals leave state unchanged.
