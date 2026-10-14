# Observer Play

`play` with no mode now starts Simulate through `LevelEditorSubsystem.editor_play_simulate()`. This is the observation path: it avoids requesting possessed viewport Play. It does not force focus, synthesize keys, release another user's mouse or end an existing session.

Gameplay scenarios that require possession must deliberately send `mode: "play"`. Existing `simulate: true/false` remains an explicit alias; contradictory parameters and non-boolean legacy flags are rejected. Possessed Play never silently falls back to Simulate when the API is unavailable.

Responses preserve `playing` and add `requested_mode`, `started`, `already_running`, `timed_out`, and `mode_observed: null`. The requested mode is not proof of the actual mode, particularly when a session already existed. A 30-second observation deadline returns `timed_out` without retrying or restarting.

Fake API checks prove routing, refusal and preservation of an existing session. The editor owner must verify native SIE input/focus behavior and migrate possession-dependent night scenarios explicitly. No live editor was started by this change. This does not prevent a human from later possessing a simulated session.
