# Capture readiness observations

`capture_view` now waits on a finite, read-only capability set before submitting
one scene capture. The command yields to the existing game-thread queue; it does
not sleep, spawn a worker, flush streaming, submit shader jobs or regenerate grass.

This source candidate depends on the PNG export fix in
[PR #99](https://github.com/RicheyWorks/Daedalus2/pull/99), exact commit
`3a608a8c2ea496f98e5ee977ceb378f8dc58d7bc`. Readiness changes are reviewed
separately from that prerequisite; neither candidate is installed by these tests.

The default `readiness_timeout` is 10 seconds; callers may select a finite number
greater than zero and at most 30 seconds. A monotonic deadline covers both the
initial readiness wait and confirmation after capture. Each wait also has an
1800-tick ceiling. A stopped editor that never ticks again cannot deliver a new
game-thread reply; the existing transport timeout and owner lifecycle handling
still apply.

The deadline is checked before and after API samples and cannot preempt a
native predicate that blocks inside its call. The audited predicates are
lightweight queries; this is a bound on cooperative waits, not native quiescence.

The sequence is:

1. Configure the existing temporary capture actor, disabling automatic captures.
2. Yield two warm-up ticks before discovering or sampling readiness APIs.
3. Observe all supported predicates idle on two consecutive ticks. A busy
   observation resets the streak. An API error or zero supported checks stops
   the command with `captured: false`.
4. Submit one explicit `capture_scene()` after that condition is met.
5. Yield and confirm idle on each of two subsequent ticks. A busy observation
   invalidates the image immediately; it is not exported or recaptured.
6. Export only after confirmation passes, using the existing bounded file wait.
   The capture actor's existing `finally` cleanup runs on success, failure and
   explicit generator close.

Successful replies retain the PNG fields and add `captured: true`, `readiness`
and `readiness_before_capture`. A failed gate returns `captured: false`,
`readiness` and `readiness_phase` (`before_capture` or `after_capture`), without
PNG fields. This is a completed observation command, so the envelope can still
have `status: ok`; consumers must check `captured`. Export interruption has an
`incomplete_reason` and phase `export`.

Readiness schema version 1 reports `status` (`observed_idle`, `timeout`,
`frame_limit`, `unsupported`, `probe_error`, `cancelled` or
`capture_invalidated`), `condition_met`, warm-up and idle counts, elapsed time,
supported/unsupported check names, per-check states and `incomplete_reasons`.
Unavailable APIs are explicitly unsupported. An exposed API that throws or
returns something other than a bool is an error, never an idle observation.
The socket identity is checked around waits and probes; stop/restart invalidates
an in-progress capture when the owner thread resumes it. This change does not alter
the bridge's queue, `stop()`, remote execution or mutation ownership.

`condition_met` means only the supported predicates held idle on consecutive
editor ticks. Every report sets `all_rendering_complete: false` and
`coverage_complete: false`. The asset registry predicate observes only initial
search completion, not all package loads. World partition describes its own streaming
state, not texture residency or rendering. Stable ticks are not a render fence;
the helper cannot guarantee shaders, distance fields, textures, grass, virtual
textures or the GPU completed work. No image quality or live acceptance claim
comes from these offline tests.

## Installed source audit

Read-only inspection on BLACKBEARD found UE 5.8.3, changelist 58210709 in
`Engine/Build/Build.version`. No Epic source is included in this change.

| Check | Installed source evidence | Python behavior |
|---|---|---|
| Asset registry initial scan | `Engine/Source/Runtime/AssetRegistry/Public/AssetRegistry/AssetRegistryHelpers.h` (`GetAssetRegistry`); `IAssetRegistry.h` (`IsLoadingAssets`); `Private/AssetRegistry.cpp` (`FAssetRegistryImpl::IsLoadingAssets`) | Detect `AssetRegistryHelpers.get_asset_registry().is_loading_assets`; idle is false. This only observes initial search completion. |
| World partition | `Engine/Source/Runtime/Engine/Public/WorldPartition/WorldPartitionSubsystem.h` (`IsAllStreamingCompleted`) | Detect class, accessor and predicate; idle is true. |
| World subsystem accessor | `Engine/Source/Runtime/Engine/Public/Subsystems/SubsystemBlueprintLibrary.h` (`GetWorldSubsystem`); `Engine/Plugins/Experimental/PythonScriptPlugin/Source/PythonScriptPlugin/Private/PyGenUtil.cpp` (`IsScriptExposedFunction`) | `BlueprintInternalUseOnly` can exclude the accessor from stock Python. Detect `SubsystemBlueprintLibrary.get_world_subsystem` and report unsupported when absent; do not presume C++ reflection means Python availability. |
| Streaming levels | `Engine/Source/Runtime/Engine/Classes/Engine/LevelStreaming.h` (`IsStreamingStatePending`); `World.h` (`GetStreamingLevels`) | No audited reflected world enumeration; explicitly unsupported. |
| Other queues | C++ manager APIs are outside the reflected Python capability set | Global async loading, asset/shader compilation, distance fields, texture streaming and render completion are explicit coverage gaps. |

The warm-up and idle-streak idea was independently implemented after reviewing
[SPEAR's MIT async-loading service at commit 6d5957f8](https://github.com/spear-sim/spear/blob/6d5957f8a8f7a557f89cb56030619f381747be28/python/spear/services/async_loading_service.py).
No donor code or its force-update/global-streaming routines were copied.

## Offline checks and owner acceptance

Run `python -m unittest discover -s tests -p test_capture_readiness.py -v` from
the connector directory. The focused workflow runs these fake-API/queue tests
on Windows and Linux without an engine or network listener.

Live acceptance belongs to the shared editor owner after draft review. Confirm
actual capability support and report gaps, tick/deadline behavior, cleanup and
PNG output under ordinary editor load. Do not install or merge this candidate
until coordinated acceptance; no second editor, Play session or heavyweight
readiness routine is required for these source checks.

Owner handoff must include the companion `capture_readiness.py` in the plugin's
Python directory. The full plugin installer already copies that directory. A
custom single-file reload of the bridge must also supply the companion module
and its import path. Socket identity cancellation covers an in-progress
generator, not queued requests that have not started; queue shutdown ownership
remains with the separate bridge lifecycle candidate.
