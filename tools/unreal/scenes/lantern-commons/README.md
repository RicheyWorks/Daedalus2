# Lantern Commons: objective and interaction UI

The current saved scene includes a real UMG Explorer Log, a contextual E prompt,
and a persistent friendly completion state. These replace the development-only
PrintString success message. The shared Daedalus HUD and native chart pickup code
remain unchanged.

The Explorer Log tells the player to discover the Lantern chart by following the
amber stones through Shade Grove and Stone Overlook to the gold arch. Within
three metres, a large bottom-centred `[E] Collect the Lantern chart` prompt appears.
Existing `DaedalusOrrery.Charts` membership supplies completion; no progress is
reset or written. After Lantern is present, the panel says `Lantern chart found!`
and invites the player to explore at their own pace. It does not vanish with the
collected actor or expire after a debug-message duration.

`WBP_LanternObjective` owns the layout and a 0.2-second native Blueprint refresh
timer. `BP_LanternUIHost` creates it for the existing player at level BeginPlay and
removes only this widget class at EndPlay. The widget clears its own timer at
Destruct. Canvas/panels do not intercept input; existing Hero controls remain.
The destination now has a contrast-backed sign with plain-language E guidance,
and its duplicate label is hidden. The peaceful rules, 104 x 105 m ground, 273
floor instances and original assets are retained.

This was a BUILD-ONLY pass: necessary Blueprint compilation and owned asset/map
saves, with clean packages and normal compute release. No Play, route, pickup,
reload, collision-grid or standalone test suite was run. Do not describe the new
UI as runtime-tested, visually accepted, shipping-qualified or bug-free. Earlier
proof files and screenshots are historical R1/R2 evidence; they do not show R3 UI.
The broad black horizon and blockout-level visual finish remain unfinished.

Use the existing saved map at the manifest world path. On a compatible Daedalus
checkout, copy only this pack's Content files to matching project Content paths
under ordinary ownership/preservation; do not overwrite other work or mount this
under plugin Content. Existing native Daedalus classes, imported Blender meshes
and engine UMG must be present. This is not a standalone project.

Editable native graph source is in `ui/objective-refresh.dsl`,
`ui/objective-events.dsl` and `ui/host.dsl`; current build details are in
`ui/build.json`. `feedback-graph.dsl` now has no PrintString node. No C++ wrapper,
new gameplay framework, project/input setting change or installation was added.

The established 17-image visual benchmark board and Adopt Me minimum still apply.
Final art style remains undecided. This is independent Daedalus work, not prebuilt
game-jam content.
