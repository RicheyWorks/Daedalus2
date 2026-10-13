# ADR-063: Island Streaming Budget planner (DSB 1)

- Status: Accepted (disk-saver, 2026-10-13). Registry row: "Island Streaming Budget planner".
- Layer: Java core (`daedalus-core/.../world/streaming/StreamingBudget.java`) + plain-C++ core
  (`engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusStreamingBudgetCore.h`).

## Problem
The world has ~10k islands. Loading them by distance alone ignores memory: the editor has already run out of RAM
on BLACKBEARD during imports, and a game client would too. We need one deterministic rule, shared by Java (authority
for which islands exist and what they cost) and Unreal (which streams sublevels every frame, with no network round
trip), for which islands are resident.

## Decision
`DSB 1` plain-text manifest, one line per island:

    DSB 1
    island <id> x <cm> y <cm> ram <kib> disk <kib>

Integers only (Unreal cm, KiB); ids `[A-Za-z0-9_]{1,64}`, unique; |x|,|y| <= 1e9 cm so squared distances fit in
int64; ram/disk 1..1e8 KiB; at most 20,000 islands. One bad line refuses the whole file ("line N: why").
Canonical write sorts by id.

`Pick(manifest, viewer, loadCm, unloadCm, ramBudgetKiB, wasResident)`:
1. Wanted = within the load radius, or already resident and within the unload radius (hysteresis; an unload radius
   below the load radius counts as the load radius).
2. Wanted islands are taken nearest first (ties by manifest index) while their RAM fits; an island that does not fit
   is skipped, never partly loaded, and smaller farther islands may still fit.
3. Result: resident flags per manifest index, total RAM, total disk, count.

## Parity
`engines/unreal/core-test/streaming_budget_core_test.cpp --write` writes `streaming_budget_parity.txt`
(40 random manifests in odd raw forms, their canonical writes, 240 chained picks where each pick's resident set
feeds the next, and every refusal message). `StreamingBudgetParityTest` replays it in Java byte for byte.

Build the C++ test:
`g++ -std=c++17 -O1 -Wall -Wextra -Werror -fsanitize=address,undefined -I../DaedalusLink/Source/DaedalusLink/Public streaming_budget_core_test.cpp`

## In-game demo (needs unreal-team)
A UE component reads the DSB 1 file for the realm, calls `Pick` as the player moves, and loads/unloads island
sublevels from the flags; the proof is a capture (tools/capture) showing the resident count and RAM staying under
budget while flying across islands. DiskSaver Island is the natural first test cell.
