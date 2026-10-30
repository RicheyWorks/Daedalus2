# daedalus_sidecar: engine-free C++17 reader for Daedalus asset sidecars

Status: standalone library + test, **no engine dependency**. Nothing in Unreal includes it yet; `unreal/DaedalusSidecarUE.h`
is a stub (`#if 0`) for when the editor is ours.

## What it reads
| File | Written by | C++ type |
|---|---|---|
| `<Asset>.sockets.json` (static props) | `tools/blender/sockets_sidecar.py` (via `build_kit.py`) | `SocketsFile` (sockets + hinges) |
| `<Asset>.sockets.json` with `schema: bb-skeletal-sockets/1` (rigged Mobs) | creature tools | `SocketsFile`, `Socket::bone` |
| `*material_variants.json` (`bb-material-variants/1`), single asset or a bundle of asset blocks | blender-team variant tools | `std::vector<MaterialVariants>` |

Hinges (`hinges[]`) give each mover's pivot and motion: `rotate` (open pose: `open_blender_euler_deg` -> `open_ue_rotator`,
`Hinge::openAngleDeg()` = signed UE yaw for door hinges), `spin` (axis, rpm) or `slide` (axis, `travel_m`).

## Axis convention (same as `sockets_sidecar.py`)
- Blender: +Z up, front = **-Y**, metres. Unreal: +X forward, +Y right, +Z up, cm.
- `UE = 100 * (x_b, -y_b, z_b) = 100 * (gx, gz, gy)`: Blender front lands on **UE +Y**.
- Meshes are not rotated at export; placement applies **yaw -90** (`kPlacementYawDeg`), turning UE +Y onto +X.
- `SOCKET_` empties are **pre-rotated** at export (`Rb = N R A^T N`, `N = diag(1,-1,1)`, `A = [0,180,-90]`) so the native
  Interchange socket equals the sidecar frame. The **sidecar rotation is authoritative**; `native_matches` is a cross-check.
- Plain sockets are mesh-aligned `[0,0,0]`; attach sockets have +X along the shaft, +Z up.
- A Blender-space hinge rotation in UE mesh space is `N Rb N` (Blender +90 about Z = UE yaw -90).

## Daedalus socket hook
```cpp
#include "daedalus/sidecar/sidecar.hpp"
using namespace daedalus::sidecar;
SocketRegistry reg;
reg.loadDirectory("path/to/staging");                  // all sockets + variant sidecars, errors in reg.errors()
auto w = reg.find("Bld_Lab_TwinDoors", "SOCKET_Hinge_DoorA", {{x, y, z}, kPlacementYawDeg});   // world cm + rotator
const Hinge* h = reg.sockets("Bld_Lab_TwinDoors")->hingeFor("Bld_Lab_TwinDoors_DoorA");          // h->openUe
const MaterialInstance* mi = reg.variants("Prop_Prism_ShardFacet_Fire")->forState("Charged");   // mi->params
```
`validate(file)` returns a list of problems (empty = consistent): units/space, SOCKET_ prefix, pre-rotation round trip,
native vs sidecar, hinge pivot == socket location, hinge open rotator == converted Blender euler, sRGB hex == linear colour.

## Build and test
```
cmake -S engines/sidecar_cpp -B build/sidecar && cmake --build build/sidecar --config Release
build/sidecar/Release/daedalus_sidecar_test engines/sidecar_cpp/tests/fixtures [bot-team/staging ...]
```
`tests/fixtures` holds copies of real staged sidecars (TwinDoors hinges, attach sockets on Bat/FishingRod, a material
variant manifest). Pass more directories (e.g. `bot-team\staging` on BLACKBEARD) to check every staged sidecar.

## Later (UE wrapper)
Add `include/` to a UE module's include paths, compile the three `src/*.cpp` into it (or link the static lib), flip the
`#if 0` in `unreal/DaedalusSidecarUE.h`. Keep logic engine-free here; the wrapper only converts types.
