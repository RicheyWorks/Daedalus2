# ADR-065 geometry review and portable grid

2026-10-13, team-codex. Response to unreal-team message 28620. This implements proposed **default placement mathematics only**. No land ownership, token minting, sale, reward, tug endpoint, save migration or Unreal level move is performed.

## Geometry findings and decisions

1. **Estate capacity:** a 4×4 block at 128 m pitch spans 512 m including its perimeter allowance, or 476 m of contiguous usable extent if the 36 m neighbour gap is retained. A 780 m island needs at least `ceil((780+36)/128) = 7` cells per side. A 7×7 estate fits inside one 10×10 district if its anchor is chosen correctly; a 4×4 maximum cannot accommodate the reported islands. Use actual level bounds before any move.
2. **Supply versus space:** 10,000 cells fit 10,000 single-cell lands. Larger estates consume more cells, so 10,000 independent deeds cannot all fit unless some deeds aggregate constituent land IDs, additional space exists, or not all lands are placed simultaneously. Resolved by Richey via Claude message 28642: estates bundle the existing constituent land numbers; no new land supply. Transactional bundling and ownership checks still need implementation. Do not silently reduce the user's requested land count.
3. **Hub footprint:** reserved spawn lanes, gates and public space also consume capacity. Cell zero is a proposed anchor, not authorization to put an island on an existing spawn lane.
4. **Transfers:** tugging must update persisted placement rather than recompute it from deed number. Swaps need authenticated consent from both current owners, atomic occupancy changes and a replay policy. Existing Parcel/ParcelAcl/deed code should be reused after those semantics are settled. No new unauthenticated endpoint is added here.

## Exact geometry convention

`defaultCell(number)` accepts 0..9999. Start at logical `(x,z)=(0,0)`, move +X, +Z, −X, −Z in legs of lengths 1,1,2,2,3,3,... and retain only coordinates inside **[-49,50] × [-49,50]**. This explicitly clips the even-sized square; taking the first 10,000 steps of an unbounded spiral would produce a different shape. Initial coordinates: `(0,0),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)`.

The hub is one of the four central cells of an even grid. A realm-local offset is `(x*12800,z*12800)` centimetres. In Unreal these logical X/Z axes map to horizontal X/Y; altitude is independent. Add the configured realm anchor only at the native placement boundary. No current world coordinates are baked into the helper.

District ID is `floor((z+49)/10)*10 + floor((x+49)/10)`, 0..99. Every district has exactly 100 cells. A square footprint grows toward +X/+Z from its anchor, must stay in the realm and must not cross a district boundary. `fitsSquare()` checks geometry only, **not occupancy or permission**. In particular `(0,0)` lies at a district edge and is unsuitable as a multi-cell estate anchor under this convention.

The table is generated once and provides O(1) lookups; it does not instantiate land terrain or load districts. Invalid Java numbers throw `IllegalArgumentException`; the C++ lookup returns false without changing the output. The C++ `Cell` offsets are intended for validated cells returned by the lookup.

## Source and verification

- Java: `daedalus-core/src/main/java/com/daedalus/world/RealmLandGrid.java`.
- Portable C++: `engines/unreal/DaedalusLink/Source/DaedalusLink/Public/DaedalusLandGridCore.h`.
- Native test emits 10,000 CSV rows: `engines/unreal/core-test/land_grid_test.cpp`.
- Java comparison: `engines/unreal/core-test/LandGridParity.java`.

MSVC C++17 `/W4 /WX` and Java 21 passed: all 10,000 positions are unique and in bounds; each district contains 100 cells; Java/native offsets, district IDs and 100,000 footprint cases agree. A separate coordinate-to-ring-rank oracle independently checks every spiral position, and out-of-range IDs are rejected. This is geometry proof, not a streamed 10,000-land Unreal performance benchmark.

Reproduce by compiling the native test and redirecting its stdout to `native.csv`, compiling the two Java files into one class output directory, then running `java -cp CLASSES LandGridParity native.csv`. Local evidence is under `C:/Users/730ri/Documents/Codex/2026-10-13/land-grid/`.

## Claude handoff

Review the even-grid origin, orientation and district convention before using it in a preview. Estate aggregation is confirmed; confirm public-space reservations and transactional bundling with Richey and blockchain-ruffff. Keep the 14-level move on hold until actual bounds and collision-free anchors are agreed. The existing undo-capable layout tool can then consume validated persisted placements, without changing land identities.
