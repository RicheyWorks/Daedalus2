# Controller consumer lifecycle continuation

This selectively ports the authenticated `11-ultra-controller-r2` consumer behavior onto continuation `d144ed9b96309b863b1c5c16260c379b1a2514cf`. Its producer is checkpoint `caf1b103f6cf5a3a66a3c718c139a7091b727b9d`, documented in `docs/production/CONTROLLER-CONSUMER-ULTRA-R2.md` and pinned by `data/assets/controller-consumer-ultra-r2-source-pins.json`. The exact producer index SHA256 is `0c4ed03f9c66b38df28eaae45205e82de8b11bac002a2168ada01e526c91220f`; local extracted-byte evidence is in the task's `gearwright-producer-caf1/EVIDENCE.json`.

Only the game consumer changes. The shared controller/settings modules, bundle, mappings, native interfaces, builder, assets and input conventions remain as before. The persistent pad instance continues to own device translation and neutral rearming.

## Retained authored behavior

- Physical keyboard codes aggregate into the existing keyboard source. Releasing ArrowUp leaves W held, and releasing one keyboard alias does not cancel pad or touch contributions.
- Settings, active button teaching, hidden documents and inactive windows pause simulation in the current mode. Pad polling, rendering and the existing audio policy continue.
- Settings/focus/visibility and teaching start/completion/cancellation boundaries clear consumer sources, buffered presses, timestamps, repeats and touch highlights, then call existing pad `releaseAll()` and `clearEdges()`.
- Blocked downs are ignored while releases still reach the consumer. Closing Settings, losing focus, hiding the document or disconnecting during teaching cancels that unfinished attempt; an ordinary disconnect preserves unrelated controls.
- Typed naming, canvas title/name choices and touch controls share the same gameplay gate. The consumer-only Control Help row explains the existing keyboard/mouse/touch fallbacks for Settings navigation.

## Adaptations to the current continuation

The current one-frame Settings transition guard also protects focus/visibility and binding boundaries. The existing `settingsFramePaused` flag still freezes battle hit-flash countdowns. All current frame modes, including fishing, ending and Game Over, remain in place. Initial inactivity comes from `document.hasFocus()` when supported. Lifecycle flags, frame clock and nullable pad/panel references initialize before synchronous reset paths.

The shared pad's `releaseAll()` emits UP synchronously, and `cancelBind()` clears its binding before emitting `bindcancel`. The reset helper permits those UP events and never cancels teaching itself; explicit suspension/close/disconnect boundaries perform cancellation separately. This avoids a reset/cancel recursion while retaining the shared lifecycle.

## Focused verification plan and limits

Review the production diff before execution. A bounded DOM-free fixture should invoke the actual registered keyboard/touch/window/document/pad/panel handlers and frame with the documented synchronous shared callbacks. Cover physical aliases, independent sources, all pause gates/modes, same-frame transitions, clearing every input layer, teaching completion/cancellation/interruption, ordinary disconnect, initial lack of focus and resumption without elapsed-time jumps. Compile the full inline script without execution. Adapt and run only directly affected existing input-transition, naming and Settings pause fixtures, with Node heap capped at 128 MiB and serial execution.

These are source/offline checks. No browser playthrough, physical controller, shared-module runtime acceptance, assets, build or native editor is certified by this continuation.

## Offline results

Serial checks with Node's heap capped at 128 MiB passed: `input_lifecycle_test.js` 24 groups, `settings_pause_test.js` 21 groups, and `name_entry_key_test.js` 14 groups. The complete inline script compiles without execution. The new fixture invokes actual consumer handlers and the current frame, using a small fake DOM/device peer that models the inspected synchronous shared callbacks and neutral-after-reset contract. Controlled former behaviors reproduce alias, hidden-timer, stale-timestamp and blocked-release failures.

No production defect or test setup failure occurred in these runs. Existing naming/Settings fixture changes supply the actual lifecycle context and new extraction anchor. Intro, skiff and storage fixtures only narrow their KEYMAP extraction to the unchanged metadata they use; their behavior was unchanged and they were not rerun. The unchanged input-transition fixture was also not rerun. No broad suite, shared module, browser or physical controller was executed.
