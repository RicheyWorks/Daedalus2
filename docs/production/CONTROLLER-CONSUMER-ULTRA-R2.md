# Controller consumer polish — Prismheart v11-ultra-controller-r2

**Source implemented; no build or play performed.** Owner: Ultra / buckwild-sol. Actual start2026-10-15 21:54:33 UTC; first saved source21:57:50 UTC. START delivered to Poot in hub32418. This is the next bounded increment after the Folly/workshop source handoff hub32412.

## Purpose and scope

Players could open Settings to adjust or teach controls while queued combat and field movement kept advancing behind the panel. Releasing held sources did not clear buffered confirm/menu presses. Ordinary keyboard aliases also shared one logical bit: releasing ArrowUp could cancel W even when W remained down.

This successor changes only the Prismheart consumer in `tools/rpg_demo/index.html` and the builder's version marker. The frozen shared pad/settings, controller rules/vectors, native mappings, bundle, global Hero and other realm clients are unchanged. It retains the Folly quest, Brannoc, workshop and battle visual polish from r1. It is local uncommitted source; published v10 is untouched.

## Implemented behavior

- Gameplay time and mode ticks stop while Settings is open, a binding session is active, the document is hidden or the window is inactive. Existing battle actions, dialogue, movement and fade state stay in place; the code does not replace the game mode with a pause mode.
- The consumer keeps polling the shared pad. Settings retains its own polling, navigation and binding UI. Audio and rendering remain active according to their existing settings; this is not a promise that every cosmetic animation freezes.
- Entering/leaving Settings, binding completion/cancellation and focus/visibility boundaries clear consumer held state, buffered presses, timestamps, repeats and touch highlights. Existing `releaseAll()` and `clearEdges()` calls require a neutral pad before fresh game input.
- Blocked gameplay downs are ignored; releases still reach the consumer. Typed name entry, title taps and touch controls honor the same gate. The frame clock stays current, preventing elapsed inactive time from advancing the simulation on return.
- Physical keyboard codes aggregate into the existing `SRC.kb`. W plus ArrowUp remains held until both are released. The existing separate pad, touch and harness source contributions remain.
- A disconnect during Teach Buttons cancels that unfinished teaching attempt. Closing Settings or losing focus also cancels an unfinished attempt. Normal disconnects preserve other connected controller and keyboard input. The shared module still owns device release events.
- The existing Settings extension API adds a Prismheart Control Help row explaining pause and keyboard/mouse/touch fallback for tabs, reset and copy after seven-step teaching. No shared settings schema was changed.

One persistent pad instance is retained. No action names, stick thresholds, confirm conventions, one-button timing, deadzones, layouts, storage keys or frozen v1 vectors were edited.

## Lineage and evidence

| Evidence | Location |
| --- | --- |
| Previous source successor | `artifacts/source-snapshots/prismheart-v11-ultra-folly-r1-source.tar`,294912bytes, SHA256 `eaf7bde2cd739e5bce5b86034addc992dd935a50bfdeb74979b39e9c8c9b0f1d` |
| Previous source extracted for comparison | `artifacts/source-snapshots/prismheart-v11-ultra-folly-r1/tools/rpg_demo/` |
| Full frozen controller reference | `artifacts/source-snapshots/controller-v1-9175723ad.tar`,1781760bytes, SHA256 `aef361abf3518b3d5b5141f057c3dee36dcf0b56a7c86cf8d517dcdce200ee6b` |
| Exact upstream commit | `9175723ad200b05558a2ea12470763c3b9432152` |
| Before/after source diff | `artifacts/source-snapshots/controller-consumer-ultra-r2.patch` |
| Source and frozen file pins | `data/assets/controller-consumer-ultra-r2-source-pins.json`, `controller-consumer-ultra-r2-frozen-pins.json` |
| Machine-readable stage and limits | `data/assets/controller-consumer-ultra-r2.json` |

Twenty-one released controller/settings/native/reference files were preserved and hashed in the full snapshot. This is an inventory, not a claim that all native code and bundle-generation paths have been reviewed. The reviewed boundary covers the web lifecycle, v1 contract and Prismheart integration. The ten preserved test scripts and bot.py remain byte-identical to r1.

## Source review and frozen limitations

Independent reviewers inspected lifecycle/reentrancy, alias aggregation, pause state, input buffering and binding/disconnect recovery. Source inspection found no remaining concrete regression after the implementation. That finding does not establish runtime acceptance.

The frozen module's `releaseAll()` leaves edge buffers and analog values available; consumers must clear edges and avoid gameplay reads while inactive. Its `destroy()` stops the timer but leaves event listeners/async bundle completion. Disconnect does not clear a captured teaching index. Default teaching records seven actions and does not retain unmapped X/Y/LB/RB inputs. This increment handles the relevant consumer boundaries and supplies fallbacks; those shared-module limitations remain in the frozen source. No broader v2 remapping or lifecycle replacement was introduced.

## Remaining production work

No project source, syntax checker, test, build, browser, native editor, Blender job or render was executed. Historical v10 acceptance counts are not r2 results. Gameplay pause/resume, physical devices, rapid taps, alias combinations, binding interruption and Settings navigation remain unobserved in a running successor.

A later authorized build must use the retained released art roots and the r1 RPG dependency snapshot. The full controller reference does not contain RPG data and is not the build's source root. Prepared command shape, **not executed**:

```powershell
python tools/rpg_demo/build_demo.py "<released FX_DIR>" "artifacts/prismheart-v11-ultra-controller-r2" --sprites "<released SPRITES_DIR>" --source-root "artifacts/source-snapshots/prismheart-v10-dependencies"
```

On that later turn, inspect pause during queued battle actions/fades/mid-step movement; close/blur/visibility with held or buffered inputs; simultaneous ArrowUp/W and keyboard-plus-pad holds; interrupted/restarted teaching; short taps and one-button controls. Retain the original serial validation discipline. The r1 deferred four-route literal assertion in `quest_test.py:46` remains unchanged; it needs a future validation owner's adaptation for the optional fifth route.

## Lessons for other realm crews

Keep the controller translating inputs and the consumer deciding when gameplay may act. Clearing held inputs alone does not discard queued presses. Modal Settings needs a simulation boundary as well as a visual overlay. Track physical aliases before aggregating logical actions. Cancel unfinished teaching at explicit lifecycle boundaries, preserve unrelated input during ordinary disconnects, and document keyboard/touch fallbacks when a frozen mapping has fewer actions than the UI.
