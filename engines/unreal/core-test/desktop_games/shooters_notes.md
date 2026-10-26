# Desktop shooter ports

These three cores port the user's selected latest Desktop revisions. The original files remain on `C:\Users\730ri\OneDrive\Desktop`; no source script is launched or imported as a module. The source oracle selects reviewed AST rule classes into a small stub namespace, with controlled random values and no Pygame import/display, home-directory file access or script startup.

| Core | Canonical source | SHA256 |
|---|---|---|
| `AsteroidsGame` | `asteroids_pygame_ce.py` (2026-05-02 08:17:04 UTC) | `8a46338b4d93d9447df7feab40dff21b99bfa0ce7614698681b8a5c91f0fc20b` |
| `SegaShooterGame` | `sega_space_shooter.py` (2026-05-01 02:59:48 UTC) | `5108b3065fa91332570445adaccbb8c5bb77e437bc0bd8e37213737e931ad0db` |
| `StarShooterGame` | `star_shootergpt1_fixed.py` (2026-04-29 02:30:08 UTC) | `05ac3a0fabddab94adb3d3a7b2c6eb9f7e1543390a48805db247a3ffd40d8281` |

## Shared contract and deliberate changes

`Game::Reset(seed)` starts an active session; the Daedalus host supplies menus, start and restart. One `Step(Input)` is one 60 Hz source frame. The host accumulates elapsed time and bounds catch-up, forwards digital controls and analog left-stick axes, and calls `Render(Frame)` without mutating simulation state. All render commands and simulation entity vectors have explicit caps. Reset clears live entities, scores, timers and transient requests. Ended Asteroids/Sega games freeze until an explicit fresh retry event or host restart.

Asteroids/Sega accept terminal `SourceControllerButton(0/1)` (pad A/Start) and
`SourceKeyDown(6/7)` (Enter/Space), through the existing raw input seam. They retain
the original reset seed. Active events and held `Step` inputs do not restart; Start
is consumed before generic pause. The existing native host may forward fresh A
into new-run gameplay, matching its other games. Star's pause/save flow is separate.

The portable seeded random stream intentionally differs from Python `random`; matching a numeric seed does **not** reproduce a Python run. Tests inject reviewed source values for numeric rule parity and separately test native deterministic replay. Native rendering does not consume game randomness. Stable stars, deterministic thruster visuals and bounded cosmetic effects are adaptations.

Sources use screen-space procedural polygons, circles, rectangles and text. The native drawing commands preserve ship silhouettes, colors, pickups and enemy types, with polygon tessellation and line-based outline approximations. No image, audio, character model or branded asset was copied. `Asteroids` and Sega/Gradius/R-Type references are source names/references, **not evidence of permission to distribute third-party names or assets**. Publication identity/provenance remains an owner decision. These games do not currently need a humanoid Blender character; ship/boss models, if requested, should follow the reviewed procedural silhouettes rather than unrelated mascots.

## Asteroids

Preserved rules include 5-degree digital rotation, 6-degree scaled stick rotation, 0.15 stick deadzone, thrust threshold below -0.4, 0.15 acceleration and 0.985 drag, screen wrapping, cooldown 8, 45-frame bullets, three sizes of splitting asteroids, points `100 * size`, three lives, progressive waves, off-center spawn rejection, UFO entry/aimed shots and 500 UFO points. The latest source's stable stars/rock shape are retained.

Polish changes: one life loss per frame, 60-frame visible respawn protection, bounded rejection sampling/entity population and bounded wave population (32 initial rocks after high levels). Rocks split after the hit pass and consumed bullets cannot damage a second target. Keyboard directions and `Input::PadLeft/PadRight/PadUp/PadDown` remain separate, preserving source additive keyboard-and-D-pad rotation. `Ship::Update(Input, hatX, hatY)` also exposes independent hat values for source actor fixtures. The source's any-button title start is a host menu concern; held face/bumper actions map to fire.

### Optional Driftstone flight practice

Option2 / Flight practice offers three sequential docking beacons at (400,180),
(650,180) and (100,420). The current one has a gold28px ring; completed beacons
turn green and future ones stay muted. Stop the ship center strictly inside the
current ring while braking to advance. The same Ship.Update turns/thrusts/coasts,
applies braking's existing .02 component snap and wraps with its original discarded
overshoot. Docking requires Braking and both components exactly zero after Update;
it never creates new stop physics. Position and heading remain between goals.
Missed approaches are recoverable through ordinary flight; there is no timer.

Practice Reset clears stage and all entities, creates the same seeded stars and
skips initial rocks. Its Step returns after Ship.Update and goal settlement,
before firing, UFO timers/collisions and empty-rock wave advancement. Thus no
combat, score, life loss or waves occur. The third dock sets Won and freezes;
existing fresh raw retry and host Restart retain mode/seed. Mode0 Endless and
Mode1 Three waves retain their complete original branches and RNG order. The old
voyage test's upper invalid option changes from2 to3 because2 is now valid; no
voyage bulk rerun is implied. The existing checked MakeMode row gains one choice;
the public actor header change is comment-only, and no host input API is added.
Native controls/focus, viewport scale and learning/difficulty remain pending.

`desktop_asteroids_flight_practice` / `asteroids_flight_practice_test.cpp` passed
36/36 strict single-TU MSVC C++17 checks. One bounded public-input route docked all
three beacons in423 steps; every step matched detached Ship.Update, with no pose
or stage assignments on that route. Local boundary fixtures retain actual reached
stage copies. Checks cover order, strict radius/braking/both-zero velocity,
original discarded-overshoot wrap,360-step no-combat/no-wave/RNG idle, short modes
0/1 companions, invalid -1/3, pure reads, freeze/retries and Driver cleanup. No old
brake/voyage/terminal suite or old-header proof was repeated. The voyage test's
updated invalid-upper-bound literal was source-reviewed only in this slice.

### Optional Driftstone three-wave voyage

Driftstone Patrol (Asteroids) offers **Endless / Three waves** through the existing
checked mode controls. Option 0 retains the original endless progression. Option
1 finishes after all rocks in wave three have been destroyed, before spawning
wave four. The original six/six/seven large rocks and all their splits remain:
133 rock destructions across the voyage. There is no duration/easier-mode promise.

Flight, brake, firing, UFOs, scoring, life loss and between-wave protection remain
unchanged. The existing wave-clear rule requires rocks, not surviving UFOs. Lethal
damage still blocks simultaneous completion. Success freezes the run and shows
its earned score; it adds no bonus or saved progression. Wave N/3 and the existing
objective line identify the goal. Restart/fresh result retry retain mode and seed;
changing mode starts over and the active native mode remains a no-op.

One friend-only AsteroidsTestAccess seam supports bounded real collision/split
regressions without exposing mutable runtime getters or requiring a fragile pilot
bot. `desktop_asteroids_voyage` / `asteroids_voyage_test.cpp` covers this slice.
The previous broad source, braking and replay suites remain separate evidence.
Native mode focus, terminal input, layout, duration and human play feel are pending.

Strict serial single-TU MSVC C++17 passed 559/559 focused assertions. One bounded
controlled route performed all 133 actual collision/split hits (19 large, 38 medium,
76 small) and earned the original 20,900 rock points. Its Endless companion kept
identical simulation/RNG through precompletion and then spawned wave four's eight
large rocks. Checks also cover no early finish/bonus, surviving-UFO completion,
simultaneous lethal/final-rock loss priority, terminal freeze, two representative
fresh retries, invalid modes, Reset and Driver input/time/pause cleanup. These are
controlled collision fixtures, not a human pilot or difficulty/duration acceptance.
No old source, braking, replay suite or old-header proof was repeated.

## Sega Space Shooter

Preserved player clamping and axis override, power levels 1/2/3 with corresponding normal/double/spread bullets, cooldown 6, basic sine and chaser enemy movement, health 2/4, 100 kill points, 25% powerup chance, power cap 3, speed cap 8, life cap 5 and 60-frame collision invulnerability. The unused enemy shot timers remain timers; no enemy projectile feature was invented.

The canonical source has no `draw_text` implementation and never tests a projectile against its separate boss, making the intended win unreachable. The native rendering contract fixes the text failure; boss bullet and contact collisions are now connected. At 1500 points the 20-HP chaser boss enters and stays in the right-side engagement region instead of drifting permanently off-screen. Defeat awards 500 points and ends in victory. Held fire and keyboard restart through the shared host are usability enhancements. Single-use projectiles and one life loss per frame fix overlapping-hit defects.

### Riftwing ordinary-enemy health cues

Ordinary enemies now show compact health pips above their original silhouettes:
two for basic ships and four for chasers, matching spawn health. Filled gold pips
empty after surviving damage. Both rows leave four pixels above the silhouette,
using the existing health state with no helper label or new timer. The boss keeps
its separate 20HP bar. The cue follows both Full run and Boss rehearsal enemies;
combat, scoring, random draws and pickup behavior are unchanged.

`desktop_sega_enemy_health` / `sega_enemy_health_test.cpp` focuses on real hit
settlement and presentation, using the existing Sega-only friend seam. Native
cue size, contrast, overlap and human play acceptance remain pending.

Strict serial single-TU MSVC C++17 passed 19/19 focused checks: both moving
silhouettes, real surviving/lethal shots, original 100-point/drop RNG behavior,
offscreen cleanup, rehearsal/boss-bar companion and repeated-render/future-state
purity. No old shooter, rehearsal or replay bulk was rerun. The added rendering
is bounded to five commands per ordinary enemy (at most 320 across the existing
64-enemy cap); no gameplay field or timer was added.

### Optional Riftwing boss rehearsal

Riftwing Vanguard (the Sega core) offers **Full run / Boss rehearsal** through the
cabinet's existing checked mode controls. Full run remains option 0 and reaches
the boss at 1500 real points. Option 1 starts that same 20-HP boss immediately,
with score zero, three lives and the ordinary weapon/speed. Regular enemies,
powerup drops, boss pursuit, collisions and shooting keep their existing rules;
enemies continue arriving throughout the encounter.

Both paths use the same boss initializer. Rehearsal victory earns the existing
500 boss points after real damage. The existing
enemies HUD row marks REHEARSAL, and its result names completion/end. Restart and
fresh terminal retry retain the selected mode and seed. Choosing the active native
mode preserves progress; changing mode deliberately starts over. There is no new
save, leaderboard, actor implementation or framework. Native focus, layout and
human difficulty/feel remain unverified.

`desktop_sega_boss_rehearsal` / `sega_boss_rehearsal_test.cpp` is the focused mode,
boss settlement, default-entry and lifecycle regression; prior broad shooter and
replay/source suites are separate evidence.

Strict serial single-TU MSVC C++17 passed 52/52 focused checks. One public-input
held-fire rehearsal at seed 730 won after 180 steps with score 600 and three lives.
Controlled real projectile Steps verified all twenty boss hits and the original
500 boss award; the short public route also earned one ordinary enemy kill. Mode
validation, unchanged full-run 1499/1500 entry, mutual loss, retry and Driver input/
time/pause cleanup passed. No broad shooter suite or old replay proof was rerun;
native integration and human play remain unverified.

## Star Shooter

Preserved latest features include Easy/Medium/Hard configurations; Python ties-to-even health rounding; speed/shoot/dive scaling; normal twin and triple shots; permanent-until-reset powerups; shield hit behavior; bee/butterfly/cruiser enemy data; wave-dependent weighted groups; cruiser escorts and doubled cruiser points when escorts are killed; straight and zigzag dives with distinct points; enemies' three shot patterns; 20-second wave progression and spawn-rate floor 28; every-fifth-wave bosses; spread/ring/aimed boss patterns; 66% enrage and 33% berserk thresholds and once-only summons; boss charges/returns; 1000 boss points, cleanup of boss shots, reset of player powerups and three replacement drops; pause and source-shaped lightweight save state.

`SetDifficulty(Difficulty)` configures the next reset; polymorphic `Game::SetOption(option, seed)` chooses Easy/Medium/Hard as 0/1/2 and starts a new run, while `GetOption()` reports it. Invalid options leave state unchanged. Default is Medium, a native host default; the Python source asks on its difficulty screen. Keyboard/stick movement priority remains source-style. The host maps right trigger/space to `Fire`, the pause action to `ActionPressed`, paused navigation to directions/stick, confirmation to `FirePressed` or `JumpPressed`, and cancel/resume to `DashPressed`.

`CaptureRun()` returns exactly the lightweight gameplay fields represented by the Python JSON save (score, wave, spawn rate, lives, triple, shield, speed boost, difficulty and boss-killed marker). `ResumeRun(snapshot, seed)` validates then restores those fields and resets transient actors/player position/timers, as source Continue does. `SaveAndQuit()` captures a pending snapshot and raises `HasSaveRequest()`/`WantsQuit()`; the pause menu also supports Resume, Save & Quit and Quit to Menu. The host must consume `GetSaveRequest()`, serialize/write it using the engine save system, expose Continue and clear the request. **On-disk persistence and top-ten leaderboard storage are not implemented in this portable core.** Save is not a full replay/world snapshot in either implementation.

Polymorphic host bindings avoid Unreal RTTI: `OwnPause`, `IsCorePaused`, `SaveState`, `RestoreState`, `SavePending`, `ClearSavePending` and `WantsExit`. The versioned native payload is `DGS1 score wave spawn_rate lives triple shield speed_boost difficulty boss_killed_this_wave`, with booleans 0/1 and difficulty 0/1/2. `SaveState()` serializes the pending save request when present, otherwise current lightweight state. `RestoreState()` rejects malformed, oversized, unknown-version, extra-field and out-of-range payloads before mutating the game. This native format does not read or overwrite the original Python home-directory JSON files.

Polish changes: dead enemies cannot score more than once, consumed bullets hit only one target, and invulnerability is rechecked between hit categories so overlapping hits cannot consume several lives/shield plus life in one source frame. Entities/effects/popups are bounded. Boss thresholds can summon once per threshold, and boss rewards occur once. Source rules for escaped cruiser escorts remain conservative: an escort disappearing offscreen does not count as a kill for the bonus.

## Evidence and owner acceptance

The native cabinet accepts a fresh pad A or Start press at Star's game-over result
to invoke its existing host RestartGame, matching R/Restart. This route is handled
before Start's ordinary pause mapping and before A enters held gameplay input.
The host retains difficulty/seed and clears score-submission/input bookkeeping;
its existing pending-save refusal still applies. Active play and source pause-menu
controls are unchanged. Terminal help names the physical controls. This Slate/copy
slice has source review only; controller repeat/focus, pending-save refusal and
successive native leaderboard acceptance remain unverified. No portable core
controller reset was added, since it would bypass the host score lifecycle.

Star's existing New run Easy/Medium/Hard buttons also opt into native focus
navigation. F2/right-stick click enters the catalog; close its list with Back/Escape,
then navigate the cabinet controls to choose a difficulty with A/Enter. Those
buttons retain their existing run-replacement/save fence and option callbacks;
activation returns board focus. Other MakeAction callers keep their prior focus
behavior. Source review confirms the wiring; exact controller traversal and
successive difficulty/restart acceptance still require native play.

`shooters_parity.txt` contains 635 executed-source cases across 21 rule categories, with original SHA pins and numeric schemas. The oracle supplies deterministic random fragments; it does not claim Pygame runtime behavior or full-screen script parity. The rectangle stub explicitly models integer construction; real Unreal input, rendering, audio, save integration and live gameplay remain separate verification stages.

Native test results, Daedalus catalog/adapter bindings, UHT/UBT compile evidence and Claude acceptance are reported by the integration owner after final-head validation. Portable native tests alone do not establish an in-game port.

The family test passed **91,839 / 91,839 checks** using MSVC C++17 `/W4 /WX /permissive-`. All 635 fixture cases were consumed; six cosmetic `STAR_HIT` particle-count fields were deliberately excluded because particles are a bounded presentation adaptation. Four 20,000-frame replays covered deterministic frames/status, terminal freeze, restart, render purity, sanitized nonfinite input and entity bounds. The late-wave run exercised 9,215 boss frames. Observed entity peaks were 27/392 (Asteroids), 47/353 (Sega), 70/1537 (Star) and 122/1537 (late-wave Star).

A render-driven native Sega pilot reached the complete boss victory at seed 1, frame 1,027, score 2,200, and confirmed frozen terminal state and a once-only reward. Host contract tests cover nine-field save roundtrip, 25 malformed/version/range/overflow/boolean/trailing/oversize payload rejections without visible or hidden RNG state changes, difficulty reset/invalid-option rejection, pause/save/quit requests, and simultaneous keyboard/stick/D-pad Asteroids input. This is portable simulation evidence; it does not substitute for Unreal compilation or human playtesting.

`shooter_terminal_test.cpp` / CMake target `desktop_shooter_terminal` adds a bounded
retry check, independent of the broad shooter fixture suite: real idle losses at
seeds 0/730/UINT32_MAX, the known seed-1 victory with a 1,200-step cap, held-result
freeze, fresh-event reset and driver input cleanup. Strict MSVC C++17 passed
487/487 checks. The same test using the prior shooter header failed 30 retry checks
as expected. Star's class source remained identical. No engine/native runtime
integration is inferred from this portable check.

## Sega terminal pickup settlement

Lethal contact now skips pickup consumption, preventing a frozen Game Over with a
restored life (or post-defeat power/speed benefit). Surviving contacts still collect
same-step pickups. Boss progression, the explicit BOSS DOWN / SHIP LOST outcome,
500-point boss reward and actor cleanup retain their existing order. A narrow
Sega-only friend seam arranges ordinary single-step collision fixtures.

`desktop_sega_terminal_pickup` / `sega_terminal_pickup_test.cpp` passed72/72 strict
single-TU MSVC C++17 checks. It covers all pickup kinds, enemy/boss contact, cleanup,
surviving companions, mutual boss/ship defeat, held freeze and seeded retries.
A controlled always-enabled pickup-loop variant (friend unchanged) passed52/72,
failing20 post-defeat pickup/life assertions as expected. Asteroids/shared prefix
and Star class source were compared unchanged. No full shooter suite, engine build,
editor or native play was run; live controller/balance acceptance remains unverified.

## Star terminal pickup settlement

Lethal projectile, enemy or boss contact now skips same-step Triple/Shield/Speed
collection. The frozen result retains its loadout at defeat and leaves the nearby
item unconsumed. Star has no Life pickup; this is a post-defeat upgrade repair.
Surviving and shield-absorbed hits still collect normally. Existing upgrades,
scoring, boss/wave order, effect expiry and entity cleanup retain their behavior.

The focused `desktop_star_terminal_pickup` target / `star_terminal_pickup_test.cpp`
passed102/102 strict single-TU MSVC C++17 checks. Fifteen contact cases use existing
Bee shot/dive and boss charge primitives, plus terminal freeze and seeded reset at
all three difficulties. An always-enabled pickup-loop variant with the same test
friend passed81/102, failing21 post-defeat assertions as expected. This did not run
the broad shooter suite, engine builds or native acceptance; Slate controller replay
and real filesystem/leaderboard behavior remain separate pending native checks.

Host pause or focus suspension after Game Over now keeps the result visible.
Star's pause flag is retained, but its live pause menu is drawn only before defeat;
the terminal Step cannot execute those menu choices. A live paused companion still
renders the menu and resumes on fresh confirmation. The focused target now passes
110/110 checks. Restoring only the old render condition passed107/110, failing the
three difficulty-specific final-frame assertions. No other pause or save lifecycle
code changed; native focus-loss presentation still needs live acceptance.

## Driftstone Patrol brake control

Asteroids adds K / left-trigger braking through the existing Action/ActionPressed
input. It suppresses thrust while preserving turning, firing, cooldown and wrap.
After original0.985 coasting drag, braking applies0.8 extra damping and snaps each
component below0.02 to rest before movement. Releasing returns to original flight
behavior. Unbraked physics and the other two shooter classes are unchanged.

Two blue ship fins and an active BRAKING cue acknowledge the action without adding
a menu. Reset/respawn clear it; terminal status and rendering suppress the active
cue. The native mapper explicitly assigns K/LT only for Asteroids, keeping pad B
and every existing fire binding intact. Left-trigger state uses the same finite/
clamped input and lifecycle reset path as the existing right trigger. No actor API,
portable input fields, save format, original Python script or fixture changes.

The focused target desktop_asteroids_brake runs asteroids_brake_test.cpp with the
existing shooters_parity.txt: only its81 AST_SHIP source cases plus braking/control
fixtures, real early-game feedback/fire and a bounded6000-step respawn/result loop.
It does not execute Sega/Star fixtures or the broad shooter suite. Test execution
and old-header proof results are recorded in the private campaign handoff; native
trigger/focus/held-button/viewport/human-flight acceptance remains separate.

Strict single-TU MSVC /W4 /WX /permissive- passed607/607 assertions, including all
81 unchanged AST_SHIP cases and a real terminal at566 idle steps. The exact
pre-feature header at d30fb8dc5 passed593/607, with14 expected brake failures.
Only an isolated header overlay was used; repository sources were not reverted.
The normalized Sega/Star suffix is identical to that predecessor. One initial
compile was deferred by the RAM guard before the compiler started; after other
source work, a fresh guard passed and the check ran once. No engine build or
broader shooter suite was executed.
