# Desktop shooter ports

These three cores port the user's selected latest Desktop revisions. The original files remain on `C:\Users\730ri\OneDrive\Desktop`; no source script is launched or imported as a module. The source oracle selects reviewed AST rule classes into a small stub namespace, with controlled random values and no Pygame import/display, home-directory file access or script startup.

| Core | Canonical source | SHA256 |
|---|---|---|
| `AsteroidsGame` | `asteroids_pygame_ce.py` (2026-05-02 08:17:04 UTC) | `8a46338b4d93d9447df7feab40dff21b99bfa0ce7614698681b8a5c91f0fc20b` |
| `SegaShooterGame` | `sega_space_shooter.py` (2026-05-01 02:59:48 UTC) | `5108b3065fa91332570445adaccbb8c5bb77e437bc0bd8e37213737e931ad0db` |
| `StarShooterGame` | `star_shootergpt1_fixed.py` (2026-04-29 02:30:08 UTC) | `05ac3a0fabddab94adb3d3a7b2c6eb9f7e1543390a48805db247a3ffd40d8281` |

## Shared contract and deliberate changes

`Game::Reset(seed)` starts an active session; the Daedalus host supplies menus, start and restart. One `Step(Input)` is one 60 Hz source frame. The host accumulates elapsed time and bounds catch-up, forwards digital controls and analog left-stick axes, and calls `Render(Frame)` without mutating simulation state. All render commands and simulation entity vectors have explicit caps. Reset clears live entities, scores, timers and transient requests. Ended games freeze until host restart.

The portable seeded random stream intentionally differs from Python `random`; matching a numeric seed does **not** reproduce a Python run. Tests inject reviewed source values for numeric rule parity and separately test native deterministic replay. Native rendering does not consume game randomness. Stable stars, deterministic thruster visuals and bounded cosmetic effects are adaptations.

Sources use screen-space procedural polygons, circles, rectangles and text. The native drawing commands preserve ship silhouettes, colors, pickups and enemy types, with polygon tessellation and line-based outline approximations. No image, audio, character model or branded asset was copied. `Asteroids` and Sega/Gradius/R-Type references are source names/references, **not evidence of permission to distribute third-party names or assets**. Publication identity/provenance remains an owner decision. These games do not currently need a humanoid Blender character; ship/boss models, if requested, should follow the reviewed procedural silhouettes rather than unrelated mascots.

## Asteroids

Preserved rules include 5-degree digital rotation, 6-degree scaled stick rotation, 0.15 stick deadzone, thrust threshold below -0.4, 0.15 acceleration and 0.985 drag, screen wrapping, cooldown 8, 45-frame bullets, three sizes of splitting asteroids, points `100 * size`, three lives, progressive waves, off-center spawn rejection, UFO entry/aimed shots and 500 UFO points. The latest source's stable stars/rock shape are retained.

Polish changes: one life loss per frame, 60-frame visible respawn protection, bounded rejection sampling/entity population and bounded wave population (32 initial rocks after high levels). Rocks split after the hit pass and consumed bullets cannot damage a second target. Keyboard directions and `Input::PadLeft/PadRight/PadUp/PadDown` remain separate, preserving source additive keyboard-and-D-pad rotation. `Ship::Update(Input, hatX, hatY)` also exposes independent hat values for source actor fixtures. The source's any-button title start is a host menu concern; held face/bumper actions map to fire.

## Sega Space Shooter

Preserved player clamping and axis override, power levels 1/2/3 with corresponding normal/double/spread bullets, cooldown 6, basic sine and chaser enemy movement, health 2/4, 100 kill points, 25% powerup chance, power cap 3, speed cap 8, life cap 5 and 60-frame collision invulnerability. The unused enemy shot timers remain timers; no enemy projectile feature was invented.

The canonical source has no `draw_text` implementation and never tests a projectile against its separate boss, making the intended win unreachable. The native rendering contract fixes the text failure; boss bullet and contact collisions are now connected. At 1500 points the 20-HP chaser boss enters and stays in the right-side engagement region instead of drifting permanently off-screen. Defeat awards 500 points and ends in victory. Held fire and keyboard restart through the shared host are usability enhancements. Single-use projectiles and one life loss per frame fix overlapping-hit defects.

## Star Shooter

Preserved latest features include Easy/Medium/Hard configurations; Python ties-to-even health rounding; speed/shoot/dive scaling; normal twin and triple shots; permanent-until-reset powerups; shield hit behavior; bee/butterfly/cruiser enemy data; wave-dependent weighted groups; cruiser escorts and doubled cruiser points when escorts are killed; straight and zigzag dives with distinct points; enemies' three shot patterns; 20-second wave progression and spawn-rate floor 28; every-fifth-wave bosses; spread/ring/aimed boss patterns; 66% enrage and 33% berserk thresholds and once-only summons; boss charges/returns; 1000 boss points, cleanup of boss shots, reset of player powerups and three replacement drops; pause and source-shaped lightweight save state.

`SetDifficulty(Difficulty)` configures the next reset; polymorphic `Game::SetOption(option, seed)` chooses Easy/Medium/Hard as 0/1/2 and starts a new run, while `GetOption()` reports it. Invalid options leave state unchanged. Default is Medium, a native host default; the Python source asks on its difficulty screen. Keyboard/stick movement priority remains source-style. The host maps right trigger/space to `Fire`, the pause action to `ActionPressed`, paused navigation to directions/stick, confirmation to `FirePressed` or `JumpPressed`, and cancel/resume to `DashPressed`.

`CaptureRun()` returns exactly the lightweight gameplay fields represented by the Python JSON save (score, wave, spawn rate, lives, triple, shield, speed boost, difficulty and boss-killed marker). `ResumeRun(snapshot, seed)` validates then restores those fields and resets transient actors/player position/timers, as source Continue does. `SaveAndQuit()` captures a pending snapshot and raises `HasSaveRequest()`/`WantsQuit()`; the pause menu also supports Resume, Save & Quit and Quit to Menu. The host must consume `GetSaveRequest()`, serialize/write it using the engine save system, expose Continue and clear the request. **On-disk persistence and top-ten leaderboard storage are not implemented in this portable core.** Save is not a full replay/world snapshot in either implementation.

Polymorphic host bindings avoid Unreal RTTI: `OwnPause`, `IsCorePaused`, `SaveState`, `RestoreState`, `SavePending`, `ClearSavePending` and `WantsExit`. The versioned native payload is `DGS1 score wave spawn_rate lives triple shield speed_boost difficulty boss_killed_this_wave`, with booleans 0/1 and difficulty 0/1/2. `SaveState()` serializes the pending save request when present, otherwise current lightweight state. `RestoreState()` rejects malformed, oversized, unknown-version, extra-field and out-of-range payloads before mutating the game. This native format does not read or overwrite the original Python home-directory JSON files.

Polish changes: dead enemies cannot score more than once, consumed bullets hit only one target, and invulnerability is rechecked between hit categories so overlapping hits cannot consume several lives/shield plus life in one source frame. Entities/effects/popups are bounded. Boss thresholds can summon once per threshold, and boss rewards occur once. Source rules for escaped cruiser escorts remain conservative: an escort disappearing offscreen does not count as a kill for the bonus.

## Evidence and owner acceptance

`shooters_parity.txt` contains 635 executed-source cases across 21 rule categories, with original SHA pins and numeric schemas. The oracle supplies deterministic random fragments; it does not claim Pygame runtime behavior or full-screen script parity. The rectangle stub explicitly models integer construction; real Unreal input, rendering, audio, save integration and live gameplay remain separate verification stages.

Native test results, Daedalus catalog/adapter bindings, UHT/UBT compile evidence and Claude acceptance are reported by the integration owner after final-head validation. Portable native tests alone do not establish an in-game port.

The family test passed **91,839 / 91,839 checks** using MSVC C++17 `/W4 /WX /permissive-`. All 635 fixture cases were consumed; six cosmetic `STAR_HIT` particle-count fields were deliberately excluded because particles are a bounded presentation adaptation. Four 20,000-frame replays covered deterministic frames/status, terminal freeze, restart, render purity, sanitized nonfinite input and entity bounds. The late-wave run exercised 9,215 boss frames. Observed entity peaks were 27/392 (Asteroids), 47/353 (Sega), 70/1537 (Star) and 122/1537 (late-wave Star).

A render-driven native Sega pilot reached the complete boss victory at seed 1, frame 1,027, score 2,200, and confirmed frozen terminal state and a once-only reward. Host contract tests cover nine-field save roundtrip, 25 malformed/version/range/overflow/boolean/trailing/oversize payload rejections without visible or hidden RNG state changes, difficulty reset/invalid-option rejection, pause/save/quit requests, and simultaneous keyboard/stick/D-pad Asteroids input. This is portable simulation evidence; it does not substitute for Unreal compilation or human playtesting.
