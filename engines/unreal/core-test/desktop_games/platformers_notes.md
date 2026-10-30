# Desktop platformer ports: IRONWAKE and Emberstep Ascent

These are ports of the actual user's Desktop scripts into the existing `daedalus::desktop::Game` contract. The Python originals are preserved. Both native cores start a playable session immediately; the Daedalus launcher owns opening, closing and restarting the minigame.

## Canonical source selection

| Game | Original path | SHA256 | Baseline |
| --- | --- | --- | --- |
| IRONWAKE | `C:\Users\730ri\OneDrive\Desktop\contra.py` | `2e845d67754fc81feeea881b7c6d3068a60042c3371e9f8fdeae5a8616d09107` | Last complete controller revision; constants/classes after line 582. File modified May 1, 2026 at 02:14:59 UTC. |
| Emberstep Ascent | `C:\Users\730ri\OneDrive\Desktop\shadow_ninja_platform_fixed.py` | `83dd921b95043a2723b61513d84471adbfaede29dd18744367835fbc3aa03e36` | May 2, 2026 fixed platform revision, including safe platform start and jump edge detection. Older numbered revisions are not the baseline. |

The user explicitly selected the last revision. `contra.py` contains two concatenated standalone programs: the first `main()` exits via `sys.exit()`, preventing the later controller revision from running as a normal script. The port uses only the last complete definitions, rather than preserving that accidental entry-point barrier.

## Runtime bindings for the Unreal owner

Include `DesktopGames/DaedalusDesktopPlatformersCore.h`. Registry constructors are `IronwakeGame` and `EmberstepGame`; each implements `Reset(uint32 seed)`, `Step(const Input&)`, `Render(Frame&)` and `GetStatus()`.

Call one `Step` per 1/60-second simulation step. The Unreal adapter should cap accumulated wall-clock time and catch-up steps, issue pressed edges only once, and clear controls when focus is lost or the minigame closes. These cores contain no wall-clock loop, window creation, Python runtime or editor dependency.

| Binding | IRONWAKE | Emberstep Ascent |
| --- | --- | --- |
| Left/right | Arrows/A/D or left stick; keyboard speed 5 px/step | Arrows/A/D or left stick; speed 5 px/step |
| AxisX | Deadzone 0.15; stick overrides keyboard and scales to 6.25 px/step | Deadzone 0.20; stick overrides keyboard |
| Jump / JumpPressed | Space/W or controller A; held jump repeats on landing, as in source | Space or A; release and press again for the double jump |
| Down / AxisY | Down/S, stick >0.5 or D-pad down crouches | Wall descent via down/S or stick >0.3 |
| Up / AxisY | Digital up feeds the optional cheat sequence | Wall climb via up/W or stick <−0.3 |
| Fire / FirePressed | Z/left Ctrl, RT >0.5 or controller X; held firing | Z/X or controller B/X; sword on the input edge |
| Action / ActionPressed | B symbol for the cheat sequence | C or controller Y/RB; throwing star on edge |
| Dash / DashPressed | No gameplay action | V or LB; ground spin on edge |
| Reset | Clear score/lives/transients, reproduce seed | Clear health/score/boss/transients, reproduce seed |

Ironwake Advance's completed/lost run accepts a fresh Enter, controller A/Start
or R/Restart to replay the stored seed. The result screen and status advertise
these existing bindings; Space starts from the title but is not a terminal retry
key. The native adapter forwards ordered fresh events and ignores held repeats.

For Emberstep Ascent, keyboard directions, stick axes and D-pad directions remain separate. `EmberstepGame::Step` passes `PadRight-PadLeft` and `PadUp-PadDown` into the player's explicit hat parameters. The source's horizontal hat wins over keyboard and stick input, including opposing directions; both D-pad flags cancel to neutral. Vertical wall-climb conditions preserve the source's independent up/down checks, so opposing keyboard/stick/hat climb requests can cancel. The wrapper should retain these independent fields rather than merging D-pad into keyboard directions or clearing stick axes. Controller connection/hotplug and physical mappings belong to the adapter.

IRONWAKE `SubmitCheatKey(key, titleScreen=false)` accepts `0=up, 1=down, 2=left, 3=right, 4=B, 5=A`. The source sequence U,U,D,D,L,R,L,R,B,A gives +5 lives, capped at 99, and 600 steps of spread in play; passing `titleScreen=true` gives the source's 30-lives title bonus. Normal gameplay feeds digital direction/action/jump edges automatically. A title-screen-specific binding is optional UI work; native `Reset` starts play directly.

`GetStatus().Lives` is lives for IRONWAKE and health for Emberstep Ascent. `Over` stops subsequent simulation; `Won` distinguishes success. The port does not grant Daedalus currencies or persistence rewards: the session owner must consume terminal state once if those are added.

## Preserved mechanics and source quirks

IRONWAKE preserves gravity 0.6, jump −13, keyboard movement 5, source crouching geometry, right-key precedence when both directions are down, camera smoothing 0.85/0.15, integer Pygame rectangle semantics, bullet speed 12/lifetime 60, fire cooldown 8 (rapid 4), three-shot ±15° spread, 900-step spread pickups, 90-step damage invincibility, grunt score 100, boss score 500, stage-driven spawning, source platforms and the source's distance victory at world x >2800. Source bosses have only two hit points. Reaching the distance target can win without defeating a boss; that original rule is deliberately preserved. Crouching still does not reduce horizontal speed. The declared `SCROLL_SPEED` was unused in Python and remains unused.

Emberstep Ascent preserves start at (175,380), feet-based platform collision and its forgiving landing band, gravity 0.6 capped at 12, ground jump −11, double jump −9, wall slide capped at 1, wall climb 3, wall jump −10/7 with a 10-pixel push, edge-triggered jumping, sword cooldown/lifetime 18/12, star cooldown/lifetime/speed 12/50/9, spin duration/cooldown 25/45, source per-frame spin damage, five health, pit death at y >540, gold score 50, sword/star/spin kill scores 150/100/200, boss spawn at score 1200, boss health 25 and victory bonus 800. The `LEVEL: 1` indicator remains unchanged because the source never increments the level. Procedural torches are static visual decoration in the port.

## Repairs and deliberate adaptations

### Ironwake target range

Optional mode1 / Target range teaches shot heights with three ordered rectangles:
(340,485,24,20), (620,340,24,40), (970,503,24,15). Source standing-ground shots are
at496, jump-apex shots at361.6 and settled crouch shots at512. The high panel gives
15 post-update jump decisions, so the original eight-step held-fire cadence has
room to connect. Actual truncated PixelContains bullet hits decide success; no
posture gate rejects valid platform, spread or other source shot alternatives.

Reset keeps the mode and clears targets, entities, weapons, particles and progress;
range skips the original initial enemies/pickup. The shared input/player/camera/
bullet prefix remains unchanged. A range branch then consumes one impacting bullet,
advances at most one target and ticks the same particles, returning before enemy
fire, random spawns, pickups, damage or source distance victory. It has no timer,
target score or extra reward. Third hit sets Won/Over and freezes. Position and
heading carry between goals; existing camera/backtracking and bullet expiry apply.
Mode0 retains the full original run and RNG/cosmetic order. Title, keyboard bonus,
selected title lives, controller start and fresh retries retain their existing paths.

Gold/green/muted panels and one offscreen edge arrow identify goals. Existing HUD
slots show target count/progress and the current shot hint; no tutorial panel/row.
The native checked mode row uses MakeMode and a game-specific IronwakeVisibility;
public actor header is comment-only, with no actor/input API or builder changes.
Mode changes start over; active native mode is a no-op. Native controls/focus,
viewport readability and human shot learning remain unverified.

`desktop_ironwake_target_range` / `ironwake_target_range_test.cpp` passed 51/51 strict
single-TU MSVC C++17 checks. A public-input standing/jump/crouch shot route finished
in198 steps, with no pose/stage assignment. Local fixtures retain real reached
stage copies and check quantized order, strict edges, expiry and consumed bullets.
Also covered12 detached player/shoot/bullet/camera parity steps,600-step safe range
movement past the source finish without spawning/completing, default/mode/RNG,
title bonus and selected lives, pure reads, terminal retries and Driver cleanup.
No old ledge/source/platformer/replay bulk or old-header proof was repeated; no
Unreal compilation, physical input or human play acceptance is implied.

### Ironwake ledge timing

The existing held-jump landing hop remains unchanged. A short ground-grace window
also accepts a jump during the six decisions after stepping off a platform, using
the same -13 impulse and subsequent 0.6 gravity. Crouching still prevents jumping.
Airborne and crouched decisions expire the window; a successful jump consumes it,
so holding Jump cannot grant another airborne jump. No landing queue or new input
edge rule is introduced.

The appended counter resets with the player. Accepted damage clears it after the
existing invincibility/terminal guard; a rejected protected hit does not erase it.
The existing fallback relocation also clears it independently of that guard.
Title/start/replay still use the same Reset path and preserve their original lives
and cheat-prefix behavior. The current readiness line recognizes grace without
adding labels. This timing allowance is a native extension, not Python parity.

`desktop_ironwake_ledge` / `ironwake_ledge_grace_test.cpp` passed 743/743 strict
single-TU MSVC checks, including only the 51 existing CSTEP cases and their
original thirteen fields. Focused cases cover actual walkoff/expiry, crouch,
no second airborne jump, unchanged held landing hops/camera precedence, enemy
and projectile damage, rejected protected Hurt, readiness, Reset/title/start/
controller replay and terminal freeze. The dormant fall relocation cleanup was
source-reviewed; no test-only seam was added to force that path.
An initial compile stopped on the test fixture's global name shadowing a template
loop variable; renaming that fixture fixed it without changing warnings or game
code. No runtime assertions ran before that correction. No full platformer suite,
fixture regeneration, repeated replay proof, engine build or native playtest.

### Emberstep Ascent jump timing

The native cabinet accepts a slightly late ledge press and a slightly early
landing tap without changing the ground/double/wall impulses or controls. Ground
grace lasts six decisions after the first unsupported step. A fresh unavailable
jump remains queued for six fixed steps including its press step. At 60 Hz each
window is about 100 ms. Ground/grace jumps use -11; an ordinary available double
jump stays immediate at -9 and the wall jump keeps its source -10/7/push behavior.

The queue is ground-only. If it reaches a normal landing, the source collision
snaps the feet to the platform, then the usual -11 upward movement begins in that
same update. The existing landing band is unchanged. A queued press cannot become
a delayed double or wall jump. Successful jumps and wall attachment clear both
windows; holding Jump cannot refresh either queue or chain another landing hop.
Reset clears the appended player counters and terminal simulation remains frozen.
The existing readiness line recognizes ground grace without adding helper labels.
These timing windows are a native extension, not Python source parity.

No new action, mode, reflected API, actor/save change, engine framework or asset is
introduced. Focus/pause and physical button feel remain native acceptance work.

`desktop_ninja_jump` / `ninja_jump_forgiveness_test.cpp` passed 1,360/1,360 strict
single-TU MSVC C++17 checks. This includes only the 83 existing NSTEP fixtures and
their original fifteen fields, plus grace/buffer boundaries, an actual spent air
jump and early landing tap, held expiry, wall cancellation, wall-entry priority,
Reset and Driver pause/input checks. The six-step window does not pre-empt a
physical wall arrival. No original fixture regenerated, broad platformer suite,
repeated replay proof, engine build or native playtest was run for this change.

### Optional Emberstep Ascent Terrace climb

The cabinet offers **Adventure / Terrace climb** using the existing checked-mode
controls. Adventure remains option 0 with its enemies, gold, boss and rules. Option
1 is an ordered three-light practice route through the same four platforms and
the same NinjaPlayer movement, jumps and wall climb. Targets are (410,290),
(640,210), then (765,140): two terrace jumps and a right-wall climb. Only the next
light is active, with a larger halo; the existing level slot counts lights /3.

Practice has no enemies or boss. Falling below the existing pit boundary restores
the player to the last supported anchor, preserving collected lights and score.
Anchors are (175,380), (410,300), then (640,220). Recovery clears transient attacks
and jump windows and latches held Jump, so it does not create an automatic hop.
Landing on the lower platform remains ordinary platforming and can be recovered
with the same controls. Each light earns the existing 50-point gold award; all
three freeze a course-clear result. No timer, persistent reward or save is added.

Reset/fresh terminal retry retain mode and seed. A mode change starts over while
selecting the active native mode keeps progress. The practice HUD replaces unused
combat readiness with one goal row and a short movement/jump/wall footer, rather
than adding a help modal. Adventure output and random draws retain their rules.
`desktop_ninja_terrace_course` / `ninja_terrace_course_test.cpp` is the focused
public-input course, recovery and lifecycle check; prior source/grace/replay bulk
is separate evidence. Native mode focus, glow/layout and human difficulty/feel are
unverified.

Strict serial single-TU MSVC C++17 passed 34/34 focused checks. The single public
movement/jump/wall route completed all three lights in 172 steps, score 150 and
health five, without setting progress or goals. Retained route states verified all
three pit anchors, preserved progress, transient/held-jump cleanup and fresh jumps.
Mode validation/reset, ten-draw Adventure reset and short default companions,
presentation purity, terminal freeze, two representative retries and Driver input/
time/pause cleanup passed. No old source, grace, replay or broad platformer suite
was repeated. Portable scripted completion does not establish native play feel.

### Emberstep Ascent enemy health cues

Ordinary enemies now carry compact health pips above their existing silhouette:
two for walkers and four for jumpers, matching the existing spawn health. Gold
pips empty after a sword, star or spin hit, making surviving damage visible. The
cue follows each enemy's current position; defeated enemies and their pips leave
together. There is no new helper label, hit timer, saved field, RNG draw or combat
rule. Player readiness, boss health, scoring, movement and replay are retained.

`desktop_ninja_enemy_health` / `ninja_enemy_health_test.cpp` passed 58/58 strict
serial single-TU MSVC C++17 checks: full/partial health, retained silhouettes,
moving coordinates, actual sword/star/spin damage, lethal removal and scores,
presentation purity, 24 paired future steps and Reset cleanup. It uses the existing
test seam. No broad platformer suite or repeated source/replay proof was run for
this render-only slice. Native cue size, contrast, overlap and human play
acceptance remain unverified.

### Other source repairs

- One coherent IRONWAKE core replaces the concatenated/unreachable script structure. New and restarted sessions share the last revision's two-enemy start and pickup at (620,350), fixing its inconsistent three-enemy restart initializer.
- A final IRONWAKE boss spawn has a once-only encounter flag; the original final-spawn block recreated a final boss after every death. Normal stage-driven boss spawning is retained. The source distance victory rule remains intact.
- Terminal state is immutable until `Reset`; lethal damage cannot be followed by a later same-frame pickup or victory that reverses death. Emberstep Ascent now enters game over immediately when boss damage reduces health to zero, instead of waiting for the next frame.
- Emberstep Ascent spin movement is clamped after the added spin displacement, and wall climbing is bounded at y=−100. The original could move outside the arena during spin or climb upward without limit. Nominal source motion and wall-jump behavior are preserved.
- Entity caps: IRONWAKE 96 friendly +96 enemy bullets, six enemies (five regular slots plus the final encounter), 160 particles and at most one pickup. Emberstep Ascent five enemies, 64 attacks and five initial gold pickups. Transient objects expire or leave bounds. Output uses the existing capped `Frame` command collection.
- Non-finite or out-of-range axes are sanitized by the shared input helpers. Unknown controller buttons no longer silently cause sword attacks; explicit Unreal action bindings own these controls.
- Native sessions use the shared deterministic portable random stream, not Python's random generator. Cosmetic explosions have a separate stream and rendering does not consume gameplay randomness. Seed replay is native-to-native evidence, not a claim of seed-for-seed Python replay.
- Source ellipses and polygons are approximated with the existing rectangle/circle/line/triangle render contract. There is no audio or imported character mesh in this portable slice.

## Verification and limits

`platformers_source_oracle.py` checks both original SHA256 hashes before selecting reviewed AST constants, controller accessors, non-rendering class methods and bounded award/pickup fragments. It runs those selected source statements with controlled controller/random/Rect providers. It never imports Pygame, runs source module initialization, starts a full main loop, displays a window or initializes audio. The Rect provider models truncation toward zero and strict right/bottom edge exclusion; this is a stub contract, not evidence from an installed Pygame runtime.

The checked-in `platformers_parity.txt` is consumed by `platformers_test.cpp`. There are 323 executed-source scenarios: 275 method scenarios cover movement, jumping, crouching, axes/hat precedence, timer expiry, shooting vectors, enemies, attacks, wall behavior and boss damage; 48 award/pickup scenarios cover scoring, fractional rectangle boundaries, sword/star/spin kills and pickups. Canonical-platform Ninja movement fixtures run through `EmberstepGame::Step`, including six explicit opposing keyboard/hat, stick/hat and keyboard-plus-stick/hat regressions. Additional native integration tests exercise horizontal D-pad precedence, vertical climb bindings, once-only rewards, terminal/restart behavior, controlled boss victory, malformed input, entity/render bounds and 20,000 replayed simulation steps per game. The isolated local MSVC C++17 `/W4 /WX /EHsc` run on October 13, 2026 passed 16,251 assertions. Many assertions inspect frame geometry; this number is not a count of distinct gameplay scenarios.

Regenerate fixtures from the untouched pinned originals:

```powershell
python -B engines/unreal/core-test/desktop_games/platformers_source_oracle.py --ironwake 'C:\Users\730ri\OneDrive\Desktop\contra.py' --ninja 'C:\Users\730ri\OneDrive\Desktop\shadow_ninja_platform_fixed.py' --output engines/unreal/core-test/desktop_games/platformers_parity.txt
```

Compile the native test as C++17 with the module's `Public` folder on the include path, then pass the fixture path as the executable's first argument. The local pass uses MSVC `/W4 /WX /EHsc`; no shared Unreal editor is touched.

This evidence does not establish UHT/UBT compilation, packaged rendering/input, controller-device behavior or actual Unreal live gameplay. Claude's integration/playtest acceptance is a separate owner dependency. Complete rendering equivalence and the entire random Python main-loop trace are not claimed.

## Character and asset handoff

IRONWAKE's procedural avatar uses a blue shirt, skin-colored head/arms, direction-dependent blue/red bandana, dark trousers and side-facing gun. Its enemies are red-uniformed soldiers and a purple alien with a magenta eye and spikes. The source explicitly references the branded IRONWAKE/Konami characters and story; those references are not asserted to be original RicheyWorks intellectual property or cleared external assets. Preserve the actual source silhouette and palette when preparing a Blender brief, and record attribution/licensing decisions before distributing character assets.

Emberstep Ascent's source avatar is a compact dark gray/blue masked ninja: 16×28 body, skin-colored round head, dark face mask, gold sword/spin streaks, silver stars and a green wall-grab indicator. The boss has a dark red/brown broad body, red eyes and larger round head. The source says Riftwing/Nintendo style but contains procedural drawings; no imported sprite or character-license provenance was found in these scripts. Blender should preserve these source cues rather than inventing a different character. Suggested animation requirements are idle/run, ground/double jump, fall, wall cling/climb/jump, sword, star throw, spin, hurt and defeat.

No new meshes, textures, animations, installs, editor leases or imports were created by this platformer task. Handoff messages and owner acknowledgments are managed and reported by the coordinating parent.
