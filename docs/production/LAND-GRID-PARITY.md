# Java / Unreal land addressing

`com.daedalus.world.land.LandGrid` supplies the ADR-065 grid to Java services without an engine dependency.
It matches `DaedalusLandGrid.h`: 100×100 cells, clipped dense spiral starting at (50,50),
256 m pitch, 10×10-cell districts and estates of 1–4 cells per side which cannot split a district.
This addresses plots; it does not allocate ownership, reserve a hub, mint deeds or persist movement.

`cell`, `number`, `ring`, `district`, `estate`, `metres` and `numberAtMetres` use horizontal
east/north coordinates. Server terrain XYZ uses Y-up; convert north to terrain Z explicitly.
Unreal uses centimetres and its own realm origin; convert at the client boundary. Cell zero's
centre is realm-local (0,0), not the editor world's origin. Pitch is independent of numbering.

Invalid integer addresses return -1 / Cell(-1,-1); invalid estate requests return -1, including
overflow-sized coordinates. Java metres conversion rejects invalid land numbers and invalid
pitch rather than returning the hub position as native `Metres` currently does. Non-finite or
off-grid position lookups return -1. Valid half-cell ties use floor(value/pitch+0.5), matching native.

## Evidence, 2026-10-13

Compiled `engines/unreal/core-test/land_grid_parity.cpp` against the existing native header with
MSVC C++17 /W4 /O2 (no compile warnings). Its canonical output contains 10,000 rows of
number/cell/inverse/ring/district/metres and 40,000 estate candidates. Normalizing CRLF to LF
produces SHA256 `182c90b14151708051576a1bb57feedb3442c7fbc4e12e8317bd244ee2aaee21`.
Native header SHA256: `1483e59d9fe35cf706391d1c826d46480ec15b37349b94140726ad758db31c3e`.
LandGridTest generates the Java rows independently and checks that digest. Changes to the
native spec require regenerating and reviewing the output, not blindly replacing the digest.
The Engines CI job compiles and checks the native dump with both gcc and clang and checks the
editor Python implementation against the same digest. Java tests run in the Maven CI job;
changing only one language fails parity. Locally run `python check_land_grid_parity.py <native-output>`
from core-test after compiling the native dumper.

Four focused tests pass (15.167 s Maven invocation). Full core `mvn -B -pl daedalus-core -am verify`
passes in 46.197 s: 723 tests, zero failures/errors/skips, coverage ratchet met and SpotBugs zero.
Tests also round-trip every cell at pitches 256 and 512, check uniqueness, hostile integer inputs,
half-cell edges, invalid pitch and non-finite positions. This proves addressing parity, not
cross-server streaming, realm transfer, persisted estate claims or blockchain identity.
