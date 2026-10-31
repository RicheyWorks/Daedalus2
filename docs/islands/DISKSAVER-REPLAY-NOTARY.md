# DiskSaver: Replay Notary (G608)

Quest `q_replay_notary`. NPC: **Notary Sabine**, who keeps the tournament ledger in the harbour customs house. Prismheart lane: tournaments and leaderboards (PLAN.md, disk-saver), first deliverable.

**What it does.** A leaderboard entry is never a bare score. It is one line of text:

```
notary1|<game>|<seed>|<plan>|<claim>
```

The notary lays the puzzle from the seed, then replays the plan through that game's own C++ core. The cores are used unchanged:
- G590 Gantry Sweep;
- G597 Buddy Berths;
- G598 Tidelinks Golf.

The score on the board is always the score the core gives. A plan the core refuses keeps the core's own refusal code. Anyone can replay any entry and get the same answer, so a tournament needs no trusted server.

**Fields.**

| Field | Values |
|---|---|
| version | `notary1` |
| game | `gantry-calm`, `gantry-rush`, `gantry-spread`, `gantry-storm` (the Gantry Sweep tide profiles), `berths`, `golf` |
| seed | 1 to 256 printable ASCII bytes (0x20 to 0x7E). It cannot hold `\|`, so use another separator, for example `tidewatch-cup:2026-10-31` |
| plan | Gantry: ship indices in service order, `3,0,1,2,4`. Berths: one offset per arrival, or `-` to turn the ship away, `0,8,-,4`. Golf: holes split by `/`, clubs by `,`, with `-` for an empty hole, `D,9,P/W,P`. An empty plan means no moves. |
| claim | The claimed score in decimal (gantry waiting ticks, berths ships turned away, golf strokes), or `-` for no claim |

Numbers in a plan are 1 to 4 digits; claims are 1 to 9 digits. Neither may have a sign or a leading zero, so every score has one written form.

**Results** (`FormatResult`):
- `ok <game> <score> verdict=<v>`: the replay matches the claim, or there is no claim.
  - Gantry: `waits=<n> travel=<n>`, verdict sweet, fair or jammed.
  - Berths: `turned=<n>`, verdict snug, fair or crowded.
  - Golf: `strokes=<n> topar=<E|+n|-n>`, verdict masterful, steady or rough.
- `forged <game> claim=<c> <score> verdict=<v>`: the plan is real, but it does not score what was claimed. The replayed score is the one to show.
- `refused <game> <code>`: the core's own code.
  - Gantry: `short`, `long`, `range`, `repeat`.
  - Berths: `length`, `align`, `busy`.
  - Golf: `holes`, `club`, `cap`, `short`, `extra`, followed by ` hole=<k>`. An unknown one-letter club reaches the golf core, which refuses it as `club`.
- `bad <reason>`: the entry cannot be read, so nothing is replayed. Checked in this order:
  1. `long`: over 8192 bytes;
  2. `fields`: not 5 `|`-separated fields;
  3. `version`;
  4. `game`;
  5. `seed`;
  6. `claim`;
  7. `plan`: a number or club token that is not well formed.

**How it plugs into Daedalus.** The hook (`data/islands/disk-saver/replay-notary-v1.json`) puts the notary in front of any leaderboard: the Prismheart Tidewatch Cup, ghost and postcard replay codes, and the Habit Rivals ladder.
- A board stores entries, not scores, and shows a score only after `ok`.
- A save that carries a score is rechecked on load by notarising its entry. This is the replay-on-load rule from the Prismheart save review.
- The notary has no network, clock or file access. It is a pure function from an entry line to a result line.

**Code.**
- `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusDiskSaverReplayNotaryCore.h`: header-only C++17. No Unreal includes, no exceptions or RTTI. It includes the three game cores and `DaedalusPyRandomCore.h` without changing them.
- `tools/streaming/replay_notary_parity.py --write/--check` writes `engines/unreal/core-test/disksaver_replay_notary_parity.txt`.
  - The expected results come from the Python rules of the three games (`gantry_sweep_parity.py`, `buddy_berths_parity.py`, `tidelinks_golf_parity.py`), so the C++ notary is checked against an independent reference.
  - Entries are hex in the file, so control and non-ASCII bytes are tested too.
  - It is also registered in `disksaver_cpp_parity.py`.
  - 1430 entries over 14 seeds (one of them the longest allowed) and all six games:
    - every habit plan and the best plan;
    - shuffled and random plans;
    - every refusal, including golf refusals on later holes;
    - true and false claims;
    - 30 malformed entries.
- `engines/unreal/core-test/disksaver_replay_notary_core_test.cpp` replays every entry and checks:
  - the result line;
  - that each result is well formed and repeatable;
  - for every scored entry, that a true claim is `ok`, a false one is `forged` with the same replayed score, and no claim reads the same as a true claim;
  - 1500 fuzzed entries (mutated golden entries and random bytes): no crash, and every result well formed and repeatable.

  The existing engines.yml loop over `disksaver_*_core_test.cpp` runs it under gcc ASan/UBSan and clang.
