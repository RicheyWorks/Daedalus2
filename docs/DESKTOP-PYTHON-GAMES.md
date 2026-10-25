# Desktop Python games into Daedalus

Recovery update (2026-10-14): PR53 merged, then deleting its base branch
automatically closed PR51 without merging it. The same PR51 is recovered against
`main`, preserving delivered `9fbd450d895bab288401445d7c488a33bb59196c` and normally
merging main snapshot `1ee121e0fd41302889f54bed0c3caaefacd92214` without conflicts.
All eleven runtime files, 21 test/oracle files and original source/compile/repair
evidence remain identical; see [stack recovery proof](desktop-games-stack-recovery.json).
Fresh CI results belong to the final recovery head in the PR body. Earlier runs
and composite DLL evidence retain their historical source pins; this recovery
does not claim another Unreal build, editor load or in-world acceptance.

The user-confirmed collection is on the assessed Windows redirected Desktop:
`C:\Users\730ri\OneDrive\Desktop`. `PythonGames/main.py` is the Dungeon Prototype;
21 loose scripts are beside the folder. **22 scripts represent 11 game families.**
Original files are reference inputs and are never edited by this port. No Git metadata
was found in the collection or its Desktop/ancestor directories.

## Latest source revisions

The user explicitly selected the last revision. Selection combines UTC modification
timestamps, revision filenames and code evolution; creation time alone is misleading
for copied/OneDrive files. Full SHA-256 pins are in `desktop-games-sources.json`.

| ID | Canonical source | Latest evidence | Port owner / backlog |
| --- | --- | --- | --- |
| pong | `pong (1).py` | May 1 04:32 UTC; adds controller to earlier `pong.py` | Pilot; root |
| dungeon | `PythonGames/main.py` | Sole script, April 25 | Maze slice |
| asteroids | `asteroids_pygame_ce.py` | May 2 08:17; later than `(1)`, adds controller | Shooter slice |
| football | `football_pygame_ce.py` | Sole script, May 2 | Sports slice |
| pacman | `pacman.py` | Sole script, May 1 | Maze slice |
| sega_shooter | `sega_space_shooter.py` | Sole script, May 1 | Shooter slice |
| shadow_ninja | `shadow_ninja_platform_fixed.py` | May 2 08:22; after numbered revisions, platform/spawn fixes | Platformer slice |
| star_shooter | `star_shootergpt1_fixed.py` | April 29; after all six other revisions, save-state restoration added | Shooter slice |
| dodge_ball | `super_dodge_ball_fixed.py` | May 2 08:24; after earlier tournament script | Sports slice |
| contra | `contra.py` | Sole file contains two full versions; later controller version is canonical | Platformer slice |
| zelda | `zelda.py` | Sole script, May 1 | Maze slice |

All are Python/Pygame; many source headers specify Pygame CE. The `(1)/(2)/(3)` and
`fixed` scripts are revisions, not extra games. The unrelated ComputerPets/Minesweeper
work is not a substitute for this collection. The native catalog contains these eleven games.
The user's next requested additions are SudokuPro and BlackJackPro: thirteen requested game
families in total, with the two Java additions assessed separately below.

## Shared runtime integration

Inspection of 67 native and 657 core/server files at baseline `ba17f688` found no generic
minigame registry. The new local catalog serves these ports only. World discovery and HUD
remain the existing `ADaedalusUsable::Nearest`, `Prompt` and `Use` seam; the new arcade
cabinet derives from that class. This eleven-game slice introduces no alternate world interaction
or Java service.
Portable C++17 `Game` objects share input, status and bounded drawing commands; Slate is
the Unreal presentation adapter. Original Python imports/display loops do not run in Unreal.

Each core update is a source-style 60 Hz frame. The driver accepts finite nonnegative
elapsed time, performs at most eight steps per call, preserves one-shot input edges and
drops excess hitch catch-up. Pause clears input/time debt; restart resets all session state.
Gamepad axes, keyboard directions and D-pad fields are separate. The presentation adapter
maps them per game so source-specific additive input and hat precedence are retained.

`ADaedalusDesktopArcade` is placeable and Blueprintable with `InitialGameId`, `InitialSeed`,
per-instance `CabinetId` and optional automatic advance. Blueprint bindings expose catalog,
select/restart, input, advance, pause, state, Star difficulty and native save/resume/leaderboard.
Do not drive a second clock while `bAutoAdvance` is enabled. The Slate host clears held inputs
on focus loss, bounds draw commands and defers close cleanup. The placeholder is an engine
cube; there is no imported cabinet mesh, character rig or new audio integration.

The cabinet catalog drafts a selection while keeping the current run paused.
Browsing or accepting a row does not start a game. **Switch game** explicitly
starts a fresh selected game; **Keep playing** discards that choice and resumes
the current run. Its title stays visible beside those actions. Existing saved
runs are retained, and pending Star saves still block switching or resuming.
F2 / right-stick click opens the native catalog for the opening Slate user.
Focused catalog controls own their keys and analog navigation, keeping those
events out of gameplay and Star's paused menu. Failed switching keeps the run
and draft choice. Native popup, focus, input and save-failure acceptance remain
pending; this source slice does not establish runtime acceptance.

Star Shooter has a native **How to play** panel, also opened with F1 or left-stick
click from game focus. It groups the survival goal, upgrades, playing controls,
save/continue behavior and terminal retry at a readable size. Help pauses the
current run and disables the cabinet beneath it. Mouse wheel, Page Up/Down or
LB/RB scroll the bounded instructions. **Resume game** explicitly resumes a live
run; **Return paused**, F1/left-stick click, Esc/Back or pad B dismisses help while
keeping the run paused. Game-over and pending-save states cannot use Resume.
Save warnings stay visible and existing save processing continues. The existing
Continue saved Star run button also participates in native focus navigation.
Help does not save, restart, change difficulty or replace the active/drafted game.
Source/API/focus review is separate from pending native layout, controller,
scrolling, save-failure and focus-loss acceptance. No new save format is introduced.

Star persistence is scoped to `Saved/DaedalusDesktopGames`: validated `DGS1` run state and
`DGL1` top-ten score/wave/difficulty records. Leaderboard writes reload/merge fresh records;
failed or malformed reads are refused. Failed run writes retain the pending payload, retry at
five-second intervals while advancing and block session replacements until success. Close/reopen
preserves the pending request, but RAM cannot survive actor EndPlay/process loss when the OS
refuses writing. New/restarted native runs deliberately retain the previous saved run; the Python
new-game path deletes it. The port never reads or overwrites the Python originals' home save files.
Per-game controls/features and intentional repairs are documented with each test family.

## Minesweeper saved boards

The existing native Minesweeper now has **Save board**, **Continue saved board** and
**Save & Close** in its cabinet. Save & Close leaves the cabinet open if writing fails.
Plain Close, Restart and game selection leave the previous saved board unchanged;
Continue explicitly replaces the current board. One local slot is shared by this
installation's Minesweeper cabinets, separate from Star Shooter's files.
F5 saves and F9 continues the saved board. While paused, gamepad X saves and Y
continues the saved board; P / Start returns to play.

The Minesweeper cabinet also exposes the engine's three existing **New board**
presets: 9 x 9 with 10 mines, 16 x 16 with 40, and 30 x 16 with 99. The current preset
comes from the actor's active option, including after Continue. Selecting any
preset, even the current one, starts a fresh board at the retained seed. Save
first to keep the current progress; changing size does not overwrite the saved
board. Preset, Save board, Continue and Save & Close buttons support native focus
navigation from the cabinet controls. Their rows wrap to the allotted width.
Source review covers wiring/save preservation; native layout and controller
traversal across sizes and Continue still require acceptance.

**New puzzle** starts an unrevealed board at the current size with a fresh native
seed. **Restart**, including result replay, retains the current seed and size;
the first revealed cell also affects the planted layout. New puzzle leaves the
saved slot unchanged. Continue can still restore that older board exactly, and
Restart then follows the restored seed. The New puzzle button uses the existing
native focus navigation and does not reuse a gameplay pad shortcut.

The native board also accepts **left click to reveal**, **right click to toggle a
flag**, and **middle click to chord** an open number. Chording keeps the existing
matching-flag rule; matching flags can still be wrong. Clicks select the rendered
cell at the current canvas scale, including its narrow gutter. Letterboxing and
clicks outside the grid do nothing. A paused or completed board ignores gameplay
clicks; resume or start another board explicitly. Keyboard/gamepad actions remain
available. Each accepted mouse press clears prior held inputs and acts once,
without adding a timer step or changing first-reveal safety.

Minesweeper also uses the native **How to play** panel (F1 / left-stick click).
Readable sections explain the clear-every-safe-cell goal, safe opening, diagonal
number clues, flood reveal, optional flags, the estimated mine counter, chording
risks, mouse/keyboard/controller controls and exact-board save/continue. The
current board pauses beneath the guide. Resume explicitly returns to a live board;
Return paused and dismiss keys keep it paused, including after a result. The same
bounded scroll, held-input guard and save warning behavior serves Star Shooter.
Help is tied to the game that opened it and closes if the active game changes;
it cannot resume a different game. No game rules, timer or save records change.
Native guide layout/focus, mixed input and save/continue acceptance remain pending.

`Saved/DaedalusDesktopGames/minesweeper.dgs` stores the exact board, flags, selected
cell, difficulty, active timer and original seed in a bounded versioned `DGM1` record.
Saving before the first reveal retains its deterministic 3x3 safe opening. Continue
does not add elapsed wall time or restore held inputs. Won and lost boards retain
their result. Invalid saves leave the current run and saved file intact.
Several mouse presses can produce a valid loss before the first timer step; that
zero-tick result also roundtrips in the same `DGM1` format.

The focused portable test covers all difficulties, pre-reveal and planted roundtrips,
continued play through completion/loss, refused saves, input cleanup and Star save
compatibility. See [Minesweeper notes](../engines/unreal/core-test/desktop_games/minesweeper_notes.md)
for format and reproduction. Unreal compilation, native filesystem failure handling
and live Slate controls remain acceptance work; portable checks do not prove them.

## Pong pilot parity and polish

The oracle reads the pinned latest `pong (1).py`, reviews/extracts only its numeric update
statements and executes those statements with synthetic keys/controller values. It never
imports Pygame, opens a display, runs the original loop or reads user save data.
Eleven source cases cover keyboard, both keys, analog/deadzone, sequential AI movement,
first contacts and scoring. C++ matches those states exactly.

Intentional enhancements: keyboard overshoot clamps to the playfield, collision direction
guards prevent repeated paddle/wall flip-flops, counters saturate instead of overflowing,
and the host supplies explicit pause/restart/close cleanup. No artificial winning threshold
is added to the source's endless Pong match. These repairs are tested separately from parity.

## Source identity and Blender handoff

The scripts draw procedural ships, characters, particles and maps; inspected code does not
load external sprite/model assets. No original Blender meshes or rigs were supplied.
Use source palettes/silhouettes as gameplay references: Contra's
blue-shirt/bandana gunner; Shadow Ninja's dark mask/outfit and sword/stars; football and
dodge-ball team colors; source ship/UFO/boss silhouettes. Pong and the dungeon prototype
need no invented character model.

CONTRA, Pac-Man and Zelda are explicitly branded source references. Their names/likenesses
are not claimed as original RicheyWorks characters; external asset rights/provenance were
not supplied. The native drawing adapter is a provisional source-faithful reference, not a
claim of cleared production art. Blender creates original production characters/cabinets and
records their provenance; commercial use needs original assets or verified rights. Claude owns
Unreal animation blending, materials, interactions and gameplay polish. A mesh export alone
does not prove rig compatibility, animation playback, collisions or gameplay. Existing Daedalus
limits remain metres, applied scale,
bottom-center origin, -Y front, blocky/beveled forms and bounded material/triangle budgets.

Pong also offers an optional **Rally practice** mode through two native toggle
buttons. A larger paddle, slower ball and full-height return wall support a
player-only rally count and session best. Misses keep the best, reset the rally
and give a two-second preparation window; Space / pad A can serve early. Every
five player returns earns a brief celebration without ending play. The counters
occupy a separate strip above the court. Restart or a mode change starts a new
session; the best is not persisted. Selecting the active mode does not restart.
The default **Match** retains its source rules, endless score and original frame.
Mode selection uses existing SetGameOption, native checked state and focus/input
cleanup; no new actor API, save format or assets are introduced. Native toggle,
viewport/focus/controller and difficulty/feel acceptance remains unverified.

Driftstone Patrol also supports **K / left trigger to brake**. Braking slows drift
to rest and takes priority over thrust; turning and firing remain available. Blue
ship fins and a live BRAKING cue show the action. Pad B keeps its fire binding.
Reset, respawn and focus/input cleanup retain the existing lifecycle. The original
coasting/thrust rules apply when not braking; Sega and Star behavior is unchanged.
Native trigger/focus and actual flight feel still require acceptance.

The desktop Dungeon cabinet's existing **Threadlight** chapter has an optional
dotted trail, toggled with **Shift / pad Y** (V / LB also work). It follows the
required NEXT lantern and finally EXIT, helping a player learn the room without
automatically moving or lighting anything. **J/Space / pad A/X** still lights a
nearby target; **K/Enter / pad B** resets the circuit. The guide starts off, resets
off, and cannot begin the clock by itself. Movement, seed order, completion and
progress rules are retained. This is a desktop cabinet feature, separate from
the world Dungeon realm. Native font/layout, physical input and playtest acceptance
remain pending.

Threadlight's **Next circuit** cabinet button visits all six authored lantern
orders, wrapping after circuit 6. The existing progress line identifies the current
circuit. Starting the next order clears the current circuit's lights, clock and
trail; **Restart / K / Enter / pad B** replays the selected order. Nothing advances
automatically on completion. This uses the cabinet's existing start-game lifecycle;
native button navigation, focus and layout acceptance remain unverified.

Football also offers **Target practice** beside its default Match mode. Clear
three glowing goal pockets by moving around the ball to aim and pressing
**J/Space / pad A/X** to kick. There is no opponent or running match clock. Misses
keep cleared targets and set up another ball; **K/Enter / pad B** sets up the same
target immediately. After three targets, a fresh kick starts another round.
The mode uses existing ball physics and native checked controls. Changing mode
or Restart clears session progress; selecting the active mode keeps it. It adds
no durable score/save or reward. Native layout, controller/focus and play feel
still require acceptance.

Shadow Ninja gives jump presses a small timing allowance: about 100 ms after
leaving a ledge, or before landing when the air jump is already used. Early taps
wait for a ground jump; available double jumps remain immediate. Wall jumps still
need a fresh press. The same Space / pad A controls and jump impulses remain;
holding Jump does not repeat landing hops. Reset clears the timing state. Native
controller feel and integration remain unverified.

Shadow Ninja's ordinary enemies show compact **health pips** above their existing
silhouette: two for walkers, four for jumpers. A surviving hit empties a pip,
making damage visible without another helper label. Sword, star, spin, scoring
and movement rules are retained. Native cue size, contrast and play acceptance
remain unverified.

Glowtrail Chase's matching blue openings in the central passage connect across
the 560-pixel maze. Movement continues through either opening with its overshoot;
pursuers can follow, and contact/dot collection remains continuous across the seam.
Other walls stay solid. Mirrored silhouettes and gate marks explain the route
without new controls. This native extension preserves the map, all 304 dots and
existing score/life/power/respawn rules; pinned source fixtures retain their
original boundary behavior. Native visual/input and chase feel remain unverified.

In Glowtrail's paired passage, chasing pursuers follow the shorter clear route
through the opposite gate when both actors are in its outer arms. The central
room's walls still block that shortcut. Frightened steering, ordinary maze pursuit,
movement speed and random choices retain their existing rules. Native chase feel
and visual acceptance remain unverified.

Ironwake Advance likewise accepts a jump shortly after stepping off a platform,
while keeping its existing held-jump landing hops, crouch restriction and jump
trajectory. The allowance expires after six decisions and is consumed by a jump;
accepted damage and new runs clear it. No new controls or mode are needed. Native
input/feel acceptance remains pending.

Courtyard Clash marks the current automatic throw target with side chevrons and
its C1/C2/C3 number in the existing readiness line. The nearest living opponent
is selected by the unchanged throw rule. A muted cue during cooldown is a current
snapshot; moving players and country supers can change the eventual flight. It
adds no control or gameplay rule. Native readability/feel acceptance is pending.

Courtyard Clash's country picker accepts **stick flicks** alongside keys and the
D-pad. Tilt vertically past 0.6 once, then center both axes within 0.3 before the
next choice. The stick gesture that opens the picker is consumed. Match movement
and the existing original-stick-versus-hat charge rules are retained. Native
hardware and selection layout acceptance remain unverified.

Courtyard Clash also uses **How to play / F1 / left-stick click** for an on-demand
guide to shared team movement, nearest-target throws, held catch/rethrow, jumping,
charging and the four-round flow. The existing native guide pauses play, scrolls
with Page Up/Down or LB/RB, and clears held input. **Resume game** returns to the
same match or result; continuing a result still needs a fresh gameplay press.
**Return paused** keeps it paused. Native layout, scroll/focus and mixed physical
input acceptance remain pending.

After Courtyard Clash's fourth round, the **tournament scorecard** declares the
overall win, opponent win or draw from the existing cumulative match wins. Large
counts and four-segment bars distinguish your chosen country from all opponents;
the smaller last-match line preserves who won that match. Earlier-round results
and all play/scoring rules are retained. A fresh continue press still returns to
title, and confirming a country starts a new tournament. Native font/layout and
physical input acceptance remain unverified.

Driftstone Patrol offers **Three waves** beside its original Endless mode. Clear
every rock and split fragment through wave three to finish the voyage. The same
flight, brake, UFO, score and life rules apply; wave N/3 and the result show the
goal. Restart/fresh retry keeps the mode, and changing modes starts over. Native
controls/layout, voyage duration and play feel remain unverified.

Riftwing Vanguard's ordinary ships show two basic/four chaser **health pips**, so
surviving hits remain visible. The boss retains its separate health bar. Combat
and scoring rules are unchanged; native cue readability remains unverified.

Riftwing Vanguard offers **Boss rehearsal** beside its default Full run. The same
20-HP boss arrives immediately, with the normal starting ship and score zero;
regular enemies still provide pressure. Full run keeps its 1500-point entry.
Rehearsal has clear mode/result cues and retains the usual shooting, pickups,
damage and earned score rules. Restart or a fresh result retry keeps the mode;
changing modes starts over. Native controls/layout and play feel remain unverified.

Pong's optional **First to 5** offers a short match beside endless Match and Rally
practice. The existing match physics and controls apply; the fifth point brings
a frozen result and a deliberate fresh Space / pad A rematch. Scores sit above
the court. R/Restart keeps the selected mode, and choosing an already selected
mode keeps the current game. No result persistence is added. Native focus/layout
and human play feel remain unverified.

## Evidence stages and acceptance

The inventory and actual source hashes are recorded; native tests, source oracle cases,
Unreal UHT/object/reflection compile, plugin link/load and live gameplay are separate stages.
All six strict local MSVC suites passed. The five source fixture families contain 1,507 reviewed
source cases (11 Pong, 239 maze, 299 sports, 323 platformers, 635 shooters), with controlled
providers rather than whole original Python loops. Six cosmetic Star particle-count fields are
excluded from parity. Deterministic native replay uses its own RNG, not Python's random stream.
Isolated Unreal 5.8.3 UHT, actor/widget object compilation and actual generated reflection object
compilation passed; `desktop-games-unreal-compile.json` records the compiled source revision,
manifest and object hashes. This is not plugin linking/loading or editor/live play evidence.
Do not label all games complete merely because catalog entries exist. The backlog tracks
source-pinned, native-tested, runtime-wrapped, compiled and Claude live-accepted independently.

Claude/unreal-team owns editor placement, plugin load and live play. Blender owns agreed
character creation; a delivered message or broker receipt is not acceptance. No shared editor
lease, restart, second editor, source-script launch, installation or source-original edit is
performed by these ports. Active audio and other teams' RPG work remain separate.

Acceptance should cover every registered game: enter through Interact, select, play core
actions/scoring/win/loss, pause/resume, restart, switch games and exit; verify held/edge input,
controller/focus loss, pawn replacement and EndPlay. Record exact build head and screenshots
or gameplay evidence. Inspect latest-specific settings/save features where present. Source
defect repairs and any deferred host persistence/audio must be explicitly visible in handoff.

## Commercial cabinet requirement

The user's intended product is a purchasable NFT arcade cabinet with broad commercial reuse
of the user's own code and assets. `CabinetId` identifies a placed instance; game selection is
independent of it. Future entitlement and licensing terms need their own implementation and
review. This port does not change repository licenses or grant rights to third-party names,
characters or artwork. No token issuance, contract, wallet, listing, payment, sale or token gate
is implemented. Playtest access remains available without token ownership.

## Pilot and remaining effort

Pong is the smallest useful playable pilot: one arena, two paddles, a ball, score and controller
input, with no character rig or external asset dependency. It proves cabinet interaction,
input isolation, frame presentation and exit cleanup before character-heavy games are accepted.
The other native cores are available in the same catalog, but every game still needs live
acceptance against its latest-specific actions and repaired source defects.

| Work | Relative remaining effort | Evidence / dependency |
| --- | --- | --- |
| Pong cabinet pilot | Smallest | Core source parity; cabinet placement and live input/exit acceptance remain |
| Dungeon, Asteroids, Football | Small to medium | Procedural geometry and compact rules; no imported source meshes |
| Maze, Zelda, Sega, Dodge Ball | Medium | Map/collision or boss/tournament paths and game-specific controls |
| Contra, Shadow Ninja, Star Shooter | Larger | Compound actions, bosses, animation needs; Star settings/save/menu/leaderboard |
| Original Blender production art | Separate asset work | No supplied rigs; silhouette, materials, rig/animation budgets need owner acceptance |
| Multiplayer/world-screen cabinet | Separate runtime work | Current overlay is standalone-only and pauses its local world |

These are comparative scope estimates, not dates or staffing promises. Native rule tests do
not reduce rendering, physical-controller, rigging or multiplayer acceptance to a checkbox.

## Next Java additions: observed API facts

### Approved upstream repair adoption

PR51's prior head `d29329b717860d3f020be17276aba883712d950f` failed only the
inherited `RetroRealmTest:163` fixture parity check (690 core tests, one failure).
The approved canonical PR53 head `7427deffef766ce6e6ef83e6d1acd33cbe680938` and
current-main fixes at `d57a388e7ae59b804d033b52c76e2b8df529d5d6` were adopted in
this isolated feature branch without conflicts. The review is stacked on
`codex/realm-production-queue`; its existing owner retains parent/main merging.
All eleven Desktop runtime blobs, the game test tree and original source-pin
blob are unchanged; [preservation proof](desktop-games-approved-repair.json)
records both sides. Existing CI gates also run on that approved stack base.
Actual final-head CI is recorded in PR51 and its existing queued handoff pin.
No fixture regeneration, duplicated catalog implementation, original-source
edit, editor lease, art request or live acceptance is implied by this repair.

Keep Java authoritative for both games. The proposed C++ adapters perform asynchronous
requests, bounded validation, presentation and lifecycle cleanup, with per-session serialized
commands and cancellation/generation guards against stale responses. These are integration
requirements, not implemented functionality in this eleven-game PR. No Java rules are rewritten.

**SudokuPro**: [repository at assessed main](https://github.com/RicheyWorks/sudokupro/tree/973c73a35f8659a17022232f0996d4ffb0095997)
uses Java 17/Maven, Spring Boot REST and a raw WebSocket; JavaFX is a network client.
`GET /api/session` returns player identity, CSRF metadata and a WebSocket ticket. Native
REST/WebSocket HTTP Basic credentials are supported; mutating REST also sends the XSRF-TOKEN
cookie and named CSRF header. The alternative WebSocket ticket expires after 60 seconds and
is single-use. Keep credentials out of actor properties, save files and logs.

`POST /api/game/new` accepts difficulty 1..5 plus chaos/mirror/timeAttack settings and returns
the authoritative board. REST supports fetch, save, resume and bounded saved-list queries.
Moves, undo, redo and sync use `/ws/game?gameId=<encoded>`; there is no observed REST move
endpoint. A move includes row/column, old/new values and type, and Java stamps its source.
The protocol has no operation IDs: do not silently retry mutations after an uncertain response;
reconcile through sync/state instead. Bound boards to 81 cells and preserve server-owned timer,
givens, notes/variants and legal move projection. No service was launched in this assessment.
The assessed head's [CI run](https://github.com/RicheyWorks/sudokupro/actions/runs/38087377620)
was blocked before jobs by the account payment/spending limit, so it supplies no new test pass.

**BlackJackPro**: [repository at assessed main](https://github.com/RicheyWorks/BlackJackPro/tree/1ec1801ac635e62945072974cbe8c78398a17849)
has a pure Java `Engine`, Swing and libGDX/Android presentation. It builds Java 17 bytecode
with JDK 21. There is no implemented HTTP/auth/database/server API at this pin. Its engine
already provides bet/deal/hit/stand/double/split/surrender/insurance legality and commands,
outcomes, net results and statistics. A small Java facade is required before an HTTP bridge
can be useful; coordinate its ownership and authoritative source pin before implementation.

The facade must project visible cards, legal actions and authoritative results. Do not serialize
`Engine.dealer()` or `liveRoundState()` wholesale: these expose the hidden hole card and future
shoe. Each mutable Engine/Shoe session needs a single serialized command owner. Use only
simulated credits; no real-money/crypto wagering, wallet, cash-out or financial integration.
Local `BlackJackPro-buff` has substantial uncommitted core/UI/build changes beyond the clean
main pin and must be preserved. The assessed head's [CI run](https://github.com/RicheyWorks/BlackJackPro/actions/runs/37192929132)
failed build/test and UI jobs; cause is not established from the available job metadata.
Historical README counts are not current CI evidence. No Java tests or services were run.

Neither Java repository supplies imported Blender character rigs at the assessed pins. Existing
procedural cards/boards, palettes and personality data can inform an original cabinet brief;
new meshes and animation compatibility remain separately accepted art/runtime work.
