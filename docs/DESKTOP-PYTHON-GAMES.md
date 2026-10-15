# Desktop Python games into Daedalus

## Current HUD overlap fix, 2026-10-15

The sole operator's native checkpoint `codex-arcade-gameplay-0344.checkpoint.json`
records 39 passing bounded checks on the installed names/input version plus
Minesweeper: twelve-game start/one-step/restart, real Hero interaction, selected
Slate/raw/controller-method actions and Star run-save failure/retry/Continue.
Its three 2560x1392 screenshots show a concrete failure: Hero/logbook/clock,
interaction prompt, crosshair and lower stats paint over the opaque arcade.
Physical controllers, whole-game progression and multiple local users remain
unverified. That baseline proof does not validate a later UI patch.

UE 5.8.3 source confirms the cause. The per-player canvas is root layer100;
the global viewport overlay is root layer200. The arcade's per-player child Z100
cannot cover Hero/Sky global child Z10. The patch hosts only the arcade at global
Z100, above those unchanged HUDs. A foreground wrapper uses the engine's current
player-host geometry, transforms both corners through absolute space, clips the
child and retains per-user hit-testing/navigation. It respects the engine's
existing hit-test setting, including PIE, without changing it. Missing/zero
player geometry stays empty; it never falls back to covering all players.

Code `bcfb1403289416aa6a6a3a9df61c1793aa2d3053` changes only the three private
presentation files `DaedalusDesktopArcade.cpp`, `SDaedalusDesktopArcade.cpp` and
`SDaedalusDesktopArcade.h`. Team-codex explicitly transferred this modal fix.
Close and EndPlay remove the same foreground host; pause/cursor/focus, ordered
input, saves, core rules, IDs, art, Hero/Sky/HUD code and Minesweeper are unchanged.
No reflected declarations or UObject layout changed.

[The bounded three-file patch](desktop-games-hud-foreground.patch) passes
`git apply --check` and application against owned copies of the exact installed
baseline; all three after-hashes match. Use explicit
`git -c core.autocrlf=false -c core.eol=lf apply` for the raw LF pins. The first
staging probe caught global Git CRLF conversion, and a fresh LF stage passed.
The unchanged portable core/Driver regression rerun passed123/123. **Those
portable checks do not compile the new UE wrapper.** Independent source review
passed against installed engine APIs; build/load and post-patch pixels remain
pending with the sole operator. No installed source, DLL, editor, map or save was
changed by this source lane.

[Install packet v7](desktop-games-polish-install.json) contains exact before/
after/source/patch hashes, the pre-fix native checkpoint/images and safe staging
instructions. Apply only these hunks after a fresh baseline check; preserve other
integrated source. Only `codex-play-guard` performs serial module build/load and
native acceptance. Repeat the three captured states, verify HUD occlusion while
open and reappearance after close, then check reopen/Escape/focus/EndPlay, input
and save behavior, resize/DPI and local-user bounds. No corrected-pixel claim is
made until that operator recheck succeeds.

## Display names and identity checkpoint, 2026-10-15

The user described the old franchise names as quick references to mechanics,
asked for identities of their own, and then explicitly requested keeping generic
names and any names with established reuse permission. The result is seven
display renames and four generic titles retained. Their implementation, gameplay,
visual aesthetic, IDs and saves are preserved. The player-facing collection is
[The Daedalus arcade](DESKTOP-ARCADE.md); it contains current names and identities
without the historical franchise labels.

This table is technical provenance for the naming decision, not player branding:

| Historical title | Current display title | Stable ID | Decision |
|---|---|---|---|
| Pong | Twinwake Volley | `pong` | Renamed |
| Dungeon Prototype | Dungeon Prototype | `dungeon` | Generic title retained |
| Asteroids | Driftstone Patrol | `asteroids` | Renamed |
| Football / Soccer | Football / Soccer | `football` | Generic title retained |
| Pac-Man | Glowtrail Chase | `pacman` | Renamed |
| Sega Space Shooter | Riftwing Vanguard | `sega_shooter` | Renamed |
| Shadow Ninja | Shadow Ninja | `shadow_ninja` | Generic title retained |
| Star Shooter | Star Shooter | `star_shooter` | Generic title retained |
| Super Dodge Ball Tournament | Courtyard Clash | `dodge_ball` | Renamed |
| CONTRA | Ironwake Advance | `contra` | Renamed |
| Zelda / A Link to the Past | Lanternwild Quest | `zelda` | Renamed |

Permission evidence: the repository's [MIT notice](../LICENSE) is retained,
including its copyright and conditions. The eleven canonical Python files in
[the unchanged original-source inventory](desktop-games-sources.json) contain
no license, project URL or naming/trademark grant; no original-project branding
policy was found in the assessed adjacent files. This is a bounded absence
finding, not a determination of infringement. The MIT notice is not treated as
permission to reuse third-party branding. [Atari's official page](https://atari.com/pages/about)
identifies Pong and Asteroids as branded games. No title was retained on the
assumption that public or open-source code automatically permits its name.
No availability, trademark clearance or legal approval is asserted for the new
names or the retained descriptive titles.

Code `4c1c2aa62f681a3ed8d947df9f5c20cedfe0c585` changes catalog titles and
descriptions, visible title/HUD/status labels, and Slate help. The adventure's
local pickup now says **Trinket/Trinkets**, with internal counters unchanged and
no new Daedalus inventory or currency. The registry/Slate label regions were
explicitly transferred by team-codex; actor header/implementation needed no edit.
Factory keys, source filenames/classes, save formats/paths, input transitions,
original Python, licenses/SPDX and PR139 Minesweeper additions remain intact.

The focused portable registry check passed **123/123** after compiling all game
core headers and Driver with MSVC `/W4 /WX`. It checks the exact stable ID set
and retired-brand absence in catalog descriptions and initial/title/active-result
frame/status strings. The prior seven-suite receipt below remains attached to
its original source commit. Current names, hashes, proof scopes and the retained
earlier receipt are in [install packet v6](desktop-games-polish-install.json).
Unreal/native text fit, cabinet readback and physical-controller acceptance remain
unverified; only `codex-play-guard` operates Unreal.

Content concerns are separate: the existing procedural yellow mouth wedge,
colored pursuers and maze arrangement, and the green pointed-cap sword/shield
character with diamond pickups remain unchanged in `DaedalusDesktopMazeCore.h`.
Their design provenance remains unverified. No imported minigame sprite/model
or implemented audio playback was found in this bounded core/arcade audit.
Renaming does not resolve art, map, character or sound permissions. Those remain
explicit follow-up concerns while preserving the user's existing aesthetic.

## Previous checkpoint: source gap closed and portable checks passed, 2026-10-15

Code commit `fe6d0ec6f6fb19671f244cdaca73c707b2bb3630` closes the confirmed
Contra title/input gap and corrects Shadow Ninja's catalog controls. All seven
portable C++ suites pass serially with MSVC 19.44.35229.0, C++17, `/W4 /WX
/permissive-`: 394,774 reported assertions, including 162 new polish checks,
78 Driver/registry checks and the existing pinned-source fixtures/replays. Python
originals and fixtures were not changed; Python oracles were not rerun.
The initial maze failure was its old 280-pixel Dungeon frame expectation; it now
checks the documented 344-pixel frame including the 64-pixel objective footer.
The final complete CTest run passed 7/7 in 10.75 seconds.

This verifies portable game cores and Driver. **This revision's Unreal actor,
Slate, UHT/module compilation, native load, visible Hero Use, rendering/focus,
physical-controller Play, game feel and E2E acceptance remain unverified.**
The exact commands, source/test/binary pins, results and limitations are recorded
in [the version 5 install packet](desktop-games-polish-install.json).

Team-codex explicitly transferred only the Contra input seam and Shadow controls
changes in `DaedalusDesktopGameTypes.h`, `DaedalusDesktopGameRegistry.h`,
`DaedalusDesktopArcade.h/.cpp` and `SDaedalusDesktopArcade.cpp`. Comparison with
PR139 source `0582c27a7fe3ad1f92da836f087efface618a8b6` found four identical
shared files; the registry differs only by PR139's Minesweeper include/catalog/
factory additions. Those additions were not copied or duplicated and must be
retained when integrating both PRs. Minesweeper remains team-codex's lane.

Contra now opens a frozen source title through `Driver::Select -> EnterTitle`.
Each non-repeat keyboard keydown goes through Slate -> actor -> Driver ->
`SourceKeyDown` immediately, before held input mapping. The literal arrow/B/A
sequence sets 30 lives; final keyboard A stays on the title. Enter/Space starts
with those lives. Separate `SourceControllerButton` dispatch lets controller A
start while preserving an unfinished keyboard sequence; controller events never
advance or reset that sequence. A/Start retries terminal results; Start otherwise
keeps generic pause. Transitions discard old pending semantic edges, then Slate
rebuilds held controls. Sticky raw mode prevents duplicate cheat submission.
Terminal Space does not retry; W is a movement/jump alias, not a title start.
Direct core Reset/host Restart still starts a standard run, and terminal retries
retain the native two-enemy initializer; both are documented host adaptations.

The bounded source audit found no additional missing Python gameplay capability
in the claimed core headers. Java original-app gaps remain in their separate
PR152 map. Star's existing five-second failed-save retry is implemented; native
failure/recovery and process-loss durability remain unverified. New shooter
polish checks use real seeded sessions; exact private-container saturation is
not forced. Characters, audio and new online/profile/reward features require
their own scope. Only `codex-play-guard` operates Unreal.

## Historical native polish cycle 4: remaining six games — source only

Claims hub 31229/31230 cover `ContraGame`, `DodgeBallGame`, `ZeldaGame` and the
three shooter classes in their existing core headers, plus the existing family
notes and install packet. The batch resumes from published PR157 checkpoint
`81ffdd840aa75c5b67fed81609d398b08295d120`. All six original Python SHA256 pins
were rechecked unchanged. The earlier five passes, shared helpers, original
files/fixtures, registry/actor/Slate, Java PR152 and team-codex's PR139 remain
preserved. Work interrupted by capacity limits was reconciled before resuming.

All eleven native game families now have a bounded source polish pass. This
means **source implemented and reviewed**, with full-app completion, compilation,
tests, native load, controller/Play/game-feel and E2E acceptance still pending.
No editor, game/oracle execution, build or test ran in this batch. No new game,
character asset, audio, reward, profile save or multiplayer service is introduced.

| Game | Concrete source change | Preserved rules and exact limitations |
|---|---|---|
| Contra | Current-position distance bar/finish marker; remaining pixels; boss HP; spread/rapid pickup effects and timers; shot-cap/cooldown, jump/crouch and protection feedback; actual controls/result/replay; direct Pad merge | Victory remains strictly `X>2800` without a boss prerequisite. Held jump/fire, in-play cheat +5/600-step spread, 900-step spread pickups and rapid-until-reset remain. Title-screen 30-lives binding is still a separate gap. No checkpoint or persistent progress added. |
| Dodge Ball | Country stats/super traits, numbered rosters and HP/alive totals; possession/flight/throw/charge/jump readiness; exact catch/control hints; four-round match-win/result/continuation feedback | All three living humans share movement/jump. Hat movement does not charge; only keyboard Up/W or original stick up does. Super is strictly `Charge>30`; effective catch ranges are `<22` normal, `<18` super and `<34` airborne. Held A/Space/Z/J can catch/rethrow; X/RB is fresh throw only. No bracket or new rules. |
| Asteroids | Rock/UFO counts, shot-cap/cooldown and protection timer/halo; wave-clear objective; final score/wave and host replay | Independent hat input remains additive with keyboard/stick. Ship physics, wrapping, splitting, UFO behavior and existing 60-step native protection remain. This pass adds no respawn rule or timer. |
| Sega Shooter | Labelled power/speed/life pickups and caps, actual shot mode, enemies/pickups/protection, boss-score distance/20 HP, combined result/replay, direct Pad merge | 1500-point boss threshold, power/speed/life caps 3/8/5, six-step fire, source physics and prior boss repair remain. Fire still reserves three bullet slots even for weaker modes. Unused shot timers do not become enemy bullets. |
| Zelda | Remaining roster/key objective, KEY label, Moblin HP, sword readiness/hurt timer, distinct result/fresh replay and direct Pad merge | Sword still hits before movement/facing update; cooldown 18, hurt timer 45, scores/drop RNG, prior key repair and death-before-win remain. The shield is decorative. No new shield, enemy or inventory mechanic. |
| Star Shooter | Wave-shift countdown, enemy/pickup counts, twin/triple/shot-cap readiness, shield/protection, boss health/state/phase, controls/pause confirmation/result/replay and direct Pad movement | `1200-WaveTimer` predicts a wave shift, not an exact boss arrival. Difficulty, boss thresholds/patterns and source powers remain. DGS1/save/restore/snapshot/resume/options/request and pause timing blocks are unchanged; existing host failed-save retry code remains unchanged and its current-head acceptance is pending. |

This batch derives feedback from existing state. No new authoritative timers,
health, scores, AI, spawn, damage, balance or RNG calls are added. Direct Pad support
for Contra/Zelda/Sega/Star mirrors the existing Slate merge; each keeps its own
keyboard/stick precedence. Asteroids and Dodge retain their independent hat rules.
Protection labels report the current source-style timer: at 1 it expires before
the next **live** collision pass. Paused Star steps do not tick it. These labels
do not copy Pac-Man's separately designed 90-subsequent-step grace policy.

Independent read-only review found and corrected one Contra presentation issue:
an initial HUD overlapped the source's reachable upper-platform jump. The top
panel now ends at Y=98, with readiness/controls in Y=526..594 below ground Y=520;
source field/collision geometry is unchanged. Actual font fit, rendering and game
feel remain unmeasured. Source review also verified unchanged simulation blocks,
shared/peer sections and Star persistence/pause contracts; it is not a compiler.

The existing `CreateGame -> Driver -> Arcade frame/state -> Slate` bindings carry
all eleven passes. The current feature/interface/UI/gap/evidence table below and
[exact install/deferred-validation packet](desktop-games-polish-install.json)
remain canonical for this delivery. The separate
[full original-app map](https://github.com/RicheyWorks/Daedalus2/blob/89ece41824b9132403ac0bfffae15343b08b13f8/docs/java-arcade/capability-coverage.md)
continues to track source/host gaps beyond polish. Next work is owner-scoped gap
integration and separately authorized validation, not a claim of eleven installed
or accepted games. Only `codex-play-guard` operates Unreal.

## Native polish cycle 3 checkpoint: Football — source only, 2026-10-14

Exact continuation claims: hub 31211/31212. Only `FootballGame` in
`DesktopGames/DaedalusDesktopSportsCore.h` changes, plus these existing canonical
notes and the install packet. The pinned original `football_pygame_ce.py` SHA256
`7b013f8151aa1c815ba0947c2d5d39cf559467106cde60aacca29df936ca3ebe` was read and
verified unchanged. The shared sports helpers and entire Dodge Ball game remain
unchanged, as do the prior Dungeon/Pong/Pac-Man/Shadow Ninja passes and other
owners' actor/registry/Slate, Minesweeper and Java files.

Before: a goal resets positions immediately with no scorer receipt, kick presses
have no acceptance/cooldown cue, and direct core Pad fields are ignored unless a
host first merges them. After: a 90-step goal receipt highlights the scored goal
and names the scorer while play continues. A 12-step accepted/ignored kick receipt
and player ring complement the actual cooldown/ready label. DEFEND/ATTACK goal
labels, mapped controls, any-distance kick explanation, a darker score strip and
distinct result/fresh replay instructions improve the existing presentation.

These counters are **cosmetic only**. A goal includes its event frame plus 89
subsequent live frames; a kick receipt includes its event frame plus 11. Each
freezes at a terminal result and clears on Reset/fresh match. No
kickoff hold, blocked movement or extra match time is added. Goals still reset
ball/positions immediately, retain player cooldowns and consume that frame's
time. Goal reset clears a stale kick receipt, not its gameplay cooldown.
The confirming Fire/Action starts/replays without kicking on the same step.
Kick still happens before movement/cooldown decrement, so an accepted press sets
12 then normally displays 11 that frame. Contact deflection can overwrite the
same step's kick velocity; an accepted receipt promises neither trajectory nor
possession. Source remote kicks, CPU pursuit, strict goal/deflection boundaries,
speeds/friction/bounces and floating 90-second clock are retained, including its
possible extra final step and truncated 89-second initial HUD reading.

Direct Pad directions now OR locally into the human's keyboard flags, matching
the existing Slate merge. Right/down precedence, unnormalized diagonals and stick
override beyond 0.2 on either axis remain. This direct Pad support is a native
adapter enhancement; the Python source has no hat input. Shared sports helpers,
Dodge Ball's independent hat semantics and all host mappings remain unchanged.
Fresh Fire/Action after the result starts play immediately; host R/Restart uses
the existing Reset and returns Football to its title.

`CreateGame("football")`, `Driver::Advance/Refresh/GetStatus`, Arcade
`GetArcadeFrame/GetState` and Slate `OnPaint/StatusText/PushInput/Restart` already
carry this pass. No replacement adapter or service is required. Read-only source
review and source pin/whitespace inspection are the current evidence;
**compilation, tests, CI, native connection, controller, Play and game-feel
validation remain deferred/unverified**. Historical sports parity/build receipts
below do not validate this revision. Exact hashes, installation settings and
deferred boundary/visual observations are in
[the existing source packet](desktop-games-polish-install.json).

No player mesh, Blender asset, audio, profile save, multiplayer, reward or new game
ID is introduced. The bounded pass does not complete full original-app E2E
coverage. Contra was next queued at this checkpoint; cycle 4 above completes its
bounded source pass. Only `codex-play-guard` operates Unreal after separately authorized work.

## Native polish cycle 2 checkpoint — source only, 2026-10-14

Continuation claims: hub 31185/31186; scope/PR139 acknowledgment 31193. This pass
uses the actual existing `Game::Reset/Step/Render/GetStatus` interface and catalog
IDs `pacman` and `shadow_ninja`. The original Python files, cycle 1 Dungeon/Pong,
Zelda, Contra, player helpers, actor/registry/Slate and PR139 remain preserved.
There is no Sonic game in the assessed eleven-family catalog.

**Uncompiled and untested.** No current build, connection, native play, controller
feel or end-to-end acceptance is claimed. This source pass does not complete the
full original-app integration backlog. The existing
[PR152 capability map](https://github.com/RicheyWorks/Daedalus2/blob/89ece418/docs/java-arcade/capability-coverage.md)
continues to track all eleven native families and Java Sudoku/Blackjack gaps.

### Pac-Man: protect and explain the respawn

Before: a nonterminal death resets only the hero, leaving ghosts live; another
ghost can take the next life on the next fixed step. After: each nonterminal death
starts an explicit **90 subsequent live-step lethal-collision guard** (nominal
1.5 seconds at 60 Hz), with a visible cyan halo and remaining-step label. This is
a new native gameplay rule, not cosmetic immunity or unchanged Python parity.
The initial run and terminal death receive no grace. A snapshot before timer decrement
protects the 90th subsequent collision step; the 91st is vulnerable. Reset clears
the counter, and terminal steps freeze it until a fresh replay/reset.

Only unfrightened ghost life loss is guarded. Hero movement, ghost updates and
random-call ordering, pellets, 300-step fright, frightened captures, scores,
all-dead ghost revival and loss-before-win ordering remain unchanged. The HUD and
`Status` now report remaining collectibles and power pellets. Terminal feedback
names the existing fresh Action/Fire/Jump retry and host R/Restart. No new score,
ghost AI, tunnel, persistence or realm reward is introduced.

### Shadow Ninja: show the existing strike and action readiness

Before: the boss's periodic strike is invisible until damage. After: the last
12 timer steps show a countdown and outlined **current** rectangular reach.
The source moves the boss before its strict `abs(dx)<300 && abs(dy)<100` check;
the outline therefore reports current reach, not a predicted safe zone. Ordinary
boss contact and enemies can still hurt. The first strike remains at 40 steps,
then every 50; damage remains one health with 60-step invincibility when eligible.
Named constants and a read-only range helper replace identical literals.

An eight-step "pulse fired" receipt follows every existing instant pulse, including
a miss or protected player. It does not assert a hit or keep damage active. Jump,
air-jump/wall-jump, spin/ground requirement and shared sword/star cooldown/cap
readiness are derived from existing player/attack state. Boss-entry score progress
and a host R/Restart terminal hint use the original 1,200 threshold and host API.
No damage, timing, movement, RNG, spawn, score, level or attack-input rule changes.
No replacement character, Blender asset or audio work is included.

## Current existing-interface coverage and remaining evidence

Rule-check receipts in this table remain pinned to the previous fe6d0ec6 checkpoint. The display-only 4c1c2aa6 revision has the focused123-check receipt above; prior full-suite results are not transferred to a new binary.

The paths below are relative to
`engines/unreal/DaedalusLink/Source/DaedalusLink/`. All bindings already exist:
`Public/DesktopGames/DaedalusDesktopGameRegistry.h::CreateGame` selects the core,
`Driver::Advance` calls bounded fixed `Step` updates and refreshes `Render`,
`Private/DaedalusDesktopArcade.cpp::GetState` exposes `Status`, and
`Private/SDaedalusDesktopArcade.cpp` paints frame commands and routes input/restart.
No new adapter is proposed or required for these eleven feedback passes.

| Implemented feature | Exact core interface/source path | Existing Daedalus UI/service binding | Missing code or scope | End-to-end evidence |
|---|---|---|---|---|
| Dungeon ordered lanterns, exit, completion/replay | `Public/DesktopGames/DaedalusDesktopMazeCore.h::DungeonGame::Step/Render/GetStatus` | Catalog `dungeon`; frame/footer and actor status; existing Action/R reset | No server quest/reward or durable run save; those are separate scope | Portable checks pass, including all six reachable routes/completion/reset; native Hero Use/route/replay pending |
| Twinwake Volley point preparation, early serve, rally/contact cues | `Public/DesktopGames/DaedalusDesktopPongCore.h::PongGame::Step/Render/GetStatus` | Catalog `pong`; existing digital/analog/hat actions and frame | No match-win rule or persistence added | Portable serve45/early edge/rally checks pass; physical controller/native rendering pending |
| Glowtrail Chase lethal respawn guard, dot/power counts, fresh retry | `Public/DesktopGames/DaedalusDesktopMazeCore.h::PacmanGame::Step/Render/GetStatus/RespawnFramesRemaining` | Catalog `pacman`; existing merged hat/stick input, terminal press edges and host R/Restart | No profile/save/inventory backend for this source game; no new adapter | Portable90/91, fright capture, reset/terminal checks pass; native play pending |
| Shadow Ninja periodic strike/readiness feedback | `Public/DesktopGames/DaedalusDesktopPlatformersCore.h::platformers::NinjaBoss::Update/IsTelegraphing/InStrikeRange`; `ShadowNinjaGame::Step/Render/GetStatus` | Catalog `shadow_ninja`; corrected B/X sword, Y/RB star, LB spin hint; separate hat/axes and host R | No character mesh/audio/progression invented; source level remains 1 | Portable timer/receipt/invincibility/terminal checks pass; native readability pending |
| Football scorer/kick receipts, ready/cooldown and direct Pad control | `Public/DesktopGames/DaedalusDesktopSportsCore.h::FootballGame::MovePlayer/Step/Render/GetStatus/IsKickReady` | Catalog `football`; existing merged hat/axes, Fire/Action edges, Frame/Note and host R/Restart | No new physics, timed kickoff pause, possession, save/network/reward or service added | Portable cue lifetimes, immediate goal reset/cooldown/clock/replay checks pass; native readability pending |
| Ironwake Advance title30, ordered keyboard/controller dispatch, distance/weapon/readiness/protection and direct Pad | `Public/DesktopGames/DaedalusDesktopPlatformersCore.h::ContraGame::EnterTitle/SourceKeyDown/SourceControllerButton/Step/Render/GetStatus` | Catalog `contra`; Game virtuals -> Driver dispatch/Refresh -> actor SubmitArcadeSourceKey/SubmitArcadeSourceControllerButton -> Slate OnKeyDown before held mapping | Confirmed title gap source-closed; no durable checkpoint/profile/rewards | Portable title freeze, finalA/30/start, prefix/controller/retry, pending-edge cleanup, strict finish and spread/cap checks pass; Unreal host and native input/layout pending |
| Dodge roster/country/throw/catch/round feedback | `Public/DesktopGames/DaedalusDesktopSportsCore.h::DodgeBallGame::Render/GetStatus/LivingPlayers/IsHumanThrowReady/HumanCatchRadius` | Catalog `dodge_ball`; existing separate hat/axes, held catch/rethrow versus fresh throw, round confirm | No new bracket, teammate switch or persistence | Portable charge30/31, hat behavior, catch/rethrow and round4 checks pass; native readability pending |
| Driftstone Patrol wave/rock/UFO/protection/fire feedback | `Public/DesktopGames/DaedalusDesktopShootersCore.h::AsteroidsGame::Render/GetStatus/IsFireReady/GetProtectionFrames` | Catalog `asteroids`; existing independent hat fields, held fire and host restart | No new physics, respawn rule, profile or asset binding | Portable seeded loss/protection/fire/bounded replay checks pass; new checks do not force private saturation; native view pending |
| Riftwing Vanguard pickup/shot/boss/protection feedback and direct Pad | `Public/DesktopGames/DaedalusDesktopShootersCore.h::SegaShooterGame::Player::Update`; `SegaShooterGame::Render/GetStatus/IsFireReady/GetBossHealth` | Catalog `sega_shooter`; existing merged movement/held fire and host restart | No enemy bullets invented; no new save/network/service | Portable source fixtures, direct Pad/cooldown/protection and seeded winning bot pass; native view pending |
| Lanternwild Quest roster/key/sword/hurt feedback and direct Pad | `Public/DesktopGames/DaedalusDesktopMazeCore.h::ZeldaGame::Player::Update`; `ZeldaGame::Render/GetStatus/LivingEnemyCount/HasGroundKey/IsSwordReady` | Catalog `zelda`; existing merged movement and fresh sword/retry edges | Decorative shield stays decorative; no new inventory or service | Portable old-facing sword, key/win/replay, cooldown/grace/death checks pass; native view pending |
| Star wave/shot/boss/shield/pause/result feedback and direct Pad | `Public/DesktopGames/DaedalusDesktopShootersCore.h::StarShooterGame::Player::Update`; `StarShooterGame::Render/GetStatus/GetWaveFramesRemaining/IsFireReady` | Catalog `star_shooter`; existing difficulty, core pause/menu, DGS1 and actor persistence/top-ten contracts | Host retry is implemented in `ADaedalusDesktopArcade::ProcessSourceRequests`; native failure/recovery acceptance pending; no process-loss durability claim | Portable wave1200/boss, paused freeze, save/quit flags, restore atomicity and replay checks pass; host disk/native view pending |

Later authorized validation must distinguish source, committed, connected, native
and accepted stages. Exact commit/blobs/SHA256 and pending operator observations
are in [the existing install packet](desktop-games-polish-install.json). Only
`codex-play-guard` operates Unreal. Legacy oracle/build receipts below apply to
their historical source pins and do not prove this pass.

## Native polish cycle 1 checkpoint — source only, 2026-10-14

Dedicated owner: `pootscoot-desktop-games`, exact claims hub 31121/31122.
User direction is to iterate and polish **each existing game** in bounded code
passes. This first batch starts with Dungeon's missing gameplay loop, then Pong's
missing between-point transition. It creates no new game ID. PR152 `89ece418`
remains a separate Java-backed source delivery; PR139 `0582c27a` and its
Minesweeper/registry/Desktop actor/Slate ownership remain untouched.

**Uncompiled and untested.** Dedicated tests/builds/CI are deferred. No live
game-feel, controller, readability or native acceptance is claimed. Source starts
from main `34dfe8340da967392930504d42a8185705449384`; original Python revisions
and previous evidence remain pinned. The [exact install packet](desktop-games-polish-install.json)
is source-only for sole Unreal operator `codex-play-guard`, after separately
authorized adoption/build/load. No source worker edits the shared editor.

### Dungeon: Threadlight Passage

The original `PythonGames/main.py` supplies a seven-row room, a green square
player and wall movement. It has no enemies, score, quest or victory. That room
is retained as a compact **local Labyrinth wayfinding exercise**. The established
[Broken Survey](realms/LABYRINTH-BUILDOUT.md) uses thread, chalk and the Lantern
Keeper's sheltered route cues; this chapter borrows that wayfinding theme without
claiming an NPC, realm quest, inventory grant or new cause of the shattering.

Before: walk/reset only, status never ends. After: find the lantern marked NEXT,
light three numbered lanterns in the seed's order, then approach and light the
unsealed EXIT. Wrong order gives a bounded hint and loses no progress. Completion
freezes the local run until a deliberate Action/reset; a held interaction cannot
replay it. Score stays zero and lives stay one. These are **new native design
rules**, not a claim about the Python source or server rewards.

Architecture: only `DesktopGames/DaedalusDesktopMazeCore.h::DungeonGame` changes.
The original map, ragged-row/boundary collision, start `(80,80)`, 40px body and
5px digital movement remain. Direct Pad fields now work without synthetic
keyboard input; Slate's existing hat mapping stays unchanged. Fresh Fire/Jump
edges interact (`J/Z/X/Ctrl/RB` or `Space`, pad X/A); existing Action (`K/C/Enter`,
pad B) resets, and host `R` still restarts. No registry, actor, Slate or shared
input rewrite is required. At this cycle 1 checkpoint, Pac-Man and Zelda sections
in the shared header were unchanged; cycle 2 above changes only Pac-Man.

Three fixed reachable centres are `(140,60)`, `(660,140)`, `(380,220)`, with exit
`(60,220)`. `seed % 6` selects permutations `012,021,102,120,201,210`. Seed 0
therefore follows Hall → Watch → Root → EXIT; reset retains that seed/order.
The player must be within 32px of a target centre. The clock starts on movement
or an interaction attempt, advances only active fixed steps, freezes on completion
and resets on replay. Live hints last 90 steps; the terminal cue remains until
reset. Numbers plus NEXT/LIT/EXIT give non-colour cues. The room remains 800×280;
a 64px footer carries objective/control feedback. No bitmap/Blender assets are
created; the existing procedural renderer supplies the presentation.

### Pong: read the point, prepare the next rally

Before: a point instantly re-centres the ball and the next frame resumes play,
with no contact/rally/point cue. After: points preserve source scoring but hold
the centred ball for 45 fixed steps (nominal 0.75s), while paddles remain live.
A fresh Fire/Jump/Action press serves early; the ball launches on the following
step. Contact/scorer flashes, current/best rally counts and a ready cue make state
changes visible. Paddle positions remain within the playfield, including the CPU.

Architecture: `DesktopGames/DaedalusDesktopPongCore.h` only. Preserve 800×600,
100px paddles, source keyboard 6/analog 8 with 0.2 deadzone, sequential CPU tests
at speed 4, ball velocity 5/3, collision windows and endless scoring. The initial
rally remains immediate. After a point, horizontal direction remains +5 for a
CPU point and -5 for a player point; inherited vertical velocity is retained.
Direct D-pad up/down behaves as digital paddle input. Saturating current/best
rally counters count paddle returns, not wall bounces or rewards. Contact cues
last 8 steps and point cues 90; these are design constants, not measured game-feel
results. Reset clears them. New HUD commands appear only after play events, so the
original six-command reset frame is preserved. Subsequent timing/visuals deliberately
differ from the old source; historical oracle passes do not validate this code.

### Per-game polish queue and coverage

Every pass tracks controls/controller, difficulty/progression, feedback, visuals,
state transitions and replayability. Complete a bounded source pass, preserve its
checkpoint, then take the next row. Do not turn the queue into an arbitrary new
game or an endless documentation pass. Native gameplay proof is a separate stage.

| Order / game | Code-supported next increment | Identity/rules to retain | Current stage / remaining validation |
|---|---|---|---|
| 1 Dungeon | Lantern objective/input/completion/replay, above | Original room, movement, reset; new goal explicitly native | Portable six-route/completion/reset checks pass; native Play pending |
| 2 Twinwake Volley | Serve/rally/contact feedback, above | Endless source scores, speeds/collision, immediate opening | Portable timing/rally checks pass; physical-controller/rendering Play pending |
| 3 Glowtrail Chase | 90-step lethal respawn guard, remaining-dot/power feedback, fresh retry | Map, speeds, ghosts, scores and win rules; guard explicitly new native rule | Portable90/91, reset/capture checks pass; native Play pending |
| 4 Shadow Ninja | Telegraph existing boss attack; jump/spin/attack readiness and pulse receipt | Existing attack timing/damage and platform movement | Portable timer/receipt/damage checks pass; native readability pending |
| 5 Football | Live scorer/kick receipts, actual readiness, direct Pad and result/replay cues | Immediate source resets, remote kicks, cooldown, physics and floating 90-second match | Portable cue/Pad/clock/result checks pass; native Play pending |
| 6 Ironwake Advance | Distance/weapon/pickup/readiness/control/replay feedback | Source distance victory, held-jump behavior, cheat distinctions | Title/raw-key/controller seam source-closed; portable checks pass; native validation pending |
| 7 Courtyard Clash | Country/roster/round and throw/catch/charge/jump feedback | Simultaneous trio control and held rethrow | Portable charge/catch/round checks pass; no bracket/persistence claim; native validation pending |
| 8 Driftstone Patrol | Wave/rock/UFO/protection/fire and run feedback | Wrap/inertia, progressive rocks/lives and independent hats | Portable suites pass; native validation pending |
| 9 Riftwing Vanguard | Boss/pickup/shot/protection/terminal feedback | Source powers/boss victory; unused timers are not enemy bullets | Portable suites pass; native validation pending |
| 10 Lanternwild Quest | Roster/key/sword/hurt/win and retry feedback | Source key goal and decorative shield | Portable suites pass; native validation pending |
| 11 Star Shooter | Wave/boss/shot/shield/pause/reset readability | Existing difficulty, patterns, save/top-ten ownership | Portable save/quit/restore checks pass; host retry/native acceptance pending |
| Java Sudoku | Existing API/native capability gaps in PR152 map | Java rules/clock/score/account/inventory authority | Separate C++ integration lane; no rule port |
| Java Blackjack | PR152 settings/full visible metadata checkpoint | Java rules, revisions, simulated credits and hidden-state boundary | Draft source `89ece418`; no current connection/native/E2E |
| Minesweeper | Existing owner's menu/persistence/feedback follow-up | PR139 original game distinct from PR49 Java-rule pilot | Owned by team-codex; no edits in this cycle |

The [full existing-app capability map](https://github.com/RicheyWorks/Daedalus2/blob/89ece418/docs/java-arcade/capability-coverage.md)
remains canonical for facade/original-app gaps. Eleven C++ source ports plus two
Java clients are not thirteen installed or fully accepted games.

### Handoff, observations and lessons

Concrete observations: Dungeon had no terminal loop; Pong had no serve phase.
Both now have source state/feedback implementations. No duration, frame-rate,
game-feel win, controller result or render screenshot was measured. The first
isolated branch switch needed a missing promisor blob; a normal authenticated
retry materialized main. Published PR152 and the shared checkout were preserved.

Reproduction for later authorized operator work: verify packet hashes/build
source, stage or reuse an approved `ADaedalusDesktopArcade` with `InitialGameId`
`dungeon` and seed 0, normal Hero Use, and the Hall/Watch/Root/EXIT route. Observe
out-of-order refusal, fresh interaction, completion/frozen movement and deliberate
reset, then compare seed 1. Switch to `pong` through the existing catalog and
observe a point's 45-step preparation/early serve, controllable paddles and rally
cues. Record exact binary/source/map/actor/input observations. Do not run that
acceptance while tests/builds/Play remain deferred.

Actionable host lesson: portable feedback can travel through the existing
`Status`/`Frame` contract without taking another owner's registry/Slate files.
Future validation should compare state transitions and frame/timer behavior, not
only old draw-command counts. Preserve the immutable source baseline separately
from deliberate polish extensions. Character upgrades, asset import, networking,
durable replay/progress saves and server quest/inventory integration remain open.

## Historical source delivery and recovery evidence

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

Star persistence is scoped to `Saved/DaedalusDesktopGames`: validated `DGS1` run state and
`DGL1` top-ten score/wave/difficulty records. Leaderboard writes reload/merge fresh records;
failed or malformed reads are refused. Failed run writes retain the pending payload, retry at
five-second intervals while advancing and block session replacements until success. Close/reopen
preserves the pending request, but RAM cannot survive actor EndPlay/process loss when the OS
refuses writing. New/restarted native runs deliberately retain the previous saved run; the Python
new-game path deletes it. The port never reads or overwrites the Python originals' home save files.
Per-game controls/features and intentional repairs are documented with each test family.

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

Twinwake Volley is the smallest useful playable pilot: one arena, two paddles, a ball, score and controller
input, with no character rig or external asset dependency. It proves cabinet interaction,
input isolation, frame presentation and exit cleanup before character-heavy games are accepted.
The other native cores are available in the same catalog, but every game still needs live
acceptance against its latest-specific actions and repaired source defects.

| Work | Relative remaining effort | Evidence / dependency |
| --- | --- | --- |
| Twinwake Volley cabinet pilot | Smallest | Core source parity; cabinet placement and live input/exit acceptance remain |
| Dungeon Prototype, Driftstone Patrol, Football / Soccer | Small to medium | Procedural geometry and compact rules; no imported source meshes |
| Glowtrail Chase, Lanternwild Quest, Riftwing Vanguard, Courtyard Clash | Medium | Map/collision or boss/tournament paths and game-specific controls |
| Ironwake Advance, Shadow Ninja, Star Shooter | Larger | Compound actions, bosses, animation needs; Star settings/save/menu/leaderboard |
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
