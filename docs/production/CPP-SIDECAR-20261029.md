# C++ sidecar module (engine-free) - 2026-10-29

`engines/sidecar_cpp` is a standalone C++17 library (no engine, no third-party deps) that reads our asset sidecars
(`*.sockets.json` incl. hinges and skeletal sockets, `*material_variants.json`) and implements the Blender -> Unreal
axis conversion used by `tools/blender/sockets_sidecar.py`. It is the C++ side we integrate when it is our turn in the
Unreal editor: `unreal/DaedalusSidecarUE.h` is a disabled stub (`#if 0`) marking that seam. See the module README for the
convention, the `SocketRegistry` socket hook and build steps.

Verified 2026-10-29 on BLACKBEARD (MSVC 14.44, VS 2022 Community, CMake/NMake): 36/36 checks; all 480 staged sidecars in
`bot-team\staging` (455 socket assets, 1737 sockets, 13 hinges, 14 variant assets) parse and validate with 0 problems.
CI (`.github/workflows/sidecar-cpp.yml`) builds on ubuntu (g++) and windows (MSVC) against `tests/fixtures`.
