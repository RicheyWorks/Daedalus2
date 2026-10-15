# Arcade capability coverage — source checkpoint, 2026-10-15

## Current continuation: session identity, recovery and inspection

Source `6e28706693319c53170dda3d545c12f8cf5f95c7` continues published `c0cacb261a960ea71de239f644be4db4f91310fb` in the same two private Java
Slate files (+207/-8), assigned32249/started32308. Existing received-ID display
is clarified as current/last received identity, separate from entered/requested
text. Use current ID only fills and focuses the local field. No Sudoku board
revision exists in the projected native state; only Blackjack shows one.

Existing RefreshSnapshot/RetryBlackjackCreate and Start/Open/Resume methods now
have state-derived guidance, candidate gates and truthful bool-result feedback.
Private actor work may still refuse a public candidate; requested never means
received or successful. Fresh Blackjack Start after a definite refusal remains
available under its previous gate. Selected-cell inspection separates received
answers/clues/editability from local and received pencil marks and pending hints.
Actor/public API/transport/guard/protocol/build/saves/rules remain unchanged.

Independent manual source/branch review found no blocker. The exact matrix and
deferred acceptance are in [cabinet-source-package.md](cabinet-source-package.md),
with final file/hash/blob pins in manifestv5. No new counted static suite or
tests/builds/services/editor/native action ran. Earlier counts are historical;
current focus, layout, typing, recovery and persistence remain unverified. This
finite source package is complete; full original apps and native play remain open.

## Historical continuation: local Sudoku editing

Source `da2b4a84e357114181cbdb65093628d595cda2a7` completes the selected
local editing package in the same two private Slate files (+207/-20), preserving
the entire actor/public API/protocol/build source at prior head9fad7509. Shared
entry now routes pad/typed digits/erase either to view-local notes or the existing
Java move call. Per-cell overrides, including zero, retain notes across same-ID
snapshots and prevent erased notes from returning. Accepted UI New/Open/Resume,
successful Configure and close clear notes; they have no durable-save contract.

The board gains 3x3 notes, first-empty/wrapping selection, typed digits, tooltips,
clue/peer/same-digit/cosmetic duplicate colors, filled and remaining-digit counts.
Display calculations never determine legality/completion. Blackjack dispatch,
settings, metadata and hint confirmation remain unchanged. Original JavaFX and
web evidence, snapshot-mask adaptation, exact lifecycle limits and deferred cases
are in [cabinet-source-package.md](cabinet-source-package.md).

Source review and57 static checks pass,14 old Slate methods unchanged; no compiler,
behavioral tests, services, editor or native acceptance. Runtime stays behind
ingestion and the sole operator. The following prior package evidence stays pinned.

## Earlier bounded source package — c7b3f3e2

Source `c7b3f3e28f759b5408a69ff00f2fde025b3d650b` extends the same PR152,
preserving the mode code below and prior Blackjack bindings. The two Slate files
now expose existing Sudoku Open by ID, original Ctrl+Z/Y and row/column-end keys,
and H-key hint confirmation. The explicit Hint button retains its original
purchase behavior. Blackjack's supported original TableKeys actions and chips
use existing legality/submission APIs; disabled actions are consumed, and
insurance acceptance also requires the projected affordability flag. Shortcuts
require direct board/table focus and the opening local user, and exclude repeats,
controller events and editing modifiers. Escape keeps cabinet-close behavior.

Service status/message and hints remain visible alongside local validation errors;
Java's hint count and insurance decision prompt are shown. No actor, transport,
guard, protocol, persistence or rule implementation changes in this second
increment. Source review and 110 static checks pass, including 56 unchanged
baseline method bodies. This is not compiler, behavior or native proof.

The complete source-to-interface map, remaining boundaries and deferred install
checklist are in [cabinet-source-package.md](cabinet-source-package.md). All four
runtime files have final source pins in the existing integration manifest.

## Current iteration: existing Sudoku create modes

Code `4d5577dc5659a9a26a9130e70cef68c2e5915ece` continues the existing PR152
four-file actor/Slate lane. The cabinet previously hardcoded chaos, mirror and
timeAttack false despite Java supporting them. Three New Game checkboxes now
feed additive `StartSudokuGameWithModes`; request values are captured after
existing gates and before asynchronous bootstrap. The creation URL uses those
captures. Current-game text comes only from Java snapshot flags/timeLimitSeconds,
separate from next-game choices. Old `StartSudokuGame(int32)` defaults, open,
resume, saves, moves, guards and all prior Blackjack metadata/settings stay intact.

Pinned existing implementation: Sudoku973c73a3 Controller65–81,
ServerApi147–154 and GameService288–308. No new service/rules/clock is introduced.
Source review plus77 static checks passed, including61 unchanged method bodies.
No UHT/compiler, test, service, editor or native execution ran. The new reflected
method needs later generated-code/module integration; current native acceptance
and full original-app completion remain open. Ingestion keeps priority.

Owner reconciliation32159–32161 and four-region claim32167–32169 were sent;
no competing Java-client claim was found. Existing web DaedalusPad/1 at39fa5581
is not a Slate transport. This uses ordinary existing Slate checkbox/focus
interfaces; no controller adapter, mapping, database or native binding is added.
Later targeted Mines/HUD acceptance does not transfer to Sudoku/Blackjack.

The following earlier coverage remains scoped to its original source proof.

The target is the full implemented applications, with their actual rules and
existing interfaces preserved. A native cabinet, offline fixture or thin facade
is an intermediate delivery. This checkpoint closes existing Blackjack facade
presentation/command gaps; it **does not complete the original desktop app**.

**UNVERIFIED:** dedicated tests, builds and CI are deferred by user instruction.
No Java service, production traffic, credentials, editor operation, placement or
Play was performed. Only `codex-play-guard` operates Unreal. The operator packet is
[blackjack-capabilities.integration.json](blackjack-capabilities.integration.json).

## Traced source and registration

- Native starting source: Daedalus2 `7a93e62de7fe5fa193878bed250f28abe3a23f79`;
  PR51 and PR55 are merged. `DaedalusLink.uplugin` registers `DaedalusLink` as a
  Runtime module. `DaedalusLink.Build.cs` already supplies Slate, WebSockets and
  its direct-loopback libcurl dependencies. Neither file changes here.
- `ADaedalusJavaArcade : ADaedalusUsable` is the existing reflected actor.
  `ADaedalusHero::Interact` uses `ADaedalusUsable::Nearest` and `Use`. The Java
  actor mounts a standalone local-player Slate overlay and refuses network worlds.
  Class registration and hooks do not establish installation or world placement.
- Blackjack current main and unchanged core:
  [`1ec1801ac635e62945072974cbe8c78398a17849`](https://github.com/RicheyWorks/BlackJackPro/tree/1ec1801ac635e62945072974cbe8c78398a17849).
  Current main was independently read and matches this pin. The dirty Buff
  checkout is a separate source selection dependency and remains untouched.
- Existing additive facade: [BlackJackPro PR62](https://github.com/RicheyWorks/BlackJackPro/pull/62),
  head `8a4dccfbc359be628b5766ea1b7082410baefe1c`, still draft. Its application
  entry is `arcade-bridge/build.gradle.kts` → `BridgeMain.main`; `BridgeServer`
  registers `/v1/blackjack/health`, `/sessions`, session GET/DELETE and commands.
  It depends only on `:core`. `BridgeService` calls the unchanged `Engine`;
  `VisibleSnapshot` explicitly filters visible fields. No replacement adapter is
  added here. Existing contract: BlackJackPro `docs/BLACKJACK-ARCADE-BRIDGE.md`.
- Original Swing plugins use `PluginRegistry.loadAll` and
  `swing/src/main/resources/META-INF/services/com.richeyworks.blackjack.plugin.BlackJackPlugin`
  (`BuiltinPlugin`). Plugin discovery does not occur in the facade. The original
  GDX `GameSession`/`TableScreen` are independent presentation/lifecycle hosts.

In the tables, **B** is `arcade-bridge/src/main/java/com/richeyworks/blackjack/arcade/`,
**C** is `core/src/main/java/com/richeyworks/blackjack/`, **S** is
`swing/src/main/java/com/richeyworks/blackjack/`, **G** is
`gdx-core/src/main/java/com/richeyworks/blackjack/gdx/`, all in the pinned Blackjack
repository. **N** is `engines/unreal/DaedalusLink/Source/DaedalusLink/` here.

Evidence labels describe historical evidence only:

- **J:** prior 33 facade Java tests / 9,600 source-engine comparisons.
- **H:** prior 41 real disposable HTTP checks at Java source `a4d5987a`; they did
  not take insurance or run Unreal callbacks.
- **U:** prior 1,330 portable policy checks / composite 43-action DLL link, with
  its original 106-input source manifest. It is not a build of this checkpoint.
- **E0:** no current connected/native/end-to-end gameplay evidence reviewed.

## Existing Blackjack facade capabilities

All native bindings below use `N/Private/DaedalusJavaArcade.cpp` and
`N/Private/SDaedalusJavaArcade.cpp`; reflected presentation types are in
`N/Public/DaedalusJavaArcade.h`. New fields commit together only after complete
validation. Existing epoch/revision/one-operation gates and unknown-mutation
reconciliation remain unchanged. Controls do not decide outcomes or credits.

| Implemented app feature | Exact existing interface/source | Daedalus UI/service binding | Missing code / remaining boundary | End-to-end evidence |
|---|---|---|---|---|
| Authenticated health | `B/BridgeServer.route`, `GET /v1/blackjack/health` | No native health operation | Readiness probe still absent; this change does not edit Poot-owned transport | H; E0 |
| Local bearer | `B/BridgeMain.main`, `BridgeServer.authorized` | `ConfigureBlackjackToken`, masked secret field | No per-player account/provider authorization; one local bearer authorizes all sessions | H; E0 |
| Create / uncertain-create recovery | `B/BridgeService.create`, `POST /sessions` | `StartBlackjackSession`, `RetryBlackjackCreate`, candidate recovery guidance and actor bool feedback | Companion delivery/adoption pending; retained create ID is lost on local close | H, U; E0 |
| Current session read | `B/BridgeService.query`, `GET /sessions/{id}` | `RefreshSnapshot`, state-derived Refresh candidate and local-attempt feedback | No reconnect/open-by-existing-session-ID control | H; E0 |
| Chips 1/5/25/100/500 | `BridgeService.Session.apply("bet")`, `C/engine/Engine.canBet/addBet` | Five existing legality-gated buttons | No side-bet command in facade | H, J; E0 |
| Clear / rebet / deal | `Session.apply`, `Engine.clearBet/rebet/deal` | Existing `SubmitBlackjackAction` controls | Current native execution remains unverified | J, H subset; E0 |
| Hit / stand / double / split / surrender | `Session.apply`, `Engine.can*` and mutations | Existing gated controls; this checkpoint adds all visible hand flags | No local rules/payout calculation | J, H subset; E0 |
| Insurance / even money | `Session.apply("insurance")`, `Engine.canInsure/takeInsurance` | Existing accept/decline gates; **new** even-money label follows the Java natural-hand flag, plus insurance stake | Source even-money behavior stays in Java; current insurance execution unverified | J; H did not take insurance; E0 |
| Five Boolean rules | `Session.apply("setRule")`, `VisibleSnapshot.rules` | **New** bound controls for `dealerHitsSoft17`, `lateSurrender`, `offerInsurance`, `doubleAfterSplit`, `splitAcesOneCard` → existing `SetBlackjackRule` | Values update from accepted snapshots, not optimistic UI mutation | J; H mid-hand refusal only; E0 |
| Deck counts 1/2/4/6/8 | `Session.apply("setDecks")`, `Engine.setDecks` | **New** deck controls → existing `SetBlackjackDecks`, current confirmed value | Shoe stays Java-owned | J; E0 |
| Maximum hands 2/3/4 | `Session.apply("setSplitLimit")`, `rules.maxSplits = hands - 1` | **New** controls → existing `SetBlackjackSplitLimit` | No split legality duplication | J; E0 |
| Broke reload | `Session.apply("reload")`, `Engine.isBroke/setBankroll` | Existing reload control, Java legality gate | Source-fixed 1000 simulated credits; no real inventory grant | J; E0 |
| Reset table / stats | `Session.apply("newSession")`: abandon/reset/1000/reshuffle | **New** explicit reset button → existing `SubmitBlackjackAction("newSession")` | Same Java session ID; no native reset or reward synthesis | J; E0 |
| End session | `BridgeService.close`, `DELETE /sessions/{id}` | Existing `CloseRemoteBlackjackSession` and End button | Overlay close cancels local work; does not guarantee DELETE | H; E0 |
| Legal actions, chips, revisions | `VisibleSnapshot.copy`, `Session.mutate` | Existing `ApplyBlackjack` / `IsBlackjackActionLegal` and guard | Mutations never replay automatically | H, J, U; E0 |
| Cards / hand flags / dealer secrecy | `VisibleSnapshot.player/dealer` | Cards plus **new** eight player flags; dealer totals/flags only when Java reveals them | Hidden-phase totals still rejected; no hole/future shoe/RNG copied | H, J, U historical; E0 |
| Current rules / payout ratios / penetration | `VisibleSnapshot.rules`, `C/engine/BlackjackRules` | **New** strict reflected DTO and readout | No API to modify payouts or penetration; read-only values, no native payout math | J; E0 |
| Authoritative round ledger | `VisibleSnapshot.copy`, `C/engine/Outcome`, `TableLabels.roundResult` | Existing result wording plus **new** insurance stake, outcome list, last net and insurance values | Outcomes copied from Java, never inferred by comparing hands | J; E0 |
| Session statistics | `VisibleSnapshot.stats`, `C/engine/SessionStats` | **New** all ten counters and exact decimal-string long totals/readout | No ratio/settlement reimplementation; no durable storage here | J; E0 |
| Shoe/cut-card status | `VisibleSnapshot.copy`: `shoe` | **New** decks, remaining, reshuffle threshold and needs-shuffle readout | No card sequence/order or RNG | H secrecy evidence; E0 |
| Bounds / failures / recovery | `BridgeJson`, `BridgeServer`, `BridgeService` | Existing strict envelope, timeout, stale refusal and explicit reconciliation; new metadata is all-or-nothing | Not durable across service restart; current parser/UI changes untested | H, J, U historical; E0 |

## Original Blackjack capabilities still outside the facade

These are implemented original features, not speculative services. Completing
them requires Java-owned existing-interface exposure and accepted native bindings.
They must not be replaced with invented Unreal payouts, storage or achievements.

| Implemented app feature | Exact existing interface/source | Current Daedalus binding | Missing code | End-to-end evidence |
|---|---|---|---|---|
| 21+3 side bet | `C/sidebet/SideBetManager`, `TwentyOnePlusThree`; `S/ui/swing/BlackJackProApp.placeSideBet/resolveSideBet`; `G/TableScreen` | None | Java command/projection plus native controls/results | E0 |
| Strategy advice / Hi-Lo | `C/engine/BasicStrategy.recommend`, `C/strategy/HiLoCounter`, `TableObservation.sync`; Swing `HiLoCounterAi` | None | Java visible observation/advice projection and UI | E0 |
| Saved bankroll/stats and round resume | `C/persist/SaveManager.save/load`, `RoundSeal.seal/open`; `G/GameSession.persist/saveRound/resumeRound` | Facade memory only | Per-player storage/resume contract preserving sealed hidden state in Java | E0 |
| Persistent preferences | `C/settings/GameSettings.load/save`; `S/ui/swing/SettingsDialog`; `G/GameSession` | Transient facade settings only | Existing preferences adapter/provider and save semantics | E0 |
| Twelve achievements | `C/achievement/AchievementService`, `RoundAchievements`; original achievement dialogs/toasts | None | Java event/projection, achievement UI; no fabricated rewards | E0 |
| 24 themes/card backs | `C/table/Palettes.all`; `ThemeGalleryDialog`, GDX palette/renderers | Basic Slate table | Existing presentation selection and native theme/art binding | E0 |
| 13 casts / chatter | `C/table/Casts.all/forPalette`, persona classes, `TableChatter.react` | None | Java persona/events, native dialogue/character binding | E0 |
| Sound/music | `C/media/GameSounds`, `ToneSynth`; `S/media/SoundFx`, `MusicService`; `G/GdxSfx` | No source-specific cabinet audio | Coordinate existing audio owner; bind existing events/settings | E0 |
| Plugins | `S/plugin/PluginRegistry.loadAll/themes/aiStrategies/sideBets`, `PluginManagerDialog`, SPI file above | Facade loads no plugins | Explicit Java plugin lifecycle/projection; no invented loader | E0 |
| Keyboard/accessibility/mobile | Swing/GDX `TableKeys`, Swing `bindKeys`, GDX `TableScreen.keyDown`; `C/table/SpokenTable`, GDX `publishAccessibility`, Android `GlAccessibility` | Supported source action/chip shortcuts now route through existing legality/submit APIs with direct-focus/user gates; ordinary Slate controls | B/21+3 has no facade command; M/menu stays unbound; spoken table, platform lifecycle and controller integration remain open | Source review only; E0 |
| Optional Steam bridge | `S/steam/SteamBridge` reflective adapter | None | Optional SDK-specific binding; no-op path is not enabled capability | E0 |

The separate `:platform` wallet/round/compliance/RNG classes are outside the
facade, which depends only on `:core`. `CryptoCashier` is an interface. No wallet,
financial deployment, paid service, entitlement, NFT or inventory authority is
created or connected by this checkpoint.

## Other assigned arcade coverage

The eleven Python-family source pins and rule/visual adaptations remain in
[desktop-games-sources.json](../desktop-games-sources.json),
[DESKTOP-PYTHON-GAMES.md](../DESKTOP-PYTHON-GAMES.md), and each family's source
oracle/notes under `engines/unreal/core-test/desktop_games/`. Their native rules
are in `N/Public/DesktopGames/`, driven by the existing desktop actor and Slate
input/render host. Whole Python event-loop/RNG/save-format equality and production
3D characters are not established by portable parity. No family is newly played
or accepted by this checkpoint.

Every Python row below shares the existing `DaedalusDesktopGameRegistry.h`
`Catalog/CreateGame/Driver`, desktop actor `Use` and Slate input/render seam. All
eleven selected Desktop originals were read-only hash checked against the recorded
pins; no original changed. Paths are under `N/Public/DesktopGames/` unless noted.

| Implemented source feature | Exact source/interface | Daedalus binding | Missing code / adaptation | End-to-end evidence |
|---|---|---|---|---|
| Pong: paddle, AI, collisions, endless scores | Desktop `pong (1).py` update loop | `DaedalusDesktopPongCore.h`, `PongGame.Step/Render` | No rule binding gap identified; overshoot/collision repairs, original loop/RNG not reproduced | Historical oracle/U; E0 |
| Dungeon: seven-row map/movement/collision | `PythonGames/main.py.is_wall` and movement loop | `DaedalusDesktopMazeCore.h`, `DungeonGame` | Source has no enemies/score/victory; native bounds/all-corner repair | Historical oracle/U; E0 |
| Asteroids: thrust/wrap/fire, splits, UFO, lives/waves | `asteroids_pygame_ce.py.Ship/Bullet/Asteroid/UFO/main` | `DaedalusDesktopShootersCore.h`, `AsteroidsGame` | Cabinet selection replaces source title; bounded population/respawn adaptation | Historical oracle/U; E0 |
| Football: kick, CPU, goals, 90-second results | `football_pygame_ce.py.Player/Ball/main` | `DaedalusDesktopSportsCore.h`, `FootballGame` | Timer display clamp; no source multiplayer/persistence exists | Historical oracle/U; E0 |
| Pac-Man: maze/dots/ghosts/fright/lives/win/restart | `pacman.py.PacMan/Ghost/main/reset_level` | `DaedalusDesktopMazeCore.h`, `PacmanGame` | Spawn/pen/power-pellet/reset source repairs; no original arcade-AI equivalence | Historical oracle/U; E0 |
| Sega shooter: powers/enemies/pickups/lives/boss/win | `sega_space_shooter.py.Player/Bullet/Enemy/PowerUp/main` | `DaedalusDesktopShootersCore.h`, `SegaShooterGame` | Missing draw_text/boss collision repaired; unused enemy-shot timer is not an implemented firing feature | Historical oracle/U; E0 |
| Shadow Ninja: movement/sword/star/spin/gold/boss | `shadow_ninja_platform_fixed.py.Ninja/Sword/NinjaStar/Enemy/Boss/main` | `DaedalusDesktopPlatformersCore.h`, `ShadowNinjaGame` | Torches static; title/bounds adapted | Historical oracle/U; E0 |
| Star Shooter: three difficulties/patterns/powers/pause/save/top ten | `star_shootergpt1_fixed.py.choose_difficulty/run_game/save_game_state/load_game_state/save_score` | `StarShooterGame`; actor option/save/resume/high-score methods; Slate Star menu | Native DGS1/DGL1; no Python JSON migration; new run retains older save; failed OS writes can be lost on process loss | Historical oracle/U; E0 |
| Dodge Ball: eight rosters/actions/CPU/KO/four-round tournament | `super_dodge_ball_fixed.py.Player/Ball/make_team/aim_and_throw/main` | `DaedalusDesktopSportsCore.h`, `DodgeBallGame` | Source center-strip stall repaired; no source teammate switch/persistent bracket exists | Historical oracle/U; E0 |
| Contra: crouch/jump/shoot/pickups/stages/bosses/win/cheat | Final complete controller revision in `contra.py` after line 582, `Player/Enemy/PowerUp/main` | `DaedalusDesktopPlatformersCore.h`, `ContraGame`; gameplay cheat edges | `SubmitCheatKey(..., titleScreen=true)` has no cabinet/Blueprint title-bonus binding; native starts gameplay directly | Historical oracle/U; E0 |
| Zelda prototype: sword/enemies/health/pickups/key/win | `zelda.py.Link/Enemy/Projectile/Collectible/main` | `DaedalusDesktopMazeCore.h`, `ZeldaGame` | Key/endless-spawn defects repaired; original shield/scenery decorative | Historical oracle/U; E0 |

Python parity covers six suites and 1,507 selected-source cases, not full event
loops. RNG and procedural drawing differ; six cosmetic Star particle-count fields
were excluded. Production 3D character/animation and controller/world acceptance
are separate remaining capabilities across every family.

Sudoku source is [973c73a35f8659a17022232f0996d4ffb0095997](https://github.com/RicheyWorks/sudokupro/tree/973c73a35f8659a17022232f0996d4ffb0095997).
In the next table, controller paths are
`server/src/main/java/com/xai/sudokupro/controller/`, and client paths are
`client/src/main/java/com/xai/sudokupro/`. Existing native bindings are the same
Java actor/Slate, now extended with the bounded source package above. **S27** means
27 historical disposable HTTP/WS checkpoints with real authentication/JPA, H2
and mocked Redis/Jedis/relay; it does not establish full platform or Unreal E2E.

| Implemented app feature | Exact interface/source | Daedalus binding | Missing code | End-to-end evidence |
|---|---|---|---|---|
| Session/CSRF, own-board moves/undo/redo/sync | `SessionController GET /api/session`; `SudokuGameController /new`; `WebSocketController` commands | Configure/start/move/undo/redo/refresh methods and Slate grid | Account/provider mapping absent; Java owns clock/score/legality | S27 subset; E0 |
| Chaos/mirror/timed modes, recommended difficulty | `SudokuGameController.new` parameters and `/recommended-difficulty`; `net/ServerApi`, `ui/MainStage` | New three mode selectors → `StartSudokuGameWithModes` → captured bootstrap options → existing create URL; confirmed flags/time limit read from snapshots | Recommended difficulty still absent; current mode binding uncompiled/unplayed | E0 |
| Save/list/resume/end | `SudokuGameController /save,/saved,/resume,/end`; `ui/MainStage` picker | Save and explicit-ID Open/Resume buttons use the existing actor methods | Saved-list picker and authoritative end absent; cabinet close cancels local work | S27 subset; E0 |
| Hint price/confirmation | `SudokuGameController POST /hint`; `EconomyController /wallet`; `ui/BoardView:342–345,477–503` | Explicit Hint action; H separately asks and confirms the same current game ID before calling that action; confirmed hint count shown | Current wallet/price is not fetched; uses source's unknown-price confirmation fallback, no native currency grant | Source review; S27 historical hint subset; E0 |
| AI solve | `SudokuGameController POST /{id}/solve`; `GameClient`, `BoardView` | None | Service operation/UI absent | E0 |
| Pencil/highlights/conflict clearing/history | `ui/BoardView:83–90,182–324,440–445,637–680`, `ui/BoardCell`; web `static/play/app.js:910–932,1155–1168` | Local pencil mode/shared entry/3x3 marks; snapshot masks preserved until local override; wrapping/typed input; confirmed cosmetic highlights/progress/counts | Server conflict metadata, clear-conflicts command sequencing and filtered history/replay remain unbound. Notes intentionally stay view-local; no pencil write endpoint invented | Current source review only; E0 |
| Replay | `GameClient`, `ReplaySession`, `ui/MainStage` | None | Display-only chronological log/replay; never replay mutations into Java | E0 |
| Share/import | `SudokuGameController GET /{id}/share`, `POST /import`; `net/ServerApi` | None | Endpoints/DTO/UI absent | E0 |
| Spectator/chat/presence | `SudokuGameController /active-of/{playerId}`, `WebSocketController`, `GameClient/MainStage` | Owner-only projection; chat ignored | Explicit permission-checked read-only spectator and chat handling absent | E0 |
| Daily/archive/leaderboards | `DailyPuzzleController`, `net/ServerApi` | None | Existing API/DTO/picker/leaderboard bindings absent | E0 |
| Duel/accept/decline/rematch/ladder | `DuelController` | None | Existing API/DTO/UI bindings absent | E0 |
| Weekly tournament/standings/season | `MetaGameController` | None | Existing API/DTO/UI bindings absent | E0 |
| Powerups/catalog/held inventory/buy/use | `MetaGameController`, `net/ServerApi` | None | Existing authoritative catalog/inventory/actions/UI; no local grants | E0 |
| Wallet/XP/level/rating/achievements/overall leaderboard | `EconomyController`, `LeaderboardController` | None | Existing read/display/API bindings absent | E0 |
| Friends/pending/request/accept/decline/remove/events | `FriendController`, `EventsController` | None | Existing API/DTO/UI bindings absent | E0 |
| Account/password/device registration | `AuthController`, `NotificationController` | Credentials configure only | Native UX/provider bindings absent; no production account/device creation here | E0 |
| Themes/audio/settings/victory/reconnect | `ui/MainStage` and source theme/audio classes | Basic overlay/manual refresh | Original richer presentation/settings absent | E0 |

Minesweeper remains with PR139 owner `team-codex`; none of its files change here.

| Existing variant | Exact source/interface and capabilities | Daedalus binding / missing code | End-to-end evidence |
|---|---|---|---|
| PR139 `0582c27a` original native game | `DesktopGames/DaedalusDesktopMinesweeperCore.h`: 9x9/10,16x16/40,30x16/99; first-reveal 3x3 safety, flood/flag/chord, safe-cell win, active-step timer, open-count/1000 local score | Owner's registry/factory and Desktop hooks; no board SaveState; shared option row observed Star-only, owner follow-up required | Draft source; E0 |
| PR49 `2bdda5d5` Java-rule-derived Retro pilot | `DaedalusMinesweeperCore.h` / `DaedalusMinesweeper.h`; `minesweeper-pro GameService` pin in GAME-PORTS.md: fixed8x8/10, configured preplanted-safe center, reveal OR correctly flag all mines, creation clock, `150*mines-floor(ms/500)` score | Separate `ADaedalusMinesweeper`/Slate; challenge lives/resurrection/shields/adaptive boards/pencils/powerups/accounts/platform APIs absent | Historical 124 checks/41 actions; E0 |

Neither variant is a Java Minesweeper backend or full `minesweeper-pro` integration.

## Completion stages and next in-world step

| Stage | This checkpoint |
|---|---|
| Source | Claimed four Java actor/Slate files and this coverage/manifest only; source review, unverified |
| Committed | Current editing source `da2b4a84e357114181cbdb65093628d595cda2a7`, preserving package source `c7b3f3e28f759b5408a69ff00f2fde025b3d650b`, mode source `4d5577dc5659a9a26a9130e70cef68c2e5915ece` and prior Blackjack source `4f63c5b04dbac43a625c64741132f61e8719813c`; exact documentation tip in draft PR/hub handoff |
| Connected | No connection established or observed by this lane; companion PR62 adoption/runtime/provider pending |
| Native | No current-head UHT/UBT/DLL/load/placement; historical evidence stays pinned |
| End-to-end | No Unreal settings/action/recovery proof; original app coverage remains open |

After source review/adoption and a separately authorized build/load, the sole
operator must place or reuse one approved `ADaedalusJavaArcade`, set `Game` to
`Blackjack`, preserve its generated unique CabinetId, and route normal local Hero
Use into its existing Slate overlay. Against an approved disposable Java companion,
confirm that settings update only from replies, mid-hand/unknown-outcome controls
stay gated, reset uses the Java command, metadata matches the same revision and
hidden dealer/future-shoe data remain absent. No credentials belong in assets,
maps, defaults, receipts or this manifest. Current source is not native/E2E accepted.
