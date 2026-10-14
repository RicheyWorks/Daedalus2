# Desktop platformer ports: CONTRA and Shadow Ninja

## Native polish cycle 2 — source only, 2026-10-14

Claims hub 31185/31186 cover only `NinjaBoss` cue constants/read-only helpers and
`ShadowNinjaGame` feedback. CONTRA, `NinjaPlayer`, attack/enemy helpers and all
existing damage/movement/input/randomness remain unchanged. Boss movement still
precedes predecrementing its timer: initial 40, subsequent 50. Strike reach is the
strict axis rectangle `abs(dx)<300 && abs(dy)<100`, independent of ordinary boss
contact at distance <35; eligible strike damage remains one health and 60-step
invincibility. Static constants preserve those exact defaults and comparisons.

The final 12 timer steps display a countdown and current reach outline. This is
not a prediction of the next moved position and does not promise safety from
contact/enemies. Each existing instant pulse records an eight-step cosmetic
"pulse fired" cue, including misses or invincible players; it never asserts damage
or extends an attack. Existing ground/air/wall jump, spin cooldown/ground need and
shared sword/star cooldown/64-attack cap drive readiness text. Boss entry remains
score 1200, level remains 1 and host R/Restart still resets the game.

**Uncompiled/untested.** No CI, service, editor, controller or native gameplay run.
The exact source packet and current per-game coverage/queue are in
`docs/desktop-games-polish-install.json` and
[DESKTOP-PYTHON-GAMES.md](../../../../docs/DESKTOP-PYTHON-GAMES.md). Later validation
must inspect timer 13/12/1/50, strict range edges, invincibility, moving boss and
receipt on hit/miss/protected pulses. The old oracle receipts below do not prove
the new cues. No new Blender assets or character imports were created.

These are ports of the actual user's Desktop scripts into the existing `daedalus::desktop::Game` contract. The Python originals are preserved. Both native cores start a playable session immediately; the Daedalus launcher owns opening, closing and restarting the minigame.

## Canonical source selection

| Game | Original path | SHA256 | Baseline |
| --- | --- | --- | --- |
| CONTRA | `C:\Users\730ri\OneDrive\Desktop\contra.py` | `2e845d67754fc81feeea881b7c6d3068a60042c3371e9f8fdeae5a8616d09107` | Last complete controller revision; constants/classes after line 582. File modified May 1, 2026 at 02:14:59 UTC. |
| Shadow Ninja | `C:\Users\730ri\OneDrive\Desktop\shadow_ninja_platform_fixed.py` | `83dd921b95043a2723b61513d84471adbfaede29dd18744367835fbc3aa03e36` | May 2, 2026 fixed platform revision, including safe platform start and jump edge detection. Older numbered revisions are not the baseline. |

The user explicitly selected the last revision. `contra.py` contains two concatenated standalone programs: the first `main()` exits via `sys.exit()`, preventing the later controller revision from running as a normal script. The port uses only the last complete definitions, rather than preserving that accidental entry-point barrier.

## Runtime bindings for the Unreal owner

Include `DesktopGames/DaedalusDesktopPlatformersCore.h`. Registry constructors are `ContraGame` and `ShadowNinjaGame`; each implements `Reset(uint32 seed)`, `Step(const Input&)`, `Render(Frame&)` and `GetStatus()`.

Call one `Step` per 1/60-second simulation step. The Unreal adapter should cap accumulated wall-clock time and catch-up steps, issue pressed edges only once, and clear controls when focus is lost or the minigame closes. These cores contain no wall-clock loop, window creation, Python runtime or editor dependency.

| Binding | CONTRA | Shadow Ninja |
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

For Shadow Ninja, keyboard directions, stick axes and D-pad directions remain separate. `ShadowNinjaGame::Step` passes `PadRight-PadLeft` and `PadUp-PadDown` into the player's explicit hat parameters. The source's horizontal hat wins over keyboard and stick input, including opposing directions; both D-pad flags cancel to neutral. Vertical wall-climb conditions preserve the source's independent up/down checks, so opposing keyboard/stick/hat climb requests can cancel. The wrapper should retain these independent fields rather than merging D-pad into keyboard directions or clearing stick axes. Controller connection/hotplug and physical mappings belong to the adapter.

CONTRA `SubmitCheatKey(key, titleScreen=false)` accepts `0=up, 1=down, 2=left, 3=right, 4=B, 5=A`. The source sequence U,U,D,D,L,R,L,R,B,A gives +5 lives, capped at 99, and 600 steps of spread in play; passing `titleScreen=true` gives the source's 30-lives title bonus. Normal gameplay feeds digital direction/action/jump edges automatically. A title-screen-specific binding is optional UI work; native `Reset` starts play directly.

`GetStatus().Lives` is lives for CONTRA and health for Shadow Ninja. `Over` stops subsequent simulation; `Won` distinguishes success. The port does not grant Daedalus currencies or persistence rewards: the session owner must consume terminal state once if those are added.

## Preserved mechanics and source quirks

CONTRA preserves gravity 0.6, jump −13, keyboard movement 5, source crouching geometry, right-key precedence when both directions are down, camera smoothing 0.85/0.15, integer Pygame rectangle semantics, bullet speed 12/lifetime 60, fire cooldown 8 (rapid 4), three-shot ±15° spread, 900-step spread pickups, 90-step damage invincibility, grunt score 100, boss score 500, stage-driven spawning, source platforms and the source's distance victory at world x >2800. Source bosses have only two hit points. Reaching the distance target can win without defeating a boss; that original rule is deliberately preserved. Crouching still does not reduce horizontal speed. The declared `SCROLL_SPEED` was unused in Python and remains unused.

Shadow Ninja preserves start at (175,380), feet-based platform collision and its forgiving landing band, gravity 0.6 capped at 12, ground jump −11, double jump −9, wall slide capped at 1, wall climb 3, wall jump −10/7 with a 10-pixel push, edge-triggered jumping, sword cooldown/lifetime 18/12, star cooldown/lifetime/speed 12/50/9, spin duration/cooldown 25/45, source per-frame spin damage, five health, pit death at y >540, gold score 50, sword/star/spin kill scores 150/100/200, boss spawn at score 1200, boss health 25 and victory bonus 800. The `LEVEL: 1` indicator remains unchanged because the source never increments the level. Procedural torches are static visual decoration in the port.

## Repairs and deliberate adaptations

- One coherent CONTRA core replaces the concatenated/unreachable script structure. New and restarted sessions share the last revision's two-enemy start and pickup at (620,350), fixing its inconsistent three-enemy restart initializer.
- A final CONTRA boss spawn has a once-only encounter flag; the original final-spawn block recreated a final boss after every death. Normal stage-driven boss spawning is retained. The source distance victory rule remains intact.
- Terminal state is immutable until `Reset`; lethal damage cannot be followed by a later same-frame pickup or victory that reverses death. Shadow Ninja now enters game over immediately when boss damage reduces health to zero, instead of waiting for the next frame.
- Shadow Ninja spin movement is clamped after the added spin displacement, and wall climbing is bounded at y=−100. The original could move outside the arena during spin or climb upward without limit. Nominal source motion and wall-jump behavior are preserved.
- Entity caps: CONTRA 96 friendly +96 enemy bullets, six enemies (five regular slots plus the final encounter), 160 particles and at most one pickup. Shadow Ninja five enemies, 64 attacks and five initial gold pickups. Transient objects expire or leave bounds. Output uses the existing capped `Frame` command collection.
- Non-finite or out-of-range axes are sanitized by the shared input helpers. Unknown controller buttons no longer silently cause sword attacks; explicit Unreal action bindings own these controls.
- Native sessions use the shared deterministic portable random stream, not Python's random generator. Cosmetic explosions have a separate stream and rendering does not consume gameplay randomness. Seed replay is native-to-native evidence, not a claim of seed-for-seed Python replay.
- Source ellipses and polygons are approximated with the existing rectangle/circle/line/triangle render contract. There is no audio or imported character mesh in this portable slice.

## Historical baseline verification and limits

`platformers_source_oracle.py` checks both original SHA256 hashes before selecting reviewed AST constants, controller accessors, non-rendering class methods and bounded award/pickup fragments. It runs those selected source statements with controlled controller/random/Rect providers. It never imports Pygame, runs source module initialization, starts a full main loop, displays a window or initializes audio. The Rect provider models truncation toward zero and strict right/bottom edge exclusion; this is a stub contract, not evidence from an installed Pygame runtime.

The checked-in `platformers_parity.txt` is consumed by `platformers_test.cpp`. There are 323 executed-source scenarios: 275 method scenarios cover movement, jumping, crouching, axes/hat precedence, timer expiry, shooting vectors, enemies, attacks, wall behavior and boss damage; 48 award/pickup scenarios cover scoring, fractional rectangle boundaries, sword/star/spin kills and pickups. Canonical-platform Ninja movement fixtures run through `ShadowNinjaGame::Step`, including six explicit opposing keyboard/hat, stick/hat and keyboard-plus-stick/hat regressions. Additional native integration tests exercise horizontal D-pad precedence, vertical climb bindings, once-only rewards, terminal/restart behavior, controlled boss victory, malformed input, entity/render bounds and 20,000 replayed simulation steps per game. The isolated local MSVC C++17 `/W4 /WX /EHsc` run on October 13, 2026 passed 16,251 assertions. Many assertions inspect frame geometry; this number is not a count of distinct gameplay scenarios.

Regenerate fixtures from the untouched pinned originals:

```powershell
python -B engines/unreal/core-test/desktop_games/platformers_source_oracle.py --contra 'C:\Users\730ri\OneDrive\Desktop\contra.py' --ninja 'C:\Users\730ri\OneDrive\Desktop\shadow_ninja_platform_fixed.py' --output engines/unreal/core-test/desktop_games/platformers_parity.txt
```

Compile the native test as C++17 with the module's `Public` folder on the include path, then pass the fixture path as the executable's first argument. The local pass uses MSVC `/W4 /WX /EHsc`; no shared Unreal editor is touched.

This evidence does not establish UHT/UBT compilation, packaged rendering/input, controller-device behavior or actual Unreal live gameplay. Claude's integration/playtest acceptance is a separate owner dependency. Complete rendering equivalence and the entire random Python main-loop trace are not claimed.

## Character and asset handoff

CONTRA's procedural avatar uses a blue shirt, skin-colored head/arms, direction-dependent blue/red bandana, dark trousers and side-facing gun. Its enemies are red-uniformed soldiers and a purple alien with a magenta eye and spikes. The source explicitly references the branded CONTRA/Konami characters and story; those references are not asserted to be original RicheyWorks intellectual property or cleared external assets. Preserve the actual source silhouette and palette when preparing a Blender brief, and record attribution/licensing decisions before distributing character assets.

Shadow Ninja's source avatar is a compact dark gray/blue masked ninja: 16×28 body, skin-colored round head, dark face mask, gold sword/spin streaks, silver stars and a green wall-grab indicator. The boss has a dark red/brown broad body, red eyes and larger round head. The source says Sega/Nintendo style but contains procedural drawings; no imported sprite or character-license provenance was found in these scripts. Blender should preserve these source cues rather than inventing a different character. Suggested animation requirements are idle/run, ground/double jump, fall, wall cling/climb/jump, sword, star throw, spin, hurt and defeat.

No new meshes, textures, animations, installs, editor leases or imports were created by this platformer task. Handoff messages and owner acknowledgments are managed and reported by the coordinating parent.
