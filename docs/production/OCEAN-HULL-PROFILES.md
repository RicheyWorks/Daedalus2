# Ocean vessel body profiles

`ADaedalusOceanVessel::ConfigureHull(HalfExtentCm)` lets the authoritative host fit an unoccupied vessel's box collider before boarding. Every dimension must be finite and between 10 and 5,000 centimetres. The effective scaled collider is bounded too. Blocking overlap rejects the change before the existing collider or replicated profile is changed. Occupied vessels and clients cannot resize it.

The accepted half extents replicate with an OnRep handler that updates the remote box. Existing vessels retain their original 180/80/70 cm default unless the host configures a profile. This avoids silently changing unrelated scenes and existing boats.

For the original harbor art, initial body profiles are 235/95/65 cm for the skiff and 280/115/90 cm for the submarine. These are conservative body boxes around waterline pivots; sails, periscopes, ropes and other decorative projections do not define a navigation hull. Assign the matching mesh separately. An authority refusal must be handled before making the vessel available for boarding.

The native `Daedalus.Ocean.HullProfile` scenario covers finite/range checks, occupied resize rejection, preserving the previous collider after refusal, overlap with a wall, and swept movement of both fitted profiles against that wall. The network fixture's `--hull-profile` mode verifies receipt of the real dimensions and box collider in a separate Unreal client and rejects client-side reconfiguration.

This is kinematic box collision. Rotation still needs obstacle-aware handling, and the complete visible-vessel navigation, grounding, buoyancy and real-world dock placement acceptance remains pending. No population or art count changes result from this code.

## Recorded verification

The fresh 136-file production snapshot at `b31bd6c9` built successfully in 210.96 seconds (49 actions). All five Ocean native scenarios passed with zero test warnings/errors. `ocean-hull-profile-build-proof.json` records every source hash and the archived production DLL hash; `ocean-hull-profile-runtime-proof.json` is the engine report.

After adding only the two network fixture files, its five-action rebuild passed in 18.65 seconds. The separate server/client runs passed in 24.407 seconds for the boat and 23.390 seconds for the submarine, including startup. Both clients received the expected body profile and applied it to their actual box components; local resize was refused. Server-observed movement and command expiry also passed. `ocean-hull-profile-network-proof.json` records the production snapshot, fixture hashes and process/log evidence. This is localhost NullRHI evidence, not WAN or rendered piloting acceptance.

Excel adds three scoped verification records and one mechanic row, retaining the 343 art references and all previous asset and verification records. Five acceptance gates remain pending. This snapshot precedes the main-branch integration with Claude's realm-session work and must not be presented as that combined build.
