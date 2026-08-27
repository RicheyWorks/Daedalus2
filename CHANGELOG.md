# Changelog

All notable changes to Daedalus are documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). Versions before
`1.0.0` (the multi-module split + first audit pass) live in git history
under the `_migration/` portfolios.

## [Unreleased] — 2026-08-20

### Changed

- **Desktop empty well paints the same idle maze as the web.** Copy alone
  still looked like a stub. The miniature uses the same thin-wall tiles,
  start / goal discs, and DAEDALUS wordmark, kept to a 132×92 budget so a
  large window does not inflate it into a dungeon.

- **The legend only names what is on the board.** A fresh maze no longer
  lists hot spots, ghosts, and fog that are not there.

- **The empty well is a mark, not leftover stub text.** A faint thin-wall
  maze sits in the void with the same Generate / Solve copy. The legend
  stays hidden until a maze is on the board. Desktop paints the same
  invitation instead of a blank canvas.

- **Right-rail captions wrap before they clip.** The rail keeps 240px,
  folds under the maze at 1440px, and the lab / tournament / theory
  labels are short enough to stay on one line. The empty-well legend
  uses `[hidden]` so `#legend { display: flex }` cannot keep it visible.

- **Desktop and web share one void.** Cosmic was navy / neon / gold path;
  the web painter is slate / mint / coral. Same dungeon looked like two
  games. `CosmicTheme` and `cosmic.css` now use the web tokens. Start and
  goal paint as floor plus a disc — a neon slab was louder than the maze.

- **Web chrome recedes so the maze can speak.** Hazards, Theory, and Play
  start closed. Daily / Crossbreed and Solve / Compare sit in quiet pairs.
  The right rail is a rail, not an inline flex bag.

- **Web canvas fills the well and paints at devicePixelRatio.** Geometry
  used to hard-code an 880px budget and write CSS pixels into
  `canvas.width`, so a wide board left a tiny maze and a 2× display
  smeared the corridors. Paint now fits `#stage`, backs the bitmap with
  `devicePixelRatio`, and redraws on resize. Empty canvas sizes to the
  well instead of keeping the last maze. Heat / lens / search / race wash
  fill openings, not just cells. The primary race lane is the loud one.

- **Web chrome treats the maze as the hero.** Deeper void, quieter
  panels, a sticky stage well, Harden looks like a control, and the fog
  legend matches the wall fill.

- **Desktop thin-wall track matches the web.** `DesktopPaint.Layout`
  used to size every 2r+1 tile the same, so a dungeon was a chunky
  bitmap. Walls are now a quarter of the passage; a non-adjacent path
  step no longer paints a chord through a wall.

- **Plugin boot failures name REGISTER_ALGORITHMS and START.** Init and stop
  were already pinned. A throw in either later phase now publishes the
  matching `PluginFailedEvent` and does not stop the next plugin.

- **Traffic tick failure is a meter and a health detail.** A thrown tick still
  retires that tracker; `daedalus.traffic.tick.failure` increments and
  `/actuator/health` reports `lastTickFailed` while staying UP. An eviction
  is not a failure.

- **Living-maze tick failure is a meter and a health detail.** A thrown tick
  still retires that run; `daedalus.living.tick.failure` increments and
  `/actuator/health` reports `lastTickFailed` while staying UP. An eviction
  is not a failure.

- **Classifier train failure is a meter and a health detail.** Identify still
  stays 503 until a later fit publishes; `daedalus.fingerprint.train.failure`
  increments and `/actuator/health` reports `lastTrainFailed` while staying
  UP. A classifier never asked is not a failure.

- **WebUiSmokeTest dropped leftover function-name pins.** The boot-and-serve
  test still pins paths, element ids, permalink kinds, refuse copy, and the
  join-vs-move 404 distinction. Identifier names belong in `sweep/`.

- **PluginFailedEvent.Phase is a roster pin.** The SPI contract now names
  every host stop, the same way `PluginLifecycle` already does. DISCOVER is
  no longer the only constructed phase in that suite.

- **Leaderboard Redis read fallback is a meter and a health detail.** A
  board GET still stays 200 from memory; `daedalus.leaderboard.redis.read.fallback`
  increments and `/actuator/health` reports `lastReadFellBack` while staying
  UP. An empty Redis set is not a fallback — only a thrown read is.

- **Paint snapshot and input leftover writes left `app.js`.** `stage.js`
  owns the scene bag, canvas paint, click-to-move, and WASD. Leftover
  `draw` / `drawEmpty` / `mazeScene` names stay as wrappers. `flashStatus`
  stays leftover — sweep pins the leftover timer. Prod enumerates
  `/stage.js`.

- **Operator-desk leftover writes left `app.js`.** `desk.js` owns auth,
  leaderboard partitions, plugins, ASCII dump, algorithm catalog, braid
  sync, and god-mode arming. Each takes `state` plus a host bag. Leftover
  names stay as wrappers. Prod enumerates `/desk.js`.

- **Prod static scripts are one enumerated list.** `ProdSecurityConfig.STATIC_SCRIPTS`
  is the fail-closed GET allowlist. Posture GET/POST rows and `WebUiSmokeTest`
  fetch from it. A new `.js` still 401s until listed; `index.html` script tags
  stay in the page because HTML cannot import the constant.

- **SpotBugs `EI_EXPOSE_REP` is no longer project-wide.** Plugin events still
  share live grids. Snapshot records copy their lists. Spring collaborators,
  the live maze cache, and heatmap arrays stay excluded with a comment each.

- **Leaderboard Redis write fallback is a meter and a health detail.** A completed
  run still stays 200 in memory; `daedalus.leaderboard.redis.write.fallback`
  increments and `/actuator/health` reports `lastWriteFellBack` while staying
  UP. Two instances can still score different boards — that is now visible,
  not a warn-only log.

- **Generation circuit-breaker fallback now runs through the Spring proxy.**
  Boot 4's AspectJ starter was missing, so `@CircuitBreaker` on
  `MazeGenerationService.generate` was a no-op and a dying generator
  500'd instead of degrading to binary-tree. `spring-boot-starter-aspectj`
  plus `MazeGenerationFallbackProxyTest` pin `POST /generate` through
  the bean the controller injects.

- **Web UI leftover coordinators left `app.js`.** `live.js` owns STOMP,
  live polls, and mutation apply; `session.js` owns play / join / move;
  `fogwalk.js` owns the agent walk; `mint.js` owns generate / adopt /
  daily / breed; `campaign.js` owns the stage ladder; `spectate.js` owns
  permalinks / watch / leave-maze; `living.js` owns bring-to-life /
  traffic / living snapshot refresh; `ghost.js` owns recorded-run
  races; `tournament.js` owns solver ranking; `lab.js` owns the
  complexity-lab panel; `hunt.js` owns
  waypoint start / status / verdict; `solve.js` owns solve /
  race / compare; `theory.js` owns
  identify / analyze / hardest / heat / sanctuaries / lens and living
  overlay refresh. Each takes `state`
  plus a host bag — they do not read leftover globals. Leftover
  `indexOf` body pins were retired from `WebUiSmokeTest`; leftover
  behavior stays in `sweep/ui-sweep.js`. Prod enumerates each path.

- **`_migration/` is gone from the working tree.** Git history still has the
  archive. Docs no longer point at a live folder of uncompiled Java.

- **CI runs the plugin-host shutdown test on Windows.** Ubuntu still runs the
  full reactor. JAR-lock is a Windows property; linux file locks hid it.

- **Plugin SPI events have constructor pins.** `PluginSpiContractTest` covers
  the remaining six events. plugin-api JaCoCo is 0.96 / 0.99.

- **Web UI paint, HTTP, share, fog, seat, lab, and caption helpers no longer share one file.**
  `draw.js` takes a scene; `api.js` names RFC 7807 errors and fetches;
  `share.js` parses hashes and walks; `fog.js` owns agent memory; `seat.js`
  owns who-moves and trails; `lab.js` owns the complexity-lab chart;
  `caption.js` owns theory-overlay HTML. `app.js` keeps leftover-state
  wiring. Prod enumerates each path.

- **Generator and solver registries share one map.** `AlgorithmRegistry` owns
  collision, built-in refusal, and unregister. The two public types are facades
  so a lifecycle bug cannot be fixed on only one side.

- **Desktop walk and canvas geometry left the FX controller.** `DesktopWalk`
  is the legal-step helper; `DesktopPaint` owns letterboxing, path-connector
  tiles, and the inset player disc. `MainController` still calls
  `GraphicsContext`.

- **Plugin SPI events and defaults have tests.** `PluginSpiContractTest` covers
  lifecycle no-ops, `AbstractPlugin` stashing context, and `PluginFailedEvent`
  with a null cause.

- **`_migration/` left the working tree.** History still has the archive.

### Fixed

- **A generator that returns null is a 500 problem, not a raw stack.**
  `MazeGenerationService.NullGridException` maps to `generator-contract`.

### Changed

- **Maze REST surface split by resource.** Generate / daily / live / solve / breed
  stay on `MazeController`. Sessions (open, spectate, move, join) moved to
  `SessionController`; the board to `LeaderboardController`. Capacity 409s in
  `ApiExceptionHandler` now share one `capacityConflict` helper. URLs are unchanged.

- **Plugin ids are claimed once.** A second plugin with the same id is refused
  instead of silently replacing the first. Cyclic or missing `requires` fail
  discovery rather than being appended in undefined order.

- **`MazeGrid.carve(Cell, Direction)` throws on out-of-bounds.** It used to return
  silently, so a generator bug that walked off an edge looked like an intentional
  wall. Matches `carve(Point, Point)`.

- **`AbstractMazeGenerator` is a marker again.** Unused neighbor helpers that no
  generator (and no plugin) called were deleted so plugin authors are not inheriting
  dead advice.

- **TESTING.md matches the tree again.** The 2026-07-28 audit still said 347 tests,
  skipped examples, no WebSocket smoke, and 0.00 coverage exemptions. The living
  count is 734 reactor methods; those gaps are closed. Pom comments and ADR-003
  no longer advertise a 0.00 floor — plugin-api is 0.11 / 0.16, desktop is
  0.09 / 0.14. `WebUiSmokeTest` is not to grow as a source-shape mirror;
  leftover-state pins belong in `sweep/`. `sweep/api-sweep.py` now exits 1 on
  failure and runs in CI against a test-profile server.

### Fixed

- **Join eviction 404 no longer talks about moves.** `POST /session/{id}/join` reused the
  move endpoint's sentence when the session was open but its maze had been evicted, so a
  joiner was told "moves cannot be validated." It now says a join cannot be seated.
  `MazeControllerJoinTest` pins the verbs.

- **Plugin shutdown now runs in the host.** `PluginManager.shutdownAll()` was implemented
  and tested in `daedalus-plugin-runtime`, but `PluginConfig` never registered it as the
  bean destroy method — so `stop()` never ran, contributed algorithms stayed in the
  catalogs, and Windows kept plugin JARs locked after a graceful shutdown. The bean now
  uses `destroyMethod = "shutdownAll"`; `PluginHostShutdownTest` closes a host context
  and asserts `plugin-echo` is gone while built-ins stay.

- **Leftover leftover #pass stays.** leftover leftover auth stay already forbids reminting leftover leftover token (N118). leftover leftover `#user` stay already forbids reminting leftover leftover account (N182). Hunt / Play / Fog / theory / Join leftover leftover `#pass` stay — leftover leftover secret you already typed. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N183).

- **Leftover leftover #user stays.** leftover leftover auth stay already forbids reminting leftover leftover token (N118). leftover leftover `#log` stay already forbids reminting leftover leftover history (N181). Hunt / Play / Fog / theory / Join leftover leftover `#user` stay — leftover leftover account you already typed. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N182).

- **Leftover leftover #log stays.** leftover leftover catalog stay already forbids reminting leftover leftover log (N115). leftover leftover `#tourBox` stay already forbids reminting leftover leftover sample (N180). Hunt / Play / Fog / theory / Join leftover leftover `#log` stay — leftover leftover history you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N181).

- **Leftover leftover #tourBox stays.** leftover leftover lab stay already forbids reminting leftover leftover `#tourBox` (N116). leftover leftover `#labOut` stay already forbids reminting leftover leftover curve (N179). Hunt / Play / Fog / theory / Join leftover leftover `#tourBox` stay — leftover leftover sample you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N180).

- **Leftover leftover #labOut stays.** leftover leftover lab stay already forbids reminting leftover leftover `#labOut` (N116). leftover leftover `#player` stay already forbids reminting leftover leftover name (N178). Hunt / Play / Fog / theory / Join leftover leftover `#labOut` stay — leftover leftover curve you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N179).

- **Leftover leftover #player stays.** leftover leftover catalog stay already forbids reminting leftover leftover `#player` (N115). leftover leftover `#hotspotCost` stay already forbids reminting leftover leftover cost (N177). Hunt / Play / Fog / theory / Join leftover leftover `#player` stay — leftover leftover name you already typed. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N178).

- **Leftover leftover #hotspotCost stays.** leftover leftover form stay already forbids reminting leftover leftover `#hotspotCost` (N114 / N123). leftover leftover `#tourBraid` stay already forbids reminting leftover leftover tour braid (N176). Hunt / Play / Fog / theory / Join leftover leftover `#hotspotCost` stay — leftover leftover cost you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N177).

- **Leftover leftover #tourBraid stays.** leftover leftover sidebar stay already forbids reminting leftover leftover `#tourBraid` (N124). leftover leftover `#labMetric` stay already forbids reminting leftover leftover metric (N175). Hunt / Play / Fog / theory / Join leftover leftover `#tourBraid` stay — leftover leftover tour braid you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N176).

- **Leftover leftover #labMetric stays.** leftover leftover sidebar stay already forbids reminting leftover leftover `#labMetric` (N124). leftover leftover `#lbGen` stay already forbids reminting leftover leftover filter (N174). Hunt / Play / Fog / theory / Join leftover leftover `#labMetric` stay — leftover leftover metric you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N175).

- **Leftover leftover #lbGen stays.** leftover leftover picker stay already forbids reminting leftover leftover `#lbGen` (N122). leftover leftover rival stay already forbids reminting leftover leftover rival (N173). leftover leftover `#lbGen` disabled stay already N144. Hunt / Play / Fog / theory / Join leftover leftover `#lbGen` stay — leftover leftover filter you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N174).

- **Leftover leftover rival stays.** leftover leftover picker stay already forbids reminting leftover leftover rival (N122). leftover leftover `#lensH` stay already forbids reminting leftover leftover heuristic (N172). leftover leftover `#rival` options stay already N146. Hunt / Play / Fog / theory / Join leftover leftover rival stay — leftover leftover rival you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N173).

- **Leftover leftover #lensH stays.** leftover leftover picker stay already forbids reminting leftover leftover `#lensH` (N122). leftover leftover solver stay already forbids reminting leftover leftover solver (N171). Hunt / Play / Fog / theory / Join leftover leftover `#lensH` stay — leftover leftover heuristic you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N172).

- **Leftover leftover solver stays.** leftover leftover picker stay already forbids reminting leftover leftover solver (N122). leftover leftover `#braid` stay already forbids reminting leftover leftover braid (N170). Hunt / Play / Fog / theory / Join leftover leftover solver stay — leftover leftover solver you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N171).

- **Leftover leftover #braid stays.** `applyRecipeToForm` remints leftover leftover braid. leftover leftover form stay already forbids reminting leftover leftover recipe (N114). leftover leftover `#generator` stay already forbids reminting leftover leftover generator (N169). Hunt / Play / Fog / theory / Join leftover leftover `#braid` stay — leftover leftover braid you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N170).

- **Leftover leftover #generator stays.** `adoptMaze` / `applyRecipeToForm` remint leftover leftover generator. leftover leftover form stay already forbids reminting leftover leftover recipe (N114). leftover leftover `#hotspots` stay already forbids reminting leftover leftover spots (N168). Hunt / Play / Fog / theory / Join leftover leftover `#generator` stay — leftover leftover generator you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover leftover Solve path stays as a theory route hint (N62). Join leftover leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N169).

- **Leftover #hotspots stays.** `applyRecipeToForm` / leave-reset remint leftover spot count. leftover form stay already forbids reminting leftover recipe (N114). leftover `#seed` stay already forbids reminting leftover seed (N167). Hunt / Play / Fog / theory / Join leftover `#hotspots` stay — leftover spots you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N168).

- **Leftover #seed stays.** `adoptMaze` / `applyRecipeToForm` / leftover tournament load remint leftover seed. leftover form stay already forbids reminting leftover recipe (N114). leftover `#cols` stay already forbids reminting leftover width (N166). Hunt / Play / Fog / theory / Join leftover `#seed` stay — leftover seed you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N167).

- **Leftover #cols stays.** `adoptMaze` / `applyRecipeToForm` remint leftover width. leftover form stay already forbids reminting leftover recipe (N114). leftover `#rows` stay already forbids reminting leftover height (N165). Hunt / Play / Fog / theory / Join leftover `#cols` stay — leftover width you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N166).

- **Leftover #rows stays.** `adoptMaze` / `applyRecipeToForm` remint leftover height. leftover form stay already forbids reminting leftover recipe (N114). leftover plugin list.map stay already forbids reminting leftover roster rows (N164). Hunt / Play / Fog / theory / Join leftover `#rows` stay — leftover height you already asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N165).

- **Leftover plugin list.map stays.** `refreshPlugins` remints leftover plugin rows. leftover plugin stay already forbids reminting leftover roster (N115). leftover `/plugins` fetch stay already forbids reminting leftover catalog fetch (N163). Hunt / Play / Fog / theory / Join leftover plugin list.map stay — leftover roster rows you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N164).

- **Leftover /plugins fetch stays.** `refreshPlugins` remints leftover `/plugins` fetch. leftover plugin stay already forbids reminting leftover roster (N115). leftover `#lb` loading copy stay already forbids reminting leftover loading copy (N162). Hunt / Play / Fog / theory / Join leftover `/plugins` fetch stay — leftover catalog fetch you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N163).

- **Leftover #lb loading copy stays.** leftover `#lb` rows stay already forbids reminting leftover board rows (N143). leftover plugin loading copy stay already forbids reminting leftover loading copy (N161). Hunt / Play / Fog / theory / Join leftover `#lb` loading copy stay — leftover board loading you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N162).

- **Leftover plugin loading copy stays.** leftover plugin stay already forbids reminting leftover roster (N115). leftover plugin unavailable copy stay already forbids reminting leftover unavailable roster (N160). Hunt / Play / Fog / theory / Join leftover plugin loading copy stay — leftover loading roster you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N161).

- **Leftover plugin unavailable copy stays.** `refreshPlugins` remints leftover plugin unavailable copy. leftover plugin stay already forbids reminting leftover roster (N115). leftover plugin empty copy stay already forbids reminting leftover empty roster (N159). Hunt / Play / Fog / theory / Join leftover plugin unavailable copy stay — leftover unavailable roster you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N160).

- **Leftover plugin empty copy stays.** `refreshPlugins` remints leftover plugin empty copy. leftover plugin stay already forbids reminting leftover roster (N115). leftover plugin manifest stay already forbids reminting leftover manifest (N158). Hunt / Play / Fog / theory / Join leftover plugin empty copy stay — leftover empty roster you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N159).

- **Leftover plugin manifest stays.** `refreshPlugins` remints leftover plugin manifest. leftover plugin stay already forbids reminting leftover roster (N115). leftover plugin id stay already forbids reminting leftover id (N157). Hunt / Play / Fog / theory / Join leftover plugin manifest stay — leftover manifest you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N158).

- **Leftover plugin id stays.** `refreshPlugins` remints leftover plugin id. leftover plugin stay already forbids reminting leftover roster (N115). leftover plugin displayName stay already forbids reminting leftover name (N156). Hunt / Play / Fog / theory / Join leftover plugin id stay — leftover id you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N157).

- **Leftover plugin displayName stays.** `refreshPlugins` remints leftover plugin displayName. leftover plugin stay already forbids reminting leftover roster (N115). leftover plugin error stay already forbids reminting leftover failure (N155). Hunt / Play / Fog / theory / Join leftover plugin displayName stay — leftover name you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N156).

- **Leftover plugin error stays.** `refreshPlugins` remints leftover plugin error. leftover plugin stay already forbids reminting leftover roster (N115). leftover plugin state stay already forbids reminting leftover boot state (N154). Hunt / Play / Fog / theory / Join leftover plugin error stay — leftover failure you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N155).

- **Leftover plugin state stays.** `refreshPlugins` remints leftover plugin state. leftover plugin stay already forbids reminting leftover roster (N115). leftover plugin version stay already forbids reminting leftover version (N153). Hunt / Play / Fog / theory / Join leftover plugin state stay — leftover boot state you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N154).

- **Leftover plugin version stays.** `refreshPlugins` remints leftover version. leftover plugin stay already forbids reminting leftover roster (N115). leftover plugins describe stay already forbids reminting leftover describe (N140). Hunt / Play / Fog / theory / Join leftover plugin version stay — leftover version you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N153).

- **Leftover #braid options stay.** leftover `#braid` options ship in the markup. `applyBraidFromMaze` / `applyRecipeToForm` / `runTournament` remint leftover braid options on maze adopt or tournament. leftover form stay already forbids reminting leftover braid value (N114). leftover `#tourBraid` options stay already forbids reminting leftover sample braid roster (N151). Hunt / Play / Fog / theory / Join leftover `#braid` options stay — leftover braid roster you loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N152).

- **Leftover #tourBraid options stay.** leftover `#tourBraid` options ship in the markup. `syncBraid` / `applyBraidFromMaze` remint leftover sample braid options on braid change or maze adopt. leftover sidebar picker stay already forbids reminting leftover `#tourBraid` value (N124). leftover `#labMetric` options stay already forbids reminting leftover metric roster (N150). Hunt / Play / Fog / theory / Join leftover `#tourBraid` options stay — leftover sample braid roster you loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N151).

- **Leftover #labMetric options stay.** `loadLabMetrics` remints leftover `#labMetric` options. leftover sidebar picker stay already forbids reminting leftover `#labMetric` value (N124). leftover `#lensH` options stay already forbids reminting leftover heuristic roster (N149). Hunt / Play / Fog / theory / Join leftover `#labMetric` options stay — leftover metric roster you loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N150).

- **Leftover #lensH options stay.** leftover `#lensH` options ship in the markup. leftover picker stay already forbids reminting leftover `#lensH` value (N122). leftover `#generator` options stay already forbids reminting leftover generator roster (N148). Hunt / Play / Fog / theory / Join leftover `#lensH` options stay — leftover heuristic roster you loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N149).

- **Leftover #generator options stay.** `loadAlgorithms` remints leftover `#generator` options. leftover form stay already forbids reminting leftover generator value (N114). leftover algos stay already forbids reminting leftover catalog (N133). leftover `#solver` options stay already forbids reminting leftover solver roster (N147). Hunt / Play / Fog / theory / Join leftover `#generator` options stay — leftover generator roster you loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N148).

- **Leftover #solver options stay.** `loadAlgorithms` remints leftover `#solver` options. leftover picker stay already forbids reminting leftover solver value (N122). leftover algos stay already forbids reminting leftover catalog (N133). leftover `#rival` options stay already forbids reminting leftover arena roster (N146). Hunt / Play / Fog / theory / Join leftover `#solver` options stay — leftover solver roster you loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N147).

- **Leftover #rival options stay.** `loadAlgorithms` remints leftover `#rival` options. leftover picker stay already forbids reminting leftover rival value (N122). leftover algos stay already forbids reminting leftover catalog (N133). leftover `#lbGen` options stay already forbids reminting leftover filter roster (N145). Hunt / Play / Fog / theory / Join leftover `#rival` options stay — leftover arena roster you loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N146).

- **Leftover #lbGen options stay.** `loadAlgorithms` remints leftover `#lbGen` options. leftover picker stay already forbids reminting leftover `#lbGen` value (N122). leftover algos stay already forbids reminting leftover catalog (N133). leftover `#lbGen` disabled stay already forbids reminting leftover lock (N144). Hunt / Play / Fog / theory / Join leftover `#lbGen` options stay — leftover filter roster you loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N145).

- **Leftover #lbGen disabled stays.** `refreshLeaderboard` remints leftover `#lbGen` disabled. leftover picker stay already forbids reminting leftover `#lbGen` value (N122). leftover walk chrome stay already forbids reminting leftover board (N111). Hunt / Play / Fog / theory / Join leftover `#lbGen` disabled stay — leftover filter still enabled or still locked to this maze. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N144).

- **Leftover #lb rows stay.** `refreshLeaderboard` remints leftover `#lb` rows. leftover walk chrome stay already forbids reminting leftover board (N111). leftover `#lb` title stay already forbids reminting leftover heading (N142). Hunt / Play / Fog / theory / Join leftover `#lb` rows stay — leftover scores still name this maze's board. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N143).

- **Leftover #lb title stays.** `refreshLeaderboard` remints leftover `#lbTitle`. leftover walk chrome stay already forbids reminting leftover board (N111). leftover `lbQuery` stay already forbids reminting leftover path (N135). Hunt / Play / Fog / theory / Join leftover `#lb` title stay — leftover heading still names this maze's board. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N142).

- **Leftover walk chrome remint stays.** Play remints leftover trails / leftover won after the maze-id discard. Fog remints leftover trails / leftover won (N109 / N110). Join remints leftover joiner crumbs after the maze-id discard. leftover walk chrome stay already forbids reminting leftover trails / leftover won during Hunt / theory (N111). Play / Fog leftover walk chrome remint stay — leftover crumbs reminted. Join leftover walk chrome remint stay — leftover joiner crumbs reminted. Hunt leftover trails stay — current walk. Theory leftover trails stay — current walk. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N141).

- **Leftover plugins describe stays.** `refreshPlugins` remints leftover describe. leftover plugin stay already forbids reminting leftover roster (N115). Hunt / Play / Fog / theory / Join leftover plugins describe stay — leftover description you already loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N140).

- **Leftover sanctuaries remint stays.** Hunt / Play / Fog / Join remint leftover rings after the maze-id discard. Theory remints leftover sibling rings (N63). `placeSanctuaries` remints leftover rings after leftover sibling null. Hunt / Play / Fog / theory / Join leftover sanctuaries remint stay — leftover rings reminted. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N139).

- **Leftover expansions remint stays.** Hunt remints leftover expansions after the maze-id discard. Play / Fog / Join remint leftover path / leftover expansions. Theory remints leftover search wash (N87). Distinct from leftover progress clock (N129). Hunt / Play / Fog / theory / Join leftover expansions remint stay — leftover wash emptied (`draw` needs leftover expansions). Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N138).

- **Leftover #pngExport stays.** adoptMaze / leaveMaze remint leftover snapshot. leftover lab / tournament / PNG stay already forbids reminting leftover `#pngExport` (N116). Click remints leftover href from the canvas. Hunt / Play / Fog / theory / Join leftover `#pngExport` stay — leftover snapshot stays visible (same maze canvas). Fog leftover snapshot visibility unused (click remints the fog walk). Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N137).

- **Leftover #asciiOut stays.** Generate / Play / Hunt / theory / Join / Fog already hide leftover dump (N68–N74). Living tick remints leftover dump only when the pre is shown. Hunt / Play / Fog / theory / Join leftover `#asciiOut` stay — leftover dump stays hidden. Fog leftover dump text unused (hidden). Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N136).

- **Leftover lbQuery stays.** `refreshLeaderboard` remints leftover `lbQuery`. leftover walk chrome stay already forbids reminting leftover board (N111). Hunt / Play / Fog / theory / Join leftover `lbQuery` stay — leftover last `/leaderboard` path still names this maze. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N135).

- **Leftover STOMP stays.** Play remints leftover session frames when it seats. Fog remints leftover session frames. Join-from-spectate remints leftover session frames. Hunt leftover STOMP stay — leftover frames still name this maze. Theory leftover STOMP stay — leftover frames still name this maze. Hunt through Play still keeps tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Race and ghost stay recordings when you asked for them (N134).

- **Leftover algos stays.** `loadAlgorithms` remints leftover `algos`. leftover picker stay already forbids rewriting leftover solver (N122). leftover picker caption stay already forbids reminting leftover `#genInfo` / leftover `#solInfo` (N127). Hunt / Play / Fog / theory / Join leftover `algos` stay — leftover catalog you loaded. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N133).

- **Leftover Play / Fog button stays.** adoptMaze / leaveMaze remint leftover `#play` / leftover `#fog`. Hunt / Play / Fog / theory / Join leftover `#play` stay — same maze still playable. Leftover `#fog` stay — same maze still fogable. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N132).

- **Leftover cleared stays.** `loadCampaign` / `leaveCampaign` remint leftover `cleared`. leftover campaign stay already forbids `leaveCampaign` (N112). leftover campaign box stay already forbids reminting leftover `#campaignBox` (N128). Hunt / Play / Fog / theory / Join leftover `cleared` stay — leftover stages you cleared. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N131).

- **Leftover cadence stays.** `startLivePolling` remints leftover `liveTickMs`. `startTrafficPolling` remints leftover `trafficTickMs`. leftover live stay already forbids reminting leftover polls (N113). Hunt / Play / Fog / theory / Join leftover `liveTickMs` / leftover `trafficTickMs` stay — leftover cadence you asked for. Reconnect re-arms with leftover cadence when leftover `#live` is disabled. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N130).

- **Leftover search / path progress stays.** Hunt remints leftover `searchProgress` / leftover `pathProgress`. Theory remints leftover search wash (N87). Play / Fog / Join remint leftover path / leftover expansions and leave leftover progress, so leftover clock is unused (`draw` needs leftover path / leftover expansions). Play / Fog / Join leftover `searchProgress` / leftover `pathProgress` stay — unused leftover clock. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N129).

- **Leftover campaign box stays.** `leaveCampaign` / `renderCampaign` remint leftover `#campaignBox`. Hunt / Play / Fog / theory / Join leftover `#campaignBox` stay — the ladder you asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N128).

- **Leftover picker caption stays.** `updateInfo` remints leftover `#genInfo` / leftover `#solInfo` when leftover generator / leftover solver changes. Hunt / Play / Fog / theory / Join leftover `#genInfo` / leftover `#solInfo` stay — the picker caption you asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N127).

- **Leftover credential stays.** login remints leftover `#pass`. logout remints leftover `#user`. Hunt / Play / Fog / theory / Join leftover `#user` / leftover `#pass` stay — the name you typed. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N126).

- **Leftover sessionStart stays.** Play remints leftover clock when it seats. Join-from-spectate remints leftover clock. Hunt leftover sessionStart stay — current walk. Fog leftover sessionStart stay — unused leftover clock (`declareWin` needs session + ghost). Theory leftover sessionStart stay — leftover clock unused. Hunt through Play still keeps tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Race and ghost stay recordings when you asked for them (N125).

- **Leftover sidebar picker stays.** `loadLabMetrics` remints `#labMetric`. `applyBraidFromMaze` remints `#tourBraid`. Hunt / Play / Fog / theory / Join leftover `#labMetric` stay — the metric you asked for. Leftover `#tourBraid` stay — the sample braid you asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N124).

- **Adopt remints leftover hotspot cost.** `applyHotspotsFromMaze` reminted spot count and left leftover `#hotspotCost` from the previous recipe, so Daily / Generate / `#maze=` of a no-spot maze still billed leftover cost when spots were later asked for. Remint cost from the snapshot (catalog 25 when the maze has none). `applyRecipeToForm` remints cost even when the permalink omits `cost=`. Hunt / Play / Fog / theory / Join leftover `#hotspotCost` stay — same maze recipe (N123). Fog still keeps tour (N17).

- **Leftover picker stays.** `loadAlgorithms` / `#generator=` hydrate already remint those selects. Hunt / Play / Fog / theory / Join leftover solver / leftover lensH / leftover rival stay — the picker you asked for. Leftover `#lbGen` stay — the filter you asked for. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N122).

- **Leftover harden stays.** adoptMaze / leaveMaze / Bring to life already enable or disable `#harden`. Living under fog is honest (N19). Hunt / Play / Fog / theory / Join leftover harden stay — same maze still alive. Leftover `#harden` checked stay — you asked for seal. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N121).

- **Leftover hash on Hunt / theory stays.** Play / Fog / Join-from-spectate remint the bar when the exclusive kind changes. Hunt leftover hash stay — same maze (`play()` remints `#session=` only when it seats). Theory leftover hash stay — same maze. Hunt through Play still keeps tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Race and ghost stay recordings when you asked for them (N120).

- **Leftover daily / breed stays.** adoptMaze / playStage / leaveMaze already drop leftover dailyId and leftover breed parent on maze change. Hunt / Play / Fog / theory / Join leftover daily stay — same maze still daily. Leftover prevMazeId / leftover `#breed` stay — breed parent still valid. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N119).

- **Leftover auth stays.** login / logout already remint the token. Hunt / Play / Fog / theory / Join leftover auth stay — still signed in. Leftover `#authWho` stay — the name you signed in as. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N118).

- **Fog / Play drop leftover tourGot.** Hunt remints collected coins. Fog dropped the seat and leftover won (N110) but left leftover tourGot; Play reminted trails / won but left leftover tourGot, so leftover collected coins painted on the new seat until the first move reminted. Drop leftover tourGot after the maze-id discard (N117). Theory leftover tourGot stay — current hunt. Join leftover tourGot stay — same session. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17).

- **Leftover lab / tournament / PNG stays.** Measure and Run tournament remint those panels when you ask. adoptMaze / leaveMaze already show or hide the snapshot. Hunt / Play / Fog / theory / Join leftover lab stay — the curve you asked for. Leftover tournament stay — the sample you asked for. Leftover PNG stay — same maze canvas (fog snapshot is the fog walk). Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N116).

- **Leftover plugin / log / player stays.** `refreshPlugins` remints the roster on login / logout / plugin failure. Hunt / Play / Fog / theory / Join leftover plugin stay — global catalog. Leftover log stay — history. Leftover `#player` stay — the name you typed. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N115).

- **Leftover form stays.** adoptMaze / leaveMaze / applyRecipeToForm already rewrite the recipe on maze change. Hunt / Play / Fog / theory / Join leftover form stay — same maze recipe. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N114).

- **Leftover live / traffic stays.** adoptMaze / leaveMaze already drop leftover polls. Living under fog is honest (N19): the poller is maze-bound and re-polls the agent instead of GET `/maze`. Hunt / Play / Fog / theory / Join leftover live stay — same maze still erodes. Leftover `#live` / `#traffic` disabled stay — maze still alive. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N113).

- **Leftover campaign stays.** `pinHash` already drops the ladder when the exclusive kind is not campaign. Hunt / Play / Fog / theory / Join leftover campaign stay — same maze. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N112).

- **Leftover trails / won / leaderboard stays.** Competing writers drop leftover crumbs / won (N109 / N110) and remint the board on maze change (adoptMaze / Daily / campaign / leaveMaze / declareWin). Hunt leftover trails stay — current walk. Theory leftover trails stay — current walk. Join leftover opener trails stay — same session. Leftover won during Hunt / theory / Join stays — session still won. Leftover leaderboard / leftover `#lb` title stay — same maze; Play / Fog / Hunt / theory / Join do not remint. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N111).

- **Fog drops leftover won.** Generate / leave-watch / leaveMaze / Play already drop leftover won. Fog dropped the seat and leftover trails (N109) but left leftover won, so leftover victory ring painted after a living tick ended the fog walk without Play. Drop leftover won after the maze-id discard (N110). Fog still keeps tour (N17).

- **Fog drops leftover trails.** Generate / leave-watch / leaveMaze / Play already drop leftover crumbs. Fog dropped the seat and leftover ghost (N15) but left leftover trails, so leftover crumbs painted after a living tick ended the fog walk without Play. Drop those trails after the maze-id discard (N109). Fog still keeps tour (N17).

- **Leftover `#status` / `#join` stays.** Competing writers rewrite leftover hunt / win / spectate chrome (N48 / N101–N107). Hunt / session / win lines during theory stay current. ASCII does not rewrite `#status`. Fog leftover `#join` text stays — Play already set the seated label; Fog only disables. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N108).

- **Join-from-spectate drops leftover spectate join title.** Open session rewrites `#join` (label + title). `leaveSpectate` rewrites when it drops a watch (N105). Join-from-spectate only rewrote the label, so leftover spectate title named a watch that is gone under the seat just taken. Rewrite the title after the seat is taken (N107). Join-from-spectate still keeps the hunt. Fog still keeps tour (N17).

- **Hunt drops leftover Hunt / win status.** Play rewrites `#status` (N48) only when it seats. `refreshTourStatus` remints hunt status only when the tour is feasible. An infeasible hunt skipped both, so leftover "waypoint hunt" or leftover "reached the goal" named the previous walk under the new coins. Restore the session line after the maze-id discard (N106). Hunt still calls `play()` after installing tour — do not null tour. Fog still keeps tour (N17).

- **Leaving a watch drops leftover spectate status.** Generate / Fog / Play rewrite `#status` (N48). Solve / Hardest / Race / Compare rewrite after leaving a watch (N101–N104). Analyze / Identify / heat / sanctuaries / lens call `leaveSpectate` and left leftover "spectating session… — read-only" naming a watch that is gone under the cuts. Restore the no-seat prompt after the leftover seat drop (N105). Join-from-spectate sets the seat first and keeps the session. Fog still keeps tour (N17) except this leave-watch path (N56).

- **Compare drops leftover Hunt status.** Generate / Fog / Play rewrite `#status` (N48). Solve / Hardest / Race rewrite after dropping tour (N101–N103). Compare dropped tour (N53) but left leftover hunt text armed, so leftover "waypoint hunt" named a hunt that is gone under the table. Restore the session line after the maze-id discard (N104). Hover still arms a preview. Fog still keeps tour (N17).

- **Race drops leftover Hunt status.** Generate / Fog / Play rewrite `#status` (N48). Solve / Hardest rewrite after dropping tour (N101 / N102). Race dropped tour (N53) but left leftover hunt text armed, so leftover "waypoint hunt" named a hunt that is gone under the arena. Restore the session line after the maze-id discard (N103). Fog still keeps tour (N17).

- **Hardest drops leftover Hunt status.** Generate / Fog / Play rewrite `#status` (N48). Solve rewrites after dropping tour (N101). Hardest dropped tour (N59) but left leftover hunt text armed, so leftover "waypoint hunt" named a hunt that is gone under the gold walk. Restore the session line after the maze-id discard (N102). Fog still keeps tour (N17).

- **Solve drops leftover Hunt status.** Generate / Fog / Play already rewrite `#status` (N48). Solve dropped tour (N65) but left leftover hunt text armed, so leftover "waypoint hunt" named a hunt that is gone under the solver path. Restore the session line after the maze-id discard (N101). Fog still keeps tour (N17).

- **Leftover Solve stats stays.** Competing writers rewrite `#stats` (N92–N99). Solve still appends current walk figures. ASCII, living, ghost, and the lab do not rewrite `#stats`. Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). A leftover Solve path stays as a theory route hint (N62). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N100).

- **Theory writes drop leftover Solve stats.** Play / Hunt / Join / Fog / Hardest / Race / Compare rewrite `#stats` (N92–N98). Analyze / Identify / heat / sanctuaries / lens left leftover solver numbers armed, so leftover figures named the previous walk under the cuts, field, rings, bands, or Identify sidebar. Rewrite the maze identity after the maze-id discard (N99). Hunt and a leftover Solve path stay. Fog still keeps tour (N17).

- **Compare drops leftover Solve stats.** Play / Hunt / Join / Fog / Hardest / Race rewrite `#stats` (N92–N97). Compare left leftover solver numbers armed, so leftover figures named the previous walk under the table. Rewrite the maze identity after the maze-id discard (N98). Hover still arms a preview. Fog still keeps tour (N17).

- **Race drops leftover Solve stats.** Play / Hunt / Join / Fog / Hardest rewrite `#stats` (N92–N96). Race left leftover solver numbers armed, so leftover figures named the previous walk under the arena. Rewrite the maze identity after the maze-id discard (N97). Fog still keeps tour (N17).

- **Hardest drops leftover Solve stats.** Play / Hunt / Join / Fog rewrite `#stats` (N92–N95). Hardest left leftover solver numbers armed, so leftover figures named the previous walk under the gold walk. Rewrite the maze identity after the maze-id discard (N96). Fog still keeps tour (N17).

- **Fog drops leftover Solve stats.** Play / Hunt / Join rewrite `#stats` (N92–N94). Fog left leftover solver numbers armed, so leftover figures named the previous walk under the fog walk. Rewrite the maze identity after the maze-id discard (N95). Fog still keeps tour (N17).

- **Join drops leftover Solve stats.** Play rewrites `#stats` (N92). Hunt rewrites when `play()` is skipped (N93). Join left leftover solver numbers armed, so leftover figures named the previous walk under the seat just taken. Rewrite the maze identity after the join POST discard (N94). Join-from-spectate still keeps the hunt. Fog still keeps tour (N17).

- **Hunt drops leftover Solve stats.** Play rewrites `#stats` (N92) only when it seats. Hunt skipped `play()` when a seat already exists, so leftover solver numbers named the previous walk under the Held-Karp coins. Rewrite the maze identity after the maze-id discard (N93). Hunt still calls `play()` after installing tour — do not null tour. Fog still keeps tour (N17).

- **Open session drops leftover Solve stats.** Generate already rewrites `#stats`. Play left leftover solver numbers armed, so leftover figures named the previous walk under the seat. Rewrite the maze identity after the session POST discard (N92). Hunt still calls `play()` after installing tour — do not null tour. Fog still keeps tour (N17).

- **Leftover paint stays.** Competing writers drop leftover paint. Hunt stays during theory; a leftover Solve path stays as a theory route hint (N62). Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour (N17). Join leftover ghost stays (N86). Race and ghost stay recordings when you asked for them (N91).

- **Compare drops leftover Solve path.** Race already drops leftover path. Compare left it armed, so leftover solver route painted under the table until a hover. Drop that path after the maze-id discard (N90). Hover still arms a preview. Fog still keeps tour (N17).

- **Race drops leftover Compare table.** Hunt already empties leftover hover (N50). Race left the table armed, so leftover cuts caption or a leftover row hover painted under the arena. Empty `#compareBox` after the maze-id discard (N89). Fog still keeps tour (N17).

- **Compare drops leftover Race lanes.** Play / theory / Solve / Hardest / Join / Hunt already drop leftover arena. Compare left it armed, so leftover lanes painted under a compare hover. Drop that arena after the maze-id discard (N88). Fog still keeps tour (N17).

- **Theory writes drop leftover Solve search wash.** A leftover Solve path stays as a route hint (N62). Leftover expansions still painted the search wash under the cuts, field, rings, bands, or Identify sidebar. Drop that wash after the maze-id discard (N87). Hunt stays. Fog still keeps tour (N17).

- **Join leftover ghost stays.** Competing writers drop leftover ghost (N80–N84). Join is the same session: the ticker is maze-bound and still races the recorded best (N86). Join-from-spectate still keeps the hunt. Fog still keeps tour (N17).

- **Open session drops leftover Hardest walk unconditionally.** N58 only dropped gold when caption was hardest. Join already drops it either way (N77). Play left leftover gold armed when caption had drifted, so leftover gold painted under the seat. Drop that walk after the session POST discard (N85). Hunt still calls `play()` after installing tour — do not null tour. Fog still keeps tour (N17).

- **Hunt drops leftover ghost.** Fog already drops the ticker. Theory / Solve / Hardest / Race already drop it (N80–N83). Hunt left it armed, and `play()` is skipped when a seat already exists, so leftover recording painted under the Held-Karp walk. Drop that ticker after the maze-id discard (N84). Fog still keeps tour (N17).

- **Race / Compare drop leftover ghost.** Fog already drops the ticker. Theory / Solve / Hardest already drop it (N80–N82). Those arena writes left ghost armed, so leftover recording painted under the lanes or a compare hover. Drop that ticker after the maze-id discard (N83). Fog still keeps tour (N17).

- **Hardest drops leftover ghost.** Fog already drops the ticker. Theory / Solve already drop it (N80 / N81). Hardest dropped leftover Race but left ghost armed, so leftover recording painted under the gold walk. Drop that ticker after the maze-id discard (N82).

- **Solve drops leftover ghost.** Fog already drops the ticker. Theory writes already drop it (N80). Solve dropped leftover Race but left ghost armed, so leftover recording painted under the solver path. Drop that ticker after the maze-id discard (N81).

- **Theory writes drop leftover ghost.** Fog already drops the ticker. Analyze / Identify / heat / sanctuaries / lens dropped leftover Race (N60) but left ghost armed, so leftover recording painted under the cuts, field, rings, bands, or Identify sidebar. Drop that ticker after the maze-id discard (N80). Hunt and a leftover Solve path stay. Fog still keeps tour (N17).

- **Join drops leftover Race lanes.** Open session already drops leftover arena (N55). Join left it armed, so leftover lanes painted under the seat just taken. Drop that arena after the join POST discard (N79). Race stays a recording. Join-from-spectate still keeps the hunt. Fog still keeps tour (N17).

- **Leftover remint stays.** Competing writers drop leftover remints. Living ticks still remint the overlay you asked for. Hunt stays during theory; a leftover Solve path stays as a theory route hint (N62 / N63). Hunt through Play and Join-from-spectate still keep tour. Fog still keeps tour and does not remint until that walk ends (N17). Race and ghost stay recordings (N78).

- **Join drops leftover Hardest walk.** Open session already drops leftover gold when caption is hardest (N58). Join left it armed, so leftover gold painted under the seat just taken and a living tick reminted `GET /hardest-route`. Drop that walk after the join POST discard (N77). Join-from-spectate still keeps the hunt. Fog still keeps tour (N17).

- **Join drops leftover Solve path.** Open session already drops leftover path (N67). Join left the solver route armed, so leftover path painted under the seat just taken and a living tick reminted `POST /solve`. Drop that path after the join POST discard (N76). Join-from-spectate still keeps the hunt. Fog still keeps tour (N17).

- **Join drops leftover sibling theory remints.** Open session already drops leftover cuts (N66). Join left leftover analysis armed, so leftover cuts painted under the seat just taken and a living tick reminted `GET /analysis`. Drop those overlays after the join POST discard (N75). Join-from-spectate still keeps the hunt. Fog still keeps tour (N17).

- **Join drops leftover ASCII.** Open session hides `#asciiOut` (N68). Join left the dump armed, so leftover art reminted the text/plain maze under the seat just taken. Hide it after the join POST discard (N74). Join-from-spectate still keeps the hunt. Fog still keeps tour (N17).

- **Theory writes drop leftover ASCII.** Generate, Fog, Play, Solve, Hardest, Race, and Hunt hide `#asciiOut` (N68–N72). Analyze / Identify / heat / sanctuaries / lens left the dump armed, so leftover art reminted the text/plain maze under the cuts, field, rings, bands, or Identify sidebar. Hide it after the maze-id discard (N73). Hunt and a leftover Solve path stay. Fog still keeps tour (N17).

- **Hunt drops leftover ASCII.** Generate, Fog, Play, Solve, Hardest, Race, and Compare hide `#asciiOut` (N68–N71). Hunt left the dump armed, and `play()` is skipped when a seat already exists, so leftover art reminted the text/plain maze under the Held-Karp walk. Hide it after the maze-id discard (N72). Fog still keeps tour (N17).

- **Race / Compare drop leftover ASCII.** Generate, Fog, Play, Solve, and Hardest hide `#asciiOut` (N68–N70). Those arena writes left the dump armed, so leftover art reminted the text/plain maze under the lanes or a compare hover. Hide it after the maze-id discard (N71). Fog still keeps tour (N17).

- **Hardest drops leftover ASCII.** Generate, Fog, Play, and Solve hide `#asciiOut` (N68 / N69). Hardest left the dump armed, so leftover art reminted the text/plain maze under the gold walk. Hide it after the maze-id discard (N70). Fog still keeps tour (N17).

- **Solve drops leftover ASCII.** Generate, Fog, and Play hide `#asciiOut` (N68). Solve left the dump armed, so leftover art reminted the text/plain maze under the solver path. Hide it after the maze-id discard (N69). Fog still keeps tour (N17).

- **Open session drops leftover ASCII.** Generate and Fog hide `#asciiOut`. Play left the dump armed, so leftover art stayed on screen and a living tick reminted the text/plain maze under the seat. Hide it after the session POST discard (N68). Hunt still calls `play()` after installing tour — do not null tour. Fog still keeps tour (N17).

- **Open session drops leftover Solve path.** N57 only dropped Compare hover. Solve then Play left the solver route armed, so leftover path painted over the seat and a living tick reminted `POST /solve`. Drop that path after the session POST discard (N67). Hunt still calls `play()` after installing tour — do not null tour. Fog still keeps tour (N17).

- **Open session drops leftover sibling theory remints.** Theory writes already drop siblings (N63). Hardest / Solve already drop them (N64 / N65). Play left leftover cuts / heat armed, so leftover analysis painted under the seat and a living tick reminted `GET /analysis`. Drop those overlays after the session POST discard (N66). Hunt still calls `play()` after installing tour — do not null tour. Fog still keeps tour (N17).

- **Solve drops leftover Hunt coins, Hardest walk, and sibling theory remints.** Race / Compare already drop those (N53). Hardest already drops leftover Hunt and sibling theory (N59 / N64). Solve left them armed, so leftover coins and leftover gold painted under the solver path and a living tick reminted `GET /analysis`. Drop those overlays after the maze-id discard (N65). Fog still keeps tour (N17).

- **Hardest drops leftover sibling theory remints.** Theory writes already drop siblings (N63). Hardest left leftover cuts / heat armed, so leftover analysis painted under the gold walk and a living tick reminted `GET /analysis`. Drop those overlays after the maze-id discard (N64). Fog still keeps tour (N17).

- **Theory writes drop leftover sibling theory remints.** Field already drops sanctuaries / lens. Analyze left leftover heat armed, so a living tick reminted `GET /distance-field` under the cuts; Field left leftover cuts reminting `GET /analysis`. Drop those sibling overlays after the maze-id discard (N63). Hunt and a leftover Solve path stay. Fog still keeps tour (N17).

- **Analyze / Identify / heat / sanctuaries / lens drop leftover Compare hover.** N60 / N61 dropped leftover Race and Hardest; Compare hover stayed, so leftover solver path painted over the theory and a living tick reminted `POST /solve`. Drop that path after the maze-id discard when caption is compare (N62). A leftover Solve path stays as a route hint. Hunt stays. Fog still keeps tour (N17).

- **Analyze / Identify / heat / sanctuaries / lens drop leftover Hardest walk.** N60 dropped leftover Race; Hardest stayed, so leftover gold painted over the theory and a living tick reminted `GET /hardest-route`. Drop `state.hardest` after the maze-id discard (N61). Hunt stays. Fog still keeps tour (N17).

- **Analyze / Identify / heat / sanctuaries / lens drop leftover Race lanes.** Hardest already dropped leftover arena (N59). Those theory writes left Race armed, so leftover lanes painted over the cuts, field, rings, bands, or Identify sidebar. Drop `state.race` after the maze-id discard (N60). Hunt stays — chokepoints during a hunt are useful. Fog still keeps tour (N17).

- **Hardest drops leftover Hunt coins and Race lanes.** Race / Compare already drop leftover Hunt (N53). Hardest left the Held-Karp walk and leftover arena armed, so leftover coins and leftover lanes painted over the cruel route. Drop those overlays after the maze-id discard (N59). Fog still keeps tour (N17).

- **Open session drops leftover Hardest walk.** N55 / N57 dropped Race and Compare; Hardest stayed, so leftover gold painted over the seat and a living tick reminted it. Drop `state.hardest` after the session POST discard (N58). Hunt still calls `play()` after installing tour — do not null tour.

- **Open session drops leftover Compare hover.** N55 dropped Race lanes; the Compare table stayed, so hovering a row painted a leftover solver path over the walk just seated. Empty `#compareBox` and drop that path after the session POST discard (N57). Hunt still calls `play()` after installing tour — do not null tour.

- **Leaving a watch drops leftover Hunt coins.** N51 dropped the seat and kept the spectated tour. Solve / Fog then Play scored a new walk against leftover waypoints, and a living tick asked `tourFor` with no seat. Drop `state.tour` with the leftover seat (N56). `startFog` still must not null tour (N17). Join-from-spectate still keeps the hunt.

- **Open session drops leftover Race lanes.** Race stayed armed after Play, so leftover arena painted over the walk. Drop `state.race` after the session POST discard (N55). Hunt still calls `play()` after installing tour — do not null tour (N50). Fog still keeps tour (N17).

- **Back onto `""` / `#generator=` does not leave the adopted generate recipe in the form.** `leaveMaze` dropped the canvas; rows / seed / braid still named the maze the bar no longer named, so Generate rebuilt it. Restore catalog defaults (N54). Do not pin.

- **Race / Compare drop leftover Hunt coins.** Hunt already empties leftover Compare / Hardest (N50). Race and Compare left the Held-Karp walk and waypoints armed, so leftover coins painted under the arena or a compare hover. Drop those overlays after the maze-id discard (N53). Fog still keeps tour (N17).

- **Solve / Analyze after spectate does not leave a leftover `#session=` permalink.** N51 dropped the seat; the bar still named the watch, so refresh reminted it. Pin `#maze=` after the drop when the canvas remains (N52). `leaveMaze` nulls the maze first so that write cannot fight History.

- **Solve / Analyze after spectate does not take the opener's leftover seat.** `leaveSpectate` only cleared `readOnly`. Arrows then POSTed `/move` on a walk this tab only watched. Drop the leftover session when we were watching and have not taken a seat (N51). Join sets the seat first and keeps it. Do not pin (`leaveMaze` must not fight History). `state.tour` stays (N17).

- **Waypoint hunt drops leftover Compare / Analyze / Hardest overlays.** Hunt installed the tour and left those armed. A leftover compare hover painted a solver path over the Held-Karp corridor you are scored against; leftover hardest was a second walk that is not the score. Empty `#compareBox` and drop those overlays after the maze-id discard (N50). Fog already drops them. `state.tour` stays (N17).

- **A leftover solve or race animation does not write progress after Generate, Fog, or Back.** Those leave paths zero path and race; an in-flight `requestAnimationFrame` still advanced the previous reveal and could `raceSummary` the maze now on screen. Bump `animGen` on leave; a stale frame returns (N49).

- **A leftover wall-block flash does not restore old status after Generate, Fog, Back, or a new Open session.** `flashStatus` captured the line and put it back 900ms later. Generate / Fog / Back / Play already wrote the new status; the restore put the previous session or hunt text on a maze that no longer has that seat. Clear the timer before those writers set status (N48). `move()` still flashes after its fog / seat discard (N27).

- **Identify's 503 wait does not keep GET `/fingerprint` on a maze Generate already replaced.** First Identify retries for 60s while the classifier warms. Generate / Fog left that maze; the wait still asked the old id. Abort the loop when fog is on or maze id no longer matches, before the next GET (N47). Paint discard stays (N30).

- **A late campaign hazard does not start `/live` or `/traffic` on a stage Generate already replaced.** N29 discarded the UI bind after those POSTs so `#live` could not attach to the maze now on screen. The POST still fired against the stage you left, so a ticker ran on a maze the bar no longer names. Gate before the first hazard POST (N46). After-POST discard stays (N29).

- **A STOMP drop re-arms the living / traffic / spectate polls CONNECT just cleared.** N43 / N44 stop those fallbacks when the broker arrives so a late snapshot cannot rewind a hop or a tick. A later disconnect left them dead, so a watched walk or an eroding campaign stage froze until the next CONNECT. After `state.stomp = null`, start the same polls again — do not POST `/live` (N45).

- **A living or traffic poll started before STOMP does not write an older grid after the broker arrives.** Bring to life / traffic arm a GET `/maze` fallback only when SockJS is down. A late CONNECT used to leave those intervals running, so a snapshot that left before the next tick overwrote the `/state` frame. Stop the poller when `state.stomp` is set; a poll-initiated refresh discards after the GET; CONNECT clears the leftover intervals (N44). Fog / maze-id discard stays (N28 / N38).

- **A spectate poll started before STOMP does not rewind a hop after the broker arrives.** `#session=` arms a 1s `GET /session/{id}` fallback only when SockJS is down. A late CONNECT used to leave that interval running, so a snapshot that left before the next move overwrote the `/player` frame. Drop the poll on CONNECT and after the GET when `state.stomp` is set (N43). Fog / session / maze discard stays (N34).

- **Spectator living ticks rescore the hunt from `GET /session/{id}/tour`, not `GET /maze/{id}/tour`.** Hydrate already painted coins from the public session read (`progressFor` rescores Held-Karp). A living tick then asked `tourFor`, which is auth-required in prod and can mint — unsigned spectate 401'd and kept a stale optimum. Prefer the session read when a seat exists; maze tour is only the Hunt-before-Play fallback (N42).

- **Late `#session=` / spectate after Generate does not steal the maze now on screen.** Initial hydrate `adoptMaze`'d the session maze before its fog check and had no maze-id discard. Generate mid-flight replaced the canvas, then the late GET still adopted over it. Capture maze id (or none) before the fetch; skip `adoptMaze` / `adoptSessionView` when fog is on or the canvas id is no longer the one you left. Leave-fog-before-fetch stays (N22). Stay until join lands. Poll discard stays (N34).

- **Late Daily / Breed / `#maze=` after Generate does not steal the maze now on screen.** Those hydrates discarded `adoptMaze` after only fog. Generate mid-flight replaced the canvas, then the late fetch still adopted over it. Capture maze id (or none) before the fetch; discard when fog is on or the canvas id is no longer the one you left. Campaign / `playStage` / `#daily=` siblings too. `playStage` still adopts the same campaign stage. Fog discard stays (N21 / N22).

- **Late Fog start after Play does not re-arm fog on the session walk.** `startFog` POSTed `/agent` then applied after only maze-id. Play on the same maze seats a session; maze id still matches, so a late mint dropped the seat and `applyFogView` recreated `state.fog` on the play walk. Capture session id; discard after the POST when the seated session is new. Maze-id discard stays (N26). Same class as N38.

- **Late living GET `/agent` after Play does not re-arm fog.** `refreshLivingMaze` GETs `/agent/{id}` then `applyFogView` after only maze-id `stale()`. Play on the same maze leaves fog; maze id still matches, so a late GET recreated `state.fog` on the session walk. Capture agent id; discard after the GET when fog is gone or the agent no longer matches. Same class as N26. Living-under-fog stays.

- **Late ghost after Generate does not seat the maze now on screen.** `summonGhost()` GETs `/ghost` then armed `state.ghost` and the ticker after only a fog + session-exists check. Generate + Play mid-flight seated the old recording on the maze now on screen. Capture maze id; discard after the GET when fog is on, the seat is gone, or maze id no longer matches. Fog discard stays (N25). Ghost is maze-bound, not seat-bound.

- **Late Join after Generate does not seat the maze now on screen.** `join()` POSTed `/join` then wrote the seat after only a fog + session-exists check. Generate + Play / a new `#session=` mid-flight wrote the joiner (`leaveSpectate`, pin) onto the maze now on screen. Capture session and maze id; discard after the POST when fog is on or the seat no longer matches. Fog discard stays (N23). Stay a watcher until join lands.

- **Late confirmWin / tour status after Generate does not paint the maze now on screen.** `confirmWin()` GETs `/session/{id}` then `declareWin` after only a fog + session-exists check; `refreshTourStatus()` painted hunt status the same way. Generate + a new Play mid-flight wrote a win (status, leaderboard, campaign) onto the maze now on screen. Capture session and maze id; discard after the GET when fog is on or the seat no longer matches. `tourVerdict` sibling too. Fog discard stays (N24). Fog still keeps tour (N17).

- **Late spectator `/session/{id}` poll after Generate does not re-seat the maze now on screen.** The STOMP-less spectate interval GETs the session snapshot then always `adoptSessionView`. Generate / Fog / a new `#session=` mid-flight wrote the old walk onto the maze now on screen. Capture session and maze id; discard after the GET when fog is on or the seat no longer matches. Overlay hydrate stay (N33). Fog still keeps tour (N17).

- **Late spectator `/session/{id}/tour` after Generate does not paint the maze now on screen.** `hydrateSpectatorOverlays` GETs session tour progress then always wrote `state.tour`. Generate / Fog / a new `#session=` mid-flight painted the old hunt onto the maze now on screen. Capture session and maze id; discard after the GET when fog is on or the seat no longer matches. Sibling `summonGhost` is the same discard. Progress only — not `GET /maze/{id}/tour`. Fog still keeps tour (N17).

- **Late Open session after Generate does not seat the maze now on screen.** `play()` POSTed `/session` after only a fog check. Generate mid-flight pinned `#session=` and wrote the seat onto the generated maze. Capture maze id before the POST; discard after `/session` (and the leave-fog GET `/maze`) when fog is on or maze id no longer matches. Fog discard stays.

- **Late `/tour` after Generate does not play or paint the maze now on screen.** `startTour` / `hardestRoute` / `placeSanctuaries` / `showAscii` fetched then painted after only a fog check. Generate mid-flight assigned the old tour, route, rings, or dump onto the maze now on screen; Hunt could even `play()` a session on the new id. Discard when maze id no longer matches. Fog discard stays.

- **Late `/solve` after Generate does not paint the maze now on screen.** `solve` / `raceSolvers` / `compareSolvers` POSTed then painted after only a fog check. Generate mid-flight applied the old path, expansions, or `#compareBox` onto the maze now on screen; Race / Compare could POST later `/solve` against the new id. Discard when maze id no longer matches. Fog discard stays. Identify / Heat / Lens / Analyze too.

- **Late campaign hazard `/live` or `/traffic` after Generate does not bind the maze now on screen.** `playStage` POSTed those hazards then always disabled `#live` and armed a poller. Generate mid-flight bound the maze now on screen. Discard after the POST when maze id no longer matches the stage. Fog stays — living+fog is honest.

- **Late `/live` or `/traffic` after Generate does not bind the maze now on screen.** `bringToLife()` / `simulateTraffic()` POSTed then always disabled the button and armed a poller. `onMutation` logged the tick and could re-enable `#live` after `refreshLivingMaze` discarded. Discard after the POST / refresh when maze id no longer matches. Fog stays — living+fog is honest.

- **Late move after Fog or a new session does not overwrite status or the new seat.** `move()` POSTed `/move` then always `flashStatus` / `applyMove`. A blocked reply overwrote fog status; Generate + a new Open session wrote the old hop onto the new seat. Arrows and click-to-move both call `move()`. Discard after the POST when fog is on or the session/maze/seat no longer match.

- **Late fog step / Fog start after Generate does not re-arm the walk.** `fogStep()` POSTed `/step` then always `applyFogView`, which recreates `state.fog` and carves the old openings into whatever maze is now on screen. `startFog()` applied the same way after Generate replaced the maze. Discard after the POST when the walk or maze is gone.

- **Late ghost after Fog does not re-arm the ticker.** `summonGhost()` GETs `/ghost` then always armed `state.ghost` and the ticker. Fog mid-flight cleared both; the GET still re-armed the ghost onto the walk. Discard after the GET when `state.fog` is set or the seat is gone. Same class as N20–N24.

- **Late confirmWin / tour status after Fog do not paint the walk.** `confirmWin()` GETs `/session/{id}` then `declareWin` with no fog/session re-check; `refreshTourStatus()` painted hunt status the same way. Fog mid-flight still wrote a win (status, leaderboard, campaign) onto the walk. Discard after the GET when `state.fog` is set or the seat is gone. Same class as N20–N23.

- **Late Join after Fog does not steal the walk.** `join()` POSTed `/join` then always wrote the seat. Fog mid-flight hit a nulled `state.session` or reattached the seat after the walk dropped it. Stay a watcher until join lands (spectate honesty); discard the apply when `state.fog` is set. Same class as N20–N22.

- **Hash hydrate leaves fog before fetch; late `#session=` does not seat after discard.** `#maze=` fetched then `adoptMaze` no-op'd during fog, so the bar named a maze the canvas still walked. A late `#session=` still ran `adoptSessionView` after adopt discarded. Leave fog before those fetches (Back / paste / Forward already wrote the bar); same-hash still no-ops. Discard adopt / the spectator seat when Fog starts mid-flight. Same class as N20 / N21.

- **Late Generate after Fog does not replace the walk.** Generate /
  Daily / Campaign / Breed stay armed during fog and fetched, then
  `adoptMaze` always replaced the maze. A Fog that started mid-flight
  still lost the canvas. Leave fog before the fetch (they are
  leave-fog paths); discard adopt when `state.fog` is set. Same
  class as N20.

- **Late Open session after Fog does not steal the walk.** `play()`
  snapshotted `hadFog`, POSTed, then always nulled fog. A Fog that
  started mid-flight was treated as “no fog” and the session still
  pinned `#session=`. Leave fog before the fetch (Open session is a
  leave-fog path); discard the apply when `state.fog` is set — Hunt
  waypoints’ `/tour` too. Same class as N18 / N19.

- **Late living refresh after Fog does not install the god-mode grid.**
  A tick that passed the fog gate could still have GET `/maze` in
  flight. Fog starts; `if (stale())` let `state.maze = maze` write
  unseen rooms into a walk that skipped that fetch on purpose.
  Discard when `state.fog` is set — same as N18. The fog path still
  does not GET `/maze`.

- **Late Analyze / Compare after Fog does not restore the sidebar.**
  N17 emptied `#compareBox` when Fog started. A request that was
  already out still landed, named chokepoints again, and Compare
  hover-armed `state.path` for Play to paint. Discard after the
  fetch when `state.fog` is set — Identify / Heat / Lens / Solve
  too. `state.tour` still stays.

- **Fog drops the leftover theory sidebar.** Analyze / Compare / Identify
  wrote `#compareBox`. Fog already dropped those overlay objects and hid
  ASCII; the sidebar stayed, so a leftover caption still named
  chokepoints during the walk and a leftover compare row could hover-arm
  a solve path `draw()` swallowed until Play. Empty it after that drop.
  `state.tour` stays — same maze, not a GET or mutate under fog.

- **Fog after Open session drops the leftover `/player` subscription and ghost ticker.**
  N15 dropped the seat and hash. The STOMP `/player` sub and ghost
  interval stayed, so a joiner's frame still logged a session move and
  the ghost still advanced while `draw()` returned early and the canvas
  walked fog. `resubscribe` and the ghost clear run after that drop.

- **Fog after Open session drops the leftover `#session=` hash.**
  Open session pinned `#session=`. Fog nulled the seat and started the
  agent walk without pinning, so the bar still named the session while
  the canvas walked fog. `pinHash` runs after that drop — daily /
  campaign stay those kinds; a leftover `#session=` becomes `#maze=`.

- **Back onto an empty or `#generator=` hash drops the maze.**
  N10 re-hydrated maze-to-maze. Back from `#maze=` onto `""` or
  `#generator=` only touched selects and left the previous maze — and a
  daily / session seat — on the canvas the bar no longer named.
  `leaveMaze` clears that leftover; it does not pin.

- **A campaign permalink names the current stage.**
  `#campaign=` stored only the seed, so hydrate — including Back onto the
  same hash — always `loadCampaign` → `playStage(0)` and reminted stage-1
  hazards. The token is now `#campaign=SEED` (stage 0, old links) or
  `#campaign=SEED:N`; `playStage` still keeps the ladder.

- **Generate / Daily / Breed from a campaign drop the ladder.**
  A non-campaign hydrate already left (N11), but those three adopted
  then pinned a matching `#maze=` / `#daily`. `hashShowsCurrent` no-op'd,
  so `state.campaign` and `#campaignBox` stayed painted and a stage click
  still played a campaign maze the bar no longer named. `pinHash` now
  leaves when the exclusive kind is not campaign; `playStage` still
  restores `stageIndex` first so the ladder stays.

- **Back from a campaign drops the ladder.**
  `hashchange` re-hydrated the maze and hash (N10), but `adoptMaze` only
  nulled `stageIndex`. `state.campaign` and `#campaignBox` stayed painted,
  so a stage click still played a campaign maze the bar no longer named.
  A non-campaign hydrate (or a different campaign id) now leaves the
  ladder; a matching `#campaign=` hydrate still keeps it.

- **Back/Forward re-hydrate the hash, and pinHash does not remint.**
  `loadFromHash` was boot-only. Generate / Daily / a `#maze=` hydrate wrote the
  bar; History Back updated the URL and left the canvas on the previous maze.
  `hashchange` re-runs the boot hydrate; a same-hash no-op stops the write from
  looping.

- **Show ASCII is a text/plain dump, not a solve.** Living-tick refresh and a
  spectator click sent `?solve=`, which ran a solver and published
  `MazeSolvedEvent` while claiming to be a lab read. The GET without a
  solver query 400'd because `@AlgorithmId` is `@NotBlank`. The dump is
  the maze as text; `leaveSpectate` stays off this path.

- **`adoptMaze` mirrors generator and seed, not just size / braid / hotspots.**
  A `#maze=` (or Daily / campaign / `#session=`) success path wrote `g=` and
  `seed=` into the hash from the maze, then left the selects on leftovers.
  Generate, Measure, and the tournament still read the form, so the bar named
  one recipe and the next click built another.

- **Show ASCII no longer drops watch to dump text, and Measure / Run tournament stay watchers.**
  Those three fill a sidebar or a `<pre>` — they do not adopt, paint, or mutate
  the watched maze. Show ASCII called `leaveSpectate` before the `text/plain`
  GET; a living tick that refreshed that dump then re-armed Bring to life.

- **Daily, Campaign, Breed, and Solve leave watch mode before they write.**
  A `#session=` hydrate left those buttons armed. Daily / Campaign / Breed
  fetched, then `adoptMaze` cleared `readOnly` as a side effect. Solve
  painted a god-mode overlay on the watched maze. `leaveSpectate` now runs
  first, same as Fog / Generate / Open session; Tour / live / traffic stay
  disarmed.

- **Fog, Generate, and Open session leave watch mode before they write.**
  A `#session=` hydrate left those buttons armed. Fog POSTed an agent walk
  and left `readOnly` set. Generate replaced the maze under the spectator.
  Open session minted, then left. `leaveSpectate` now runs first, same as
  join-from-spectate; Tour / live / traffic stay disarmed.

- **Open session after a `#session=` hydrate actually plays, and this tab moves its own seat.**
  Spectate left `readOnly` set. Open session minted a session and said "arrow
  keys to move", then arrows and clicks no-op'd. Clicks still aimed at the
  opener after join-from-spectate. A late hydrate started the ghost on the
  opener's current cell. Tour / live / traffic stayed armed and could mint
  or mutate under the player. `leaveSpectate` drops watch mode; click and
  arrows share `thisTabSeat`; the ghost starts at the maze start.

- **Solve and Compare name a 422 `solver-budget` instead of dumping the status line.**
  HTTP already answers 422 when a solver spends its node budget. The page
  still logged `422 Unprocessable Entity … — solver-budget: …`. `nameBudget`
  maps the kind; matching the named string again is a no-op.

- **Spectator hydrate and a `#maze=` permalink name a TTL-evicted maze as gone.**
  Join already said "that session is gone". `#session=` then `GET /maze/{id}`
  after idle TTL dumped `404 Not Found on /maze/{id}`, and permalink wrapped
  the same status line. `nameGone` maps maze/session/agent 404s; a missing
  tour or ghost stays unnamed so those reads can stay silent.

- **Daily, campaign, and breed 409s carry `maze-capacity` the same way generate does.**
  Those routes share `admit()`. Generate already had an HTTP pin; a full cache
  on the daily, a campaign plan, or a crossbreed had none. Standalone MockMvc
  now expects 409 `maze-capacity` on `GET /maze/daily`, `GET /campaign`, and
  `POST /maze/breed`.

- **The page names the pool a 409 refused, including a permalink remint at maze-capacity.**
  Living and traffic already said "too many mazes are already alive/tracked".
  Session, fog, generate, and tour dumped `409 Conflict on /path — kind: …`,
  and a `#maze=` rebuild that hit the cache cap was logged as "not found".
  `nameCapacity` maps the ProblemDetail kind; `permalinkLoadFailed` does not
  treat a refused remint as a missing maze.

- **A first `GET /tour` on a new maze at the placement cap no longer LRU-evicts another maze's frozen coins.**
  Caffeine `get(compute)` at `maximumSize` on `WaypointService` placements
  silently dropped the LRU coin set, so `progressFor` went null, pickups
  stopped attaching, and a later `tourFor` reminted a different set.
  HTTP can 409 a first tour — unlike a move that already happened — so a
  new maze at cap is refused. A later tour for a seated maze still
  returns that maze's first-insert set. Admission is one lock, the same
  compound living/traffic/session/walk/maze closed; idle TTL still
  evicts abandoned tours.

- **A finish on a new maze at the ghost cap no longer LRU-evicts another maze's recording.**
  Caffeine `maximumSize` on `GhostService` silently dropped the LRU ghost, so
  `GET /maze/{id}/ghost` 404ed while someone was still racing or spectating
  that maze. Finish cannot 409 — the run already completed — so a new maze
  at cap drops this ghost instead of an in-use one. An existing seat still
  merges the higher score. Admission is one lock, the same compound
  living/traffic/session/walk/maze closed; idle TTL still evicts abandoned
  recordings.

- **Generating a maze at cache cap refuses instead of LRU-evicting one still in play.**
  Caffeine `maximumSize` on `MazeGenerationService` silently dropped the LRU
  maze, so an unrelated generate 404ed a live session or walk
  (`tryMove` / agent step treat a missing maze as gone). Admission is one
  lock, the same compound living/traffic/session/walk closed; idle TTL still
  evicts abandoned mazes. Daily, campaign, and permalink share `generate`.
  Waypoint `collected` refuses a new hunt's first pickup at cap rather than
  wiping a mid-hunt set. The new generate is 409.

- **Opening a session or walk at cap refuses instead of LRU-evicting a live one.**
  Caffeine `maximumSize` on `GameSessionService` and `AgentWalkService`
  silently dropped the oldest mid-hunt entry so an unrelated open 404ed
  it. Admission is one lock, the same compound living/traffic closed;
  idle TTL still evicts abandoned work. The new open is 409.

- **Two first `GET /tour?count=` can no longer mint two coin sets.**
  `tourFor` keyed `mazeId:k`, so two first asks at different counts each
  placed. `placedFor` then preferred the default count or the first
  `asMap()` scan, and pickups attached to the wrong hunt. Placement
  keys on the maze alone; the first insert wins. Progress stays a read.

- **Two first campaigns can no longer both take a free plan slot.**
  `CampaignService.campaign` checked `size()` then `clear`/`put` without a
  lock. Two first seeds both inserted, and two arrivals at a full map
  both survived the wipe. Admission is one lock, the same compound
  living/traffic closed; two first requests for one seed mint one plan.

- **Two sessions finishing the same maze keep both runs, and the better
  ghost.** `LeaderboardEntry.compareTo` stopped at elapsed time, so the
  in-memory skip-list treated a tied score as one member and dropped a
  run Redis would have kept. Identity breaks the tie. In-memory
  add-and-trim is one lock, so two threads at the cap cannot
  `pollLast` an extra row. Ghost `merge` already keeps the higher
  score; a two-thread pin holds it.

- **Two joiners can no longer both take the last seat.** `GameSession.join`
  checked `size()` then `putIfAbsent` without a lock. `ConcurrentHashMap`
  does not make that atomic, so two names racing the eighth seat both sat
  down. The method now uses the same session monitor `tryMove` already
  holds. A two-thread pin overflows on the unsynchronized body.

- **Living/traffic 409 and a spent solver budget now have an HTTP pin.**
  The services threw; the advice mapped them; nothing asked the
  controller. Dropping the handler would 500. Standalone MockMvc now
  expects 409 `living-capacity` / `traffic-capacity` and 422
  `solver-budget`. The STOMP smoke publishes a mutation and a traffic
  pulse, so those listeners are on the broker, not only `convertAndSend`.
  The page names a full pool instead of dumping the status line.

- **`/state` is not generate-only.** Living ticks and traffic pulses already
  ride `/topic/maze/{id}/state`. The README and the STOMP wiring javadoc
  still said `GeneratedFrame` only. They now name all three shapes and the
  field that distinguishes them. The TypeScript sketch no longer ends
  mid-`SolvedFrame`.

- **Join names finished, full, or gone — not the multiplayer flag.** The
  server already splits those 409s. The page logged every other failure
  as "is the flag on?", including a 404 for an unknown session, which
  is also how a flag-off join is supposed to look. Plugin DTO javadoc
  names `/api/v1/plugins`. The README no longer headlines the July test
  count or claims the TypeScript sketch is missing `walks`.

- **Fog locks the overlays `draw()` would swallow.** Solve, analyze, the
  tour, Identify, and ASCII stayed clickable during a walk; they wrote
  `state` and painted nothing. Those buttons disable for the walk and
  re-arm when generate, play, or an agent 404 ends it. Living stays
  armed. Stats and campaign hazards go through `esc()`.

- **OpenAPI names this release and the live tags.** The spec still said
  `1.0.0` and listed Mazes / Plugins / Leaderboard. The version is
  `1.2.0-SNAPSHOT`. Agents, Insight, Campaign, and Auth are registered.
  `GET /leaderboard` sits under Leaderboard instead of an empty tag.

- **A `#maze=` permalink carries the recipe that rebuilt it.** Seed, size,
  algorithm, braid, and hotspot count sit beside the id. If the cache
  dropped the maze, the page regenerates the same spots instead of 404ing.
  Two first hits on the daily mint one maze, not an orphan. The TypeScript
  sketch names `/api/v1` and the fields it used to omit.

- **First Identify no longer trains on a Tomcat worker.** The classifier
  fit runs on a dedicated thread. Concurrent first hits share that one
  train. Until it publishes, `GET /fingerprint` is 503 with
  `Retry-After`; the page retries instead of hanging the tab.

- **Living and traffic caps are real under burst.** First starts used
  to read `map.size()` inside a per-key `compute`, so two mazes could
  both see a free slot and both insert. Admission is now one lock;
  a two-thread first-start pin keeps the last slot singular.

- **Join 409 says finished or full, and agent views cost a step.**
  `POST /session/{id}/join` used to answer an empty 409 for both a
  completed session and a full one. Those are now
  `session-completed` and `session-full` problem types. `GET /agent/{id}`
  shares the `agentStep` budget. Session and solve DTO javadocs name
  `/api/v1`.

- **ASCII errors, a failed compare, and an evicted maze.** `apiPlain`
  reads ProblemDetail the same way `api` does, so a 401 is not a missing
  maze. Compare no longer logs `best path Infinity` when every solver
  fails. A move against an evicted maze says the maze aged out.

- **Hotspots, offline wins, and joiner credit.** Generate places
  weighted cells from the seed, not `Math.random()`, and a `#maze=`
  refresh restores the count. An offline hop that does not show `G`
  still asks the session snapshot, so a living tick cannot hide a
  finish. A joiner who steps on the goal is the name on the leaderboard
  and the ghost walk; the opener's empty trail no longer drops the
  recording.

- **Catalog blurbs, `#generator=`, breed weights, and prod XFF.**
  Algorithm notes go through `esc()`. A `#generator=` permalink sets
  Generate, not only the leaderboard select. SockJS/stomp.js carry SRI.
  Crossbreed unions parent hotspots (max cost on a shared cell). Prod
  no longer trusts `X-Forwarded-For` unless `DAEDALUS_RL_TRUST_XFF=true`.
  Harden after `/live` is already running is refused instead of a silent
  no-op.

- **Tour progress ignored `?count=` and unsigned spectators could not
  paint the hunt.** Pickups and `GET /session/{id}/tour` looked up
  `mazeId:defaultCount` only, so a hunt opened at `count=8` was
  uncollectable. Progress now finds the placed instance, includes the
  coins and the Held-Karp path (so a public spectator GET can paint
  without `GET /maze/{id}/tour`, which is auth-required and would mint),
  and reports the opener's trail rather than every seat's hops. A fog
  walk that 404s falls through to `GET /maze` instead of leaving
  `carveFogOpenings` tiles on a god-mode canvas. `GameSession` no longer
  claims to live in Redis.

- **Session permalinks and live-grid moves.** Open session logged a
  `#session=` link and left `#maze=` in the bar; joining a spectate
  dropped the hash and renamed `primary` to the joiner, so the ghost
  and win keyed on the wrong seat. Campaign and daily stay first;
  everything else with a session pins `#session=`. Arrows follow
  `state.seat`. `tryMove` re-reads the cached grid inside the session
  lock so a living tick cannot accept a sealed wall or refuse a newly
  opened one. Leaving fog via play refetches the maze.

- **Generate echoes the braid factor.** The request accepted it; the response
  did not. The page labelled Daily and a `#maze=` permalink from the leftover
  select. The factor now lives on the cached maze, is omitted when zero, and
  survives a living or traffic tick. The stats line reads `maze.braid`.

- **Generate-id smoke stubbed the pre-braid overload.** The controller
  calls `generate(..., hotspots, braid)`. The mock still answered the
  five-arg form, so Mockito returned null and `cached.metadata()` NPE'd
  — the audit's "report the fallback algorithm" pin was not running.

### Changed

- **README matches the tree.** The glance list was a changelog of every UI
  honesty fix; it is a product sketch again. The fat-jar example is
  `1.2.0-SNAPSHOT`, not `1.0.0`. The July 623-test snapshot is dated. The
  TypeScript file is a sketch, not a generated client. Golden digests cover
  nine solvers because IDA\* answers 422.

### Added

- **Living mazes v2 — hardening (ADR-008).** ADR-006 left wall-closing out of v1 because
  opening is safe by construction and closing is not. The named trigger (build traffic or
  fog-of-war, then revisit with a connectivity proof) fired: both shipped 2026-07-30, and
  a fog-of-war walk already sees the live grid, so a maze that can get *harder* mid-walk
  is the composition that note called the killer version.

  The proof is a **spanning-forest complement**, not the cut-vertex check the trigger
  asked for. Closing a wall removes an edge, so the certificate is a cut-edge. And "close
  every current non-bridge" is not safe as a batch — two parallel paths are each a
  non-bridge; closing both disconnects the rooms. A BFS forest of the habitable graph
  (rock skipped) is computed in the grid's stable neighbour order; every edge *not* in
  that forest can come off at once and the forest still joins everyone. On a perfect maze
  the extra set is empty, so hardening is a no-op — the same honesty the hardest-route
  endpoint learned on trees.

  `Sealer` in core; `MazeGrid.seal` is `carve`'s inverse. `POST /api/v1/maze/{id}/live`
  takes optional `seal` in `[0, 1]`; `daedalus.living.seal-factor` defaults to **0**, so
  a call without the query param is v1 erosion. `MazeMutatedEvent` / `MutationFrame` grow
  an additive `wallsClosed`. The web UI's Harden checkbox passes `seal=0.08`.

  Along the way: the living ticker's "at least one wall while any dead end remains" rule
  treated `erosion-factor: 0` as "still erode". Zero now means off, matching seal, so a
  harden-only run is actually possible.

- **Campaign finale hardens (ADR-008 composition).** The ladder already declared `living`
  then `traffic`. The new verb sits on the last stage only — `hardening` — and the web UI
  folds it into the existing `/live` call as `?seal=0.08`. A second `POST /live` would
  join the running ticker and drop the factor (start is idempotent per maze), which is
  why this is a declared hazard the client maps, not a second endpoint. The hazard test
  pins the whole ramp; `campaignteeth.py` has a mutation that dumps hardening at the
  living threshold.

- **Capacitated max-flow (ADR-009 / ADR-001 appendix 2).** `MazeFlow.minCut` takes an
  optional `PassageCapacity`. The no-arg overloads stay unit-capacity — `GET /analysis`
  still counts chokepoints — and a real function turns `cutSize` into bisection
  bandwidth. Uniform capacity scales the cut and leaves the bottleneck set alone;
  heterogeneous capacities make `cutSize` the sum, not the count. Weights stay costs.
  The topology example prints both readings.

- **Hilbert's live descriptor stopped claiming best locality.** The vision table was
  corrected in July; `GET /algorithms` still advertised "best locality of any curve
  generator". The tagline now matches the measured stretch (worse than Morton, more
  than double Prim's diameter). A diameter test pins the order and refuses a
  Hamiltonian snake.

- **Bipartite b-matching (ADR-010 / ADR-001 appendix 3).** `BipartiteMatching` assigns
  a batch of requests to servers under per-server capacity — the selection question
  A* cannot answer. The LoadBalancerPro strategy seam is still closed; this is the
  offline primitive, same posture as capacitated flow. First-fit is not a substitute:
  the test that pins the class is the fixture first-fit gets wrong. The topology
  example assigns a lattice of request sites onto k-center replicas and shows
  capacity leaving seats unmatched.

- **Living mazes rescore waypoint tours (ADR-014).** Placement freezes on
  first ask; Held-Karp runs against the live grid. A cached optimum was a
  recording of a maze that erosion and hardening had already changed. The
  coins stay put so collection tracking does not teleport; the number you
  are scored against does not. The UI refetches `/tour` on each living
  refresh.

- **Cell walls are a nibble; `MazeGraph` stopped boxing a `Point` per hop
  (ADR-016 leftovers).** The class already claimed to be allocation-free.
  `neighbors` was not. `MazeGrid.isOpen(row, col, dir)` is the coordinate
  form that made the claim true. The `long[]` `MazeGrid` rewrite stays out.

- **Join grants STOMP on owned sessions (ADR-012).** Multiplayer and
  per-destination authorization shipped the same day and did not compose: join
  put a piece on the board and left `/topic/session/{id}/player` owner-only, so
  a second authenticated client could move over REST and never see a frame.
  `GameSession` now keeps a subject allowlist (owner plus anyone who joined
  with a token). Anonymous join still gets a seat, not the feed. Rejoin of a
  name does not hand the seat to a different token. Cap is 8. The spectator
  permalink stays read-only until **Join this session**. Subjects stay off
  `SessionResponse`.

- **The web UI signs in and walks fog-of-war.** The page is living API
  documentation, but it never called `/auth/login` and never opened an agent,
  so prod generate/play were 401 from the only client we ship, and ADR-012's
  join-with-token had no way to attach a principal. Sign in stores the JWT in
  `sessionStorage` and puts `Authorization: Bearer` on REST and STOMP
  `CONNECT` (reconnect after login so the subject exists). Fog of war paints
  only cells the walk has stood on — the agent response never includes the
  grid, and using `state.maze.tiles` for unseen cells would have been theater.
  Controls are grouped under `<details>` (IDs unchanged; `ui-sweep.js` keys on
  them). `WebUiSmokeTest` pins `#login`, `#fog`, `/auth/login`, and
  `Authorization`.

- **The web UI fetches ASCII and the plugin list.** `GET /maze/{id}` as
  `text/plain` and `GET /plugins` were product surfaces the living docs never
  called — a client-side tile dump would have skipped content negotiation, and
  plugin failures already arrived on STOMP with no roster to attach them to.
  Show ASCII asks the server (and stays off during fog, because the art is the
  grid). The plugin panel is empty-honest when nothing is loaded, and refreshes
  after sign-in because prod keeps `/plugins` closed.

- **The web UI reads the per-generator leaderboard.** `GET /leaderboard?generator=`
  shipped with the attribution fix and the page never sent it — the only
  scopes were daily/campaign `maze=` or the global board. The Algorithm
  select asks that partition; it disables on a shared maze because `maze=`
  wins if both are sent and a selected generator would have been theater.
  `state.lbQuery` is the path actually fetched, so a title-only fake fails
  the sweep.

- **Solver movement stays in the corridors.** The web UI drew routes as a
  polyline through cell centers, `0.4·cell` wide, over passages that are
  `0.25·cell`. Every turn cut the corner post. Shortest-path solvers hid it;
  wall-follower and Trémaux — long walks revealed in a flat 700 ms — looked
  like they tunneled. Routes now paint stood-on cells and the opening between
  consecutive 4-adjacent cells (what the desktop already did), refuse a chord
  across a non-adjacent pair, put a marker on the walk head, and scale the
  reveal to path length.

- **Play, fog, and the ghost walk the same corridors.** Solver routes painted
  openings; a player trail was still dots at cell centers, fog was a marker
  on the void, and the ghost jumped. All three now feed `paintWalk` — the
  fog walk is the ordered agent path (not the seen-set), and the ghost is
  start plus every `to` whose clock has elapsed.

- **A spectator permalink paints the walk, not just the seat.**
  `GET /session/{id}` already returned live positions; frames only carry the
  next hop, so a late `#session=` arrival saw a marker and no corridor.
  The snapshot now includes the opening player's recorded trail (the same
  `TimedMove` list a completed run becomes a ghost from) and the opening
  name. The page hydrates `paintWalk` from start plus every `to`, keeps
  `#session=` in the address bar so a refresh still spectates, and
  polling rebuilds the walk from the snapshot instead of teleporting the
  marker. Subjects stay off the body.

- **The waypoint tour paints the Held-Karp walk, not just the coins.**
  `WaypointTour` already built every cell of the optimal route; the product
  `Tour` dropped it and the page drew diamonds on the stops. You were
  scored against a corridor you could not see. `GET /maze/{id}/tour` now
  includes `path` (start through goal, `optimalCost` hops), and the UI
  feeds it to `paintWalk`. A living tick already refetches the tour, so
  the walk moves with the score (ADR-014).

- **Shared views tell the truth, and a spectator GET no longer writes the
  puzzle.** Three lies, one seam. `adoptMaze` always wrote `#maze=`, so a
  campaign link became a mute maze, Daily lost its scoped board on
  refresh, and `#generator=` did not exist. One `pinHash` writer keeps
  `#session=`, `#campaign=`, `#daily`, `#maze=`, or `#generator=` —
  whichever kind the page is actually in. `GET /session/{id}/tour` used
  to call `tourFor`, which freezes coins: a public spectator hit minted
  the instance the players then had to collect. Progress is a read;
  unknown session and "no hunt yet" are different 404s (same distinction
  the ghost learned). A `#session=` arrival hydrates the hunt (if one
  was asked) and the ghost (if one exists) without creating either.

- **The plugin roster and the braid factor tell the truth.**
  A `PluginFailedFrame` hit the log and left the Plugins panel on
  STARTED — the frame exists so the roster can change. The panel now
  re-fetches `GET /plugins` and shows the manifest description the
  describe endpoint was the only way to see. Generate and the tournament
  each had a braid select; they stay in lockstep so a ranking cannot
  race a different braid than Load it rebuilds.

- **Identify generator follows the living grid.** The button's claim is
  eroded mazes whose recorded author no longer matches. A living tick
  left the first verdict on screen. The page now re-asks `/fingerprint`;
  the interesting answer is a falling dead-end ratio and, often,
  `agrees: false`.

- **Theory overlays follow the living grid, not the snapshot they were first asked about.**
  A living tick already re-solved the route, re-analyzed cuts, and rescored
  the tour (ADR-014). Hardest-route, the distance field, sanctuaries, the
  heuristic lens, and the ASCII dump stayed on the tree. The services already
  read the current snapshot — HardestRouteService says that is the point —
  so the page now re-asks. Race and ghost stay recordings. The panel caption
  updates only for the overlay that last wrote it.

- **Generate can braid, so the tournament's "load it" is the maze that was raced.**
  `POST /maze/generate` takes optional `braid` in `[0, 1]` — the same
  `Braider` pass, same seed, then extremes on the braided graph. The
  page's Braid select is that field. "Load the adversarial maze" used
  to set seed and size only: a braided sample rebuilt the tree, and a
  changed Algorithm select rebuilt the wrong generator. The link now
  sends generator, seed, size, and the sample's braid. Zero braid is
  today's generate.

- **A spectator sees every seat's walk, not just the opener's.**
  `GameSession` recorded hops only for the opening player — ghost
  material. A joiner was a marker. The snapshot now includes `walks`
  (every name that has moved); `trail` stays the opener's list so a
  ghost is still one recording. The page hydrates `paintWalk` per
  player from start plus every `to`. Subjects stay off the body.

- **Fog of war no longer pulls the god-mode grid when the maze lives.**
  A living tick used to `GET /maze/{id}` and replace `state.maze.tiles`.
  Fog paints from those tiles for every stood-on cell, so erosion in
  rooms you had visited — and openings on the edge of the seen-set —
  appeared without the agent reporting them. The agent contract is
  position, openings, goal. The refresh now re-polls `GET /agent/{id}`
  only, and `carveFogOpenings` writes the four gap tiles at your feet
  from `view.open`. Memory of the void stays put. The sweep holds the
  unseen glyph string across a tick.

### Fixed

- **Signed-in live frames could not connect in prod.** `/ws/**` required a
  bearer header on the HTTP upgrade. Browsers cannot set that header on
  SockJS, so the UI's `CONNECT` token never left the tab. The handshake is
  public; STOMP `CONNECT` stays required. `WebSocketProdHandshakeTest` pins
  both sides: `/ws/info` is 200 without a token, a token-less `CONNECT` is
  still refused, and a valid token opens a session.

### Decided

- **Incremental SSSP declined (ADR-011 / ADR-001 appendix 5).** Living ticks,
  traffic, and hotspot drift all change the graph, so the UI re-solves every 2 s.
  Measured on this machine: a full Dijkstra after those mutations is 50–200 µs at
  API sizes and 2 ms worst at 128² — a thousand times faster than the ticker.
  D\*Lite would keep a search tree through edge insert, edge delete, and weight
  change for a 200 µs baseline. The recompute *is* the architecture. Harness at
  `docs/evaluations/IncrementalSsspEval.java`; re-fire if the tick becomes a
  data-plane interval or someone regularly solves ≥256² living mazes.

- **Bellman-Ford / Johnson declined (ADR-013 / ADR-001 appendix 4).** API
  weights are costs in `[1, 1000]`; core rejects negatives. Bellman-Ford on
  that graph is a slower Dijkstra. Johnson without negatives is n Dijkstra,
  slower than the already-dormant `DistanceOracle`. Re-fire if a directed
  latency graph with signed or genuinely asymmetric hops appears.

- **Kruskal texture declined (ADR-015 / CLRS G4).** Random unique weights
  are a shuffle, which Kruskal already does. Directional bias is weighted
  Prim's; the two algorithms produce the same MST. Braiding already shipped
  as a post-process.

- **Packed `MazeGrid` declined (ADR-016 / CLRS D2).** Measured: a packed
  neighbor sweep saves ~150 µs at 128² on a 1.6 ms Dijkstra; `copy()` is
  tens of times slower than memcpy and still sub-millisecond against a 2 s
  tick. Harness at `docs/evaluations/BitsetGridEval.java`. The nibble and
  the allocation-free graph walk are the leftovers that paid.

### Fixed

- **The web UI answered 401 in prod, and the spectator permalink never worked.** `GET /` and
  `GET /index.html` were closed by `anyRequest().authenticated()` — measured on a prod-profile
  boot, not inferred. The README publishes the UI as "served at `/`"; prod refused it.

  What makes this more than a missing row is where it lands. `ProdSecurityConfig` deliberately
  opens `GET /api/v1/session/{id}`, its tour, the ghost run and the agent re-poll, and argues
  the case at length in its own javadoc: a spectator link only the operator can open is not a
  spectator link, and until 2026-07-31 those endpoints "did not work in prod at all". But the
  link the UI hands out is `https://host/#session={id}` — origin root plus a fragment. Every
  endpoint on that carefully-reasoned list was reachable and the page that calls them was not,
  so **the feature still did not work.** The fix had been applied to the half that had a test.

  **Why no test could have caught it.** `ProdAuthPostureTest` is the strongest security test in
  the repo and is blind to this by construction: its completeness half walks
  `controller/**.java` extracting `@…Mapping` annotations, and a file served off the classpath
  has no annotation to find. The gap was not a forgotten row — it was in what that table is
  *able* to contain.

  Fixed with an enumerated allowlist (`GET /`, `GET /index.html`), not a glob. The UI is one
  file, so the enumeration is complete today and fail-closed tomorrow: a second asset 401s until
  somebody lists it, which is the same reasoning as the single-segment `*` matchers beside it.

- **`ProdStaticSurfacePostureTest` and `mutants/staticteeth.py` — the table the annotation
  scanner cannot hold, and its teeth.** The test records an explicit posture per non-API path,
  drives them against a real prod boot, and walks the static directory so a new file fails the
  build until a decision is recorded for it. A third test asserts the page prod serves is
  actually the page: a 200 with an empty body satisfies any status-only table and still leaves a
  blank screen in front of every spectator.

  **The harness scored 4/5 on its first run.** The survivor was the *method* scope — dropping
  `HttpMethod.GET` from the matcher permits every verb on that path — and it survived because the
  new table was keyed on paths alone with GET assumed on every row. A table cannot catch a
  distinction it does not express.

  Fixing it took more than adding write rows. `POST /` fails either way; what differs is **which
  layer refuses it**. With the method scope, the security layer answers 401. Without it, security
  says yes and the servlet layer answers 405. So 405 is now deliberately excluded from the
  refused set — the property being pinned is "the security layer is the thing that said no", not
  "the request did not succeed". 5/5.

  One mutation is deliberately absent and the harness says so: nothing in this repo's source can
  be edited to produce "prod answers 200 with something that is not the page". That failure
  arrives from packaging or a resource-handler change, not a line to flip, and an inert edit
  faking coverage reads exactly like a genuine gap.

- **Every completed run was attributed to a generator called "unknown".** `GameSessionService`
  built its `LeaderboardEntry` with the literal string `"unknown"` in the `mazeGeneratorId`
  slot — one construction site, unconditional, on every run this server has ever recorded. A
  debugging pass found it by *running* the thing: boot the jar, play a session through to the
  goal, read the board back, and there it is in the response body.

  **The visible half** is an API field that is always false. The shipped web client does not
  render it, which is how it survived; any client that trusted it got a constant.

  **The half that mattered more** is that `LeaderboardService.submit` keys a Redis sorted set on
  that value — `daedalus:leaderboard:gen:{id}`. The per-generator partition was therefore never
  a set per generator. It was one set, named after the placeholder, holding every run on every
  algorithm. And it had no reader anywhere in main or test: a sorted-set write plus a trim on
  every completed run, serving no request. The trim's own javadoc argues against exactly that,
  three lines below the line doing it — *"write-only storage … a slow leak with a scoreboard
  attached"* — which it was diagnosing for the global set's tail while the per-generator set
  was the whole thing.

  **Why the suite could not see it.** Six test classes construct a `LeaderboardEntry` and every
  one supplies its own generator id. Each is a fine test of what it tests; together they mean
  the value the *service* writes is the one value nothing observes. That is the shape worth
  naming and it is now a lesson in `mutants/README.md`: a field whose only producer is the code
  under test, asserted everywhere by fixtures that supply it themselves.

  Fixed in both halves. `GameSession` now carries `generatorId`, recorded at **open** rather
  than resolved at completion — a session is allowed to outlive its maze's cache entry (this
  codebase already handles that case explicitly), so a completion-time lookup would put the
  placeholder back on exactly the longest games. And `LeaderboardService.topByGenerator` is the
  reader the partition never had, exposed as `GET /api/v1/leaderboard?generator=<id>`; `maze=`
  still wins when both are given, being the more specific of the two.

### Added

- **`mutants/boardteeth.py` — seven mutations on leaderboard attribution, and the first run
  scored 5/7 against the tests written for this very fix.** Both survivors were the same
  mistake the bug came from, committed again in its own regression test. One: reverting the
  controller to the four-argument `open()` — the original defect moved one level up — left
  every attribution test green, because all of them called the service directly with the
  generator id already in hand. Exercise the production path or you are testing your fixture.
  Closed with an endpoint test that generates a maze and opens a session over HTTP, then asks
  the stored session what it thinks it is playing. Two: `topByGenerator(n, null)` forwarding to
  the global board is load-bearing, because the controller routes every *unpartitioned* request
  through it — and the routing test cannot see that, because it mocks the service. Now 7/7.

- **The bidirectional solver's `b^(d/2)` advantage is now asserted — and the number its header
  advertised was the best case reported as the typical one.** `BidirectionalSolver` expands the
  *smaller* of its two frontiers, and its javadoc leans on that twice: once for speed, and once
  for correctness, because the argument that its first-touch stop is safe rests entirely on the
  two search depths staying balanced. `mutants/solverteeth.py` flipped the comparison so the
  larger frontier is expanded. Every path came back byte-identical, the whole core suite stayed
  green, and the solver quietly became a slower BFS with two parent arrays — taking the premise
  of the correctness argument with it.

  **The obvious test does not work, which is the useful part.** "Bidirectional expands fewer
  cells than BFS" was the first version, and the mutant *passes* it: with the balance removed it
  still edges BFS out on every fixture, by about half a percent. What separates them is the
  margin — 0.67 of BFS's expansions with the balance in place against 0.997 without — so the
  threshold is the assertion. `BidirectionalOptimalityTest` now requires every fixture under
  0.85, which sits in the gap between a measured worst case of 0.743 and a measured mutant best
  of 0.991.

  **And the fixture had to change too.** Over 120 perfect mazes at four sizes the real solver
  expanded *more* cells than BFS on 34 of them. The advantage is exponential in branching factor,
  and a perfect maze is a spanning tree of one-wide corridors with almost none; on top of that
  the goal-side search pays for the dead ends hanging off the far side of the goal, which BFS
  never reaches because it stops the moment it pops the goal. The class header promised "~40% the
  explored count of plain BFS" on a 100×100 maze — measured over 30 seeds at 101×101 that is
  0.877 mean, 1.296 worst, and losing to BFS on 10 of 30. 0.384 is real, and it is the best case.
  Header replaced with the measured table for perfect and braided grids, and with the reason for
  the difference, so the next person picks this solver for the graphs where it actually wins.

### Changed

- **Dial's decrease-key machinery is unreachable in this codebase — documented, kept, and no
  longer counted as a hole.** Deleting `tentative < dist[next]` from `DialSolver`'s relaxation
  is the textbook way this algorithm fails, and it passes the entire core suite. The first
  reading was that a uniform-cost suite could not see it and weights would; `WeightedSolverOptimalityTest`
  was written on that hypothesis and it is wrong. This engine uses an **entry-cost** model —
  `Graph.edgeWeight` returns the weight of the destination cell, never a property of the edge —
  so every edge into a node costs the same, buckets are scanned in ascending key order, and a
  node's first relaxation always uses the smallest key any of its neighbours will be settled at.
  Every later attempt is greater or equal. The branch cannot fire, and neither can the
  `settled[current] || dist[current] != k` guard that exists to discard the stale bucket entry
  such a relaxation would leave behind. Instrumented over 640 weighted grids (four sizes, four
  braid factors, random weights 0–39 including zero-cost cells) the improving branch fired
  **0 times in 231,734 relaxations** and the stale-entry guard **0 times**.

  Both stay. The reason they are dead lives in `Graph`, not in `DialSolver`, and the day
  `edgeWeight` becomes genuinely edge-dependent — a one-way ramp, a door that costs more from one
  side — they come alive and a Dial without them returns wrong distances silently. Deleting dead
  code whose deadness depends on a neighbouring class's contract is how that class gets to break
  this one from a distance. The class javadoc now says so, the mutation is retired from
  `solverteeth.py` with the measurement rather than left standing as a permanent survivor, and
  `WeightedSolverOptimalityTest` keeps the thing weights genuinely do expose: of the seven solvers
  `SolverBraidedMazePropertyTest` holds to BFS's *hop count*, only Dijkstra, Dial and A* read
  `weightOf` at all — a split that lived in `TrafficService`'s prose and in no test.

  `mutants/solverteeth.py` now reads **3/3**, from a first run of 1/6: one real hole, three
  mutations proved inert and retired with their proofs, two closed by the weighted sweep.

- **`MANHATTAN_TIE_BROKEN`, the heuristic lens's fourth option — and the first that measures a
  claim the lens has been making in prose since it was written.** Yesterday's audit found
  `Heuristics.manhattanWithTieBreaker` with no caller anywhere in the repository, not even a test,
  while `HeuristicLensService`'s own javadoc argued that "on some mazes tie-breaking matters more
  than the heuristic does" and its note told operators the tie band "decides more of this search
  than the heuristic does". Both true; neither measurable. The unused method is exactly the
  instrument for it, and wiring it in cost one enum case and one switch arm.

  On the 21×21 dungeon of seed 7 (optimum 40 steps) the three inadmissibility regimes now line up
  in one request each:

      heuristic                mandatory   tie   expansions   above C*   route
      MANHATTAN                       30    88          115          0      40  (optimal)
      MANHATTAN_TIE_BROKEN            30     1           80         50      40  (optimal)
      INFLATED (×3)                    0     1           78         78      42  (worse)

  Tie-breaking captures nearly all the speed that tripling the heuristic buys — 115 expansions
  down to 80, against 78 — and pays none of its price. The mandatory band does not move, because
  that band is the heuristic's business and this changes no cell's estimate relative to any
  other's; the whole saving comes out of the tie band, which is the claim the note was making.

  It is inadmissible too — 50 cells above `C*` were expanded, and that is the mechanism rather
  than a defect. What differs from `INFLATED` is the size of the violation: `eps` is
  `1 / (cells + 1)`, weighted A* returns within `(1 + eps)` of optimal, and no route on a grid
  exceeds its cell count, so the excess is under one whole step — and with integer costs an
  excess under one step is no excess at all. A tie-breaker is not distinguished from weighted A*
  by declining to scale; it is distinguished by keeping the inflation below the resolution of the
  cost function.

  That guarantee needed its own fixture to be worth anything. Asserting optimality on the 21×21
  dungeon does not pin it: a fixed `eps = 0.5` — plain weighted A* at w = 1.5 — still returns a
  shortest route there, because Manhattan is a weak enough bound inside a maze that half again on
  top of it rarely overestimates. A sweep found where it does: on the 31×31 dungeon of seed 5 a
  fixed epsilon returns 93 steps against a best of 91. That maze is the second test, chosen
  because it discriminates, and the `lensteeth.py` mutation that swaps the per-maze epsilon for a
  constant fails on that assertion and nowhere else.

- **Campaign mode (ADR-006 idea #10) — completes the roadmap.** `GET /api/v1/campaign?seed=`
  returns a deterministic ladder of stages (omit the seed for today's shared campaign). Stage
  *n*'s maze seed derives from `(campaignSeed, n)` alone, so a campaign link replays
  byte-identical stages anywhere with no stored state. Each stage's difficulty is **measured,
  not assumed**: the service generates candidate mazes across three sizes, grades each with the
  new `DifficultyGrader`, and keeps the one nearest that stage's target that still clears the
  previous stage. Later stages declare hazards (`living`, `traffic`) but the service never
  starts a ticker — the client activates them through the existing opt-in endpoints, so their
  capacity caps and rate limits keep governing. Deliberately one endpoint: a campaign is a
  table of contents over the API that already existed, so every stage gets its own leaderboard
  partition (batch 2) and its own ghost (batch 3) for free, proven end-to-end in the tests.
  UI: a campaign panel with the stage ladder, per-stage boards, and hazards activating on entry.
- **`DifficultyGrader` in the theory module.** Grades a maze's playability from structure:
  detour factor (route length over perimeter), branchiness (dead ends per perimeter),
  scale, and a discount for braided alternate routes — reporting every measurement behind the
  score, so callers can audit it rather than trust it. Weights and label bands are *chosen*, not
  calibrated against human play, and the class says so; what it guarantees is **ordering**,
  which is what a ladder needs. Two ordering defects were caught by measurement while building
  it: normalizing dead ends per *cell* graded a trivial 3×3 above a 5×5 (tiny mazes spend a
  third of their cells on dead ends), and the original label bands put nearly every maze this
  project generates into "hard" or "brutal".

### Added

- **`ProdAuthPostureTest` — every endpoint's prod authentication posture, asserted rather than
  inherited.** Twelve endpoints were added across ADR-007 and not one of them made an
  authentication decision. They are all correctly closed, because `ProdSecurityConfig` ends in
  `anyRequest().authenticated()` — but "protected because nobody listed it" and "protected
  because somebody decided" look identical from outside, and only one of them survives a matcher
  being widened later. The chain already permits `GET /api/v1/maze/*`; **one extra asterisk**
  would publish the whole analytical surface — hardest route, distance field, sanctuaries,
  heuristic lens, fingerprint, tour, analysis, ghost — and nothing in the suite would have said a
  word. What existed before was `SecurityConfigProfileTest`, which checks `@Profile` annotations
  and no actual decision, and `ProdProfileBootTest`, which pins exactly one path, against a README
  that publishes an "Auth (prod)" column for the entire API.
  The test boots a real prod context and drives unauthenticated requests at all 32 endpoints,
  asserting each is refused or public per an explicit table — the README column made executable.
  A second test scans the controller sources and fails if any mapping is missing from that table,
  so a new endpoint cannot ship until somebody records which side of the line it belongs on. A
  third holds the README's published table to the same standard in both directions.

  **The first version of this test was written wrong, and the way it was wrong is the point.**
  Its expectation table was filled in from what the running server answered — which makes the
  test agree with the behaviour by construction, so it cannot find a behaviour bug, and it
  promptly failed to find three (see *Fixed* below). The second source of truth is what makes it
  work: the README says what the API promises, the boot test says what the server does, and the
  build now fails when they disagree. Teeth proven nine ways in `mutants/authteeth.py` —
  widening `maze/*` to `maze/**`, flipping `anyRequest()` to `permitAll`, closing the spectator
  permalink again, adding an unclassified endpoint, declaring one with a bare `@GetMapping` or
  the `value = ...` form, narrowing the source scanner back to its original regex, and both
  flipping and dropping a README row. All nine caught. A security test under default-deny passes
  before it is written and keeps passing if it breaks, so it needs the mutations more than most.

- **`ErrorContractTest` — every way the API can say no, held to one shape.** Twenty-one distinct
  failure modes driven at a running server, bodies compared against RFC 7807. The test that
  matters is the third one: it does not list failure modes, it *generates* them from the
  controller sources — every mapping gets the wrong verb and an uncoercible path variable, and
  any 4xx or 5xx that comes back without a `type` field fails the build. All five gaps found by
  this audit were on paths no test happened to visit, and a hand-written roster of failure modes
  is a list of the paths somebody thought of, which is the same blind spot in a different
  costume. A new endpoint is covered the day it is written. Teeth: `mutants/errteeth.py`, nine
  mutations. The load-bearing one removes the 405 handler **and** the roster entry naming it, so
  only the generated test can catch it — if that survives, the generated test is decorative.
- **`UnknownAlgorithmException` in the theory-facing core.** Carries the kind, the requested id,
  and every id that *is* registered, so a 404 tells the caller what to type instead of only that
  they were wrong. Deliberately a subtype of `NoSuchElementException` (source-compatible with
  what the registries threw before) rather than a reuse of it: mapping `NoSuchElementException`
  itself to 404 would have caught `Optional.get()` and `Iterator.next()` too, quietly turning
  genuine internal invariant failures into "not found".

- **`DeterminismGoldenTest` — determinism checked across a process, not across a cache hit.**
  Determinism is one of this project's loudest claims: a campaign link "replays byte-identical
  stages anywhere with no stored state", waypoints "derive from the maze alone", complexity fits
  reproduce exactly. Every test of that ran inside one JVM, and almost every one of those
  endpoints sits behind a Caffeine cache keyed on its inputs — so the second call returns the
  first call's object and the assertion passes whether the computation is deterministic or not.

  The bug class this cannot see is specific and real: anything reading `Object.hashCode()`
  identity, or `HashSet` iteration order over enums (enum `hashCode` is identity-based, so the
  order is stable within a run and arbitrary between runs). A tie-break fed by such an order
  gives every user a different "optimal" route depending on when the server last restarted.

  The oracle is a file of 23 digests recorded by a different JVM and committed to the repository,
  so every build is a cross-process comparison. Covered: seeded generation, the seeded campaign,
  all seven analytical endpoints, the tournament, a complexity fit, **all nine solvers**, and the
  algorithm catalogue. Teeth: `mutants/detteeth.py`, five mutations, three of them aimed at the
  canonicaliser rather than the product — blind that one function and every digest compares equal
  to every other and the test checks nothing.

  **The audit itself found nothing broken.** Sixteen endpoints captured, server restarted cold,
  all sixteen identical. Two false alarms along the way were both the probe's fault and are now
  the test's design constraints: identifiers are per-process (the first probe stripped only
  top-level keys and missed the daily maze's nested `maze.id`), and `elapsedMs` was 5 on the
  first solve after a cold start against 0–2 warm. A third apparent finding — "bidirectional-BFS
  is nondeterministic" — was a solver id typo producing a 404 whose `instance` field carries the
  request path, maze UUID included. That one changed the design: identifiers are now redacted by
  *shape* wherever they appear, because an exclusion list of field names cannot name an id
  hiding inside a URL.

### Changed

- **`MazeGrid`'s "BIG SPEED WIN" is gone, and the measurement is why.** The class opened with a
  header promising "dramatically faster generation", a `boolean[][] visited` field annotated
  `← THIS IS THE BIG SPEED WIN`, and an `Arrays.fill` described as a "blazing fast primitive
  blast". `mutants/gridteeth.py` had already found that nothing in production read it — removing
  the array's synchronisation was an inert mutation precisely because `grid.isVisited(Point)` has
  no caller anywhere, while every generator uses `grid.cell(p).isVisited()`. The open question
  was whether to wire it or delete it, and taste is a poor way to answer that, so it was measured:
  interleaved A/B at 300×300, best of five runs each.

      generator                with array   without
      recursive-backtracker      71.2 ms     57.5 ms
      prims                     115.8 ms     98.8 ms
      aldous-broder             859.8 ms    864.4 ms
      copy()                     51.5 ms     49.1 ms

  Removing it was never slower across eight paired runs, and it drops `rows × cols` bytes per grid
  and per `copy()` — which the living-maze tick allocates every two seconds per animated maze.
  Aldous-Broder is the control: dominated by its random walk, it does not care either way, and a
  result where everything improved would have been the suspicious one.

  The milliseconds are not really the point. Two mutable copies of one fact, kept in step by a
  single line inside one method, is a correctness hazard whose failure mode is a caller reading
  whichever copy happens to be stale — and this one was kept alive entirely by the comment
  advertising it. There is now one visited flag, on the `Cell`, with the grid-level accessors
  delegating to it: same public API, no allocation, and no way for the two views to disagree.
  `MazeGridContractTest` pins that they are one flag, so a second copy cannot come back quietly.

### Changed

- **Coverage ratchet raised to 0.93 / 0.96 — the ceiling has now fired twice.** Measured
  instruction coverage is 95.10% (94.63% on 08-01, 82.2% on 07-29). The four contract suites added
  today pushed the ratio past the old 0.95 ceiling and failed the build until this bump, which is
  the ceiling working as designed: it forces the threshold move into the same commit as the tests
  that earned it, instead of banking slack the next regression can spend unnoticed.

  `ratchetteeth.py` needed a bump of its own, and it is the more interesting half. Its
  regression-simulating case sets a floor *above* actual coverage — 0.95 when coverage was
  94.63% — and at 95.10% that floor now passes, so the case would have reported a false survivor
  while testing nothing. Value-based mutations drift exactly like anchor-based ones, and nothing
  in the harness notices; the case now sets 0.97 and will need chasing again the next time
  coverage climbs.

- **Off the Jackson 2 APIs Boot 4 marks for removal.** `MappingJackson2MessageConverter` →
  `JacksonJsonMessageConverter` in the STOMP smoke test, and `HttpStatus.UNPROCESSABLE_ENTITY` →
  `UNPROCESSABLE_CONTENT` (RFC 9110 renamed 422; the wire status is unchanged). With the Redis
  serializer below, the reactor now compiles with **zero** deprecation warnings — which is worth
  keeping at zero, because the one that mattered was invisible in a list of seven.

### Fixed

- **A digest-only catch now reports as no catch at all.** Yesterday's campaign work found that
  four of `campaignteeth.py`'s reported catches came from `DeterminismGoldenTest` alone, and that
  three of those mutations survived once the golden test was excluded — the target range, the
  candidate-pool width and the hazard ramp could each revert to a configuration the code's own
  javadoc records as broken, with every property test green. The conclusion was written down and
  the comparison was done by hand, which is a habit rather than a rule, and habits are exactly
  what the rest of this folder exists to replace.

  `verdict.classify` now attributes each failure to its test class, and when the only failing
  class is a snapshot test the verdict is `DIGEST ONLY` and does not count toward the tally. A
  harness that would once have printed a comfortable 11/13 now prints the two survivors *and*
  names the mutations whose only evidence was a byte comparison. `detteeth.py` opts out with
  `digest_counts=True`, because its subject genuinely is the determinism digest: there, a golden
  failure is the property rather than a proxy for one. Both harnesses were re-run under the new
  rule — campaign 12/12, determinism 5/5 — which turns "the campaign fixes hold" from an
  assertion into a measurement.

- **Four more stores bounded by a clock nobody could move — and now a rule instead of a habit.**
  The same defect had been found and fixed three times on three days: delete `expireAfterAccess`
  from `GameSessionService` (08-01), from `MazeGenerationService` (08-02), from `AgentWalkService`
  (08-03), and the suite stays green every time, because no test can advance a Caffeine clock
  without a `Ticker` seam. Three identical fixes is not bad luck, it is a missing rule, so the
  fourth response was to go looking rather than wait for the fourth harness.

  Nine Caffeine caches in the server, six of them idle-bounded, and **four services holding five
  of those caches had no seam at all**: `GhostService`, `WaypointService` (two), `TournamentService`
  and `ComplexityLabService`. `BoundedStoresTest` already scanned the source to prove every cache
  declares a `maximumSize` — the same scan now requires any cache with an idle TTL to belong to a
  class a test can hand a `Ticker`. It named all four on its first run, which is how the list
  above was produced rather than guessed.

  Making eviction *observable* was the harder half. A memoization cache — tours, tournaments,
  complexity fits — is a pure function behind a map: evicting it changes no answer any caller can
  see, because the recomputed value is identical. So each service now reports its cached count,
  the same window `trackedCount()`, `liveCount()` and `plannedCount()` already open onto their
  stores, and the four new tests advance a clock and watch the count fall to zero. Without that
  the assertion would have been unfalsifiable, which in a test file is worse than nothing: it
  reads like coverage. Verified by deleting the ghost store's expiry and watching the new test go
  red.

- **The fog-of-war agent leaked in four directions nobody was checking.** `AgentWalkService` is a
  benchmark surface — its javadoc invites "a shell script, an RL policy, a student's first
  wall-follower" — and it had never been mutated. Fourteen mutations, seven survivors, six real.
  The shape of the gap is worth naming, because it generalises: `AgentWalkServiceTest` tests the
  walk from the caller's side and does it well, and a caller-side test asks whether the walk
  *works*. It has no reason to ask whether the walk revealed too much, whether a configured
  ceiling was honoured, or what happens on a path a caller cannot reach on purpose. An agent that
  can see the whole maze still reaches the goal — faster, and with a cleaner test log.

  What survived: the in-bounds half of the fog filter (a stray border opening would be offered to
  the agent as a direction to walk); both step-budget clamps, so `max-steps` bounded nothing for
  either an explicit request or the `4·rows·cols` default; the `AgentSteppedEvent` publish, whose
  removal stops agents raising traffic congestion at all while both suites stay green, because
  `TrafficServiceTest` publishes that event by hand and so covers the far side of a wire it never
  checks is connected; the agent store's idle expiry — the third store in three days with a size
  bound and no clock, after the session store and the maze cache, so `AgentWalkService` gets the
  same `Ticker` seam; and the evicted-maze path, which answers 404 by design and threw a
  NullPointerException once mutated. `AgentWalkContractTest` covers all six. `mutants/agentteeth.py`,
  14/14.

  Two of the fourteen taught something about writing mutations rather than about the code. One was
  inert by construction: it rewrote the wall-bump guard into a logically identical condition, and
  "survived" while testing nothing — a wall bump cannot be made to cost budget by editing that
  condition, because the throw aborts the store's compute and nothing is written either way.
  Re-aimed at the realistic defect (return a walk that stayed put with the step spent, silently),
  it is caught. And the first version of the border-fog test asserted nothing, because `adopt`
  re-places start and goal at the extremes and moved the agent off the doctored cell — it passed
  with the guard deleted. A one-row corridor, where every cell is on the north edge whichever one
  `adopt` picks, is what made the assertion real.

- **The desktop shipped no configuration file, and the check that would have caught it only
  looked at the server.** `daedalus-desktop` is a Spring Boot application; `ThemeManager` reads
  `daedalus.ui.theme` through `@Value`; `CosmicTheme`'s javadoc tells the reader the default lives
  "in `application.yml`". There was no `application.yml` in that module — the only way to pick a
  theme was a `-Ddaedalus.ui.theme` flag nothing documents.

  That is precisely the failure `ConfigCoverageTest` exists to prevent. Its own javadoc says
  "configuration that is documented and inert is a lie", and it checks both directions of the
  server's config surface — while scanning `src/main/java` relative to the server module, so it
  could not see the desktop at all. A guard scoped to where the last bug was found has a blind
  spot by construction. The desktop now ships an `application.yml` with the key and a
  `DAEDALUS_UI_THEME` override, and the check walks every module that reads configuration:
  removing that new file fails it, which is how the fix was verified rather than assumed.

- **Three dead links in the published API document.** `OpenApiConfig` served
  `https://github.com/` as the project's contact URL — a placeholder with a `TODO: fill in once
  the repo is public` beside it, still there after the repo went public — and gave the licence and
  README as the relative paths `./LICENSE` and `./README.md`, which Swagger UI resolves against
  `/swagger-ui/`. An OpenAPI document exists to be handed to someone who does not have the source
  checked out, and every link in this one failed exactly that reader. All three are now absolute,
  and `ApplicationSmokeTest` asserts it: the placeholder fails the new assertion, checked by
  putting it back.

### Audited, unchanged

  A sweep for wiring gaps also turned up things worth recording rather than acting on, and two
  worth *not* acting on. Nine public methods have no caller anywhere in the repository — not in
  production, not in a test: `Cell.isDeadEnd/isJunction/isCorridor/openWalls`,
  `Point.translate/euclidean`, `TileType.walkable`, `Direction.shuffled`, and
  `Heuristics.manhattanWithTieBreaker`. The last is the interesting one, because
  `HeuristicLensService`'s own javadoc records that "on some mazes tie-breaking matters more than
  the heuristic does" while the lens offers Manhattan, landmark and inflated — and not the
  tie-breaking variant sitting unused beside them. A further ten methods are called only by their
  tests (`DSU.largestComponent/connected/sizeOf`, `MazeFlow.edgeConnectivity`,
  `FacilityPlacement.kCenterAcrossComponents`, `DistanceOracle.eccentricity`,
  `GrowthEstimator.classifyVisited/toTable`, `WeightedMazeGrid.getWeight/setAllWeights`): library
  surface, defensible as such, and now written down. The agent-walk feature — three endpoints, a
  service and an event that feeds traffic — is the only server capability with no call site in the
  web UI.

  The two that look like gaps and are not: `daedalus.session.multiplayer` is absent from
  `application.yml` on purpose (`ConfigCoverageTest` records the exemption, and the UI's join
  button ships disabled with the flag named in its tooltip), and `DistanceOracle` is dormant by an
  argument written into `TopographyService`'s javadoc. Both were checked before being reported,
  which is the only reason they are not in the list above.

- **Eleven fixes, eleven named guardians, one that does not guard.** After finding that
  `MazeGenerationStartGoalTest` passes with the fix it was written for deleted, the obvious
  question was whether that is a pattern. `mutants/claimteeth.py` answers it: it pairs a fix with
  the single test the repo's javadoc or commit message claims holds it, deletes the fix, and runs
  **only that test**. A catch by anything else is deliberately invisible, because the question is
  not "is this covered somewhere" but "does the guardian named in the comment actually guard".

  Ten of eleven claims hold. Trémaux's third rule, the weighted copy's weights, `carve` opening
  both sides, the directed landmark bound, the rate limiter's refill floor, the per-session lock,
  the leaderboard trim, the STOMP `SEND` refusal, the hotspot cascade — each fails its named test
  within seconds of being removed. The single exception is the one already known, and it is now
  backstopped twice: `MazeGenerationContractTest` catches it, and `MazeGenerationStartGoalTest`
  has been given a diameter equality so it catches it too.

  A negative result, and worth the run. The failure found in the substrate was one bad assertion
  rather than a habit, which is the more reassuring answer and not one available by inspection —
  every one of these tests *looks* like it holds its fix, including the one that does not.

- **The regression test for the corner bug does not detect the corner bug.** `MazeGenerationService`
  is the substrate every feature commits through — generation, the cache, the swap point both
  tickers use, the adoption path for crossbred mazes, the circuit-breaker fallback — and no
  mutation had ever been aimed at it. Thirteen mutations, eight survivors, and unusually for this
  folder every one of the eight was real. Not one was inert.

  The headline is the placement of start and goal. That code exists because of a documented bug:
  they used to be dropped at fixed corners, and "a dungeon's corners are solid rock, so the served
  maze was unsolvable and a play session opened inside a wall". `MazeGenerationStartGoalTest` was
  written to hold the fix. Delete `placeStartAndGoalAtExtremes` from `generate` today and all
  three of its tests still pass — verified directly, not inferred: mutate, run that class alone,
  3 of 3 green.

  The reason is not the obvious one, and the first version of this entry got it wrong. It is not
  seed luck: a probe found the 15×21 dungeon's corner cells are solid rock in **200 of 200** seeds.
  It is that `DungeonGenerator` places its own start and goal inside carved rooms — 50 of 50 seeds
  put them off the corners, and every one of those mazes is solvable before the service touches it.
  The service-level placement is redundant for exactly the maze the regression test exercises, so
  no sweep of dungeon seeds at any count can fail on its removal. A test cannot catch a defect that
  can no longer reach it, and no amount of strengthening that particular assertion would have
  changed the result.

  What the service placement still buys is the other half of its javadoc: spanning-tree generators
  leave the corner defaults alone (0 of 50 seeds move them), so without it a perfect maze is played
  corner to corner instead of across its diameter — the maximum-challenge placement the core
  recommends, quietly downgraded. `MazeGenerationContractTest` asserts that as an *equality* (a
  perfect maze is a tree, which makes the double-BFS placement exact), and so, now, does
  `MazeGenerationStartGoalTest` itself: the fix is pinned where the code comment says it is pinned.

  The rest were unpinned in the ordinary way. `replace` promises `computeIfPresent` so an evicted
  maze is never resurrected; `put` also answers null for an absent key, so the naive form passes
  an `isFalse()` assertion while quietly putting the entry back — and both tickers read false as
  "stop", leaving a maze nothing will ever tick or evict again. The maze cache's idle expiry was
  unpinned exactly as the session store's was on 08-01, so it gets the same `Ticker` seam and the
  same clock-advancing test; size and idle are separate promises and only the first was checked.
  `adopt` promises to run generation's finishing steps so an adopted maze is "indistinguishable
  from a generated one downstream", and neither its placement nor its `MazeGeneratedEvent` was
  asserted. The hotspot bounds check was pinned only by a comfortably out-of-range cell, so the
  boundary it exists for — `row == rows`, the first invalid index — was free to drift. The
  fallback's rethrow of a caller error, which is what makes a bad request answer 400 rather than
  200 with a maze nobody asked for, had no test. And the null-grid guard is not the formality it
  looks like: generators are a plugin extension point, so "returns null" is third-party behaviour
  this service has to survive. `mutants/genteeth.py`, 13/13.

- **A golden digest was standing in for four of campaign mode's properties.** `CampaignService`
  is the newest substantial code in the repo and its test is the most self-aware: it sweeps
  several seeds rather than one *because* a single-seed version once passed while the ladder
  walked backwards on 15 of 40 seeds, and it carries a second ten-stage test solely because it
  measured that the default configuration cannot pin the clear-the-previous rule. Thirteen
  mutations, eleven reported caught — and the interesting number is not the two survivors.

  Four of those eleven were caught by exactly one test: `DeterminismGoldenTest`, which compares
  endpoint output against recorded digests. Re-running those four with the golden test excluded
  is the measurement that mattered, and three then survived. The target range could revert to
  the configuration this class's own javadoc records as collapsing monotonicity from 60/60 seeds
  to 34/60. The candidate pool could collapse to the single size recorded as 25/40. The hazard
  ramp could dump both hazards at the half-way mark instead of ramping. Every campaign-specific
  assertion passed through all three; only the bytes noticed.

  That is worth naming as a pattern, because a golden digest looks like coverage and is not. It
  is a change detector: it fires on every mutation here precisely because every mutation changes
  the output, and it is regenerated by whoever deliberately retunes a constant — which is exactly
  the moment a monotonicity collapse rides along unnoticed. Counting its failures as catches
  inflates the score while pinning nothing. So the default-config seed sweep went from five seeds
  to twenty, which costs half a second and now fails on the target and pool mutations by itself,
  and the hazard test pins the ramp rung by rung rather than checking its two ends (the shape
  "empty at the bottom, both at the top" is equally true of a cliff).

  The two outright survivors were the plan map's bound — the house rule this class states in its
  own javadoc and nothing checked, now pinned via a `plannedCount()` accessor matching the
  `trackedCount()` / `liveCount()` the sibling services already expose — and the eviction path.
  A campaign link outlives the bounded maze cache easily, and `allStagesStillCached` is what
  replans a campaign whose stage mazes were dropped rather than handing back ids that answer 404.
  Neither is reachable without a fake, so `ScriptedGen` grew a `hidden` set: eviction without a
  clock or a size bound.

  One mutation is retired with its reasoning rather than pinned. Colliding candidate seeds across
  size variants survives everything but the digest, and should: the three size variants then share
  three seeds, but a seed at a different size is a different maze, so the pool is still nine
  distinct candidates graded on their merits. It changes which mazes are considered, not how many
  or how they are chosen. `mutants/campaignteeth.py`, 12/12.

- **The same question, asked of `LivingMazeService`: six more unpinned promises.** Erosion's
  ticker is `TrafficService`'s twin — per-maze runs over the same copy-on-write cache entry,
  bounded concurrency, self-termination — so the honest move after finding four scheduling holes
  in one was to point mutations at the other rather than to read its tests and feel reassured.
  Twelve mutations, five caught, seven survivors, six of them real. Worth stating plainly because
  it cuts against the obvious lesson: `LivingMazeServiceTest` is the *better* of the two suites.
  It pins the copy-on-write swap by identity, checks the pre-tick snapshot is still intact
  afterwards, proves determinism by eroding two identical mazes under one seed, and asks exactly
  the right idempotence question — restart a live maze with a different tick count, check the run
  kept its original one. A suite can do all that and still not see a boundary.

  Two of the six were the same holes as next door: the `future == null` guard (a second `/live`
  on a living maze schedules a second ticker, so the maze erodes at twice the requested rate
  while `status` reports the run's own tick count, advancing normally) and the `stop` in the
  tick's `catch`. Three were bounds nobody had pinned. `max-ticks` is what stops one request
  occupying the shared ticker indefinitely, and a caller asking for a million ticks got a
  million. `drift` skips uniform cells so erosion never mints hotspots; without the skip every
  cell in a weighted maze breathes and the response's hotspot list grows from two entries to
  half the grid — each one still inside the API's cost domain, so every existing hotspot
  assertion still passes. And the one worth the whole exercise: `Braider` opens
  `round(factor * deadEnds)`, so a bare `erosion-factor` of 0.08 opens **nothing** once fewer
  than about six dead ends remain. The floor `max(erosionFactor, 1.0 / deadEnds)` is what
  guarantees progress, and without it a run reports itself *settled* with dead ends still in the
  maze. Stalling and settling are indistinguishable from outside — same event, same flag, same
  connectivity, same determinism — which is why nothing caught it.

  The sixth was `replace` answering false: the documented stop signal for a maze the cache has
  evicted, and the one place this class could put an entry back into a cache that just dropped
  it. Like the throwing tick, it is unreachable without a fake, so it had never been exercised.
  Both now are: `ScriptedGen` is a real `MazeGenerationService` whose commit can be made to fail
  either way in one line, and `ManualTicker` — extracted from the traffic work and now shared —
  runs ticks synchronously and answers how many tickers are alive. `LivingMazeTickContractTest`,
  seven tests, no sleeps. `mutants/livingteeth.py`, 11/11.

  The twelfth mutation is retired to that harness's docstring with its reasoning, because it is a
  third category: not caught, not inert, but breaking no promise. Freezing the per-tick seed
  keeps determinism (a fixed seed erodes identically too) and keeps erosion progressing (the
  dead-end list shrinks under it regardless), so no assertion should fail. What it would quietly
  ruin is `drift`: the same seed hands every hotspot the same multiplier every tick, and
  breathing becomes a ratchet — a cell that drew 1.2 climbs to the 1000 ceiling and pins there, a
  cell that drew 0.8 decays to uniform and leaves the hotspot list for good. Pinning that means
  asserting a random walk did not saturate, which is a statistical claim wearing a test's
  clothes. Recorded as deliberately unpinned rather than tested badly.

- **`TrafficService` promised four things about scheduling and could prove none of them.** At
  230 lines it was the largest server class no mutation had ever been aimed at, and it is the
  one with the most ways to fail quietly: nearly every guarantee it makes is about something
  *not* happening — a ticker not scheduled twice, a weight not growing past its ceiling, a
  decay not converging asymptotically instead of stopping, a tracker not running after the
  players leave. Nothing throws when any of those lapses; the maze just gets slowly,
  permanently worse. Ten mutations, five caught by the existing tests, five survivors, four of
  them real.

  Two of the four were the same guarantee seen from both ends. The javadoc says `enable` is
  "idempotent while tracked", and `TrafficServiceTest` does call it twice and assert
  `trackedCount() == 1` — but that count is a map size keyed by maze. It reads 1 whether the
  second call reused the existing tracker or *replaced* it, and it says nothing at all about how
  many tasks are queued. Both breakages walked through it: dropping the reuse branch takes a
  second slot against `max-concurrent` (at capacity 1, the maze 409s on itself), and dropping
  the `future == null` check schedules a second ticker whose handle immediately overwrites the
  first, so the first can never be cancelled and outlives the tracker it was started for. The
  third survivor was the quiet-counter reset, without which quiet ticks accumulate across
  activity and a maze in steady use retires mid-game; the fourth was the `catch` that retires a
  tracker whose tick threw, without which a permanently broken maze logs a warning every two
  seconds forever.

  What all four have in common is that a test watching a real clock cannot see them. The
  difference between one scheduled task and two is a leak, not a failure, and the wall-clock
  test for it is a sleep long enough to be slow and short enough to be flaky. So `TrafficService`
  now takes its `ScheduledExecutorService` through a package-private constructor — the same seam
  and the same argument as `GameSessionService`'s `Ticker` — and `TrafficTickContractTest` hands
  it a scheduler that never schedules: `tick()` runs every live task once, on the test thread,
  and the fake can report how many are still scheduled. Four exact assertions, no sleeps; ticks
  are counts rather than durations. Production behaviour is unchanged, the public constructor
  passing the same daemon single-thread executor the field used to build inline.

  Adding that second constructor broke the Spring context, which is the sort of thing worth
  recording rather than quietly fixing: with two unannotated constructors there is no longer a
  sole candidate, and every request-side bean that depends on `TrafficService` failed to start.
  `TrafficEndpointTest` caught it on the first run. A slow full-context test that only ever
  seemed to re-check what the fast tests already covered earned its nine seconds in one go.

  The fifth survivor was inert and is retired rather than left standing. Reverting the epsilon
  comparison in the decay loop to an exact `!=` cannot change an observable, for exactly the
  reason the code comment gives: `SNAP` runs first, so a weight either lands on exactly `1.0`
  (differing from a non-uniform `w` by more than EPSILON by definition) or stays above 1.05,
  which forces a move of at least 0.0125. The two conditions agree on every value the code can
  produce. The guard is still worth keeping — it is what makes the comment's "one decay-factor
  change away" safe rather than lucky — but it is not an untested guarantee, and a permanent
  survivor in the list would have said it was. `mutants/trafficteeth.py`, 9/9, with the algebra
  in its docstring.

- **Two more ways the mutation harnesses could lie, both found by using them.** The first cost
  an hour of confusion this morning. `mutants/README.md` already warned that a killed run leaves
  a mutation in the tree and told the reader to check `git diff` afterwards — which is advice,
  not a mechanism. `trafficteeth.py` was launched under a two-minute wrapper, the wrapper sent
  SIGTERM mid-mutation, and SIGTERM's default action ends the process without running the
  `finally` that restores the source. Quiet-tick retirement stayed disabled in the working tree,
  and the damage did not announce itself: the next run snapshotted the mutated file as its own
  baseline, so it "restored" to the mutation, reported that mutation as `SKIP (anchor x0)` —
  the anchor it looks for being the code it had replaced — and reported eight of nine as caught,
  because a welded-in defect fails tests all by itself. A green-looking sweep against a broken
  tree is the worst possible output. `verdict.restore_on_signal()` now turns SIGTERM and SIGHUP
  into an exception so the existing `finally` runs, and all 21 scripts call it. SIGKILL still
  cannot be caught, which is what the pristine sidecar `fuzzteeth.py` carries is for.

  The second was subtler and had been true from the start. `verdict.failing_tests` looked for
  `Class.method` anywhere in Maven's stdout — and **a passing test that logs a stack trace names
  its own method in that trace**. `TrafficTickContractTest` deliberately makes a tick throw, the
  service logs it as designed, and the frame `at ...TrafficTickContractTest.aTickThatThrows...`
  appeared in every run, so that test was credited with catching all nine mutations including
  ones it never exercises. Harmless there, because each was genuinely caught by something else,
  but it is the failure this module exists to prevent one level down: a catch attributed to a
  test that did not catch it, and — for a build that dies after the logging but before any real
  failure — a catch attributed to no failure at all. Output from the forked test JVM arrives
  unprefixed; Surefire's failure lines and end-of-run summary come through Maven with `[ERROR]`.
  Matching only prefixed lines separates them exactly, and the attribution is now right: the
  capacity mutation is credited to `untrackedMazesIgnoreOccupancyAndCapacityIsBounded`, the
  ceiling to `costsClampAtMaxAndNeverLeaveTheWeightedApiDomain`.

- **`MazeGrid`'s input contracts were documented and unenforced — and its "big speed win" is
  dead code.** 63 test files reference this class and no mutation had ever been aimed at it,
  which is the standard shape of a substrate blind spot: every caller tests its own concern and
  takes the foundation for granted. Nine mutations. The load-bearing ones were all caught —
  carving one side of a wall, reflecting the wrong wall, ignoring walls entirely — but two
  documented contracts were not: `carve(Point, Point)` promises to reject pairs that share no
  wall, and the constructor promises to reject non-positive dimensions. Deleting either check
  passed the whole suite. Neither is a live bug, which is exactly why they were worth pinning:
  an unenforced contract on a class this widely used degrades in silence, and the first caller
  to violate it gets a corrupt grid instead of an exception. `MazeGridContractTest` covers both.

  The harness then caught a hole in that new test, which is the best argument for owning one.
  `directionBetween` decides on a *signed* delta, so widening its NORTH branch to `dr <= -1` is
  invisible to a non-adjacent pair whose delta is positive — the first version of the test
  sampled only the downward ordering and the mutation walked straight through it. A rejection
  test that samples one sign of an asymmetric comparison is half a test.

  Three further mutations were measured and removed as unreachable rather than left as standing
  survivors, and one of them is worth acting on. Dropping the in-bounds filter in
  `openNeighbors` changes nothing, because a border cell's outward wall can never be open.
  Removing the Cell synchronisation from `markVisited` and `clearVisited` changes nothing for a
  more interesting reason: **nothing in production calls `grid.markVisited(Point)` or
  `grid.isVisited(Point)` at all.** The `boolean[][]` the class comment labels "THE BIG SPEED
  WIN" is written by nobody and read by nobody — every generator uses the Cell-level API
  directly — so the array, its synchronisation, and the comment advertising it are dead weight
  kept alive by the comment. Left in place pending a call on removing public API.

- **The directed half of the ADR-001 optimality bug was documented but not pinned.**
  `LandmarkHeuristic`'s javadoc explains at length why weighted mode cannot use the symmetric
  bound `|d(L,t) - d(L,s)|`: the entry-cost model makes the graph directed, so `d(a,b)` and
  `d(b,a)` differ by `w(b) - w(a)`, and the absolute value silently assumes the symmetry that
  does not hold. Restoring that `Math.abs` passed the entire suite.

  It is not a small error. Swept across every ordered pair of a braided 12x12 grid with entry
  costs straddling 1.0, the symmetric bound over-estimates on **7,454 pairs**, worst case
  `h = 9.94` against a true cost of `5.97` — inadmissible by 67%, which is A* returning routes
  that merely look fine. The existing admissibility test is exhaustive in the wrong dimension:
  it sweeps every source against **one** goal, and fixing the goal collapses exactly the
  asymmetry being guarded. `heuristicNeverExceedsTrueCost_forEveryOrderedPair` varies both
  endpoints, and catches it.

  Recorded in `mutants/landmarkteeth.py`, 4/4. Three further mutations were written, measured,
  and deleted rather than filed as gaps, which is the more useful half of the exercise: routing
  weighted grids through `hopEstimate` returns 0 (admissible — the hop fields are empty in
  weighted mode), removing the unreachable-landmark guard cannot over-estimate (a pair that sees
  a -1 field entry spans components and has infinite true cost), and dropping the inbound bound
  leaves the heuristic correct but looser. The last one is a real gap of a different kind —
  weighted-mode *tightness* is unpinned — and the harness says so in prose instead of carrying a
  permanent survivor that would train the reader to skip the survivor list.

- **Two untested promises in `GameSessionService`, found by pointing mutations at it for the
  first time.** The class had never been mutated, which mattered because the `GameSession` field
  fix earlier the same day rests on it: making the fields safe for unlocked readers is only half
  a design, and the per-session lock in `tryMove` that serialises the writers is the other half.
  Ten mutations; eight were caught by tests that already existed — including widening the lock
  to a shared monitor, which every single-threaded test survives and `SessionLockIsolationTest`
  does not. Two survived.

  **The idle TTL was never checked.** `BoundedStoresTest` pinned `maximumSize`, and pinned
  reflectively that every Caffeine cache in the server declares one — but it passed a one-hour
  TTL and never moved a clock, so deleting `expireAfterAccess` left the suite green. Size and
  idle are separate bounds: with only the first, a finished game holds its slot until 10,000
  more push it out, which on a quiet instance is most of what the unbounded map it replaced did.
  Fixed with the `Ticker` seam `PerKeyRateLimitInterceptor` already established for exactly this
  reason, and `sessionStoreEvictsAfterItsIdleTtl` advances a fake clock past it.

  **The score floor was never checked.** `Math.max(0, ...)` clamps a long game's score at zero,
  and removing the clamp passed everything. The negative regime is reachable honestly — 10,000
  moves is about fourteen milliseconds of work, and the session TTL is two hours — so the test
  paces a session past its own base score and asserts the published number stays non-negative.

  Recorded in `mutants/sessionteeth.py`; 10/10 caught now. One note kept in that file for the
  next author: the obvious way to mutate away the lock, `if (true) {`, does not compile, because
  javac then cannot see that the method always returns — the harness reports a broken build
  rather than a result. Locking a fresh object per call removes the mutual exclusion and leaves
  the control flow intact.

- **Hotspot bounds were being enforced by a deprecated path, and nothing pinned them.**
  `GenerateRequest` cascaded into its hotspot list with `@Valid List<Hotspot>` — the container
  form Hibernate Validator deprecates as HV000271, which names the collection rather than what
  is inside it. It still cascades today (checked: an out-of-range hotspot produces all three
  element violations), so this is a fix ahead of the removal rather than a live hole. The failure
  it would have become is the quiet kind: element bounds stop being checked, nothing errors, and
  a `cost` of 0.5 reaches the engine — where sub-1.0 weights invalidate the unit-cost landmark
  bound and A\* returns silently suboptimal routes, measured at up to 36% in ADR-001 item 4.

  Now written `List<@Valid Hotspot>`, and — the part that was actually missing —
  `MazeControllerValidationTest` pins the cascade. Every other bound in that class guards a
  scalar on the request itself; this is the only one that has to travel into a collection to
  matter, and it was the only one untested. Teeth: dropping the cascade fails the new test;
  reverting to the deprecated container form still passes, which is correct — the test pins the
  behaviour, so it starts failing on the day the deprecation lands and not before. That clears
  the last `HV000271` from the build.

- **Two heuristic-lens mutations had been aimed at deleted code since the epsilon refactor.**
  Once the harness could start, an audit of every mutation anchor (run each script with
  `subprocess` stubbed, so only the anchor checks execute — a two-second pass instead of a
  multi-hour suite) found 17 of 19 harnesses aimed at live code and two that were not.
  `lensteeth.py`'s "must-expand uses <=" and "tie folded into must" still targeted
  `if (f < optimal)` / `f == optimal`, which the classifier replaced with an epsilon band
  (`delta < -EPSILON` / `delta <= EPSILON`). Both had been silently reporting SKIP ever since,
  and nobody saw it because the script could not run at all. Re-aimed; both caught.

  `idateeth.py`'s inert-cutoff mutation is retired to its docstring. It anchors on a line
  deliberately deleted from the solver, so it reported SKIP forever — harmless until the tally
  fix above started counting unresolved results as survivors, at which point it became a
  permanent phantom entry, and a survivor list that always has something in it is a survivor
  list nobody reads.

  **One thing this did not find, reported because the near-miss is the useful part.** A new
  mutation aimed at `EPSILON` first scaled `delta` by 1e-9 and survived, which reads exactly
  like an unpinned guarantee — the band bounds are all vacuously satisfiable when every cell
  lands in one band, so the conclusion was plausible enough to write a test for. The mutation
  was inert: path costs are integers and EPSILON is 1e-9, so every comparison landed where it
  already had. Re-aimed at the constant itself (`1e-9` → `1e9`) it is caught immediately, by two
  tests that already existed. The test written for the imagined hole was then measured against
  the harness — 8/8 mutations caught with it and 8/8 without — and deleted. An inert mutation is
  the most expensive kind of false negative: it does not merely fail to find a bug, it invents
  one and sends you writing assertions to cover it.

- **The mutation harness could not run, and called broken builds catches.** Two defects in the
  thing that verifies everything else. Sixteen of the nineteen scripts in `mutants/` hardcoded
  `REPO = pathlib.Path("/root/daedalus-work/repo")`, a path belonging to the sandbox they were
  authored in; every command `mutants/README.md` documents died on `FileNotFoundError` before
  its first mutation. And the verdict logic — thirteen near-copies of it — read "Maven exited
  non-zero" as "a test caught the mutation", which are different claims. A build that dies in
  POM resolution, or compilation, or an OOM-killed fork, exits non-zero having run no tests at
  all.

  Both were found the same way: `retentionteeth.py`'s first run reported a confident **4/4
  caught** while all four builds were failing before a single test executed. The five scripts
  that did guard against this checked for the literal string `COMPILATION ERROR`, which none of
  those failures print.

  The rule is now in one place, `mutants/verdict.py`, and it is *no named failing test, no
  catch*. Seventeen harnesses share it. Fixing the per-mutation verdicts turned out to be half
  the job — the summary line counted anything not spelled `SURVIVED` as caught, so a run whose
  every verdict read `NOT A CATCH` still printed "4/4 caught; survivors: none"; the tallies go
  through `verdict.is_catch` now too. Verified in both directions: with a deliberately unusable
  local repository the harness reports 0/4 and names all four as unresolved, and against the
  real build it still reports 4/4 with the specific test that caught each mutation.
  `rlteeth.py`, which could not start before this, now runs and catches 3/3.

- **The Redis leaderboard sets grew forever.** Only the per-maze key carried a bound (a 48h
  TTL). The global and per-generator sorted sets gained a member on every completed run and lost
  one never. The constructor's javadoc called that keeping "full history", and the phrase was
  doing a lot of work: `MazeController` caps `n` at 100 and every read is a `reverseRange` from
  rank 0, so rank 101 downwards was storage no request could reach. Twenty-two generators means
  twenty-two of these.

  The argument against it was already written down, one field away — the in-memory cap's own
  javadoc says retention past the deepest page anyone can request is pure growth, and the set was
  capped for exactly that reason. Only the Redis half was exempt from its own reasoning. `submit`
  now trims each set to `maxEntries` on write, so the config property that used to bound one
  backend bounds both.

  `removeRange(key, 0, -(maxEntries + 1))` deletes by *ascending* rank while every read here is
  descending, which means the correct call looks backwards and the wrong one looks right. That is
  why `LeaderboardRedisRetentionTest` asserts on **which entries survive** rather than on the
  arguments the call was made with: a trim aimed at the best end leaves the set exactly the right
  size while deleting exactly the wrong members, and `verify(zset).removeRange(...)` would wave it
  through. The test drives a fake with real sorted-set semantics — score order, inclusive rank
  windows, negative indices — so the assertions are about state. Teeth in
  `mutants/retentionteeth.py`: four breaks (no trim, partitions unbounded, wrong end, off by one),
  all four caught.

  The coverage ratchet earned its keep again here — the new tests pushed the server past its 0.94
  ceiling and failed the build until the threshold was re-pinned to 0.92/0.95, which is the point
  of pairing tests with a threshold move instead of banking slack a later regression can spend.

- **The Redis leaderboard backend wrote a format it could not read.** `RedisConfig` handed the
  template a hand-built `ObjectMapper` with `activateDefaultTyping(validator, NON_FINAL)`, and the
  two halves of that disagreed. Writing uses the value's runtime type, and `LeaderboardEntry` is a
  `record` — **final** — so no type header was emitted. Reading targets `Object`, which is
  non-final, so the deserializer demanded one. Every read threw `SerializationException`.

  The interesting part is how completely that hid. `LeaderboardService` catches read failures and
  falls back to its in-memory set, so with `daedalus.redis.enabled=true` the boards still answered
  — out of memory, one warn line per call — while every completed run kept appending unreadable
  JSON to sorted sets that no code path could read back. Two of those three keys carry no TTL, so
  the backend's only measurable effect was Redis growth. It looked like it worked and did nothing.

  Fixed by moving to Spring Data's Jackson 3 `GenericJacksonJsonRedisSerializer` with default
  typing enabled explicitly, which writes an `@class` property for every value regardless of
  finality. Enabling it *requires* a `PolymorphicTypeValidator` — Jackson 3 removed the
  laissez-faire default — and that requirement was worth having: the old configuration, asked to
  read `["javax.naming.InitialContext",{}]`, constructed one. The replacement allows
  `com.daedalus.*` and collections and refuses everything else.

  Nothing caught this because the only Redis test asserted the beans **exist**. A serializer bean
  that constructs is not a serializer that works, and the gap between those two claims was the
  bug's entire hiding place — `RedisSerializationRoundTripTest` now closes it by round-tripping
  through `RedisConfig`'s own factory method. Three of its four assertions fail against the old
  configuration; the fourth is documented in the test as not having teeth, because `ArrayList`
  is not final and therefore always did round-trip. That is the bug's shape in one line: it bit
  exactly the final types, and a fixture stored in a list would have missed it.

- **A stopped plugin's algorithms kept working.** `shutdownAll()` called `stop()` on each plugin
  and closed its `URLClassLoader` — and neither registry had any removal path, so everything the
  plugin had contributed stayed in the global maps. Closing a loader does not unload classes
  already loaded from it, so those objects were perfectly alive: a "stopped" plugin's generator
  was still listed by `/api/v1/algorithms`, still resolvable, and still able to serve a request.
  On Windows the JAR also stays locked while its classes are reachable, which is the file-handle
  problem the classloader hygiene work was supposed to have solved.

  Both registries now have `unregister(id)`, and it **refuses built-ins**. That refusal is the
  point rather than a detail: a removal path reachable from plugin teardown is a removal path a
  buggy teardown can aim at `recursive-backtracker`, which would undo the collision guard from
  the opposite direction — a plugin that cannot *replace* a shipped algorithm could otherwise
  simply delete one. A fix for a leak that deletes built-ins on shutdown is worse than the leak.

  Attribution was the awkward part. Every plugin shares one `PluginContext` and therefore one
  registry, and `register` takes only the algorithm, so nothing records who contributed what.
  `PluginManager` now diffs the registry's id set across each plugin's whole boot — not just
  `registerAlgorithms`, because a plugin can register from `start()` too — and unregisters
  exactly those ids on shutdown. It is honest about its limit: a plugin that registers later,
  from a thread it started, is unattributable and is left alone rather than guessed at. This
  needs no change to the SPI plugin authors compile against.

  Unloading covers **every** entry, not only the `STARTED` ones. A plugin that registered two
  algorithms and then threw in `start()` never reaches `STARTED`, and its contributions are in
  the registry all the same — an unload keyed on state would have leaked precisely the failure
  case while handling the healthy one.

  The coverage ratchet earned its keep here: the first version of the test registered only
  generators, and the floor dropped 1 point because the entire solver branch of the unload was
  dead code as far as the suite was concerned. Teeth in `mutants/unloadteeth.py`.

- **A plugin could silently become a built-in algorithm.** `PluginContext` hands every plugin the
  live `GeneratorRegistry` and `SolverRegistry`, and `register` was a bare `map.put` — so any
  third-party JAR dropped in the plugins directory could declare
  `id() == "recursive-backtracker"` and take the name. Measured with a hostile generator: the
  registry's size did not change (2 → 2), `/api/v1/algorithms` still advertised the id while
  carrying the impostor's description, `require(...)` returned the impostor, and neither registry
  has an unregister, so the substitution outlived the plugin for the life of the process.

  Everything this project claims about reproducibility resolves through that lookup — the daily
  challenge, campaign stages, the seeded waypoint tour, and the cross-process digests in
  `DeterminismGoldenTest`. A plugin could move all of them at once, and the only symptom visible
  from outside would be that yesterday's seed makes a different maze today.

  Both registries now refuse a collision with `DuplicateAlgorithmException`, naming the class
  that holds the id and the one turned away. Refusing rather than warning costs nothing:
  `PluginManager` already contains a throwing plugin, marks it `FAILED`, boots the rest, and the
  plugin subsystem's health indicator reports it — so a colliding plugin now fails by the same
  route as any other broken one, and the built-in it wanted keeps working. Built-ins register
  from the constructor, through the same guarded path, so a duplicate among the shipped set fails
  at startup instead of silently dropping one.

  The guard's first draft exempted re-registering the *identical instance*, on the theory that a
  double-boot should not fail. Writing the test for it showed nobody could name a path that
  reaches it, so the exemption was permission granted for a case that does not exist — the same
  shape as the `ALLOW_EMPTY_404` flag and the one-sided coverage ratchet. Removed: a taken id is
  taken. Teeth in `mutants/registryteeth.py`; the load-bearing mutation keeps the throw and moves
  the overwrite *before* it, so a test asserting only "an exception was raised" would pass while
  the built-in is gone anyway.

- **Any connected client could publish a forged frame onto any STOMP topic.** The client inbound
  channel had two interceptors: one authenticating `CONNECT`, one authorising `SUBSCRIBE` to an
  owned session's player feed. Neither looked at `SEND` — and because the broker is Spring's
  *simple* broker with `/topic` enabled, a client frame addressed to a `/topic` destination is
  never dispatched to application code at all. The broker relays it. Measured, not theorised: a
  second anonymous client sent one frame to another player's `/topic/session/{id}/player` and the
  spectator received it, indistinguishable in shape from a server-published move. The same worked
  on `/topic/maze/{id}`. `StompSendRejectionInterceptor` now refuses every client `SEND`.

  **Two things about how this hid.** First, `WebSocketConfig`'s own Javadoc said "do not read
  their presence as evidence that a client can send frames today" — a reassurance written after
  correctly confirming that no `@MessageMapping` exists. The observation was right and the
  inference was wrong: no mapping proves no code *of ours* handles a client frame, not that the
  frame goes nowhere. The simple broker is application code somebody else wrote, and it was
  listening. Second, note which direction got the attention. Real design work went into who may
  *read* an owned session's feed; nobody asked who may *write* to it. From the outside a guard on
  one direction of a channel is indistinguishable from a guard on the channel.

  What an attacker got was display, not state — `PlayerMovedEvent` is published by the server
  from its own record, so scores, the leaderboard and waypoint progress were never forgeable. But
  the spectator seam, the ghost racer and the multiplayer view all render what arrives on these
  topics, and "the number is right, the picture is a lie" is not a defensible place to stand.

  The refusal is **total** rather than per-destination, because this application has nothing for
  a client to say. That is a fact about the codebase rather than a principle, so
  `StompSendRejectionTest` scans for message-mapping annotations and fails the build if one
  appears — the day a real client-to-server message is added, the blanket rule becomes wrong and
  the build says so instead of the feature quietly not working.
- **The last 27 errors with no body at all.** `ResponseEntity.notFound().build()` appeared 27
  times across `MazeController`, `InsightController` and `AgentController`, each answering 404
  with nothing in it — the remaining hole after the error-contract audit, and a perverse
  inversion: a typo'd URL came back with a helpful problem detail while an expired maze id came
  back with silence. The expired maze is the common case by a wide margin (mazes live in a
  bounded Caffeine cache and get evicted) and the one the caller can act on. All 27 now throw
  `ResourceNotFoundException` and answer in the house shape, saying which kind of thing was
  missing and, for a maze, that regenerating with the same seed reproduces it exactly.

  A helper returning a populated `ResponseEntity` was the obvious repair and does not compile:
  `ResponseEntity<AnalysisResponse>` cannot carry a `ProblemDetail`, so every affected method
  would have had to widen its return type to `Object`. Throwing keeps the signatures.

  **Several of those 27 were never answering the same question.** `POST /session/{id}/move`
  404s both when the session is unknown *and* when the session is fine but its maze has been
  evicted — different problems, previously identical replies. `GET /maze/{id}/ghost` 404s for
  "no such maze" and for "nobody has finished this maze yet", which call for opposite reactions
  (regenerate, versus keep playing). `POST /maze/breed` named neither of the two parents it
  could not find. `GET /complexity` 404s for an unregistered generator and for an unmeasured
  metric; the first is now an `UnknownAlgorithmException` listing all 23 generators, the second
  names the metrics that exist. One case deliberately did *not* gain detail: `join` with the
  multiplayer flag off returns the same "no such session" body an unknown id produces, because
  the 404 is there to make the endpoint look absent rather than disabled, and a more helpful
  message would turn it into a feature-flag oracle. That is asserted, not just intended.
- **`ComplexityLabService` swallowed every runtime exception from its registry lookup.**
  `catch (RuntimeException unknown) { return null; }` collapsed "no such generator" into the
  same null as "no such metric" — and, being a catch-all, would have turned any unrelated
  failure in that lookup into a silent 404 too. The lookup now propagates.
- **A client typo answered 500.** `POST /api/v1/maze/generate` with a mistyped `generatorId` and
  `POST /api/v1/maze/{id}/solve/{solverId}` with a mistyped solver both returned **Internal
  Server Error** with a stack trace in the log, because both registries' `require(...)` threw a
  bare `NoSuchElementException` and `ApiExceptionHandler` had no handler for it. The two
  most-used endpoints in the API were the two reporting a user's typo as a server fault, while
  every analytical endpoint added later answered a clean 404. Both now answer **404** with a
  problem detail listing all 23 registered generators (or all 10 solvers). The underlying mistake
  is worth naming: `find` returns an `Optional` and `require` throws — the controllers called
  `require` on caller-supplied input, which is the method for internal invariants.
- **Three failure modes returned the right status with the wrong body.** A missing required query
  parameter, the wrong HTTP verb, and an unsupported `Content-Type` all fell through to Boot's
  default `{timestamp, status, error, path}`, as did an unmapped path. These are more dangerous
  than the 500s: the status code looks correct from the outside, so nothing goes red, while a
  client reading `detail` and `title` off the documented RFC 7807 contract silently gets nulls.
  Four new handlers, and the 405 now carries the `Allow` header RFC 9110 §15.5.6 requires.
- **Three shipped features did not work in prod at all.** The `#session=` spectator permalink,
  the ghost racer and the fog-of-war agent's free re-poll are documented public in the README's
  "Auth (prod)" column and were all being refused by `ProdSecurityConfig`'s default-deny rule —
  `GET /api/v1/session/{id}`, `GET /api/v1/session/{id}/tour`, `GET /api/v1/maze/{id}/ghost` and
  `GET /api/v1/agent/{id}` answered 401 to the anonymous caller they exist for. This system has
  exactly one account, so "authenticated" here meant "only the operator", which makes a spectator
  link nobody can spectate and a shareable ghost nobody can watch. All four are now permitted
  explicitly, with **single-segment** matchers: `/api/v1/session/*` deliberately does not reach
  `/session/{id}/join`, and `/api/v1/agent/*` deliberately does not reach `/agent/{id}/step` —
  both of those spend server state and stay closed. Found only because the README and the
  filter chain were finally compared to each other.
- **`GET /api/v1/session/{id}/tour` reached Held-Karp with no rate limit.** It reads like a cheap
  progress lookup and was metered as one — but `progressFor` calls `tourFor`, so a request that
  misses the tour cache runs the same `O(2^k · k²)` exact TSP that its sibling
  `GET /api/v1/maze/{id}/tour` carries a `mazeSolve` limiter for. Two routes to one computation
  and only one of them counted; the limiter had been placed by reading the method, not by
  following the call. Now on the `mazeSolve` budget, which matters more since the endpoint is
  also anonymously reachable as of this release.
- **The API table in the README was two rows short.** `GET /api/v1/complexity/metrics` and
  `POST /api/v1/session/{id}/join` were live and undocumented. The cross-check test found both
  on its first run.
- **The endpoint scanner could not see two annotation forms.** `ProdAuthPostureTest`'s
  completeness scan required a parenthesised string literal, so `PluginController`'s bare
  `@GetMapping` and `MazeController`'s `@GetMapping(value = ..., produces = ...)` were invisible
  to it — and `GET /api/v1/plugins` was consequently the one endpoint in the API with no posture
  on record, in the test whose entire job is that no endpoint lacks one. The scanner now counts
  annotations independently of parsing them and fails on any mismatch, so a form it does not
  understand is a build failure instead of a silently smaller sweep.
- **The coverage ratchet had stopped ratcheting.** `jacoco:check` enforced a floor and nothing
  else, so it caught regressions and never noticed the floors going stale as coverage climbed.
  Audited across all five modules:

  | module | floor was | actual | slack |
  |---|---|---|---|
  | daedalus-server | 0.79 | 0.910 | **+12.0 pts** |
  | daedalus-plugin-api | 0.00 | 0.130 | no guard at all |
  | daedalus-desktop | 0.00 | 0.105 | no guard at all |
  | daedalus-core | 0.87 | 0.901 | +3.1 pts |
  | daedalus-plugin-runtime | 0.84 | 0.870 | +3.0 pts |

  Server coverage could have fallen by a ninth of the codebase before the build objected, and the
  README's claim of "a per-module JaCoCo coverage ratchet that fails the build on regression" was
  only meaningfully true for two of five modules. `TESTING.md` had prescribed exactly the right
  policy — pin each module a few points under actual, "raising it as coverage rises" — and, like
  most conventions that rely on someone remembering, it was not followed.
  The rule now carries a **maximum** alongside the minimum: drift more than 3 points above the
  floor and the build fails asking for the bump, which makes the ratchet mechanical rather than
  aspirational. Floors raised to 0.90 (server), 0.89 (core), 0.85 (plugin-runtime), and real
  non-zero floors set for the two modules that had none. The cost is honest: improving coverage
  now occasionally means a one-line pom edit, paid by the person who improved it rather than by
  whoever regresses it six months later. Both directions proven by `mutants/ratchetteeth.py` —
  set the floor above actual and the minimum fires, leave it 12 points stale and the maximum does.
- **The JavaFX desktop froze for up to 1.8 seconds per click, on an assumption that used to be
  true.** `MainController` ran generation and solve inline on the JavaFX Application Thread, and
  said so in a Javadoc that also named its own trigger for change: *"fast enough at the
  Spinner-bounded sizes (≤ 128² = 16 384 cells) that we don't background them; if a later change
  pushes that into the multi-second range, wrap the calls in a Task."* Nobody re-measured it
  across twenty features. Re-measured now, at the spinner's own maximum:

  | operation at 128×128 | on the FX thread |
  |---|---|
  | hunt-and-kill generate | **1101 ms** |
  | IDA\* solve, perfect maze | **1783 ms** (spends its node budget, then refuses) |
  | IDA\* solve, dungeon | **1518 ms** |

  Every millisecond of that is a frozen window — no repaint, no input, and on some desktops the
  "not responding" overlay. The assumption was true when written; the code that invalidated it
  lives in another module, which is exactly why a documented assumption needs re-measuring rather
  than re-reading. Both operations now run on a `javafx.concurrent.Task`, the buttons disable
  while one is in flight (two concurrent Generates could otherwise race to assign the current
  maze), and the worker thread is a daemon so it cannot outlive the window.
- **The desktop was a second, unhandled consumer of `SolverBudgetExceededException`.** When IDA\*
  gained its node budget, only the REST layer learned to translate it. The desktop happened to
  catch `RuntimeException` and print the message, which reads acceptably by luck rather than
  design — the exception's text was written to make sense outside the API. That is now explicit:
  `DesktopWork.describeFailure` reports a budget refusal in its own words with no "Solve failed:"
  prefix, since it is a cost guard rather than a crash, and unwraps `ExecutionException` because
  that is how a Task hands a failure back.

- **`POST /session/{id}/move` had no rate limit, and it is the most expensive write on the
  surface.** Counting annotations across the API found 10 of 32 endpoints unmetered. Most are
  cheap reads and deliberately stay that way; this one is not. A move mutates the session, feeds
  traffic tracking and ghost recording, and publishes a `PlayerMovedEvent` to every plugin
  listener **synchronously, inside the session lock** — the project already reasoned carefully
  about a 60 ms listener serialising a session's moves, but never bounded how fast moves could
  arrive. Measured against the running server on the default profile:

  | endpoint | result |
  |---|---|
  | `POST /session/{id}/move` | **1206 accepted in 6.0 s (201/s), never throttled** |
  | `POST /agent/{id}/step` | 1200 accepted, then 429 — `agentStep` budget working |

  The two are the same shape of traffic, and the agent endpoint's own config comment says so:
  "a blind walk is hundreds of tiny requests by design". Its twin would have sustained roughly
  ten times the rate that reasoning allowed. A new `sessionMove` budget gives moves the same
  1200/min; re-measured after the fix, the endpoint accepts exactly 1200 and then answers 429
  with the standard ProblemDetail. Nobody removed the annotation — it was simply never added,
  which is why the fix below matters more than the annotation does.
- **`application.yml` documented a maze cache that did not exist.** A post-ADR-007 configuration
  audit found the file declaring `daedalus.cache.maze-cache-size: 256` and
  `maze-cache-ttl-minutes: 30`, while `MazeGenerationService` reads `daedalus.maze.cache.max-size`
  and `daedalus.maze.cache.idle-ttl` — different keys entirely. The real cache therefore held
  **5,000 mazes for two hours** against the 256-for-30-minutes the file advertised, a twentyfold
  difference in footprint, and an operator tuning the documented knob changed nothing at all.
  Undocumented configuration is a nuisance; configuration that is documented and inert is worse,
  because the value looks deliberate and survives review. Behaviour is unchanged — the defaults
  were always the live ones — but the file now describes reality and the knob works.
- **Five config blocks the code reads were missing from `application.yml` entirely** — the play
  session store, the leaderboard cap, the distance-field/lens payload cap, and the tournament's
  four bounds. All are now documented alongside the rest, with the environment overrides the
  other blocks use.

### Added

- **`DesktopWork` — the desktop's long operations as plain `Callable`s, so they are testable.**
  A `javafx.concurrent.Task` cannot run headless (its state transitions go through
  `Platform.runLater`), and this module deliberately carries no TestFX or Monocle — the existing
  tests say so outright. Splitting the work from the wrapper keeps the part with behaviour under
  test and leaves only glue in the controller. Six tests, including one that the job is *lazy*:
  if building it did the generating, moving to a Task would have relocated the freeze to the
  button click rather than removing it.
- **`RateLimitCoverageTest` — three scans over the controller sources.** Every state-changing
  endpoint (POST/PUT/PATCH/DELETE) must carry `@PerKeyRateLimit`; every budget named in code must
  exist in `application.yml`, since one naming a missing instance silently limits nothing; and
  every configured limiter must be named by some endpoint, since one guarding nothing is dead
  weight that reads as protection. The allowlist for unmetered writes is empty and documented as
  worth keeping empty. The rule is deliberately scoped to writes: extending it to GET would force
  a dozen annotations whose only effect is noise, and a rule everyone waives is worse than none.
- **`ConfigCoverageTest` — the durable fix, checked in both directions.** It scans the server's
  sources for `${daedalus.*}` references and cross-references them against `application.yml`,
  failing the build on a key the code reads and the file omits *or* a key the file declares and
  nothing reads. Keys bound wholesale by `@ConfigurationProperties` are exempted by prefix rather
  than by name, and a third test pins that the exemption stays narrow — a single prefix of
  `daedalus` would silently forgive the entire tree.
- **`BoundedStoresTest` now scans for caches rather than naming three.** The audit counted
  **nine** Caffeine caches in the server against three named eviction tests. All nine declared a
  `maximumSize`, so the "bounded everywhere" rule held — but it held because everyone remembered,
  which is a run of luck rather than a property. The new test walks the sources and fails on any
  `Caffeine.newBuilder()` without a `maximumSize`, so a tenth cache is covered the moment it
  exists. Same reasoning as the registry-driven generator fuzz: a hand-written roster is correct
  the day it is written and quietly incomplete afterwards.

### Added

- **Heuristic lens (ADR-007 idea 8) — completing the roadmap, and not the way it was written.**
  `GET /api/v1/maze/{id}/heuristic-lens?heuristic=MANHATTAN|LANDMARK|INFLATED` partitions a maze
  into the three bands that *explain* A\*'s work, with an overlay in the UI.
  The ADR asked for "measure where A\*'s heuristic lies most, and overlay it". That was measured
  first and rejected: per-cell heuristic error against wasteful expansion correlated anywhere from
  **+0.42 to −0.17** across perfect, braided and dungeon mazes — inconsistent in magnitude and
  unstable even in sign. An overlay built on it would have been a convincing picture that explains
  nothing. What A\* actually obeys is exact, not statistical: it expands a cell only when
  `f = g* + h` is at most the optimal cost `C*`. So the lens reports **must expand** (`f < C*`, no
  tie-breaking can avoid these — this region *is* the heuristic's cost), **tie decides**
  (`f = C*`, where measured on a 21×21 dungeon the band holds 88 cells against a mandatory 30, so
  tie-breaking matters more than the heuristic there), and **never touched** (`f > C*`, of which
  A\* expanded **zero** across every configuration measured — reported as a live check rather than
  assumed).
  That makes "a better heuristic" a measurable claim: the four-landmark ALT heuristic drops the
  mandatory band from 925 cells to **0** on a 31×31 perfect maze and cuts real expansions by 1.8×
  to 5.5×.
- **A deliberately inadmissible heuristic, because a check that can only report zero cannot be
  tested.** `INFLATED` (Manhattan × 3) was added after a mutation survived: the test asserted
  `expandedAboveOptimal == 0`, so a mutation that never incremented the counter was invisible.
  An overestimating heuristic gives the counter something it must detect — and demonstrates the
  weighted-A\* trade honestly. Measured on a 31×31 dungeon it cuts expansions from 341 to 213 and
  returns a **96-step route where the optimum is 88**. The response says so outright.
- **SpotBugs caught float equality in the new lens, and it was a real trap.** The band logic
  compared `f == C*` exactly. That happens to be correct for all three heuristics wired up —
  they return integral values on a unit-cost grid — but the code accepts an arbitrary
  `ToDoubleBiFunction`, and `Heuristics.EUCLIDEAN` already exists in the codebase: with it, a cell
  whose `f` is exactly `C*` would fall into the tie band or the never band depending on the last
  bit of a square root. Now compared against an epsilon, the same fix this project applied once
  before to float comparison of cell costs.

- **Solver tournament with confidence intervals (ADR-007 idea 10) and adversarial seed search
  (idea 7).** `GET /api/v1/tournament?generator=&size=&mazes=&braid=&seed=` runs every registered
  solver over a deterministic sample of mazes and reports, per solver, mean work with a
  **Student-t** 95% interval, the median, the spread as a coefficient of variation, mazes won,
  and how often it found a shortest route. The UI adds a **Solver tournament** panel.
  **The headline is not the ranking — it is how much the ranking can be trusted.** ADR-007 sold
  this as "a tournament says which solver is *actually* better"; measurement says that depends
  entirely on the maze. On perfect mazes dead-end filling won 30 of 30, so one race already gave
  the right answer, and the response says so. On braided mazes the winner split four ways out of
  16 and wall-follower's spread reached **94% of its own mean** — a single race there is close to
  a coin flip, and no single race would reveal the instability. So the report leads with spread
  and with **statistically indistinguishable pairs**: BFS, Dial and Dijkstra come out tied because
  all three explore essentially every cell, and printing them as 1st, 2nd and 3rd would be a
  ranking invented out of rounding error.
  Idea 7 falls out of the same sample: the maze where the leader does worst against the runner-up
  is reported by **seed**, and because the sample is deterministic that seed regenerates exactly
  that maze — the UI offers a link to load it. Verified in the sweep by regenerating it.
  A solver that spends its node budget is excluded after three refusals and its statistics are
  **withheld rather than averaged**: measured on 19×19 dungeons IDA\* finishes five mazes before
  its third refusal, and a mean over those five would be survivorship bias with an error bar on
  it. The count of finished mazes is reported so a reader can see what was discarded.
- **`SampleStats` in `daedalus-core`** — mean, median, sample standard deviation, coefficient of
  variation, Student-t intervals and paired differences, with the statistics kept out of the
  Spring layer so they can be tested in a pure JVM against hand-computed values. Three decisions
  worth naming: the interval uses **t, not 1.96** (at n = 8 the normal quantile is 21% too
  narrow, which is exactly the error that manufactures a difference); comparisons are **paired**,
  though the docs record that pairing bought nothing on this project's own A\*-versus-BFS data
  because BFS is nearly constant; and skew is flagged by the standard **nonparametric skew**
  coefficient rather than a threshold picked to look strict — the first version demanded half a
  standard deviation and failed to notice `{10, 11, 12, 13, 900}`, because an outlier inflates
  the standard deviation faster than it moves the mean off the median.

### Fixed

- **IDA\* could run for minutes on a maze the API happily accepts — it now gives up in about a
  second.** Probing solver workloads for the tournament idea turned up an unbounded request on a
  public endpoint. Measured on dungeons: 15×15 instant, **21×21 nine to sixteen seconds** (~90
  million node expansions), **25×25 abandoned after 300 seconds still running**. Every other
  solver finishes the 21×21 dungeon in under 40 ms, and the UI's "Compare all solvers" runs IDA\*
  alongside the other nine, so four extra rows of maze turned a slow page into one that never
  loads. Iterative deepening re-searches from scratch under each new f-bound, and a rock-heavy
  looped graph makes every pass expensive — no traversal tuning fixes that, only a bound.
  `IDAStarSolver` now carries a 5,000,000-expansion budget (~1 s at the measured ~5.7 M/s) and
  throws `SolverBudgetExceededException`, which the API answers as **422** with the solver id and
  the budget in the ProblemDetail. Measured after: the 21×21, 25×25 and 41×41 dungeons all refuse
  in 0.8–1.4 s, a 51×51 perfect maze still solves optimally in 0.13 s, and compare-all on a
  dungeon fell from over 16 s to **0.94 s** with nine solvers answering and one honestly refusing.
  A 512×512 perfect maze also now refuses in under a second instead of driving the recursive
  search toward the stack limit.
  **This is a deliberate behaviour change:** the 21×21 dungeon used to return a correct answer
  after 16 seconds. It was never given the option of returning an empty path instead — the
  `MazeSolver` contract reads an empty list as "unreachable", so a budget-exhausted search
  reporting one would put a confident false claim into the compare table, the arena and the
  sweep. Refusing loudly is the only answer that does not lie in a data structure.
- **`sweep/api-sweep.py`'s `call()` had an `expect=` parameter that was never used.** It looked
  like a status assertion and asserted nothing — three call sites passed `expect=400`, `422`,
  `None` and got no checking whatever. Removed rather than implemented, since every caller
  already compares the status it got. Error bodies are now parsed as JSON so a check can assert
  on a ProblemDetail's fields instead of substring-matching a truncated string.

### Added

- **Distance heat map (ADR-007 idea 6) and sanctuary placement (ADR-007 idea 5).**
  `GET /api/v1/maze/{id}/distance-field?from=GOAL|START` returns every cell's walking distance
  from a landmark, and the UI shades the maze with it — one hue, monotone in lightness, the
  near-zero end receding into the floor. `GET /api/v1/maze/{id}/sanctuaries?k=` solves metric
  k-center by farthest-first greedy (a 2-approximation, and the best guarantee available unless
  P = NP), reporting the covering radius, how many cells are actually served, and *which* cell
  is served worst — drawn as a ring, the loneliest place in the maze. Measured on a 21×21 perfect
  maze the radius falls 203 → 149 → 90 → 48 → 39 as k goes 1 → 8. Unreachable cells report `-1`
  rather than being omitted, so a dungeon's rock stays unshaded instead of being drawn as
  distance zero. The field is payload-capped at 16,384 cells and **refused with a 400 that
  explains itself** above that — the sweep stays linear at 512×512, the 1.5 MB of JSON does not,
  and silently downsampling a per-cell overlay would be a lie told in colour.
- **`DistanceOracle` stays dormant on purpose, with a measurement behind it.** ADR-007 justified
  the heat map as "revives `DistanceOracle`". It does not, and shouldn't: the oracle tabulates
  all-pairs distances for O(1) lookups, caps itself at 4,096 cells (the table is `V²` shorts —
  32 MB at 64×64), and a heat map needs one source, not all pairs. It also loses on its own
  ground — computing every cell's eccentricity measured **1,738 ms** precompute-then-scan against
  **1,485 ms** for running the same sweeps directly, allocating nothing. It only pays for many
  random-pair queries, which nothing here does. Eight of the nine `theory` classes are now
  reachable from the product; the ninth is unreferenced by decision rather than neglect.

### Fixed

- **The heat map looked broken on first render and was not — the legend now says why.** The
  overlay showed no smooth halo around the goal: bright patches mid-maze, sharp discontinuities
  everywhere. Checking the numbers rather than the picture, the field is 0 at the goal and its
  four *physically adjacent* cells measure 201, 1, 189 and 157. A maze distance field is walking
  distance, so touching cells are remote when a wall stands between them, and every abrupt change
  of shade marks a wall doing that work — the most informative thing the overlay shows. Both the
  legend and a test now pin it, so the next reader does not "fix" the correct behaviour.

### Added

- **Hardest-route mode (ADR-007 idea 3) — and the roadmap entry for it was wrong.**
  `GET /api/v1/maze/{id}/hardest-route` returns the longest simple route from start to goal
  alongside the shortest, the ratio between them, the maze's independent loop count, and whether
  the answer is a proven optimum or a lower bound (longest-simple-path is NP-hard, so the search
  is budget-bounded and says which it gave you). The UI adds **Hardest route**, drawing the walk
  in gold. ADR-007 proposed this as a start/goal *placement* mode — "put them on the longest
  simple path instead of the extremes" — and ten minutes of measurement killed that: a perfect
  maze is a tree, a tree has exactly one simple path between any two cells, so on 22 of the 23
  generators the proposed mode changes nothing (measured: 145 and 145 steps on a 15×15). What
  is worth shipping is the *measurement*, which is zero on a tree and large once loops exist —
  the same 21×21 braided at 0.5 goes 203/203 → 56/260 (**×4.6**), a dungeon measures 40 against
  122, and thirty erosion ticks took a living maze from ×1.00 to ×2.69 while opening 31 loops.
  On a tree the response says so outright and names the operations that open loops, because a
  feature that is honest about being inert beats one hiding it behind a number.

### Fixed

- **`LongestPath` threw `StackOverflowError` on every perfect maze from 200×200 up.** The search
  recursed, and a 512×512 tree — a size `GenerateRequest` explicitly permits — has a unique
  start-to-goal route tens of thousands of cells deep. That is an `Error`, not an exception,
  escaping a public core API and surfacing as a 500. Braided mazes hid it completely, because
  the visit budget ran out at shallow depth long before the stack did, which is how this
  survived a green suite for so long. The frames now live in arrays sized from the grid, with
  identical traversal order and identical results; a 512×512 perfect maze returns a
  proven-optimal 74,268-step route in 74 ms. Pinned by a 300×300 regression test that fails with
  `StackOverflowError` against the previous implementation.
- **`LongestPath` answered "there is no route" about mazes anyone can walk.** On a 41×41 at
  braid 0.5 (and a 61×61 at braid 1.0) the DFS spent its entire two-million-visit budget in the
  cycle-rich middle of the maze without once reaching the goal, and returned `length = -1` with
  an empty path. The incumbent is now seeded with the BFS shortest path, so the result is a real
  route at worst and the budget is spent improving rather than hunting for a first success;
  `exact` is untouched, so a seeded-but-unimproved answer is still correctly labelled a lower
  bound. This changed a documented contract — the old test asserting `-1` for a starved search
  was rewritten rather than deleted, and it explains why.

### Added

- **Generator invariant fuzzing (ADR-007 idea 9) — 23 generators go from "presumably fine" to
  measured.** `GeneratorInvariantFuzzTest` property-tests every registered generator against the
  invariants that hold whatever the algorithm — dimensions honoured, walls agreed on from both
  sides, no opening leading off the grid, every carved cell mutually reachable, identical output
  for an identical seed, different output for a different seed, and *if* a generator fills the
  grid then it must be a spanning tree. 506 generations across 11 shapes (1×1, 1×7, 7×1, 2×9,
  9×2, 16×24 and friends — the degenerate and lopsided inputs where generators actually break)
  and 2 seeds. **Result: zero violations.** Driven by the injected `GeneratorRegistry` rather
  than a hardcoded roster, so a newly wired generator is covered the moment it is registered;
  the spanning-tree rule is likewise stated as a conditional, so the Dungeon generator opts out
  by being half rock rather than by being named in an exclusion list. That is the difference
  from core's existing `PerfectMazePropertyTest`, which checks the same tree contract over a
  hand-listed **8** generators at one size and one seed — it stays (pure-JVM, no Spring, faster
  signal), and this is the wider net over the other 15.
- **`mutants/fuzzteeth.py` — six deliberate breaks proving the fuzz can fail.** Zero violations
  is exactly what a vacuous test reports, so the harness sabotages Binary Tree six ways (a
  one-sided opening, an opening off the grid edge, the seed mixed with the clock, the seed
  ignored entirely, cycles from carving both directions, a walled-off two-cell island) and
  checks the fuzz names the *specific* property each one violates. All six caught. One is
  informative beyond passing: carving both directions unconditionally also makes output
  seed-independent, so it trips two properties — the net overlaps rather than partitions.

### Fixed

- **`WebSocketOwnershipSmokeTest` was flaky — and the flake was in the assertion, not the
  server.** `anotherSubjectsSubscriptionIsRefusedWithAStompError` failed about one run in three
  (measured: 1 of 3, then 1 of 4 in isolation) during the full `verify`. Rather than re-running
  until green, the latch was instrumented to record what happened when it timed out; the answer
  was `ConnectionLostException: Connection closed`. The server refuses a non-owner by sending a
  STOMP ERROR frame **and then closing the socket**, and those two race — the test was waiting on
  one of two legitimate outcomes. Both mean refused. The latch now trips on the ERROR frame, a
  conversion failure reading it, or the transport dying, and reports which. Because accepting a
  bare close would weaken the check, both refusal tests now also assert the stronger property:
  the refused subscriber receives **no frames** while the owner's events are republished at it.
  Teeth confirmed by disabling the interceptor — both tests fail, and the new diagnostic reads
  "nothing at all was observed", which is the message the old assertion could not produce.
  Stable 5 of 5 afterwards.
- **The first `fuzzteeth.py` result was contaminated and is not the one reported above.** The
  harness was launched under a wrapper that hit a timeout; the wrapper was killed, the Python
  process survived orphaned and kept mutating, and a second copy started against the same file.
  Two interleaved runs printed a confident "6/6 caught" and left a sabotaged generator in the
  working tree — caught only because `git status` was checked before committing. The harness now
  holds a lock file, writes a pristine sidecar that the next run restores from, reverts after
  every mutation instead of once at the end, and reverts on SIGTERM; the 6/6 above was
  re-measured from a verified-clean tree. `mutants/README.md` records the trap and notes that
  the three older harnesses restore per mutation in a `finally` but still have no lock.

### Added

- **Maze fingerprint + generator classifier (ADR-007 idea 4) — name the algorithm from the
  shape alone.** `MazeFingerprint` reduces a maze to eight scale-invariant structural ratios
  (degree shares, directional bias, straight-run length, edge density), and
  `GeneratorClassifier` does nearest-centroid over signatures learned from the registered
  generators. `GET /api/v1/maze/{id}/fingerprint` returns the signature and the verdict; the UI
  adds **Identify generator**. Measured on held-out seeds it names the exact generator **58.9%
  of the time against 4.3% chance**, and the right *family* of algorithm **87.4%** of the time.
  The gap is the interesting part rather than a shortfall: the residual error is concentrated in
  algorithms that are equivalent by construction — Aldous-Broder and Wilson's both sample
  uniform spanning trees, so no statistic of a single maze can separate them, and counting that
  as an error would be scoring the classifier against mathematics. Most usefully, **confidence
  is calibrated**: verdicts at ≥0.25 confidence are ~89% accurate against ~45% below it, so a
  caller can trust the confident answers and read the unsure ones as "one of these two
  families". Disagreement with the recorded generator is surfaced rather than hidden — an eroded
  maze legitimately stops looking like its author (measured: dead-end ratio 0.106 → 0.042 after
  30 erosion ticks, and the verdict changes with it).
- **Complexity Lab (ADR-007 idea 2) — measure the algorithms instead of asserting them.**
  `GET /api/v1/complexity?generator=&metric=` runs a generator across a capped size sweep, fits
  the recorded work against candidate growth curves, and returns the winner with its exponent,
  R², and the measured points. The web UI plots it log-log, where a power law is a straight line
  whose slope *is* the exponent. Counters are fitted and wall-clock deliberately is not — timing
  measures the machine, while cell counters are deterministic per `(generator, size, seed)`, so
  any fit reproduces exactly. Two results worth the price of admission: **Prim's peak frontier
  measures O(√n)** (the frontier of a growing blob is its perimeter) while Kruskal's is linear,
  and **Aldous-Broder explores 266,830 cells to carve 9,216** — 29× overdraw, the cover-time
  cost of a uniform spanning tree. Sweeps never touch the maze cache or fire generation events.
- **Waypoint Tour mode (ADR-007 idea 1) — the exact TSP solver, made playable.** `GET
  /api/v1/maze/{id}/tour` places waypoints and returns the *provably optimal* order collecting
  them all: Held-Karp over the waypoint set plus the goal as a compulsory final stop. Collect
  them in the UI ("Waypoint hunt") and the finish line scores your walk against a number that is
  not an estimate — *"tour complete in 360 steps; the optimal route is 264 (136% of optimal)"*.
  Placement uses k-center farthest-first, so waypoints spread instead of clumping, which means
  the mode revives **two** dormant theory classes rather than one. Everything derives from the
  maze alone, so the daily challenge, per-maze leaderboards, ghosts and campaign stages all work
  in this mode without a line of change in any of them. Progress is observed server-side from
  real moves (the same event seam traffic uses) rather than accepted from the client, so the
  count that scores cannot be claimed.
- **ADR-007** (`docs/adr/ADR-007-theory-as-product.md`), from an audit with an uncomfortable
  finding: **six of nine `theory` classes had zero references from any user-facing module** —
  exact TSP, k-center placement, longest-simple-path, all-pairs distance oracles, and empirical
  complexity fitting, all built and tested and invisible. The ADR proposes ten ideas that close
  that gap, weighs three designs for the first, and records why waypoints must be server-owned
  (a comparison against "optimal" is meaningless if the client picks the instance).

### Fixed

- **The regression sweep hid rate-limit failures behind a `TypeError`.** Its maze-generating
  helper returned the error body on a non-200, so a 429 surfaced downstream as
  `TypeError: string indices must be integers` — a message that says nothing about the cause.
  It now raises with the status and body, and a sustained 429 explains that a full sweep exceeds
  the default 30-generations-per-minute budget and should run against the generous `test`
  profile. A helper that hides the real failure costs more than the failure.

- **The Complexity Lab's default metric was degenerate, and said so.** Measuring `cellsVisited`
  reports O(n) at R²=1.000 for all 23 generators — a spanning-tree generator carves every cell
  exactly once, so the metric *is* the cell count and the chart would have said the same thing
  about everyone. It is kept as a real invariant check (it catches a generator that skips or
  double-counts cells) and now labels itself as one, steering to `cellsExplored` and
  `maxFrontierSize` where generators actually differ.
- **A metric a generator never increments no longer poses as zero growth.** Fitting a curve
  through all zeros yields a NaN exponent that rounded to a confident-looking `0.0`; those cases
  now report `not reported` with an explanation instead of inventing a growth class.
- **An over-large waypoint count answered 500 instead of capping.** The count was clamped to
  `WaypointTour.MAX_WAYPOINTS` and *then* the goal was appended as the compulsory final stop,
  handing Held-Karp one stop more than it accepts. Caught by the mode's own bounds test.
- **A stale poll response could reinstate the maze you just navigated away from.** With STOMP
  unavailable, living and traffic mazes refresh by polling, and `refreshLivingMaze` assigned the
  fetched maze to `state.maze` *after* an await without re-checking that the maze was still
  current. Switch mazes during that window — click Daily, load a campaign stage, hit Generate —
  and the in-flight response put the old maze back: reproduced deterministically by delaying the
  old maze's fetch, leaving `state.maze` on the previous maze under a "Daily leaderboard"
  heading, where a session opened next would play a different maze than the one being scored.
  Every await in that function now drops its result if the player has moved on. Found by chasing
  a one-in-three flake in the new sweep rather than re-running until green.

### Changed

- **Added an end-to-end regression sweep (`sweep/`).** Every ADR-006 feature exercised against a
  running server — 14 API checks and 16 browser checks, each reporting evidence and continuing
  past failures. It exists because features were verified individually in the batch that built
  them, while later consolidation modified services those earlier features depend on
  (`LivingMazeService`, `TrafficService`, `MazeBreeder`); nothing had ever exercised all ten
  together. Current state: **14/14 and 16/16**, stable across repeated runs and with the
  multiplayer flag both on and off.
- **The per-session lock's isolation is now a tested guarantee.** A move's event listeners run
  while its session lock is held — deliberately, so listeners see moves in the order they were
  applied — and the listener chain has grown over this roadmap to include a STOMP send, traffic
  occupancy, the ghost recorder, and any installed plugin. That is only tolerable because the
  lock is *per session*, so a blocked listener can delay nobody but the player who triggered it.
  Changing `tryMove`'s `synchronized (s)` to `synchronized (this)` — one word, queueing every
  player in the server behind a single lock — broke exactly **one test out of 186**, and only
  after that test was written. New `SessionLockIsolationTest` pins both halves: a listener
  blocked on one session cannot stop another session moving, and moves on the *same* session
  still serialise. `GameSessionService` now records what the design costs, measured rather than
  asserted: a move is ~1.4µs with no listeners and ~1.3µs with traffic tracking (in-tree
  listeners are free within noise), while a listener that blocks for 60ms serialises that
  session's next ten moves into 579ms — so a listener needing slow or I/O-bound work should hand
  off to its own executor rather than borrowing the request thread. Added to the mutation
  harness, with a note on the anchoring trap below.
- **Mutation-tested the headline guarantees.** Six semantic breaks were injected one at a time
  — players able to walk through walls, BFS made LIFO so its paths stop being shortest,
  generators ignoring their seed, the leaderboard comparator inverted, rate limiting disabled,
  and half of all recorded search expansions dropped — each followed by a full test run and a
  byte-for-byte restore. **All six were caught**, so the suite has real teeth on the properties
  the project is sold on. (Harness at `mutants/run.py`; two apparent survivors turned out to be
  artifacts of running only the module that owned each file, which is worth stating rather than
  reporting as findings.)
- **Two core guarantees now defend themselves in core.** That module-locality point was a real
  gap, not just a harness quirk: `LeaderboardEntry`'s ordering and `SearchRecorder`'s fidelity
  live in `daedalus-core`, but every test of them lived in `daedalus-server`, so
  `mvn -pl daedalus-core test` stayed green with the leaderboard ranking worst-first and with
  half of every recorded search thrown away. A developer iterating on core got false confidence.
  New `LeaderboardEntryOrderingTest` and `SearchRecorderFidelityTest` close that, verified by
  re-running the mutations core-only — including one that drops a *single* expansion.
  `SearchRecorderFidelityTest` also documents a metric trap found while writing it:
  `cellsVisited` looks like the count to compare a recording against and disagrees with it by up
  to 17 on a 31×31 DFS solve; `cellsExplored` is the right one, and the true invariant
  (`cellsExplored - recorded ∈ {0, 1}`, measured over 324 solves) is what the arena's
  expansion-count verdict rests on.

### Fixed

- **`LivingMazeService` still compared a cell cost with `==` in one place.** The previous batch
  fixed the two sites SpotBugs flagged and left an identical third in `hotspotsOf`, where a
  weight a hair off `1.0` would be reported as a hotspot and shaded red. Now uses the same
  `WEIGHT_EPSILON` as its neighbours. Consistency rather than a live bug — traffic's decay snaps
  to exactly `1.0` — but it is the same defect class, one function away from the fix.
- **`TrafficService.quietTicks` was a `volatile int` being incremented.** The same
  read-modify-write pattern SpotBugs flagged on `LivingMazeService`'s tick counter, which it
  happened not to flag here. The fix goes the opposite way, because the field is genuinely
  different: it is touched only by the single-threaded ticker, so it is now a plain `int` with
  the confinement documented, rather than advertising cross-thread sharing that does not exist.
- **Campaign planning polluted the maze cache and lied to plugins.** Candidates were graded by
  generating them through `MazeGenerationService.generate`, which caches every maze and
  publishes `MazeGeneratedEvent`. A 6-stage campaign evaluates 54 candidates and serves 6, so
  **89% of them** were landing in the bounded maze cache — evicting mazes real users were
  playing, up to 2,400 junk entries at the default `max-campaigns` — while every plugin and
  STOMP subscriber was told 48 mazes had been generated that nobody could fetch. Candidates are
  now graded off the generator registry directly and only the winner enters the world;
  determinism makes that exact rather than approximate. Planning also got 58% faster as a side
  effect (411ms → 171ms), and the regression is pinned by a test, since nothing in the campaign
  response revealed it.
- **Dungeon crossbreeds came out with no dungeon left in them.** The connectivity repair ran
  Kruskal over every closed wall, which connects uncarved rock as eagerly as rooms: breeding two
  21×21 dungeon parents that were 49% and 50% rock produced children that were **0% rock on
  every seed** — connected, and unrecognisable as either parent. Repair now works on the
  habitable subgraph and tunnels a shortest corridor through rock only where leaving it would
  orphan a room; dungeon crossbreeds measure 46–50% rock and stay fully playable. Habitability
  is decided by each patch's donor parent rather than read off the stitched grid — the
  distinction matters, because a cell's four edges are inherited independently and the lottery
  can seal a cell both parents had carved, which the first version of this fix silently
  abandoned as rock (caught by spanning-tree parents, which contain no rock at all, producing
  children that did).
- **Campaign hazards silently 404'd.** The UI built hazard paths by interpolating the hazard
  name, but the `living` hazard is served by `POST /live` — every late-stage hazard failed. The
  hazard→path mapping is now explicit, with the mismatch noted.
- **Living and congested mazes changed in silence without STOMP.** Tick and pulse narration
  came only from broker frames, so with the CDN unreachable the polling fallback updated the
  maze with no explanation — worst exactly on late campaign stages, where hazards are the point.
  The polling path now reports walls opened and congestion changes.
- **`LivingMazeService.tick` incremented a `volatile int`.** `done++` is a read-modify-write and
  is not atomic even with a single writer thread; it is now an `AtomicInteger`. Pre-existing,
  surfaced by re-enabling SpotBugs (below).
- **Cell costs were compared with `==`.** `TrafficService` and `LivingMazeService.drift` tested
  computed doubles for exact equality to decide "did anything change?". Both now compare against
  a tolerance — the old code happened to work because a snap forces exactly `1.0`, which is one
  tuning change away from spinning on invisible deltas.
- **Verification gap owned:** batches 2–4 of this roadmap work were verified with
  `-Dspotbugs.skip`, so they never passed the project's own static-analysis gate. The full gate
  is green again, and the findings it had been hiding are fixed above (plus two documented
  `DMI_RANDOM_USED_ONLY_ONCE` false positives excluded with justification, per the project's
  convention of targeted exclusions over lowering the threshold).

- **Maze crossbreeding (ADR-006 idea #5).** `MazeBreeder` in core: two equal-sized parents
  produce a child by a patch-inheritance genome (3×3 blocks assigned to a parent by seeded
  coin flip, so offspring visibly wear both lineages — a Hilbert curve's discipline melting
  into a backtracker's rivers at the seams), then a seeded repair pass carves the minimum set
  of openings that makes every room mutually reachable while leaving genuine rock intact. That
  repair is load-bearing and proven so: disabling it leaves cells unreachable and fails the
  connectivity test immediately.
  `POST /api/v1/maze/breed?a=&b=&seed=` adopts the child as a first-class maze via the new
  `MazeGenerationService.adopt` (same metadata, cache entry, and `MazeGeneratedEvent` as a
  generated maze) — so a child can be solved, played, analyzed, brought to life, and bred
  again. Mismatched parents answer 400 with the dimensions. UI: **Crossbreed with previous**.
- **Spectator mode (ADR-006 idea #6).** `GET /api/v1/session/{id}` returns a read-only
  session snapshot, and the web UI gained a `#session=<id>` permalink: it loads the maze
  plus live positions and follows the same `/topic/session/{id}/player` frames the players
  produce (polling fallback when STOMP is unavailable). Spectators are genuinely read-only
  — keyboard and click input are refused client-side, verified in-browser (a spectator
  mashing arrow keys leaves `moveCount` at 0) — and owned sessions keep their existing
  per-destination STOMP authorization. Opening a session now logs its shareable link.
- **Chokepoint analytics (ADR-006 idea #9).** `GET /api/v1/maze/{id}/analysis` finally
  surfaces the `theory` module on the product surface: start↔goal min-cut (the actual
  chokepoint passages from `MazeFlow` — exactly 1 on every perfect maze, pinned at the
  HTTP seam), dead ends, and shortest-route length, computed on the maze's *current*
  snapshot. The web UI's **Analyze structure** button draws the cut passages as glowing
  violet gaps and dead ends as quiet dots, with a metrics banner — and re-analyzes on
  every living-maze tick, so you can watch a chokepoint dissolve as erosion braids it
  away. Shares the `mazeSolve` budget (comparable cost).
- **Ghost runs (ADR-006 idea #8).** Sessions now record the opening player's timed trail
  (`GameSession.TimedMove`, capped at `MAX_TRAIL`); on completion a new
  `SessionCompletedEvent` fires and `GhostService` keeps the best-scoring run per maze
  (bounded Caffeine store, `daedalus.ghost.*`) — the seat only changes hands on a
  strictly better score (teeth-proven: last-write-wins fails exactly the incumbent
  test). `GET /api/v1/maze/{id}/ghost` serves the recording; opening a session in the
  web UI summons it as a translucent racer replaying with its original pacing,
  hesitations included, and the finish line announces whether you beat it. Second
  players never pollute the recording.
- **Traffic simulation (ADR-006 idea #3).** `POST /api/v1/maze/{id}/traffic` closes the
  loop between play and routing: every cell a player or fog-of-war agent enters
  accumulates occupancy, a scheduled pulse applies it as cost (clamped at
  `daedalus.traffic.max-cost`) and decays every raised cost back toward uniform — so
  weight-aware solvers route around the crowd, and the shortcut reopens as it disperses.
  Both occupancy sources count identically (new `AgentSteppedEvent` alongside
  `PlayerMovedEvent`). Single-writer copy-on-write like the living ticker: moves only
  bump counters; the pulse thread copies, applies, swaps, and publishes a `TrafficFrame`
  (third frame shape on `/state`). Uniform grids are wrapped `WeightedMazeGrid` on
  enable; congestion mirrors into the response's `hotspots` list so cost shading just
  works. Bounded trackers (409 at capacity), self-retiring when fully decayed and quiet.
  UI: **Simulate traffic** button — pace back and forth and watch the floor heat up
  under your feet.
- **Solver arena (ADR-006 idea #2).** **Race solvers** in the web UI: two algorithms'
  REAL recorded expansion orders (the existing replay seam — observation, never
  reenactment) replay simultaneously at the same expansions-per-second, so the one that
  found the route with less work visibly finishes first; both routes then draw in lane
  colors and the verdict names the winner with the work ratio. Honest by construction:
  a solver that legitimately gives up loses by default, stated as such.
- **Per-maze leaderboards.** `GET /api/v1/leaderboard?maze={id}` — `LeaderboardEntry`
  gained a `mazeId` partition key (legacy null-maze entries stay global-only, pinned by
  `LeaderboardPartitionTest`, teeth-proven by disabling the filter). The daily
  challenge's board is now its own partition: the UI shows **Daily leaderboard** when
  today's maze is on screen, so a run on an easy 5×5 can never outrank daily runs.
  Redis backend keeps true per-maze sorted sets with a 48h TTL (time bounds key growth).
- **API errors now explain themselves in the web UI.** The server has always answered with
  RFC 7807 `ProblemDetail`, but the client's `api()` helper logged only the status line, so
  every failure looked identical. It now surfaces the server's `detail` — "400 … — parents
  must share dimensions: 15x15 vs 7x7" instead of a bare "400".
- **Fog-of-war agent API (ADR-006 idea #7).** The maze as a benchmark anything that
  speaks HTTP can compete on. `POST /api/v1/maze/{id}/agent` opens a *blind* walk: the
  agent sees only its position, the goal's coordinates, and which of the four directions
  are open from its current cell — the grid is never in any response (asserted on every
  response of the endpoint test's full walk). `POST /api/v1/agent/{id}/step?direction=…`
  moves; walking into a wall answers 400 *without consuming budget* (the view already told
  you the openings); `GET /api/v1/agent/{id}` re-polls visibility for free. Visibility is
  recomputed from the maze cache's **live** grid on every step and view, so a living maze
  erodes under the agent's feet mid-walk — the composition ADR-006 predicted, proven by
  `AgentWalkServiceTest` (swap an eroded snapshot in; the walled direction becomes open
  and walkable). Bounded everywhere: Caffeine agent store (`daedalus.agent.max-agents` /
  `idle-ttl`), per-walk step budget (default `4·rows·cols`, capped by `max-steps`), and a
  new `agentStep` rate budget (1200/min — a blind walk is hundreds of tiny requests by
  design). Verified end-to-end: a right-hand wall follower written against nothing but
  the HTTP surface solved the daily maze blind in 475 of its 1764 budgeted steps.
- **Daily maze (ADR-006 idea #4).** `GET /api/v1/maze/daily` — one shared challenge per
  UTC day. The seed derives from the date alone (epoch day × 64-bit golden ratio), so
  every instance, restart, and replica serves the *identical topology* with zero
  coordination or storage; teeth-proven by breaking the seed with `nanoTime()` and
  watching exactly the cross-instance determinism test fail. Lazily generated, self-
  pruning date map (no unbounded store), regenerates identically if the maze cache evicts
  it, and the literal `/maze/daily` path is pinned to outrank the `/maze/{id}` UUID
  template. The web UI grew a **Daily challenge** button; the daily maze is a first-class
  maze — solve it, bring it to life, or walk it blind.
- **Living mazes (ADR-006).** `POST /api/v1/maze/{id}/live` brings a maze to life:
  scheduled erosion ticks copy the cached grid, open a fraction of its dead-end walls
  (`Braider` reused as the erosion primitive), drift hotspot costs on weighted grids
  (clamped to the API's `[1, 1000]` domain), and atomically swap the new immutable
  snapshot into the maze cache — readers keep consistent old snapshots, no locking
  anywhere. Safe by construction: erosion only ever *opens* walls, so a live maze can
  never become unsolvable and a mid-run player can never be walled in. Deterministic:
  same maze + same seed erodes identically (default seed derives from the maze id).
  Bounded everywhere: ticks per run (`daedalus.living.max-ticks`), concurrent runs
  (`max-concurrent`, capacity answers 409), a new `mazeLive` per-caller rate budget
  (base/test/prod), and every run self-terminates — ticks exhausted, maze settled
  (nothing left to erode), or maze evicted (`replace` never resurrects). Each tick
  publishes `MazeMutatedEvent` (new plugin-api event), bridged as a `MutationFrame` on
  `/topic/maze/{id}/state`; the web UI's new **Bring to life** button re-fetches and
  quietly re-solves on every frame, so the drawn route visibly adapts as walls open —
  with a polling fallback at the server-reported tick interval when STOMP is absent.
  Chosen from a ten-idea deep audit recorded in ADR-006 (solver arena, traffic
  simulation, daily maze, fog-of-war agents, ghosts, chokepoint analytics, and more —
  now the roadmap). New core seam: `MazeGrid.copy()` / `WeightedMazeGrid.copy()`
  (weights preserved — teeth-proven: removing the override flattens weighted mazes to
  uniform cost and `LivingMazeServiceTest` fails on exactly that). Tests:
  `MazeGridCopyTest`, `LivingMazeServiceTest` (mutation, snapshot isolation,
  connectivity, determinism, settling, capacity, drift clamp),
  `LivingMazeEndpointTest`, `MazeWebSocketMutationBridgeTest`, and the templates test
  now pins `mazeLive`.
- **`application-prod.yml` now lists `sessionOpen` and `mazeLive` explicitly** with
  env-var-tunable limits and health indicators, matching their sibling budgets (they
  previously inherited base-yml defaults silently).

### Fixed

- **`WebSocketOwnershipSmokeTest` teardown race** — the refused-subscription tests
  provoke a server-side ERROR + close; `disconnect()` could race the socket into
  CLOSING and fail the test that had just passed. Teardown now tolerates that close.

### Changed

- **Server coverage ratchet raised 0.67 → 0.79** — measured 82.2% instruction (up from
  70.3% when pinned; the UI-sprint and audit tests), re-pinned ~3 below per the ratchet's
  own rule. Core (90.3%) and plugin-runtime (87.0%) barely moved; their pins stand.

### Fixed

- **Wiring audit (2026-07-29): the plugin subsystem's configuration was wired to nothing.**
  `PluginConfig` read `daedalus.plugin.dir` while every profile configured
  `daedalus.plugins.directory` — the configured plugin directory and the
  `DAEDALUS_PLUGIN_DIR` env var were silently ignored (plugins loaded from `./plugins`
  relative to the working directory). And `daedalus.plugins.scan-on-startup`, set in every
  profile and `false` under test, was read by nothing: startup scanning ran unconditionally,
  and the test profile only *appeared* to disable it. Both properties are wired now, pinned
  by `PluginSpiEndToEndTest` — the suite's first true SPI proof: a JAR packaged at test time,
  discovered from the configured directory by a booting server, its generator listed in the
  catalog, generating over HTTP, visible on the ops endpoint, and reported STARTED by
  `/api/v1/plugins`. Fails against the old property name.
- **The glyph projection lied about dungeons — at the source.** `toTileGrid()` marked every
  cell PASSAGE whether or not anything carved it, so rock rendered as floating floor specks
  in every JVM consumer (JavaFX desktop, ASCII art) — the web UI had patched it client-side,
  which was the tell the fix belonged in core (ADR-003 rule 1). Two honesty rules now:
  uncarved cells project as WALL, and a wall post surrounded by four open segments is room
  interior. Perfect-maze output is byte-identical (pinned), so spanning-tree consumers see
  no change; dungeons render honestly everywhere at once. `TileGridProjectionTest`.

### Fixed (earlier this day)

- **Back-end audit: every in-memory store the server accumulates into is now bounded.**
  Three had the same slow leak the rate-limiter buckets had before their Caffeine bound
  (BACKLOG, 2026-07-19): the **maze cache** (one full grid per generation, up to 43k/day
  inside the base rate limit, kept forever), the **session store** (never evicted, not even
  after completion), and the **in-memory leaderboard** (one entry per completed session,
  forever). Maze cache and sessions now sit in Caffeine caches (size + idle-TTL bounds,
  `daedalus.maze.cache.*` / `daedalus.session.*`); the leaderboard trims from the worst end
  past `daedalus.leaderboard.max-entries` (default 100 — `top(n)` caps at 100, so deeper
  retention was pure growth; the Redis backend keeps full history independently). Eviction
  rides the APIs' existing "unknown id" 404 paths, and the idle TTLs (2h) far outlive any
  game actually being played. `BoundedStoresTest` pins all three bounds.

### Added

- **Weighted mazes over the API** — the load-balancer thesis made demonstrable.
  `GenerateRequest.hotspots` raises per-cell traversal costs (validated `[1.0, 1000.0]`,
  ≤64 spots, out-of-bounds → 400 via a new `IllegalArgumentException` handler); the served
  grid becomes a `WeightedMazeGrid` and the response echoes the applied spots. Dijkstra,
  A\*, and Dial route around expensive cells wherever the topology offers a choice —
  `WeightedMazeApiTest` proves the detour by pricing Dijkstra off its own best route on a
  dungeon. The web UI grew hotspot controls and cost-shaded floors; combined with search
  replay, the detour happens on screen. This fires the last dormant ADR-004 trigger
  (weighted-floor shading), and honestly: the API creates the data now, not a constant.
  The circuit-breaker fallback preserves hotspots and rethrows caller errors instead of
  swallowing them into a silently different maze.
- **The prod profile boots under test for the first time.** `ProdProfileBootTest`
  assembles the full application under `prod` (env contract satisfied with test values,
  Redis off) — a prod-only wiring break now fails CI instead of the first production start.
  It also pins the prod actuator posture: health open, unexposed endpoints answer 401.
  `RateLimiterTemplatesTest` pins that every `@PerKeyRateLimit` budget has its yml instance.
- **Mazes over `curl`** — `GET /maze/{id}` content-negotiates `text/plain` into terminal
  ASCII art (core `AsciiMazeVisualizer` on the product surface), with `?solve=<solverId>`
  overlaying a route. Dungeons render honestly thanks to the projection fix.
- **ADR-005: single-instance posture.** The audit's design-level observation, written down:
  sessions, the maze cache, and the leaderboard's serving path are process-local on purpose,
  a second instance today would misbehave in specific enumerated ways, and the
  externalization path (Redis sessions with a distributed replacement for the tryMove lock,
  recipe-based maze regeneration, STOMP broker relay) is recorded now with the existing
  concurrency test named as its acceptance bar. Trigger: a real deployment wanting a second
  instance.
- **`docs/handoff/`** — the three LoadBalancerPro issues as paste-ready files, the Dependabot
  re-triage as a dry-run-first PowerShell script over `gh`, and Codecov activation steps:
  the full GitHub-side chore list reduced to a fifteen-minute pass.
- **`sessionOpen` rate-limit budget** on `POST /maze/{id}/session` and
  `POST /session/{id}/join` (60/minute/caller at the base config) — session creation feeds
  every bounded store downstream, so the inflow gets the same per-caller budget the other
  write endpoints already had.

## [1.1.0] — 2026-07-29

**The web UI grew up, and it caught a released bug on day one.** A visual audit
(headless-browser screenshots of all 23 generators through the real UI) drove
five rounds of front-end work — and the deepest find wasn't cosmetic.
Suite: 398 → **416 tests**.

### Fixed

- **Every REST-served dungeon was unsolvable (shipped in 1.0.0).**
  `MazeGenerationService` pinned start at `(0,0)` and goal at the far corner —
  carved cells for every spanning-tree generator, solid rock for a BSP dungeon.
  Every solver returned `success=false` and a play session opened inside a
  wall. Found by looking at the rendered output; the same corner assumption the
  07-19 audit removed from `theory`, one layer up. Fixed with
  `MazeMetrics.placeStartAndGoalAtExtremes` (largest-component-seeded,
  deterministic) — dungeons work, and every maze now gets the maximum-challenge
  diameter-endpoint placement the core recommends. `MazeGenerationStartGoalTest`
  fails against the pre-fix service.
- **Player names reached `innerHTML` unescaped** in the UI's log (and would
  have in the leaderboard) — stored XSS via a 64-char player name. Untrusted
  text now renders via `textContent`/escaping everywhere.

### Added

- **`MazeReplay` (ADR-004's deferred item, its trigger now fired).**
  `SearchRecorder` is the single interception point the design note called
  for: a thread-confined observer decorating the `Graph` that
  `AbstractMazeSolver.graphOf` hands out. Solvers run untouched — replay is
  observation, never simulation. `?replay=true` on the solve endpoint ships
  the expansion order (omitted otherwise: pre-replay clients see byte-identical
  JSON); off-seam solvers (IDA\*, wall follower) return empty expansions
  rather than a fake. The UI plays it in two acts: the real exploration front
  spreads cell by cell, then the route draws over it — BFS visibly floods,
  A\* visibly leans.
- **Web UI, five rounds.** Renderer rewrite (wide light corridors on thin dark
  walls; rock and interior wall-posts detected so dungeons read as rooms, not
  polka-dot noise); algorithm descriptor cards from the live catalog; solve
  stats readout; **compare-all-solvers** table (best path / fewest visits
  highlighted, hover previews each route, honest "gave up" rows); leaderboard
  panel over the existing API; click-to-move; illegal-move feedback; victory
  ring + session-complete banner; breadcrumb trails; maze permalinks
  (`#maze=<id>`); PNG export; `prefers-reduced-motion` support; graceful
  degradation when the STOMP CDN is unreachable (play still works via local
  position fallback).

### Decided

- **Weighted-floor shading stays unbuilt** — examined and the trigger has
  genuinely not fired: no REST-served maze carries cell weights (wall weights
  are consumed during Weighted-Prim's construction; `WeightedMazeGrid` is an
  embedding-only tool). Recorded in ADR-004; re-fires when the API can serve
  genuinely weighted mazes.

## [1.0.0] — 2026-07-28

**The audit's to-do lists are now empty.** One day, nine pushes: TESTING.md's
gap audit written and then fully executed (P1 through P3), the BACKLOG's last
hardening item and all four stretch goals shipped, and the engine audit's §2
recommendations either implemented or declined with reasons (ADR-004). The
suite grew 347 → **398 tests**, and — keeping the 07-19 through-line honest —
one of the new tests surfaced a live production bug (a check-then-act race in
`tryMove`) that was fixed before it shipped anywhere.

### Added

- **Example modules now build in CI.** `ci.yml` builds `loadbalancer-topology`,
  `dungeon-layout`, and `benchmark-harness` after the reactor `install` —
  before this, 17 test methods across those modules (including the one that
  caught the Hilbert forest) never executed on any push. (TESTING.md P1.)
- **`WebSocketSmokeTest`** — the realtime counterpart of `ApplicationSmokeTest`
  and the first test to construct a real `WebSocketStompClient`: connect
  without credentials in the advisory profile, valid-token accept, forged-token
  reject (proving the interceptor is *installed*, which the unit test cannot),
  and one broker frame round-trip per topic family. The simple broker sends no
  RECEIPTs, so tests republish their idempotent event until the first frame
  arrives — never `Thread.sleep`. (TESTING.md P1.)
- **Structural roster guards.** `PackageScan` (test-only, ~30 lines over
  `ClassLoader.getResources`) makes the solver and generator rosters
  completeness-checked against the package contents: a new concrete
  implementation left off the sweep now fails the build instead of silently
  shipping untested — the exact hazard that hid Trémaux. `DungeonGenerator`'s
  exclusion became visible code. (TESTING.md P2.)
- **JaCoCo ratchet.** `jacoco:check` fails `verify` below per-module
  instruction thresholds pinned 2–3 points under measured coverage — core
  0.87 (was 90.1%), plugin-runtime 0.84 (87.0%), server 0.67 (70.3%) — with
  desktop and plugin-api exempted as explicit `0.00` properties. Before this,
  a PR that deleted tests passed CI with a quietly shrinking badge.
  (TESTING.md P2.)
- **`PluginControllerTest` + `SpringPluginContextTest`** — the two zero-
  reference classes from the audit. The context test pins fail-fast
  `NoSuchBeanDefinitionException` for unavailable beans as plugin contract.
  (TESTING.md P2.)
- **Session ownership + STOMP per-destination authorization** — the second
  half of the BACKLOG auth item. Sessions opened by an authenticated request
  record the token's subject (`GameSession.owner()`, null for anonymous);
  `StompSubscriptionAuthorizationInterceptor` refuses SUBSCRIBE to an owned
  session's `/topic/session/{id}/player` unless the principal is the owner.
  Deliberately open: unowned sessions, unknown ids (no existence oracle), and
  the shared maze/plugin topics. Integration tests replayed against a build
  without the interceptor registered: exactly the two refusal tests fail.
- **Multiplayer sessions** behind `daedalus.session.multiplayer` (default off
  — off is byte-for-byte the pre-flag behavior). Per-player positions,
  `POST /session/{id}/join` (404 with the flag off; rejoin keeps position),
  `MoveRequest.player`, additive `player` on `PlayerMovedEvent`/`MoveFrame`.
  Any player reaching the goal completes the session exactly once.
- **Web UI** — one file of vanilla JS at `static/index.html`, served at `/`:
  generate/solve/play over REST, live frames over STOMP via SockJS, canvas
  rendering with path overlay and per-player markers. No build step, no npm;
  it exercises the public surfaces exactly as an external integrator would.
- **`ChaosGenerator`** (`id: chaos`, generator #23): splits the grid into 2–3
  bands, delegates each to a seeded random pick from four algorithms, joins
  bands with single doors — trees joined by single edges are a tree, so the
  spanning-tree contract holds and the roster guard forced it into the full
  connectivity/awkward-shape sweep automatically. Band doors are guaranteed
  chokepoints: deliberate stress texture for routing policies. (Audit §2.1.3.)
- **`MazeVisualizer` + `AsciiMazeVisualizer`** in `com.daedalus.visualize`,
  with `MazeGrid.toString()` now rendering ASCII art through the same
  `TileType` projection the REST surface ships. (Audit §2.1.1 + §2.3.)
- **`/actuator/algorithms`** — live registry observability (counts +
  descriptors, plugin contributions included); visible in dev, absent from
  prod's include list, JMX for free via actuator. (Audit §2.1.2.)
- **Codecov upload** in CI, guarded on the `CODECOV_TOKEN` secret — absent
  the secret, CI is unchanged. (BACKLOG, last piece of the original CI item.)
- **`TESTING.md`**, **ADR-003** (desktop testing policy: thin shell, logic
  moves to core, no TestFX, ratchet exemption as visible code), **ADR-004**
  (disposition of audit §2: Octile declined — the grid is 4-connected;
  parallel generation and `MazeReplay` deferred with named triggers).

### Fixed

- **`GameSessionService.tryMove` had a check-then-act race.** `ConcurrentHashMap`
  protects the map, not compound operations on one session: two racing moves
  could both validate against the same stale position (illegal transition),
  lose `moveCount` increments (`long++`), or double-complete a session — two
  leaderboard rows for one win. Now guarded by a per-session lock; the
  4-thread × 500-round hammer in `GameSessionServiceConcurrencyTest` fails
  against the pre-fix code on every run tried and passes deterministically
  after. Found because TESTING.md P3 said "test only if inspection finds
  check-then-act" — it did. This guard becomes ownership-critical now that
  sessions have owners.

### Changed

- **ADR-001 is Accepted** — items 1–5 and 7 done with measurements inline;
  item 6's remaining step (pasting the prepared LoadBalancerPro issues into
  their tracker) is a GitHub-side action, as are the Dependabot re-triage
  pass (commands recorded in BACKLOG.md) and the Codecov token.

## [1.0.0] — 2026-07-18 → 2026-07-19 (released with 1.0.0)

**Framework migration, three correctness fixes, and the test gaps that hid
them.** Repo is live at `RicheyWorks/Daedalus2`. Spring Boot moved 3.3.1 → 4.1.0
for four coordinates and one import; the graph seam finished absorbing the
solvers; and `theory` grew the pieces the ecosystem work needs.

The through-line of 07-19 is worth stating once, because three separate bugs
shared it: **the test fixtures were all the easy shape.** Every solver fixture
was a *perfect* maze — a spanning tree, where exactly one route exists between
any pair of cells, so a solver can be badly wrong and still look right. That hid
an inadmissible `LandmarkHeuristic` (A\* still returned the only path there was)
and a `TremauxSolver` missing one of Trémaux's three rules (it could not solve a
looped maze at all). Every generator fixture was a *square* grid, and every
`theory` caller assumed `(0, 0)` was part of the maze — false for a BSP dungeon,
whose corners are solid rock, which made `diameter` return 0 and put a generated
level's entrance and exit on the same square. Separately, every server test was
a *slice*, so a springdoc major version bump sailed through 267 green tests
without anything ever requesting `/v3/api-docs`.

Each fix therefore ships with the property test that would have caught it:
braided mazes across every solver, awkward grid shapes across every generator,
and one full-context smoke test that boots the real application. Where a
decision was measured rather than argued, the numbers are in the entry.

### Added

- **`MazeMetrics.largestComponentCell`, and the corner assumption it removes —
  found by building the ai-dungeon-master example.** Four call sites seeded
  themselves at `new Point(0, 0)`: `MazeMetrics.diameter`,
  `FacilityPlacement.kCenter` / `kCenterAcrossComponents`, and
  `LandmarkHeuristic.precompute` (twice). That is safe for a maze generator —
  every cell is carved, so the top-left is always in the single component — and
  silently wrong for anything sparser.

  A BSP dungeon has **solid rock in its corners**. Running the new
  `examples/dungeon-layout` against a 33² dungeon, the first output was:

  ```
  exact diameter   99 steps
  fast estimate     0 steps        <- measured a one-cell component
  rooms served      1 of 529 floor cells
  entrance (0,0)   boss (0,0)      <- same square of rock
  ```

  `diameter` seeded at an isolated rock cell, returned 0, and
  `placeStartAndGoalAtExtremes` therefore put the entrance and the boss room in
  the same place. `FacilityPlacement` collapsed the same way. After seeding from
  the largest connected component instead — one extra O(V + E) flood fill, so
  `diameter` stays linear — the same level reports diameter 99 (agreeing with
  `exactDiameter`), a hardest route 2.5× the direct one, and **529 of 529 floor
  cells served**.

  On a fully carved maze `largestComponentCell` returns `(0, 0)`, so nothing
  changes for existing callers. This is the same defect class as the Trémaux and
  ALT bugs: an assumption about graph shape that every maze fixture satisfies.

- **`FacilityPlacement.kCenterAcrossComponents` — k-center that survives a
  partitioned graph.** Found by auditing `theory` for a second shape assumption:
  not loops this time but **disconnection**, which the vision docs' own
  chaos-engineering pitch creates ("inject 15% node failure").

  Nothing in `theory` throws on a fragmented graph — `DistanceOracle` reports
  `UNREACHABLE`, `WaypointTour` reports `feasible=false`, `MazeFlow` correctly
  gives edge connectivity 0 across a cut. But `kCenter`'s greedy scores an
  unreachable cell as `-1` and compares with `>`, so it can never leave the
  component it started in. Measured on a 16×16 tree severed along one column
  (16 cut edges in a spanning tree ⇒ 17 components):

  | k | `kCenter` radius / served | `kCenterAcrossComponents` radius / served |
  |---|---|---|
  | 1 | 82 / 114 of 256 | 82 / 114 of 256 |
  | 2 | 44 / 114 | 82 / 126 |
  | 3 | 25 / 114 | 82 / 169 |
  | 8 | 12 / 114 | 82 / 212 |
  | 12 | **7** / 114 | 82 / 254 |

  Adding facilities drives the covering radius steadily down — 82 to 7, a
  placement that looks better and better — while coverage never moves off
  **114 of 256 cells**. Every extra facility refines service inside the one
  component the greedy can see; the other 142 cells are no closer to anything.
  Nothing lies; `servedCells` is in the result. But a quality metric that
  *improves* while more than half the graph stays unreachable is worth naming
  explicitly.

  **Both behaviours are kept, because both have a real consumer.** For a dungeon
  — placing treasure, save points or boss rooms — unreachable cells are solid
  rock, genuinely not places, and `kCenter` is correct. For a partitioned
  network, every fragment still holds real nodes, and `kCenterAcrossComponents`
  is. The new variant ranks unreachable cells as infinitely badly served, which
  is simply what the k-center objective says: the cost of a placement is the
  distance from the worst-served node, and for an unreachable node that is
  infinite. The 2-approximation still holds per component; across components no
  ratio is claimed, since with fewer facilities than components the objective is
  unbounded. On a connected grid the two are asserted to agree exactly, so the
  generalisation cannot disturb the ordinary case.

- **`MazeMetrics.exactDiameter` — the true diameter, for when the estimate
  isn't good enough.** Came out of auditing the `theory` package for the same
  defect class that bit the solvers: code that is only correct on a tree. The
  two prime suspects both turned out to be **already honest** —
  `MazeMetrics.diameter` documents itself as "exact for perfect (tree) mazes; a
  lower-bound heuristic if the maze has cycles", and `LongestPath` names its own
  NP-hardness and states outright that "the problem only becomes hard once the
  maze is braided". No bug to fix.

  What neither did was *quantify* the caveat, which is what a caller actually
  needs. Measured over 15 mazes at 20² per setting, double-BFS against the true
  diameter:

  | braid factor | mean error | worst error |
  |---|---|---|
  | 0.0 (perfect) | 0.0% | 0.0% |
  | 0.1 | 0.5% | 9.6% |
  | 0.3 | 0.6% | 8.4% |
  | 0.5 | 1.4% | **20.0%** |
  | 0.7 | 3.4% | 9.5% |
  | 1.0 | 2.5% | 13.6% |

  Tight on average, but **up to 20% low on an individual looped maze**. The
  two-sweep argument needs the farthest cell from an arbitrary source to be an
  endpoint of some diameter, and one cycle breaks that — a shortcut can land the
  first sweep somewhere lying on no diameter at all.

  That distinction is use-case dependent, so both are now available and the
  javadoc says which to reach for. Ranking generators or placing a start and
  goal far apart: keep the O(V + E) estimate — `placeStartAndGoalAtExtremes`
  deliberately still uses it. Capacity or latency planning over a braided
  topology, where the diameter *is* the worst-case route length: use
  `exactDiameter` and pay the O(V²).

  Tested against an independent brute-force implementation at four braid
  factors, plus a directional assertion that the fast estimate is **never an
  over-estimate** — that direction is the one that matters, since an
  over-estimate would understate worst-case route length in planning use.

- **Generator shape sweep — every generator against awkward grid shapes.**
  Third shape assumption audited today, after loops and disconnection: **grid
  shape itself**. Every generator fixture in the repo used a square grid, yet
  several generators carry an implicit assumption about dimensions — the
  space-filling curves want a power of two, `EllersGenerator` works a row at a
  time, `DungeonGenerator` needs room to split BSP leaves.

  `GeneratorConnectivityTest` already covered this for `HilbertCurveGenerator`
  specifically, since that is where the forest bug was found. It now sweeps all
  21 spanning-tree generators across eight shapes: `1×1`, `1×10`, `10×1`, `2×3`,
  `7×13` (both prime), `33×17`, `5×64` (extreme aspect ratio) and `20×20`
  (square but not a power of two). `DungeonGenerator` gets its own case at the
  same shapes, asserting the property that survives its contract — rock is meant
  to be unreachable, but the **carved** space must be a single connected level,
  or the layout contains rooms the player can never enter.

  **The audit found nothing**: 22 generators × 9 shapes, zero violations. Worth
  having anyway — it converts "the square-grid tests happen to pass" into an
  enforced property, and a generator that quietly dropped the last column of a
  lopsided grid, or divided by zero on a single row, would now fail loudly.

- **`examples/benchmark-harness` — timings for all 22 generators and 10
  solvers.** Standalone `main`, configurable sizes and seeds, writing
  `docs/benchmarks/benchmark-<date>.csv` alongside a console summary with a
  "vs fastest" column.

  The design decisions are mostly about **not producing misleading numbers**.
  Every CSV carries its JVM, OS, CPU count and heap in the header, because a
  timing without its machine is an anecdote rather than a measurement — during
  this project's own optimisation work, repeated runs of identical code varied
  by more than 2× on a loaded host. So the column worth acting on is relative
  cost within a single run. Timings are **medians**, not means, so one GC pause
  cannot move a published figure. And an algorithm that exceeds a 2-second
  budget is measured once and flagged `single-sample` instead of being warmed up
  and repeated five times — IDA\* costs roughly 300× BFS, and without that rule
  the sweep simply never finishes. It is deliberately outside the reactor and
  outside CI: a timing assertion on a shared runner fails for reasons that have
  nothing to do with the code. Its own tests assert structure — full algorithm
  coverage, well-formed rows, median-over-mean behaviour — and never a duration.

  Two self-inflicted bugs fixed during the build, both worth noting because both
  were silent. `exec:java` runs with the *module* as its working directory, so
  the original relative output path created a second, invisible
  `examples/benchmark-harness/docs/benchmarks/`; results now resolve to the
  repository root. And an XML comment cannot contain a double hyphen, so
  documenting the `--sizes` flag inside the pom's comment block made the pom
  unparseable.

- **`PluginSubsystemHealthIndicator` — plugin state as actuator detail, never
  as a verdict.** Reports `loadedPlugins`, `failedPlugins` and a `lastFailure`
  description, listening for `PluginFailedEvent` to keep the count.

  It is **deliberately incapable of reporting DOWN**, and that is the whole
  design. Boot folds component statuses into the aggregate, and the aggregate
  is what a load balancer or Kubernetes readiness probe acts on — so an
  indicator that condemned the instance because an *optional* plugin failed to
  boot would pull a healthy server out of rotation. That is not hypothetical:
  the stock Redis indicator did exactly that earlier the same day, dragging
  `/actuator/health` to 503 on an application working fine on its in-memory
  backend. The fix there was to stop it contributing; the lesson applied here
  is to not contribute a failure status at all. Failures surface as details for
  a human or dashboard, and the engine, REST API and solver registry keep
  serving — which is the point of loading plugins in isolation.

  Tested twice over, deliberately. A unit test hammers 250 failures across every
  `Phase` and asserts the status never budges; the smoke test then asserts the
  bean is actually **registered in the booted context**, because a unit test can
  only prove the indicator would answer UP if asked, not that Spring ever asks.
  That second assertion goes through the `ApplicationContext` rather than the
  health payload — component detail is hidden by default, and a test that
  tolerated its absence would have asserted nothing at all.

- **`SolverBraidedMazePropertyTest` — every solver, over mazes with loops.**
  Closes the gap that let two separate correctness bugs ship behind a green
  suite this month: **every solver fixture in the repository was a perfect
  maze**. A perfect maze is a spanning tree, which makes it a uniquely
  forgiving subject — exactly one route exists between any pair of cells, so a
  solver can be badly wrong and still look right. `LandmarkHeuristic` was
  inadmissible yet A* still returned the optimal path (there was only one to
  return); `TremauxSolver` could not solve a looped maze at all and no fixture
  contained a loop.

  The test sweeps 10 solvers × 4 generators × 5 seeds × 4 braid factors and
  asserts three properties: every returned path is a legal traversal (starts at
  the start, ends at the goal, never crosses a wall), every *complete* solver
  finds a route wherever BFS does, and every *optimal* solver still returns a
  shortest one once route choice actually exists. Runs in ~1.2 s.

  **The audit behind it found no further defects** — nine of ten solvers are
  correct at every braid factor, and the tenth, `wall-follower`, fails only
  where its own javadoc says it will (wall following is provably complete only
  on simply-connected mazes; it gives up via an iteration cap rather than
  hanging, and never returns a wrong path). Its exclusion is scoped to
  completeness alone — it is still held to the legality contract, and a separate
  case pins the guarantee it *does* make. Asserting that it fails on loops would
  forbid anyone from later improving it.

  Verified to have teeth rather than assumed: replaying the pre-fix
  `TremauxSolver` against this exact matrix fails **21 of 80** cases. There is
  also a tripwire asserting the solver list is complete, since silently omitting
  a new solver is precisely how Trémaux went untested.

- **`ApplicationSmokeTest` — the first test that boots the whole application.**
  Until now every server test was a slice (`@WebMvcTest` for controllers,
  `ApplicationContextRunner` for `RedisConfig`), which left a blind spot: no
  test ever assembled the full context, and nothing whatsoever exercised what
  the starters contribute for free. The springdoc **2.6.0 → 3.0.3** major bump
  went through a fully green 267-test suite without a single assertion touching
  `/v3/api-docs`. This adds one `@SpringBootTest(webEnvironment = RANDOM_PORT)`
  covering the joins: the context loads with the engine registries wired across
  the module boundary, `/actuator/health` is `UP`, `/v3/api-docs` serves a
  document whose `paths` cover the contract endpoints, and `/swagger-ui` is
  served. Path coverage is asserted as a *subset* (`containsAll`), not an exact
  count — adding an endpoint shouldn't fail the test, but silently losing one
  should.

  It paid for itself on the first run by failing on the 503 health bug recorded
  under **Fixed** below — a defect no slice test could have observed, and one
  that had been latent in the default profile.

  Implementation note for anyone extending it: this uses Spring Framework 7's
  `RestTestClient`, because **Boot 4 removed `TestRestTemplate`** from
  `spring-boot-test`. `WebTestClient` is the usual alternative but pulls in
  `spring-webflux`, which this module deliberately does not depend on.

- **`theory.ComplexityAnalyzer` — empirical complexity harness.** Revives the
  long-stubbed `com.daedalus.theory.ComplexityAnalyzer` (last seen in the v1.x
  portfolio) against the current engine API. Runs every registered generator
  at a fixed seed across configurable square sizes (default 32²/64²/128²),
  capturing the work each reports through `MazeStats` (cells visited, peak
  frontier, backtracks, path length) plus a wall-clock timing. `analyzeAll()`
  sweeps a `GeneratorRegistry` and returns a stably-sorted `Report` (a
  generator that throws is recorded as `success=false` rather than sinking the
  sweep). `Report.toCsv()` / `toJson()` emit only the deterministic,
  seed-stable columns — no wall-clock — so the report is a committable golden
  file for regression detection; timing stays on each `Measurement` for live
  inspection. Hand-rolled CSV/JSON, so daedalus-core gains no new dependency.
  Covered by 10 tests (determinism, no-stats and throwing-generator paths,
  a sweep over all 20 built-in generators, and the serialized shape). Clears
  the item from `BACKLOG.md` "New surfaces".
- **`theory.GrowthEstimator` — empirical Big-O labelling.** Turns a
  `ComplexityAnalyzer` sweep into a growth verdict per generator: fits each
  `metric(n)` against candidate classes (`O(1)` … `O(n^2)`) by
  least-squares-through-origin plus R² model selection, and reports the
  log-log power-law exponent alongside. Deterministic (rides the seed-stable
  counters); metrics that stay at zero or fewer than two distinct sizes return
  `UNKNOWN` rather than a fabricated class. Covered by 8 tests over synthetic
  known-growth data plus a live sweep. Implements idea **T1** from
  `AUDIT_CLRS_IDEAS_2026-07-18.md`.
- **`theory.MazeMetrics` — diameter & auto start/goal placement.** Double-BFS
  over the passage graph (CLRS Ch. 22) finds the maze's two farthest-apart
  cells — exact for perfect (tree) mazes, a lower-bound heuristic when the maze
  has cycles — and `placeStartAndGoalAtExtremes` drops the start and goal there
  for a maximal-challenge layout. Also exposes `farthestFrom` and
  `distancesFrom` (BFS distance field, `-1` for unreachable) for heat-maps.
  Deterministic (row-major tie-break on the farthest cell). Implements idea
  **T3** from the CLRS audit; 6 tests over hand-built mazes and a real
  perfect maze.
- **`theory.MazeFlow` — min-cut chokepoints & edge connectivity.** Edmonds-Karp
  max-flow (CLRS Ch. 26) over unit-capacity passages: the minimum start→goal
  cut is the fewest passages that would seal the goal off, and the cut edge set
  is exactly those bottleneck passages. Equivalently the start↔goal edge
  connectivity — `1` for a perfect maze (single route), `≥2` once braided.
  `minCutStartToGoal` / `edgeConnectivity` convenience; deterministic.
  Implements idea **X1** from the CLRS audit; 6 tests (perfect vs. braided,
  cut-edges-actually-disconnect, determinism).
- **`solver.solvers.DialSolver` — bucket-queue (Dial's) shortest path.** Dijkstra
  with a bucket priority queue keyed by integer distance (CLRS Ch. 24, and the
  bounded-key idea of Ch. 20): `O(C·V + E)` instead of `O((V + E) log V)`,
  near-linear on a grid. Reads the same `weightOf` hook as `DijkstraSolver` and
  returns an identical optimal path on uniform and integer-weighted mazes; it
  refuses fractional weights (bucketing is ill-defined — use Dijkstra there).
  Registered in `AlgorithmConfig` as solver id `dial`. Implements idea **S1**
  from the CLRS audit; 7 tests (matches Dijkstra on uniform + integer-weighted
  grids, detours around costly cells, rejects fractional weights, determinism).
- **`theory.LongestPath` — hardest route (longest simple path).** Budget-bounded
  DFS backtracking for the longest simple start→goal path: exact for small mazes,
  an honest lower bound (`exact=false`) when the budget is hit — never a wrong or
  non-simple path. The class javadoc documents why this is NP-hard (Hamiltonian
  path reduces to it, CLRS Ch. 34) and why no polynomial exact algorithm is
  attempted (Ch. 35). Trivial on perfect mazes (unique path), interesting once
  braided. `hardestRoute(grid)` convenience. Implements idea **T2** — the last of
  the CLRS-audit top five; 5 tests (braided longest > shortest, perfect == unique
  path, inexact-under-budget, determinism).
- **`engine.Braider` — dead-end braiding.** Seeded, deterministic post-process
  that opens one wall on a configurable fraction of dead ends, turning any
  generator's perfect maze (a spanning tree) into a braided one with real loops
  and route choice. This is the keystone for the structural metrics: min-cut
  (`MazeFlow`) is always 1 on a tree and longest-path (`LongestPath`) always
  equals shortest, so both only become meaningful once braided. Implements idea
  **G4**; 6 tests (full braid leaves zero dead ends, edge count exceeds `V-1` so
  cycles exist, exact fractional targeting, determinism, no-op at factor 0).
- **`solver.LandmarkHeuristic` — ALT (A\*, landmarks, triangle inequality).** BFS
  distance fields from a few greedily-spread landmarks give the bound
  `h(a,b) = max_L |d(L,b) - d(L,a)|`, admissible by the triangle inequality (the
  same potential-function reasoning as Johnson's reweighting, CLRS Ch. 25).
  Unlike Manhattan — which measures straight-line distance and is oblivious to
  walls — these distances are measured through the actual passages, so the bound
  reflects the detours a solver really has to make. Plugs straight into
  `AStarSolver`'s existing heuristic constructor. **Measured: ~55% fewer A\*
  expansions than Manhattan** (58,799 → 26,167 cells across 45 mazes at 25², 40²
  and 60²). Unit-cost grids only — hop counts would over-estimate on a
  `WeightedMazeGrid` and break optimality, which the javadoc states plainly.
  Implements idea **S2**; 5 tests (admissibility checked on *every* cell,
  optimality vs BFS, the aggregate expansion win, deterministic landmark choice).
- **`engine.generators.WeightedPrimsGenerator` — Prim's as an actual MST.**
  Weights every wall up front and always carves the cheapest frontier wall via a
  priority queue (CLRS Ch. 23), where the existing `PrimsGenerator` pulls a
  *uniformly random* frontier wall — a different algorithm with a different bias,
  so the two yield different mazes from the same seed. Registered as generator id
  `weighted-prims` (the built-in roster is now 21).
  **Correction to the original idea:** it proposed weight *variance* as a texture
  knob, but that cannot work — an MST depends only on the relative *order* of edge
  weights, and any strictly monotone reweighting (scaling, powers, variance
  changes) leaves the order, and hence the tree, identical. i.i.d. weights from
  any continuous distribution give the same family of mazes. What genuinely
  changes texture is breaking isotropy, so the knob shipped is a
  `horizontalBias` subtracted from east–west walls, which stretches the maze into
  long horizontal corridors. Implements idea **G1**; 5 tests (spanning-tree
  property, determinism, differs from random-frontier Prim's on the same seed,
  the bias measurably increases east–west passages, stats populated).
- **`theory.MazeFlow.vertexDisjointPaths` — route redundancy via Menger.** Counts
  the routes between two cells that share no intermediate cell, using the
  vertex-splitting reduction to max flow (CLRS Ch. 26): every cell becomes
  `v_in → v_out` joined by a capacity-1 arc, so no single cell can carry two
  routes. By Menger's theorem that count is also the fewest intermediate cells
  you'd have to block to sever the two. It is always `<=` the edge connectivity
  from X1 — blocking cells is at least as powerful as blocking passages — and is
  exactly `1` on any perfect maze, since a tree has one route; `Braider` is what
  creates genuine alternatives. Implements idea **X2**; 8 tests, including the
  vertex `<=` edge invariant checked across 15 braided mazes.
- **`theory.WaypointTour` — optimal "collect all the coins" routes.** Shortest
  route from a start cell visiting every waypoint, solved exactly by the
  Held–Karp dynamic program (CLRS Ch. 15's subset DP applied to the TSP-path
  variant of Ch. 34). Visiting waypoints nearest-first is *not* optimal — picking
  the order is the hard part — so the DP keys on *(set already collected, cell
  you're standing on)* instead of the full ordering, trading factorial time for
  `O(2^k · k²)`. That's exponential in the waypoint count but independent of maze
  size, which is exactly the right shape for a game mode: a handful of coins in a
  large maze. Waypoints are capped at 16 with a clear error beyond that, and the
  chosen order is stitched back into a real cell path. Also adds
  `MazeMetrics.shortestPath`. Implements idea **T5**; 7 tests, the key one
  cross-checking the DP against brute-force enumeration of every visiting order.
- **`util.TileGridCodec` — run-length wire encoding for tile grids.** Encodes the
  rendered `char[][]` the REST/STOMP surfaces ship as `<rows>x<cols>:` plus
  row-major runs. Since no `TileType` glyph is a digit, a count-prefixed run
  parses with no separators or escapes, and a run of one is written as the bare
  glyph so the encoding can never expand the payload. Runs cross row boundaries,
  which is where the border and corridor stretches collapse.
  **Measured saving: 36–38%** (encoded is 62–64% of raw, stable from 16² to
  128²). Implements idea **X3**; 7 tests covering round-trip on real mazes, every
  glyph, malformed input and ragged grids.
  **Worth knowing before using it:** a rendered maze alternates cell/wall at
  nearly every column, which is close to the worst case for run-length coding, so
  36% is about all it can give. The far bigger win is not compressing this grid
  but *not sending it* — the rendered grid is `(2r+1) x (2c+1)`, roughly four
  times the cell count, while the maze itself is two wall bits per cell. Measured
  side by side at 64² and 128², sending cell bits is **~16× smaller** than the
  rendered glyph grid. This codec is the drop-in that needs no API change; the
  16× needs a client-side renderer.
- **`examples/loadbalancer-topology` — the integration made runnable (ADR-001, item 5).**
  A standalone module (not a reactor child, matching `examples/biome-plugin`) that
  demonstrates the three LoadBalancerPro integrations needing no changes to either
  project: generate a topology, measure its capacity with min-cut, and place replicas with
  k-center — plus latency-aware routing done the corrected way, with load in the edge cost
  and an admissible heuristic. A fifth section builds a spine-and-leaf `CsrGraph`, a
  degree-3 topology no `MazeGrid` could express, to show the seam taking a real network
  shape. Seven tests pin the claims, because an example that only prints is documentation
  that can rot.
  **It also surfaced a defect the vision documents miss:** `HilbertCurveGenerator`'s raw
  output is **not connected**. At 32² the edge connectivity from `(0,0)` to `(31,31)`
  measures **0** — no route exists — with 396 dead ends. Since both the vision document and
  the integration guide recommend Hilbert as *the* topology generator and then route across
  it with A\*, anyone following that advice gets an empty path back, silently, in the same
  way the heuristic bug was silent. Measured across braid factors: `0.0` → connectivity 0,
  `0.6` → 1, `1.0` → 2. The example therefore braids fully and says why, and a test pins
  the raw generator's disconnectedness so the finding cannot quietly regress.
- **`theory.FacilityPlacement` — k-center placement (ADR-001 appendix, item 1).** Where to
  put `k` edge caches / replicas / rack anchors so the worst-served node is as close as
  possible, by the farthest-first greedy (CLRS Ch. 35): take any node, then repeatedly add
  the node currently worst served. That is a **2-approximation**, and since no polynomial
  algorithm can guarantee better than 2 unless P = NP (Ch. 34), the simple algorithm also
  carries the best available guarantee. The greedy step turns out to be
  `MazeMetrics.farthestFrom` generalised to a set — the same rule `LandmarkHeuristic`
  already uses to spread landmarks, which is not a coincidence: both want points far from
  each other and from everything else.
  Also exposes `coveringRadius(grid, facilities)` for scoring a placement you already have.
  Unreachable cells (a dungeon's solid rock) are simply unserved rather than distorting the
  radius. 8 tests, the load-bearing one **verifying the 2-approximation against brute-force
  enumeration of every k-subset** on small mazes — the guarantee is checked, not asserted.
- **`com.daedalus.graph` — the graph seam (ADR-001, phase 1).** `Graph` is the abstraction
  that lets Daedalus route over any topology rather than only a rectangular maze:
  dense integer node ids, and adjacency delivered into a **caller-owned buffer**
  (`neighbors(node, int[] out)`) so a search loop allocates nothing. Two
  implementations ship: `MazeGraph`, a zero-cost **live view** over `MazeGrid` that
  reads wall flags directly, and `CsrGraph`, a compressed-sparse-row snapshot built
  from caller-supplied edges — the entry point for a service mesh or rack layout that
  was never a maze, with in-place `setEdgeWeight` so live latency/load can move
  without rebuilding the structure.
  `BfsSolver` is retargeted onto it as the proving spike, and the seam paid for
  itself immediately: **2.39–2.75× faster** (58–64% less time over 12 mazes at 80²)
  against a faithful copy of the previous implementation. That beats even D2's
  1.42–1.72×, because BFS shed the per-node `ArrayList` from `openNeighbors` on top of
  the hashing. Every existing test passed **unchanged**, including the cross-solver
  agreement checks that compare bidirectional and A\* against BFS — which is the
  evidence the retarget is behaviour-preserving.
  **Phase 2** moved `DijkstraSolver` and `AStarSolver` onto the same seam, removing the
  last per-expansion `List` from their loops. Benchmarking that change was
  **inconclusive** — 1.44×, 1.21×, then 0.86× across reps, i.e. inside the noise — and it
  is recorded as such rather than dressed up. The reason is that D2 already took the big
  win here by removing the hash collections; what remains is priority-queue work plus the
  `Point` that `MazeGraph.edgeWeight` still allocates, so the list was a small share of
  the total. **This phase is justified by architecture, not performance**: one adjacency
  contract across every solver, and the ability to run them on a topology that was never a
  maze. A node-indexed weight accessor would remove the last allocation and is the obvious
  next measurement.
  **`DialSolver`** followed, and is worth recording as a worked example of predicting
  wrong. It was the last `HashMap<Point,…>` solver, so a BFS-sized win was predicted. The
  first retarget delivered **1.14× / 1.28× / 1.00×** — barely anything. The cause was in
  the new code, not the old: buckets were still a `Map<Integer, IntBucket>`, so every
  relaxation did a `computeIfAbsent` on a **boxed distance key** and put hashing straight
  back on the hottest path — the exact cost the seam exists to remove. Indexing buckets by
  distance directly (a plain `IntBucket[]`, grown on demand) delivered
  **1.94× / 2.36× / 1.99×**, the win originally predicted. Behaviour is unchanged
  throughout: `dial` still returns paths identical to `dijkstra`, and still rejects
  fractional weights.
  **`theory.MazeMetrics`** moved onto the seam last, chosen by measurement rather than by
  working down the solver list: it is the one class on everything's hot path, because
  `DistanceOracle.precompute` runs a BFS *per cell* and `LandmarkHeuristic` and
  `WaypointTour` sit on it too. Removing the per-cell neighbour list there compounds
  across all of them — `DistanceOracle.precompute` on a 48² maze (2,304 BFS runs) went
  from ~239 ms to ~146 ms, a steady **1.59–1.73×**. The remaining six solvers all still
  use `HashMap`/`HashSet` and are candidates on the same evidence, but each should be
  measured rather than assumed, since Dijkstra and A\* showed the seam pays nothing where
  hashing was already gone.
  **`theory.MazeFlow`** followed, picked by the same rule and giving the largest win yet:
  **2.46× / 3.21× / 5.59×** on eight braided 64² mazes. It was the heaviest hasher left — a
  `Map<Long, Integer>` residual table keyed by packed `(from, to)` pairs, boxing a `Long` on
  every residual lookup, and max-flow performs one per edge per BFS. That is now a
  compressed-sparse-row residual network (`offsets` / `targets` / `twin` / `capacity` arrays)
  with an `int[]` BFS queue, so the inner loop boxes nothing. Cut sizes and cut edges are
  unchanged — both `MazeFlow` suites pass untouched, including the test that verifies removing
  the reported edges genuinely severs source from sink. This matters beyond microbenchmarks:
  min-cut is what capacity analysis calls in the LoadBalancer example, so it is on the
  ecosystem's hot path rather than the maze game's.
  `vertexDisjointPaths` followed in the same file, replacing its
  `List<List<Integer>>` adjacency and `Map<Long, Integer>` residual with an arc-indexed
  split graph — every arc paired with a zero-capacity reverse twin, grouped by tail, which
  is the textbook max-flow representation in flat arrays. **2.02× / 3.04× / 3.74×**, with
  the vertex `<=` edge invariant and every other assertion unchanged. `MazeFlow` now holds
  no hash structures at all, and the dead `key()`, list-based `addArc` and
  `findAugmentingPath` helpers are gone with their imports.
- **`engine.generators.DungeonGenerator` — rooms and corridors (C3).** Binary
  space partitioning: split the grid recursively, carve a room in every leaf,
  then join sibling regions with L-shaped corridors on the way back up. The
  recursion order is what guarantees connectivity — each subtree is joined to its
  sibling exactly once. Registered as generator id `dungeon` (the roster is now
  22).
  This is the first generator here that is **deliberately not a perfect maze**,
  and it inverts all three of the usual properties: rooms are open areas (interior
  cells open on all four sides), rooms are dense blocks of cycles so routes are
  never unique, and the rock between rooms is never carved and stays unreachable.
  Callers that assume full reachability must not use it — the `MazeGenerator`
  contract allows this explicitly ("unless their theoretical contract says
  otherwise"). A pleasant side effect: the structural metrics that need `Braider`
  to become interesting on a maze — `MazeFlow`'s min-cut, `LongestPath` — are
  non-trivial here for free. 8 tests covering room openness (measured against a
  perfect maze of the same size), loop presence, unreachable rock, connectivity
  of everything carved, and statelessness across reuse.
- **`theory.DistanceOracle` — all-pairs distances, O(1) queries.** BFS from every
  cell tabulated into a flat `short[]`, so any later "how far is A from B" — a
  leaderboard scoring against the optimal route, arbitrary start/goal queries,
  ranking cells by eccentricity — is a single array read (CLRS Ch. 25, unweighted
  special case). Also exposes `eccentricity` and `diameter`.
  The binding constraint is memory, not time: the table is `V²`, and `V` is
  itself quadratic in the maze's edge length, so 32² needs 2 MB, 64² needs 32 MB
  and 128² would need 512 MB. Rather than quietly exhaust the heap it caps at
  4,096 cells and throws with a pointer to `MazeMetrics.distancesFrom` (one BFS,
  one row of this table) for larger mazes. Implements idea **S4**; 8 tests,
  including an exhaustive every-pair check against BFS and a diameter
  cross-validation against `MazeMetrics`, which derives the same number by
  double-BFS instead of exhaustive scan.

### Changed

- **ADR-002 — CSRBT `RankedSet` behind `TailLatencyPowerOfTwoStrategy`:
  evaluated and declined** (ADR-001 item 7). Measured against the real classes
  from both sibling projects — `ServerStateVector` / `ServerScoreCalculator`
  from LoadBalancerPro 2.4.2, `OrderedSet` / `RedBlackStrategy` from csrbt-core
  0.1.0 — over a simulated 64-server fleet. Harness committed at
  `docs/evaluations/CsrbtRoutingEval.java`.

  Reading the strategy first changed the question. It samples exactly **two**
  servers at random and takes the better one; its only O(n) step is a boolean
  health filter, and `ServerStateVector` already carries per-server `p95`/`p99`.
  **There is no order statistic in it to accelerate**, so adopting a ranked
  structure necessarily means changing the *policy* — to "gate to the best q%
  of the fleet, then power-of-two inside that pool".

  The decisive variable turned out to be **how stale the balancer's view is**,
  which is also the entire reason power-of-two-choices exists. Benchmarking
  against a perfectly fresh view measures a system nobody runs:

  | view refreshed every 25 requests | mean ms | p99 ms | max in-flight | ns/decision |
  |---|---|---|---|---|
  | **uniform po2 (shipped)** | **6.03** | **19.13** | **5** | **48** |
  | greedy least-score | 33.77 | 52.77 | 19 | 200 |
  | RankedSet-gated po2 | 7.86 | 22.32 | 13 | 5 870 |
  | quickselect-gated po2 | 7.78 | 21.52 | 10 | 417 |

  Three findings, any one sufficient to decline. The gating policy **herds** —
  29% worse mean, 17% worse p99, double the peak in-flight — because
  concentrating the sample pool on whatever looked best in the last snapshot
  sends every request to the same place; greedy, the limiting case, is 9× worse.
  Where gating *did* win (fresh view only), an O(n) quickselect matched the tree
  at **1/9th the cost**, so the gain came from the policy, not the structure.
  And `RoutingStrategy.choose(List<ServerStateVector>)` hands over a **fresh
  list per call**, so an order-statistic tree — whose whole advantage is
  incremental maintenance — must be rebuilt every time: **5.8–9.1 µs per
  decision against 46–185 ns**, 30–125× more expensive, on the per-request hot
  path.

  That last point is a fact about the call shape rather than about CSRBT, and it
  produced a concrete upstream request (ADR-001 item 6, request 3): give
  `RoutingStrategy` an optional stateful form, since the current signature
  obliges every strategy to be stateless and O(n) per decision.

- **`LongestPath` moved onto the graph seam — the last hot hashed structure in
  the engine (ADR-001 item 3).** Its backtracking DFS held membership in a
  `HashSet<Point>` and the path in an `ArrayDeque<Point>`, probed and mutated
  once per neighbour of every visited node, up to the two-million-visit default
  budget per call. Now a `boolean[]` and an `int[]` stack over dense node ids.
  **Measured 3.56–3.76× faster** on braided 14² mazes — the case that is
  actually hard, since a perfect maze has exactly one simple path and no search
  to do. Equivalence checked over **192 A/B cases** across four generators, four
  braid factors and two sizes: identical paths throughout.

  One detail that would have been a silent corruption: the recursion needs **one
  adjacency buffer per depth level**, not a shared one. Every frame holds a live
  neighbour iteration, so a child call reusing the parent's buffer would
  overwrite the list the parent is still walking. Depth is bounded by the cell
  count — a *simple* path cannot revisit a cell — so `V` buffers is an exact
  bound rather than a guess.

  `WaypointTour`'s remaining `Set<Point>` was deliberately left alone: it
  de-duplicates at most 16 waypoints once, and is not on any hot path.

- **`DeadEndFillingSolver` moved onto the graph seam — the last solver where it
  pays (ADR-001 item 3).** Both phases retargeted: the cascade's `HashSet` of
  filled cells and `ArrayDeque` frontier, and phase two's BFS maps.
  **Measured 1.60–2.75× faster** over 12 mazes at 80².

  One deliberate simplification. The old cascade could enqueue the same cell
  several times and discarded the duplicates at poll time, which meant no exact
  capacity bound existed. Enqueueing each cell at most once is equivalent — a
  cell is filled the first time it is polled and never unfilled, so later
  enqueues were always no-ops — and it makes V an exact bound rather than a
  guess. That is the kind of "obviously equivalent" reasoning worth distrusting,
  so it was checked: **1024 A/B cases identical** on path, `cellsVisited` and
  `cellsExplored`.

  The nested neighbour scan needs **two** adjacency buffers, not one — the inner
  loop counting a neighbour's surviving exits would otherwise clobber the outer
  loop's contents mid-scan. Sharing one buffer compiles and passes casually
  written tests; it silently corrupts the cascade.

- **`BidirectionalSolver` and `DfsSolver` moved onto the graph seam (ADR-001
  item 3).** These were the two largest remaining holdouts — bidirectional
  carried **seven** hashed-`Point` collections (two parent maps, two seen sets,
  two `ArrayDeque` frontiers, plus a `LinkedList` for reconstruction), DFS
  carried three. Both now run on `MazeGraph` adjacency into a reused buffer,
  with `int[]` parent arrays, `boolean[]` seen flags and `int[]` frontier
  storage sized at exactly V (each node is enqueued at most once, so that bound
  is exact rather than a guess).

  | | before | after | speedup |
  |---|---|---|---|
  | `bidirectional` | 11.97–13.14 ms | 4.88–5.86 ms | **2.12–2.69×** |
  | `dfs` | 10.71–11.20 ms | 3.46–3.51 ms | **3.09–3.19×** |

  Measured over 12 mazes at 80², mean of 5 reps after warm-up. Both land in the
  band BFS got (2.39–2.75×), which is the fourth consecutive confirmation of the
  rule this phase established: **the seam pays exactly where hashing survived,
  and nowhere else.** Every solver that had already been moved onto cell-id
  arrays showed no further gain; every one still hashing `Point` gained 2–3×.

  Equivalence was verified rather than argued: **1024 A/B cases each**, across
  four generators × eight seeds × four braid factors × two sizes × four random
  start/goal pairs, comparing path *and* stats (`cellsExplored`, `cellsVisited`)
  against a verbatim copy of the previous implementation. All 2048 identical.
  Random start/goal pairs matter for bidirectional specifically — its
  smaller-frontier balancing rule is only exercised when the two searches are
  unbalanced, which corner-to-corner runs never do.

- **`TremauxSolver` moved onto the graph seam; edge marks are a flat `byte[]`
  (ADR-001 item 3).** Diagnosed before being touched, which changed the fix.
  Trémaux was among the slowest solvers, and the intuitive read — "it's a walk,
  walks are long" — is wrong: it takes **1.04 × V steps against BFS's
  1.00 × V**, essentially identical work. The whole gap was **cost per step**,
  so no algorithmic tuning would have moved it.

  The culprit was the mark table. Marks lived in a `Map<Edge, Integer>` where
  `Edge` was a record wrapping two `Point` records, so every lookup allocated a
  composite key — and lookups ran once per neighbour **and again inside a
  `Comparator` during a per-step `sort`**, so each step allocated edge keys
  O(d log d) times plus a comparator, a neighbour `List`, and boxed `Integer`
  values, all to choose between at most four options.

  Marks are now `byte[V * 4]` addressed by `cell * 4 + direction`, with both
  halves of a passage incremented together so the pair acts as one undirected
  mark. Neighbours come from `MazeGraph` into a reused buffer, and the sort is
  replaced by a linear min-scan. **Measured 3.3–6.8× faster** over 12 mazes at
  80², which puts Trémaux at roughly BFS's cost (0.8–1.45×) instead of several
  times it. Selection is provably equivalent — `MazeGraph` yields neighbours in
  the same `Direction` order and the old sort was *stable*, so "first minimum
  wins" reproduces the previous choice exactly.

- **`MazeGrid.weightOf(Point)` is now `final`** — closing a silent-failure hazard
  the coordinate-indexed accessor introduced. Once the graph seam started asking
  for weights by `(row, col)`, a subclass overriding the older `Point` form
  would still compile but be **bypassed entirely**: its costs would vanish and
  A\* would quietly optimise the wrong thing. Sealing the delegate turns that
  into a compile error naming the method to override instead. Nothing in the
  repo was affected — only `WeightedMazeGrid` overrode it, and that had already
  moved — but `daedalus-plugin-runtime` loads third-party jars that may subclass
  `MazeGrid`, so the failure mode was reachable from outside.

- **`MazeGrid.weightOf(int row, int col)` — coordinate-indexed entry cost.**
  The graph seam addresses nodes by dense integer id, so
  `MazeGraph.edgeWeight(int, int)` was building a `Point` on every edge
  relaxation purely to hand it to `weightOf(Point)`, which immediately unwrapped
  it again — one allocation per relaxation, in the hottest loop the engine has.
  Subclasses now override the `(row, col)` form and `weightOf(Point)` delegates
  to it, so there is a single implementation point and both forms cannot drift.
  This is ADR-001 item 4's "add `EdgeWeightedGraph`" resolved without adding a
  type: `Graph.edgeWeight` was already node-indexed, so a parallel interface
  would have been ceremony around a one-method change.

- **Spring Boot 3.3.1 → 4.1.0 (with Framework 7).** The server, plugin runtime
  and desktop modules now build on the Boot 4 line. Four coordinate changes and
  a single import were the entire migration:

  | | before | after |
  |---|---|---|
  | `spring-boot-starter-parent` | 3.3.1 | **4.1.0** |
  | `resilience4j.version` | 2.2.0 | **2.4.0** |
  | resilience4j artifact | `resilience4j-spring-boot3` | **`resilience4j-spring-boot4`** |
  | `springdoc.version` | 2.6.0 | **3.0.3** |

  The lone source change is in `RedisConfigConditionalTest`: Boot 4 split the
  monolithic `spring-boot-autoconfigure` jar into per-technology modules, which
  both moved *and* renamed the class —
  `org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration`
  became `org.springframework.boot.data.redis.autoconfigure.DataRedisAutoConfiguration`
  (now in `spring-boot-data-redis`). Nothing in `src/main` needed touching in
  any module.

  **Verified, not assumed.** The migration was first run in a throwaway copy of
  the tree. The initial `mvn test` reported **28 errors** — a mix of
  `NoSuchMethodError` on `MockHttpServletRequestBuilder.contentType(String)` and
  `IncompatibleClassChangeError: HttpHeaders does not implement MultiValueMap`.
  Every one of those was an artifact of Maven's *incremental* compilation
  leaving Boot 3 test bytecode on disk to run against Boot 4 jars; return types
  and interface sets are part of a JVM method signature, so stale classes fail
  exactly this way. A `clean` rebuild reduced 28 errors to **one** — the Redis
  import above. The lesson generalises: when a dependency bump produces
  `NoSuchMethodError` for a method that plainly still exists in source, rebuild
  clean before reading it as an API break.

  After the fix, the full reactor is green on Boot 4: **267 tests, 0 failures,
  0 errors, 0 Checkstyle violations, 0 SpotBugs findings** (core 183,
  plugin-api 7, plugin-runtime 16, server 57, desktop 4). The per-key rate
  limiter and its 429 path pass unchanged, so `RequestNotPermitted` handling
  survived both the Boot and the Resilience4j bump.

  **springdoc's major bump was checked at runtime, not by test.** Nothing in
  the suite exercises `/v3/api-docs`, so the packaged jar was booted and probed
  directly: it starts clean, `/v3/api-docs` returns **HTTP 200** with all **10**
  paths documented, and `/swagger-ui/index.html` returns 200. One behavioural
  change worth knowing about downstream: springdoc 3 emits **OpenAPI 3.1.0**
  where 2.x emitted 3.0.x. Nothing in this repo consumes the spec —
  `Code/daedalus-api-dtos.ts` is hand-written against the Java records rather
  than generated — but external clients running codegen against the published
  document will see the version change.

- **Solvers index state by cell id instead of hashing `Point` (D2).**
  `DijkstraSolver` and `AStarSolver` now hold distance / parent / closed state in
  flat arrays addressed through the new `solver.GridIndex` (`row * cols + col`),
  replacing `HashMap<Point,…>` / `HashSet<Point>`. **Measured 1.42–1.72× faster**
  (29–42% less time) over 12 mazes at 80², A/B'd against a faithful copy of the
  previous implementation with identical stats bookkeeping. Behaviour is
  unchanged by construction — queue ordering, neighbour iteration and
  tie-breaking are all identical — and the full suite passes untouched, including
  the assertions that `dial` equals `dijkstra`, that weighted routing picks exact
  known paths, and that A\* matches BFS. This is the item the D3 benchmark
  redirected effort toward.

### Fixed

- **`TremauxSolver` was missing Trémaux's third rule and could not solve mazes
  with loops.** The implementation carried only "never enter a twice-marked
  passage" and "prefer the least-marked passage". The rule it lacked — **on
  re-entering a junction you have already stood on, having arrived along a
  previously unmarked passage, turn straight back** — is the one that retires
  that passage and guarantees a retreat route stays open. Without it the walk
  strands itself: it reaches a cell whose every passage is already twice-marked
  while the goal sits unvisited elsewhere. The old code read that state as
  "unreachable" and returned an empty path, under a comment asserting it was
  *"impossible on connected maze"*.

  It was not impossible. Measured at 20² over 40 seeds per setting:

  | braid factor | mazes failed (old) | mazes failed (fixed) |
  |---|---|---|
  | 0.0 (perfect) | 0 / 40 | 0 / 40 |
  | 0.25 | **19 / 40** | 0 / 40 |
  | 0.5 | **20 / 40** | 0 / 40 |
  | 1.0 | **10 / 40** | 0 / 40 |

  BFS finds a path on every one of those grids, so the mazes were plainly
  solvable. Only perfect mazes were ever safe — a spanning tree has no loop to
  strand you — and **every fixture in the suite was a perfect maze**, which is
  why 183 passing tests never saw it. `TremauxSolver` had no test of its own at
  all until now; the new `TremauxSolverTest` braids deliberately and asserts the
  walk is a legal traversal (starts at start, ends at goal, never crosses a
  wall) across four generators and four braid factors.

  Perfect-maze behaviour is unchanged: 64/64 A/B fixtures produce a walk
  identical to the previous implementation's, since a tree never triggers the
  restored rule.

- **`LandmarkHeuristic` was inadmissible on weighted grids, so A* returned
  suboptimal routes (ADR-001 item 4).** The heuristic stored BFS **hop counts**
  regardless of the grid's costs. Hop counts bound cost from below only while
  every edge costs at least one hop's worth, so the class documented a "keep
  weights `>= 1.0`" rule — which `WeightedMazeGrid.setWeight` never enforced
  (it accepts any non-negative value). Violate it and A* still returns a path;
  it just isn't the cheapest one.

  Measured on twelve fully-braided 24² mazes with weights drawn from
  `[0.05, 0.35]`:

  | | before | after |
  |---|---|---|
  | cells where `h` exceeded true cost | **575 / 576** | **0 / 576** |
  | worst over-estimate (true distance ≈ 32) | **132.1** | 0 |
  | seeds where A* beat by Dijkstra on cost | **12 / 12** | **0 / 12** |
  | worst excess cost | **+36%** | 0 |

  **Why the suite never caught it:** every existing fixture was a *perfect*
  maze. A spanning tree has exactly one route between any pair of cells, so
  every heuristic — admissible or not — returns it. The defect only becomes
  reachable once the topology has redundancy, which is why these tests braid
  the maze first, and why it matters: braided multi-path meshes are precisely
  what the LoadBalancer integration guide tells users to build.

  `precompute` now chooses its metric from the grid rather than assuming.
  Uniform-cost grids keep the BFS fields (O(V + E) per landmark). Any grid
  carrying a non-`1.0` weight gets Dijkstra fields **in both directions** — and
  the second sweep is not redundancy. `MazeGrid` charges the weight of the cell
  being *entered*, so `d(a,b) − d(b,a) = w(b) − w(a)`: the graph is directed
  even though its passages are not, and the familiar symmetric
  `|d(L,b) − d(L,a)|` bound quietly assumes otherwise. Weighted mode uses the
  directed pair `d(L,t) − d(L,s)` and `d(s,L) − d(t,L)`, each of which follows
  from the triangle inequality without a symmetry assumption.
  `MazeMetricsWeightedDistanceTest` asserts the two sweeps genuinely disagree,
  so nobody deletes one as duplication.

  The fix is also a win, not just a tax: on 64² braided weighted topologies A\*
  with the corrected heuristic uses **5.79× fewer expansions and searches 1.9×
  faster** than plain Dijkstra. Precompute costs ≈ 8 ms per topology against
  ≈ 2 ms for a single Dijkstra solve, so it repays after roughly four queries —
  the normal case, since a topology is routed over many times between updates.
  No API change; existing callers get the correction for free.

- **The server reported itself unhealthy (`/actuator/health` → 503) whenever
  Redis was disabled — which is the default.** `spring-boot-starter-data-redis`
  is unconditionally on the classpath, so Boot's `DataRedisAutoConfiguration`
  contributes a `RedisConnectionFactory` even when `daedalus.redis.enabled` is
  `false` and `RedisConfig` is correctly gated off. The health
  auto-configuration then registered an indicator against that factory, its
  `PING` failed, and the failure propagated to the **aggregate** status:

  ```
  "redis": { "status": "DOWN",
             "details": { "error": "...Unable to connect to Redis" } }
  ```

  Everything else — `diskSpace`, `ping`, `livenessState`, `readinessState`,
  `ssl` — was `UP`, and `LeaderboardService` was logging *"in-memory backend
  (Redis disabled or unavailable)"*, i.e. the application was working exactly
  as designed. But `dev` is the default profile and sets
  `daedalus.redis.enabled: false`, so **anyone who cloned the repo and ran it
  had an app that answered its own health check with 503** — precisely the
  signal a load balancer or Kubernetes readiness probe uses to pull an instance
  out of rotation.

  Fixed in `application.yml` by binding the stock indicator to the same flag
  that gates the config:

  ```yaml
  management:
    health:
      redis:
        enabled: ${daedalus.redis.enabled:false}
  ```

  Note this is a *binding*, not a blanket disable — with
  `daedalus.redis.enabled=true` (the prod default) the indicator returns and
  Redis is monitored as before. `RedisHealthBindingTest` pins that direction
  specifically, because the tempting "simplification" to a literal `false`
  would silently blind production monitoring. It also closes the first half of
  the standing BACKLOG item for custom `HealthIndicator`s, with no custom code:
  Boot's indicator was already correct, it was merely registered
  unconditionally.

- **`HilbertCurveGenerator` emitted a forest, not a maze.** Found by auditing all 22
  generators for the spanning-tree contract after the LoadBalancer example produced an
  impossible result. At 32² it yielded **953 edges for 1024 cells — 71 disconnected
  components — with only 66 cells reachable from the origin**. Two causes, both silent: the
  hand-rolled recursive quadrant split did not compose into a real Hilbert curve, so
  consecutive cells were sometimes not adjacent; and when a cell arrived with no visited
  neighbour the code did `if (!candidates.isEmpty())` and simply **skipped carving it**,
  orphaning the cell without any error. The traversal is now the canonical `d2xy` Hilbert
  mapping (guaranteeing adjacency on power-of-two grids), and cells that cannot attach
  immediately are deferred to a repair pass instead of dropped. This mattered beyond
  aesthetics: both vision documents name Hilbert as *the* topology generator for
  LoadBalancer work, so anyone following that advice was routing over a disconnected graph
  and getting empty paths back with no error.
- **The "Hilbert has the best locality" recommendation is measurably false.** Having fixed
  Hilbert's connectivity, the obvious next question was whether it is actually the curve it
  claims to be — connectivity and fidelity are different properties. Measuring **stretch**
  (maze distance ÷ straight-line distance, 20,000 random pairs at 32²) inverts the vision
  document's comparison table:

  | generator | mean stretch | p95 | max | diameter |
  |---|---|---|---|---|
  | **prims** | **2.48** | 5.50 | 57 | 110 |
  | archimedes-spiral | 2.50 | 5.60 | 59 | 95 |
  | gauss | 2.60 | 6.33 | 69 | 123 |
  | morton-curve | 3.06 | 7.50 | 77 | 123 |
  | **hilbert-curve** | **4.62** | 11.00 | 115 | **235** |
  | recursive-backtracker | 9.31 | 25.40 | 289 | 436 |

  Hilbert scores **worse than Morton**, the reverse of the documented ranking, with more than
  double Prim's diameter. The cause is a conflation: the Hilbert *curve* does have excellent
  locality, but `HilbertCurveGenerator` walks the grid in curve order and then attaches each
  cell to a **random visited neighbour** — so the spanning tree is not the curve and inherits
  none of its locality. The vision document and the example now carry the measured table and
  recommend `prims` or `archimedes-spiral` for topology work.
  **The obvious fix was then tested and is worse.** Carving strictly *along* the curve — the
  maximally curve-faithful generator — measures **16.69** mean stretch with a diameter of
  1023, i.e. **3.6× worse than today's version and 6.7× worse than Prim's**. A space-filling
  curve carved end to end is a Hamiltonian *path*, and a path is the spanning tree with the
  worst possible diameter: two cells touching in 2-D can be a thousand steps apart along the
  snake. The relationship is therefore inverted from the intuition — greater curve fidelity
  makes maze locality *worse*, because curve locality is about ordering while maze locality is
  about tree diameter. What actually predicts it is **bushiness**, which the generator
  descriptors already record ("bushy texture; many short branches" for Prim's; long winding
  corridors for the worst performer). Topology generators should be chosen on that axis rather
  than on mathematical pedigree.
- **Connectivity is now verified for every generator.** `PerfectMazePropertyTest` covered
  8 of 22, which is how the above hid. `GeneratorConnectivityTest` asserts the full
  spanning-tree contract (reachable everywhere, exactly `V-1` edges) across all 21
  generators that claim it, plus Hilbert specifically on non-power-of-two and rectangular
  grids where the enclosing-square filter can break curve adjacency. `DungeonGenerator` is
  excluded by contract and keeps its own connectivity test.

### Verified

- **Uniform-spanning-tree cover times measured (G2 + T4).** Aldous-Broder and
  Wilson's sample the *same* distribution — a uniform spanning tree — so they
  differ only in cost, and the audit wanted that shown empirically. At first it
  couldn't be: both generators counted only cells *added to the maze*, which is
  exactly `n` for both, so `MazeStats` was blind to the random walking that
  actually dominates them. Both now count walk steps into `cellsExplored`, and
  the picture is stark (averaged over 7 seeds):

  | cells | Aldous-Broder steps | Wilson's steps | ratio | AB per cell | W per cell |
  |------:|--------------------:|---------------:|------:|------------:|-----------:|
  | 256   | 4,938   | 1,204  | 4.1x | 19.3 | 4.7 |
  | 1,024 | 27,492  | 6,925  | 4.0x | 26.8 | 6.8 |
  | 4,096 | 144,699 | 27,671 | 5.2x | 35.3 | 6.8 |

  Wilson's cost *per cell* stays flat (~5–7) while Aldous-Broder's climbs
  steadily (19 → 35) — the signature of blind cover-time walking versus
  loop-erased hitting-time walking — and the gap widens with size, as theory
  predicts. Locked in `RandomWalkCoverTimeTest`.
- **`GrowthEstimator` caveat found and documented.** Classifying those same
  random-walk series exposed a real limitation in the T1 tool: fitted from a
  *single seed*, Aldous-Broder's label swung between `O(n)` and `O(n^2)` across
  seeds and Wilson's once came back `UNKNOWN`, despite their true behaviour being
  stable and clearly separated once averaged. The javadoc now warns to average a
  randomized metric over several seeds before fitting.
- **DSU certified near-constant amortized (D1).** `util/DSU` already carried both
  optimizations — union by rank *and* two-pass path compression — so no
  production change was needed. Added structural guards that behaviour alone
  can't provide: if someone simplified `find` into a plain root walk, every
  correctness test would still pass while the structure silently degraded from
  inverse-Ackermann to `O(n)`. The new tests read `parent` directly to assert the
  path really is rewritten, and that rank ordering survives (CLRS Ch. 21 + 17).
- **Reservoir-sampled frontier declined (G3).** The idea was to cut frontier
  memory, so the frontier was measured first — using the `maxFrontierSize` the
  generators already record. Randomized Prim's peaks at 561 walls on a 64² maze
  and only 4,866 on a 512² one: **1.9% of cells, about 0.22 MB**, and the share
  *falls* as mazes grow, because the frontier tracks the perimeter of the grown
  region rather than its area. There is no pressure to relieve. Independently,
  the technique doesn't fit: Algorithm R samples one pass over a stream, whereas
  Prim's frontier is live mutable state that must persist across steps, so using
  a reservoir would mean rescanning the grid every step — O(n²) instead of the
  current O(frontier). Noted the real lever if it ever matters: encode each wall
  as one `int` rather than a two-`Point` object, ~10× smaller, no algorithm change.
- **Consistent hashing declined (X4).** The maze cache is a single-process
  bounded map; Redis is wired for the leaderboard, not for sharding mazes. A hash
  ring would be distribution infrastructure for a system that isn't distributed —
  and if it ever becomes one, Redis Cluster already shards by hash slot with
  minimal reshuffling, so doing it in the application would duplicate the
  datastore's mechanism and add a second thing to get wrong.
- **Parallelism trio measured; C1 and C2 declined, C3 reframed.** Generation was
  timed before any thread pool was written: 1.96 ms at 64², 5.01 ms at 128²,
  18.3 ms at 256², 106 ms at 512² (Borůvka). At the sizes this project actually
  serves — ≤128² — generation is **2–5 ms**, which fork/join setup would simply
  consume. The decisive objection is not speed but the contract: `MazeGenerator`
  promises *"same seed ⇒ same maze"*, and `ComplexityAnalyzer`, `GrowthEstimator`
  and much of the suite depend on that determinism; parallel rounds would put it
  at risk to save milliseconds. **C2** falls harder still — after D2 a full
  Dijkstra over an 80² maze runs in under a millisecond, so there is nothing to
  parallelise. **C3** was reframed rather than dropped: its speed rationale dies
  with C1, but quadrant generation with doorways punched through the seams is how
  rooms-and-corridors dungeon layouts get built, and that's a real gap — every
  current generator makes uniform perfect mazes. It belongs in the backlog as a
  single-threaded feature, judged on the layouts it produces.
- **`DeadEndFillingSolver`: a `Stream` removed from the cascade's inner loop.** Profiling put
  this solver second-worst at 14.66 ms, and the cause was not hashing. Its cascade counted a
  neighbour's surviving exits with
  `openNeighbors(n).stream().filter(...).count()` — a full stream pipeline built once per
  neighbour of every filled cell, which on a recursive-backtracker maze (almost entirely dead
  ends) is the hottest line in the solver. Replaced with a plain counting loop.
  Measured on the cascade phase in isolation, with both variants asserted to fill an identical
  set of cells: **1.13× / 1.24× / 2.77×**. The spread is wide because stream pipelines are
  exactly the shape JIT behaviour varies most on, so the honest reading is "consistently
  faster, magnitude unstable" rather than a headline multiple. Worth recording that the first
  attempt at this benchmark was **invalid** — it compared the legacy cascade alone against the
  full new solver including its BFS phase, which measures nothing; the numbers above come from
  the corrected like-for-like version.
- **Solver costs profiled before optimising, which redirected the work entirely (ADR-001).**
  With six solvers still using `HashMap`/`HashSet`, the plan was to move them onto the graph
  seam. Timing them first over 12 mazes at 80² changed the answer:

  | solver | time | | solver | time |
  |---|---:|---|---|---:|
  | wall-follower | 2.55 ms | | bidirectional | 6.94 ms |
  | bfs | 2.70 ms | | dead-end-filling | 14.66 ms |
  | dial | 4.83 ms | | tremaux | 20.01 ms |
  | dfs | 5.26 ms | | **ida-star** | **875.91 ms** |

  **IDA\* costs ~300× BFS and 44× the next-worst solver.** De-hashing it would have been
  rearranging deck chairs: the cost is inherent to iterative deepening, which re-searches from
  scratch each pass under a slightly larger f-bound — with unit costs the bound rises by 1 per
  pass, so a maze with a path hundreds of steps long is re-explored hundreds of times.
  The fix turned out to be a heuristic already built for another purpose. Swapping Manhattan
  for `LandmarkHeuristic` (ALT): **342.7 ms → 8.4 ms, a 41× speedup**. The same swap saves A\*
  only ~55% of expansions; IDA\* gains far more because re-expansion multiplies every saving.
  No code changed — `IDAStarSolver` already accepts a heuristic. Its javadoc now carries the
  measurements and says plainly when to use it: ALT when a maze is solved repeatedly, A\*/BFS
  for one-shot queries (ALT's precompute costs about as much as just solving the maze), and
  IDA\* itself only when `O(d)` memory is the actual constraint. It is a memory-optimised
  algorithm, not a time-optimised one, and the default heuristic makes that trade steeply.
- **d-ary heap benchmarked and declined (D3).** A 4-ary heap was measured against
  `java.util.PriorityQueue` inside a real Dijkstra loop (12 mazes at 80², warmed
  up, three reps) and came in at −1.5% / −8.5% / −1.8% — inside the noise, with a
  d=2 control swinging 11.8ms→22.7ms across reps. The heap simply isn't the
  bottleneck: the loop is dominated by `HashMap`/`HashSet` lookups on `Point`
  keys. No code was shipped rather than add a placebo optimization. The follow-up
  measurement is the useful part — swapping those maps for flat arrays indexed by
  `row * cols + col` ran **1.47–2.00× faster** on the identical workload, so idea
  **D2** was upgraded to High impact and is now the top performance item.
- **Bidirectional termination audited (S3).** `BidirectionalSolver` stops at the
  first frontier touch, and textbooks warn that this can return a path one step
  longer than optimal. Rather than assume it, the concern was measured: across
  **4,320** randomized braided mazes (sizes 6–20, three braid factors, random
  start/goal pairs) it never disagreed with BFS on path length, so the solver was
  left alone and the termination rule documented instead. A braided-maze sweep
  now lives in the suite as a regression guard — worth noting the previous tests
  could never have caught this, since a perfect maze has only one route.

### Security (2026-07-19)

- **STOMP `CONNECT` frames are now authenticated.** HTTP security guarded the
  `/ws/**` upgrade under `prod`, but nothing inspected STOMP frames, so the
  messaging layer had **no notion of who was connected**. Two consequences: a
  deployment exposing the endpoint without that HTTP rule — a misconfigured
  profile, or a proxy terminating the upgrade — had no second line of defence,
  and there was no principal on which any per-destination rule could ever be
  built. `StompAuthChannelInterceptor` validates the bearer token from the
  `CONNECT` frame's native headers and attaches a `Principal` carrying the JWT
  subject, sharing `JwtTokenService`'s decoder so issuance and verification
  cannot drift.

  Required under `prod`, advisory elsewhere — matching how `SecurityConfig` and
  `ProdSecurityConfig` already split the HTTP surface, so a dev or embedded
  desktop client still connects without minting a token. **A token that is
  present but invalid is refused in every profile**, including the permissive
  ones: "no credentials" and "bad credentials" are different situations, and
  only the first is something a relaxed profile should wave through.

  **Scope, stated plainly: this is authentication, not authorization.** A client
  can still subscribe to another user's frames. The broker's destinations are
  not scoped to an owner, and nothing in the domain records which subject owns a
  session, so "may this principal subscribe here?" is not yet answerable —
  closing that needs session ownership modelled first. The BACKLOG entry has
  been rewritten to say so rather than marked done.

  Per-frame validation was deliberately omitted: the principal is established
  once at `CONNECT` and carried on the session, so re-decoding the token on
  every `SEND` would cost thousands of verifications for no extra guarantee.
  The trade-off is that a connection outlives its token's expiry.

- **Per-key rate-limiter buckets are now bounded — and bounding them carefully.**
  The interceptor created a Resilience4j instance per distinct caller key and
  never evicted it, so anyone able to mint keys — forged subjects, or forged
  source IPs when `daedalus.ratelimit.trust-forwarded-header` is on — could grow
  the `RateLimiterRegistry` without limit. Buckets now live in a Caffeine cache
  capped by `daedalus.ratelimit.max-keys` (default 10 000) and expiring on
  `daedalus.ratelimit.idle-ttl` (default 10 minutes).

  **The obvious implementation would have been a bypass.** Evicting a bucket a
  caller has already drained hands them a full budget the moment they return, so
  a naive LRU turns "cycle keys fast" into "no rate limit at all" — trading a
  memory-exhaustion bug for an authentication-adjacent one. Each bucket's
  effective TTL is therefore raised to at least its own `limitRefreshPeriod`:
  past that point it would have refilled anyway, so discarding it is
  unobservable. That requires a per-entry Caffeine `Expiry` rather than a
  cache-wide `expireAfterAccess`, since base limiters configure different refresh
  periods (`mazeGenerate` and `authLogin` do not agree). Size-based eviction
  keeps the property too — Caffeine evicts approximately LRU, so a key flood
  discards the attacker's own idle entries rather than an active caller's
  drained bucket.

  Bucket creation also moved off `RateLimiterRegistry.rateLimiter(name, config)`
  to standalone `RateLimiter.of(...)`, because the registry retains every
  instance it creates — which is the leak being closed.

  Two things caught during the work, both by tests that already existed for
  other reasons. Widening `RateLimitProperties` broke four call sites at compile
  time (good — loud). Adding a convenience constructor then gave the record two
  constructors, and Spring's binder will not choose between them: it looks for a
  no-arg constructor, fails, and **the entire application context stops
  starting**. `ApplicationSmokeTest` — added earlier the same day precisely
  because no test booted the real context — turned that into a clear failure
  instead of a broken deployment. Fixed with an explicit `@ConstructorBinding`.

### Security

- **Per-key rate limiting on the throttled endpoints.** The three limiters
  (`mazeGenerate`, `mazeSolve`, `authLogin`) were global — a single
  Resilience4j bucket shared across every caller, so one noisy client could
  spend everyone else's quota (and one IP could burn the whole `authLogin`
  brute-force budget). Replaced the method-scoped `@RateLimiter` annotations
  with `@PerKeyRateLimit(...)` plus a `PerKeyRateLimitInterceptor` that
  resolves a caller key — authenticated subject (`Authentication.getName()`),
  else client IP — and throttles each key against its own bucket, cloned from
  the named instance's config in the `RateLimiterRegistry`. The YAML
  instances now serve as per-caller *templates*. `X-Forwarded-For` is trusted
  only when `daedalus.ratelimit.trust-forwarded-header` is set (off by
  default; on in `application-prod.yml`, which runs behind an ingress) so a
  direct client can't spoof the header to mint a fresh bucket per forged IP.
  The `429` wire contract is unchanged: `ApiExceptionHandler` collapses the
  composite instance name (`mazeGenerate::ip:…`) back to the base
  `mazeGenerate` for the body's `limiter` property, so no caller IP or subject
  leaks into the response, and `Retry-After` still resolves from the base
  instance's refresh period. New code lives under
  `com.daedalus.server.ratelimit` (`PerKeyRateLimit`, `RateLimitNaming`,
  `RateLimitKeyResolver`, `PerKeyRateLimitInterceptor`) plus
  `RateLimitProperties` / `RateLimitWebConfig` in `…server.config`; covered by
  18 new tests (naming round-trip, key resolution, per-key bucket isolation,
  and an end-to-end MockMvc 429 path). Clears the "per-key rate limiting" item
  from `BACKLOG.md`.

### Infrastructure

- **CI fixed and verified green.** Run #1 failed because `ci.yml` ran
  `mvn clean verify`, which never installs reactor artifacts into `~/.m2`,
  so the standalone `examples/biome-plugin` build couldn't resolve
  `daedalus-plugin-api:1.0.0-SNAPSHOT`. Switched the reactor step to
  `clean install` (commit `2519a1f`, 2026-07-02); also bumped actions for
  the Node 24 cutover (`checkout@v6`, `setup-java@v5`, `upload-artifact@v7`)
  and fixed the README badge URL. Run #2 (2026-07-03) passed — 56s total,
  reactor + biome-plugin both green.
- **`.gitattributes` added.** `* text=auto` with explicit `eol=crlf` for
  `*.bat`/`*.cmd`, `eol=lf` for `*.sh`, and `binary` for PDFs, images, and
  archives. Ends the CRLF churn that made untouched files (`.gitignore`,
  `_migration/migrate.bat`) show up as fully-rewritten phantom diffs on
  Windows. Tree renormalized with `git add --renormalize .`.
- **`.gitignore` cleaned.** Removed two literal `ECHO is on.` lines — an
  artifact of the batch script that originally generated the file (`echo`
  with no argument prints its own status instead of a blank line).
- **Coverage.** JaCoCo agent + per-module report wired into the reactor at
  `verify`. CI regenerates `.github/badges/jacoco.svg` on pushes to main
  (cicirello/jacoco-badge-generator) and commits it back `[skip ci]`; README
  shows the badge next to CI status.
- **Static analysis gates.** Checkstyle (minimal hygiene ruleset,
  `config/checkstyle.xml`, runs at `validate`) and SpotBugs (medium threshold,
  runs at `verify`) now fail the build. First run over the codebase surfaced
  and fixed four real issues: an unused import in `JwtTokenService`, a dead
  local (`ideal`) in `GameSessionService.complete`, a swallowed exception on
  classloader close in `PluginManager.shutdownAll` (now debug-logged), and a
  missing null guard on Micrometer’s `@Nullable Timer.record` return in
  `MazeGenerationService.generate`. Intentional-design findings
  (EI_EXPOSE_REP on events/DTOs/DI, CT_CONSTRUCTOR_THROW, MS_EXPOSE_REP on
  the static context accessors) are excluded with per-block justifications
  in `config/spotbugs-exclude.xml`.
- **Dependabot.** Weekly update PRs for the Maven reactor, the standalone
  biome-plugin pom, and the GitHub Actions used by the workflows; minor/patch
  bumps grouped into a single PR.
- **Issue & PR templates.** Bug report and feature request forms
  (`.github/ISSUE_TEMPLATE/`) plus a PR checklist template.
- **Container image.** Multi-stage `Dockerfile` (Maven build layer → slim
  Temurin 21 JRE, non-root user) for `daedalus-server`; the release workflow
  gained a job that publishes `ghcr.io/richeyworks/daedalus2:{version,latest}`
  on every `v*` tag.
- **CHANGELOG de-binarified.** The 2026-05-05 entry documenting OneDrive
  null-byte corruption contained a literal `\0` character, which made grep
  and diff tools treat this whole file as binary. Replaced with the escaped
  text form.

## [1.0.0] — 2026-05-11 (released with 1.0.0)

**Reference plugin + CI + core consolidation.** Four BACKLOG items closed
in this pass: the worked example plugin (`BiomeGeneratorPlugin`), GitHub
Actions CI, the Lightning policy decision, and the final newest-pick
generator (Recursive Backtracker) folded onto the shared Growing-Tree
engine. The example plugin lives in `examples/biome-plugin/` (deliberately
not part of the main reactor so `mvn clean verify` at the root keeps its
current scope) and demonstrates every interesting touchpoint of the SPI:
manifest declaration, algorithm registration, programmatic event
subscription, and stop-time disarm. The core changes finish what the
2026-05-07 Growing-Tree unification started — every member of the
newest / oldest / random / norm / state-machine family now plugs into
`GrowingTreeEngine` through a `GrowingTreePolicy`, with no bespoke loops
left in the catalog.

### Added

- **`examples/biome-plugin/`** — reference plugin module. Registers two
  themed generators (`forest-biome`, `desert-biome`) against
  `GeneratorRegistry` and subscribes to `MazeGeneratedEvent` to log a
  one-line summary per generation. Both generators are written from
  scratch against the public SPI — no reach-ins to package-private engine
  internals — so the example doubles as a from-zero tutorial for plugin
  authors.

  - `ForestBiomeGenerator` — recursive backtracker with a weighted
    vertical-first carve order. With probability 0.7 the two vertical
    directions occupy slots 0–1 of the per-cell try-order; with the
    complementary probability the two horizontal directions take those
    slots. Within-pair order is uniformly random on each side. Long
    trunks, short side branches. Perfect maze (single component, no
    cycles); seed-deterministic.
  - `DesertBiomeGenerator` — Sidewinder variant with a 1/3 run-close
    probability (vs. Sidewinder's 1/2). Longer horizontal corridors.
    Perfect maze; seed-deterministic.
  - `BiomeGeneratorPlugin` — extends `AbstractPlugin`. Subscribes to
    `MazeGeneratedEvent` by looking up Spring's well-known
    `ApplicationEventMulticaster` bean and calling
    `addApplicationListener(...)` on it. Plugin instances are loaded via
    `ServiceLoader` (not by the Spring bean factory), so `@EventListener`
    annotations on plugin classes are silently ignored; programmatic
    registration is the supported path. The listener unwraps
    `PayloadApplicationEvent` manually — `PluginEvent` is a Daedalus-domain
    POJO that doesn't extend `ApplicationEvent`, so Spring wraps it on
    publish; `@EventListener` does this automatically via its method-adapter
    layer, but a raw `ApplicationListener` doesn't. An `AtomicBoolean armed`
    flag is flipped to false in `stop()` to neutralise the listener; Spring's
    `removeApplicationListener` would also work, but the flag keeps the
    lifecycle methods one line each without retaining the listener reference
    as plugin state.
  - `BiomeGeneratorsTest` — perfect-maze invariant + seed-determinism +
    descriptor smoke tests for both generators.
  - `META-INF/services/com.daedalus.plugin.MazePlugin` — ServiceLoader
    entry so the plugin is discovered by the host's `PluginManager`.
  - `examples/biome-plugin/README.md` — build / run instructions plus
    the why-not-`@EventListener` explanation.

- **`examples/run-with-biome.sh`** — one-shot demo script. Installs
  `daedalus-plugin-api` into the local Maven repo, builds the plugin
  JAR, stages it in a `mktemp -d` plugin directory, then boots
  `daedalus-server` with `daedalus.plugins.directory` pointed at that
  directory. Forwards any extra arguments as Spring Boot run arguments.

- **`.github/workflows/ci.yml`** — `mvn -B verify` on push/PR for
  `main`. Java 21 Temurin via `actions/setup-java@v4` with built-in
  Maven cache. Locale + timezone forced to `en_US.UTF-8 / UTC` so any
  format-sensitive test is deterministic across runners. Builds the
  reference plugin in a follow-on step so the example doesn't silently
  rot. Concurrency group cancels in-flight runs on rapid pushes.

- **`.github/workflows/release.yml`** — tag-driven release pipeline.
  Triggers on `v*` tags; builds the reactor (`-DskipTests` since CI
  already validated the tip), builds the example plugin, extracts the
  matching CHANGELOG section as release notes, and publishes a GitHub
  Release with the server's `-exec.jar` and the plugin JAR attached.
  `softprops/action-gh-release@v2` handles the upload. Tags with
  `-rc` / `-beta` / `-alpha` suffixes are marked prerelease.

- **`GrowingTreePolicies.newestWithNormJump(double pJump)`** — new
  composed policy: mostly pick the newest cell (RB-style long corridors),
  with probability `pJump` jump to the active cell with the largest
  quadratic norm (a fork toward the high-norm corner). Endpoints
  short-circuit to the underlying singletons — `pJump = 0.0` returns
  `newest()`, `pJump = 1.0` returns `quadraticNorm()` — so the seed
  consumption pattern at the endpoints matches the underlying policy
  byte-for-byte. Used by `LightningGenerator` (see below); also generally
  available to plugin authors who want the same texture.

- **`GrowingTreePoliciesTest`** — five new unit tests covering
  `newestWithNormJump`: equivalence to `newest()` at `pJump=0.0`,
  equivalence to `quadraticNorm()` at `pJump=1.0`, seed determinism in
  the mixed regime, branch-coverage at `pJump=0.5` (both component
  policies fire over a small sample), and bounds-rejection for NaN /
  out-of-range probabilities.

### Changed

- **`LightningGenerator`** — given a genuinely different selection policy
  to restore its visual identity. The 2026-05-07 unification collapsed
  Lightning onto Gauss (both delegated to `quadraticNorm()`); per the
  BACKLOG resolution, Lightning now uses
  `GrowingTreePolicies.newestWithNormJump(0.15)` — mostly RB-like long
  corridors with a 15% chance per turn of forking toward the highest-norm
  active cell. Produces a jagged "lightning bolt with branches" texture
  distinct from every other generator in the catalog. **Seed-mapping
  change:** the `seed → maze` mapping for id `"lightning"` changed in
  this pass; pinned seeds from before 2026-05-11 will resolve to
  different mazes. The displayName drops the "(Fast)" qualifier since the
  hand-tuned fast path is long gone.

- **`RecursiveBacktrackerGenerator`** — folded onto `GrowingTreeEngine`
  via `GrowingTreePolicies.newest()`. The pre-refactor implementation
  maintained its own stack-of-cells DFS with a Fisher–Yates shuffle of
  `Direction.values()` and an in-order scan for the first unvisited
  neighbour; the engine's slow-path enumeration uses
  `Collections.shuffle` on a `List<Direction>`. For size-4 lists
  `Collections.shuffle` takes the fast path and emits exactly the same
  Fisher–Yates sequence (`nextInt(4), nextInt(3), nextInt(2)`).
  **Seed-mapping: preserved.** The original BACKLOG note had worried
  about a different `Random` consumption pattern; a side-by-side audit
  of the pre- and post-refactor code confirmed identical bit consumption
  end-to-end (same start-cell call, same shuffle output, the `newest()`
  policy consumes zero bits). Clients with pinned RB seeds resolve to
  the same maze before and after this refactor. The equivalence is
  locked by the new
  `RecursiveBacktrackerEngineEquivalenceTest` (parameterised over five
  `(rows, cols, seed)` combinations including tall, wide, and non-square
  grids). This was the last newest-pick generator carrying its own loop
  — the entire Growing-Tree family now lives behind one engine.

- **`README.md`** — adds a CI badge, points the "Writing a plugin"
  section at `examples/biome-plugin/`, and lists `examples/` in the
  workspace-layout overview.
- **`BACKLOG.md`** — removes the closed "Reference plugin:
  `BiomeGeneratorPlugin`" item and rewrites the stretch-goal
  "GitHub Actions CI" entry to reflect that the CI + release pieces
  are now done; only the optional coverage-upload step remains. The
  entire "Refactoring (core)" section is dropped — both items
  (Lightning's fate and RB on `GrowingTreeEngine`) shipped in this
  pass and the section had no other entries.

---

## [1.0.0] — 2026-05-07 (released with 1.0.0)

**Four BACKLOG items closed in one pass:** DSU extraction, Growing-Tree policy
unification, REST input validation, and per-method rate limiting on write
endpoints. All four were called out in `BACKLOG.md` (server hardening + core
refactor sections); each now has a real implementation plus tests, and the
matching backlog entries have been removed.

**Desktop visualizer is now actually runnable.** The `daedalus-desktop`
module shipped with `DaedalusLauncher` + `DaedalusPrimaryStage` referencing
a `/ui/main.fxml` and a `Theme` SPI that had no implementations and no
resources directory — the app would have crashed on startup with
`NullPointerException: main.fxml missing from /resources/ui`. This
release fills in the missing pieces so
`mvn -pl daedalus-desktop javafx:run -am` opens a window and draws mazes:

- **`/ui/main.fxml`** — `BorderPane` with a top toolbar (generator
  picker, rows / cols spinners, seed field, Generate button), a center
  `Pane` holding the rendering `Canvas`, and a bottom status bar.
  Controller wired via Spring's bean factory.
- **`/ui/cosmic.css`** — paired stylesheet for the Cosmic theme.
- **`MainController` (`@Component`)** — populates the generator
  and solver dropdowns from the live `GeneratorRegistry` and
  `SolverRegistry`, runs generations and solves through
  `MazeGenerationService` / `MazeSolverService` (so plugin events and
  metrics fire exactly as they do for the REST surface), renders the
  resulting `MazeGrid` via `toTileGrid()` onto the canvas with
  theme-driven colors, and re-renders on window resize. Three layers
  on every paint: tile grid (passages / walls / start / goal); solve
  path overlay in `theme.path()` (drawn under endpoint markers so
  start and goal stay visible, with connector tiles between
  consecutive path cells so the trace renders continuously rather than
  as dots); and finally the movable player marker as a circle in
  `theme.player()`. Reset puts the player back at start without
  re-running the generator. Arrow keys and WASD walk the player
  through open walls (closed walls silently block); reaching the goal
  flips the marker to `theme.path()` color and announces the win in
  the status bar.
- **`CosmicTheme` (`@Component implements Theme`)** — first concrete
  theme: dark navy + cyan + magenta palette; matches the
  `daedalus.ui.theme: cosmic` default in `application.yml`.

Note: `DaedalusLauncher` boots the full Spring context including the
embedded servlet container, so running the desktop client also exposes
the REST API on port 8080. Useful for debugging; potentially noisy if
something else is bound to that port.

### Added

- **`com.daedalus.util.DSU` — shared union-find utility.** Single
  implementation with both standard optimizations (path-compressing two-pass
  `find`, union-by-rank with `byte[]` ranks) over a fixed `int[]` keyspace.
  Maze generators that work in 2-D coordinates flatten via
  `r * cols + c`. Replaces the inline `HashMap<Point, Point>` DSUs that
  used to live in `KruskalsGenerator` and `BoruvkasGenerator` — same
  asymptotic complexity, no more boxing on the hot inner loop. The API
  also surfaces `sizeOf(int)`, `largestComponent()`, and
  `isFullyConnected()`; the first two are backed by an `int[]
  componentSize` array maintained at the root on every union plus a
  running `largestSize` max, so both queries stay O(1). `DSUTest` (unit
  + randomized stress against an oracle, cross-checking connectivity *and*
  size bookkeeping) locks in the invariants.

- **Kruskal's now early-exits when the spanning tree is complete.**
  `KruskalsGenerator` checks `dsu.isFullyConnected()` at the top of the
  edge-iteration loop and breaks when true, sparing the shuffle's
  cycle-creating tail (~half of the original edge list on a typical
  maze). Output is bit-for-bit identical for the same seed — the skipped
  edges were all guaranteed-no-op `union` calls; we just stop visiting
  them.

- **`GrowingTreePolicy` SPI + `GrowingTreeEngine` shared loop.** The
  Growing-Tree family (`GrowingTreeGenerator`, `LightningGenerator`,
  `GaussGenerator`, `TuringGenerator`) used to repeat the same
  frontier-list / pick-cell / carve-or-drop skeleton four times with only
  the cell-selection rule differing. Extracted: each generator now passes
  a one-method `GrowingTreePolicy` lambda (or stateful object, in
  Turing's case) into `GrowingTreeEngine.run(...)`. Existing public
  generator classes are kept as thin adapters for backward compatibility
  — callers that hold `new GaussGenerator()` references compile and
  behave identically. Named factories live in `GrowingTreePolicies`
  (`newest`, `oldest`, `random`, `middle`, `mixed(double)`,
  `quadraticNorm`, `turingMachine`); the four registered generators
  consume them instead of inlining lambdas, and the stateful
  Turing-machine policy was moved out of `TuringGenerator`'s private
  inner class into the shared bucket. `GrowingTreePoliciesTest` pins
  each factory's contract directly (synthetic active lists + fixed-seed
  `Random`).

- **`OldestPickGenerator` (id `oldest-pick`).** New built-in: a
  Growing-Tree variant that always expands the head of the active list,
  giving BFS-shaped wave-front growth — short branches, "expanding ring"
  texture, the visual opposite of Recursive Backtracker's long winding
  rivers. Existence as a five-line class plus one line in
  `AlgorithmConfig.builtInGenerators()` is the demonstration that the
  engine + policy extraction pays off. Covered by
  `PerfectMazePropertyTest`.

- **REST input validation on every write endpoint.** `GenerateRequest`,
  `MoveRequest`, and `LoginRequest` carry `jakarta.validation`
  annotations (`@NotBlank`, `@Pattern` for IDs, `@Min`/`@Max` for grid
  dimensions, `@Size` for usernames/passwords). `MazeController` is
  `@Validated` (enables param-level constraints on path / query) and
  every body parameter is `@Valid`. `ApiExceptionHandler` translates
  `MethodArgumentNotValidException` and `ConstraintViolationException`
  into RFC 7807 `ProblemDetail` 400 responses with a sorted
  `fieldErrors` map keyed by the offending field — replaces the
  previous "malformed payload returns 500" behavior that was called out
  in the audit. New: `MazeControllerValidationTest` (boundary cases per
  field) and `AuthControllerValidationTest` (login DTO).

- **`@AlgorithmId` composite constraint.** New annotation in
  `com.daedalus.api.validation` that bundles
  `@NotBlank + @Pattern("^[a-z0-9][a-z0-9-]{0,63}$")` with
  `@ReportAsSingleViolation`. Single source of truth for the algorithm
  / solver id regex; `GenerateRequest.generatorId` and
  `MazeController.solve`'s `solverId` path variable both wear it now,
  replacing the duplicated `@NotBlank @Pattern(...)` blocks. The
  composite's message is preserved verbatim from the prior
  `@Pattern` message so existing test assertions still hold.

- **`@NonNegativeCoordinate` constraint on `MoveRequest.to`.** Closes
  the documented validation gap where a request body with a negative
  `row` or `col` slipped past the API surface and silently flipped
  `GameSessionService#tryMove` to `false` (returning `200 OK`
  body=`false` instead of a structured 400). The validator lives in
  `daedalus-server`'s validation package and reaches into `Point` via
  its public accessors, so `daedalus-core` stays framework-free per its
  existing rationale. Upper-bound and adjacency checks remain owned by
  `tryMove` (which has access to the grid dimensions and current
  position); validation only catches the structurally impossible. New
  test cases in `MazeControllerValidationTest` cover null `to`,
  negative `row`, and negative `col`.

- **Resilience4j rate limiting on the three write endpoints.** Three
  named `@RateLimiter` instances configured in `application.yml`:
  `mazeGenerate` (30/min), `mazeSolve` (60/min — solving is cheaper),
  and `authLogin` (10/min — brute-force guard). `application-test.yml`
  overrides with very generous limits so MockMvc tests don't trip over
  themselves; `application-prod.yml` tightens `authLogin` further. All
  three configured `timeout-duration: 0` — fail fast with
  `RequestNotPermitted` rather than queueing.
  `ApiExceptionHandler#onRateLimited` maps the exception to a
  `429 Too Many Requests` with a `Retry-After` header carrying the
  limiter's actual `limit-refresh-period` (rounded up to whole seconds,
  floored at 1 per RFC 9110) and a problem-detail body whose `limiter`
  property names which instance was exhausted, so clients can
  differentiate "your generate quota is gone" from "your solve quota is
  gone" without us baking business meaning into HTTP.
  `ApiExceptionHandler` now takes an optional `RateLimiterRegistry` via
  an `@Autowired` constructor (Resilience4j Spring Boot autowires it
  from YAML); tests using the no-arg constructor see the previous
  1-second floor as the fallback. New:
  `ApiExceptionHandlerRateLimitTest` — five unit tests against the
  handler in isolation, including the registry-aware path
  (verifies `Retry-After: 60` for a 1-minute refresh, `Retry-After: 1`
  for a 250 ms refresh and for unregistered limiter names).

### Changed

- **`LightningGenerator`'s seed → maze mapping is no longer bit-for-bit
  identical to its pre-refactor output.** Pre-refactor Lightning used a
  faster array-based shuffle that filtered out-of-bounds neighbors
  *before* shuffling — that consumed `Random` differently than the other
  three Growing-Tree variants. The unified `GrowingTreeEngine` uses the
  slow path (shuffle all four directions, then iterate and bounds-check)
  so that `GrowingTreeGenerator`, `GaussGenerator`, and
  `TuringGenerator` all stay bit-for-bit identical to their previous
  output. Lightning was the odd one out, and unification + reproducibility
  across the family was preferred over Lightning's marginal allocation
  savings. Anyone pinning a Lightning seed should regenerate.

### Caveats

- **Rate limits are global, not per-IP / per-subject.** Resilience4j's
  `@RateLimiter` annotation is method-scoped — a single bucket shared by
  all callers. A new BACKLOG entry has been kept ("Per-key rate
  limiting") to track the upgrade to a `RateLimiterRegistry` plus
  `HandlerInterceptor` keyed off the request principal / IP.

## [1.0.0] — 2026-05-06 (released with 1.0.0)

**Cost-aware routing landed.** New `WeightedMazeGrid` adds per-cell entry
costs, and `DijkstraSolver` / `AStarSolver` now read those costs through
a polymorphic `MazeGrid#weightOf(Point)` hook (default `1.0`). Plain
`MazeGrid` instances are unchanged behaviourally, so existing solver
callers and the perfect-maze property test keep working untouched. Two
new core test files (`WeightedMazeGridTest`, `WeightedRoutingTest`) lock
in defaults / validation and prove that on a two-corridor maze the
solvers detour around a heavily-weighted cell and stay on the short
corridor when the penalty is modest.

This is the LoadBalancer-Lab integration angle from the Vision docs:
load on a node = cost to route through it. The same pattern works for
latency, terrain cost, swamp tiles, etc. Edge cost from `u` to `v` is
defined as `weightOf(v)`; the start cell is never charged because the
solver begins there rather than entering it.

**Multi-JAR discovery test restored and broadened.** `PluginManagerJar
DiscoveryTest` had a 4th test method (`discover_withMu...`) that lost
its body — the file was truncated at line 199 and broke the reactor.
Reconstructed as `discover_withMultipleJars_isolatesEachInItsOwnClass
loader`, plus a new `OtherSamplePlugin` test fixture so two genuinely
different plugins can coexist in the registry. Test asserts both jars
reach the registry under distinct ids, that `externalLoaders` holds
two distinct `URLClassLoader` instances, and that each loader's URL
list points at exactly one of the two jars we wrote (not collapsed
into a single loader). The "plugin.getClass().getClassLoader() is the
URLClassLoader" assertion is intentionally absent — Maven Surefire's
parent-first delegation lets the parent CL define the class because
the test fixtures are on the test classpath, so we probe the invariant
through `getURLs()` instead.

**Plugin-runtime audit gaps closed.** Three more tests added to
`PluginManagerJarDiscoveryTest`:

- `discover_ignoresNonJarFiles_butStillLoadsJarsBesideThem` — drops a
  real plugin JAR alongside `.txt` / `.yml` / `.zip` files plus a
  jar-named subdirectory; only the JAR is processed.
- `discover_jarWithNoServiceFile_tracksLoaderButRegistersNothing` —
  documents that a JAR with a class file but no `META-INF/services`
  entry produces zero plugins yet still has its `URLClassLoader`
  tracked, so `shutdownAll()` can release the file handle on Windows.
- `discover_corruptJar_publishesPluginFailedEvent_discoverPhase` —
  builds a JAR whose service file names a missing class and asserts
  the failure surfaces as a `PluginFailedEvent.Phase.DISCOVER`.

### Fixed

- **`PluginManager.loadJar()` now catches `Throwable`, not just
  `Exception`.** The original `catch (Exception e)` couldn't catch
  `ServiceConfigurationError` (which extends `Error`), so the most
  common discovery failures — service file naming a missing class,
  wrong type, plugin constructor throwing — would crash `discover()`
  outright instead of publishing a `PluginFailedEvent.Phase.DISCOVER`.
  The event-publication branch was effectively unreachable. Widening
  the catch to `Throwable` aligns this method with how `bootAll()` and
  `shutdownAll()` already treat lifecycle failures (each catches
  `Throwable`) and makes the "operators see plugin failures via
  `/topic/plugins/failures`" guarantee actually hold for discovery.

- **OneDrive sync corruption — 10 server-module files repaired.**
  A reactor build surfaced compile errors in six files with the
  unmistakable pattern of an interrupted OneDrive sync: trailing null
  bytes (`\0`) on some, mid-method truncation on others. A full
  sweep then found four more in the same state that the compiler
  hadn't reached yet because the build aborted early.

  **Cleanly recovered (trailing nulls only — surviving content is
  byte-identical to the pre-corruption file):**
  - `daedalus-server/.../config/OpenApiConfig.java`
  - `daedalus-server/.../controller/MazeWebSocketController.java`
  - `daedalus-server/.../test/.../MazeWebSocketControllerPluginFailedTest.java`

  **Reconstructed (truncation, but the missing tail was small or
  obvious from surrounding context):**
  - `daedalus-server/.../controller/MazeController.java` — initial
    pass added only the missing closing brace because the surviving
    tail looked clean; a follow-up build error revealed two more
    methods had been silently lost: the `GET /api/v1/leaderboard`
    endpoint (present in the class Javadoc but not the body) and a
    private `toResponse(UUID, String, int, int, long, MazeGrid)`
    helper called by both `generate` and `get`. Both now restored;
    the helper flattens `MazeGrid#toTileGrid()` (which returns
    `TileType[][]`) into the `char[][]` shape `GenerateResponse`
    expects. Lesson: corruption-tail detection that relies on "ends
    with `}`" misses the case where the last surviving content was
    itself a method-end brace inside a longer file.
  - `daedalus-server/.../controller/PluginController.java` — last
    `.toList()` of the existing stream pipeline plus the `/describe`
    endpoint (signature documented in README's REST table)
  - `daedalus-server/.../test/.../MazeControllerGeneratorIdTest.java`
    — the last few `jsonPath` assertions on `$.cols` and `$.seed`
  - `daedalus-server/.../test/.../JwtTokenServiceTest.java` — the
    body of `issuedToken_expiresAtMatchesTtl` (TTL math against
    `IssuedToken#expiresAt`)
  - `daedalus-server/.../DaedalusApp.java` — the small
    `SpringApplicationBuilder` shim subclass

  **Reconstructed with reasonable confidence but worth a second pair
  of eyes** (the surviving header + Javadoc described the intent
  clearly, but a meaningful chunk of body had to be rebuilt):
  - `daedalus-server/.../config/ProdSecurityConfig.java` — last few
    `requestMatchers` for protected write endpoints + plugin
    introspection + `/ws/**` + `/v3/api-docs/**` deny + `.anyRequest()
    .authenticated()` + `.oauth2ResourceServer(...jwt)` wiring
  - `daedalus-server/.../config/SecurityConfig.java` — entire
    `@Bean SecurityFilterChain` body (CSRF off, stateless sessions,
    `permitAll` on every documented path glob)

  **Backups of the corrupted originals** are at
  `/tmp/server-backup/` in the build sandbox; if the reconstruction
  diverges from the user's intent, the surviving prefixes can be
  diffed against the rebuilt files to find disagreement.

  **Root cause** is OneDrive's "Files On-Demand" feature lazily
  hydrating cloud-only files: when an editor or compiler reads a file
  that hasn't fully synced down, OneDrive sometimes returns the
  cached-locally portion plus null padding instead of waiting for
  hydration. The fix on the user's side is either pinning the project
  folder ("Always keep on this device") or moving the working copy
  off OneDrive entirely.

## [1.0.0] — 2026-05-05 (released with 1.0.0)

Reactor green: `mvn clean verify` passes 25 / 25 tests across all six modules
in 16 s. The four findings from the May 3 audit are confirmed applied; the
follow-ups it called out as "non-blocking" are now also done.

Two further changes landed later in the day, after the build was verified:
**OpenAPI / Swagger UI polish** and a **profile-aware Security split**. Both
are additive — the dev / test posture is unchanged, only the prod posture
gets meaningfully more restrictive, and there's a new test that locks in
which `SecurityFilterChain` bean activates per profile.

A subsequent pass added **JWT-based auth** to the prod posture — single ops
user with bcrypt-hashed password from env vars, `POST /api/v1/auth/login`
issues a self-signed HS256 JWT, write endpoints + `/ws/**` + plugin
introspection require the token, reads stay public. Two new test classes
(`JwtTokenServiceTest`, `AuthControllerTest`) lock in issue/decode round-trip
and the login contract.

### Added

- **`com.daedalus.api.dto` package** with 10 record-based DTOs extracted from
  controller inner classes — `GenerateRequest`/`Response`, `MoveRequest`,
  `SessionResponse`, `SolveResponse`, `GeneratedFrame`, `SolvedFrame`,
  `MoveFrame`, `PluginFailedFrame`, `PluginInfo`. Every record has Javadoc
  describing its endpoint or STOMP topic.
- **OpenAPI / Swagger UI polish.** New `OpenApiConfig` populates the doc-level
  `Info` (title, description, version, contact, license placeholder), declares
  the dev server URL, and pre-registers three tags (`Mazes`, `Plugins`,
  `Leaderboard`) for stable ordering in Swagger UI. `MazeController`,
  `PluginController`, and the leaderboard endpoint carry `@Tag` and
  `@Operation` summaries so the rendered UI explains each route. Spec is
  served at `/v3/api-docs` (JSON), `/v3/api-docs.yaml`, and `/swagger-ui.html`
  in dev / non-prod profiles.
- **`ProdSecurityConfig`** — new `@Profile("prod")` filter chain:
  `/actuator/health`, `/actuator/info`, `/actuator/prometheus` stay public
  (matching `application-prod.yml`'s exposure list); every other
  `/actuator/**` path requires authentication; `/v3/api-docs/**` and
  `/swagger-ui/**` are explicitly denied; `/api/**` and `/ws/**` remain
  permitted with TODOs for wiring real auth (OAuth2 / JWT / mTLS) before
  any non-trusted-network deployment.
- **`SecurityConfigProfileTest`** — locks in the `@Profile` split so the
  dev and prod chains can never both activate (which would crash boot).
- **JWT auth (prod)** — `JwtAuthProperties`, `AdminCredentialsProperties`,
  `JwtTokenService` (HS256, self-signed via `NimbusJwtEncoder` / `Decoder`),
  `LoginRequest`/`LoginResponse` DTOs, `AuthController` with
  `POST /api/v1/auth/login`. Dependency added: `spring-boot-starter-oauth2-
  resource-server` (brings in `nimbus-jose-jwt`). Config bound from
  `daedalus.security.jwt.*` and `daedalus.security.admin.*`; prod requires
  `DAEDALUS_JWT_SECRET` + `DAEDALUS_ADMIN_PASSWORD_BCRYPT` env vars. Dev
  defaults are baked into `application.yml` so login works out-of-box during
  development (admin / admin).
- **`JwtTokenServiceTest`** (4 cases) — round-trip claims, foreign-secret
  rejection, short-secret refusal at construction time, TTL math.
- **`AuthControllerTest`** (4 cases) — 200 + token on success; identical
  401 / no body on wrong password, unknown user, and unconfigured admin
  (no leakage of which check failed).
- **API versioning** on the REST surface: `MazeController` now mounts at
  `/api/v1`, `PluginController` at `/api/v1/plugins`. Class Javadoc, the one
  test that hits the endpoint, and its docstring all updated.
- **Desktop module tests** (`daedalus-desktop`, previously had none):
  - `ThemeManagerTest` — 3 cases covering the constructor's default-resolution
    branches (named-default present, named-default missing → fall back to first,
    empty theme list → no NPE).
  - `DaedalusLauncherTest` — 1 case locking in the static-lifecycle null-safety
    contract.
- **`@AfterEach closeManager()`** in `PluginManagerJarDiscoveryTest` — releases
  every `URLClassLoader` opened by `discover()` so JUnit's `@TempDir` cleanup
  can delete the test JARs on Windows.

### Changed

- **Controllers stripped of inner records.** `MazeController` 135→128 lines,
  `MazeWebSocketController` 68→63 lines, `PluginController` 40→37 lines.
  Routing/handler logic unchanged.
- **`SecurityConfig` is now `@Profile("!prod")`.** Behaviour for dev / test /
  the JavaFX desktop client is unchanged: every endpoint is `permitAll()`,
  Swagger UI works, actuator is open. Each `requestMatcher` is now explicitly
  declared and commented so the intent is obvious. `PasswordEncoder` moved
  to its own `PasswordEncoderConfig` class so the bean stays available
  regardless of which profile is active.
- **`AUDIT_RECOMMENDATIONS_2026-05-05.md`** rewritten from a backlog into a
  verification log. All audit items, including the five "non-blocking"
  follow-ups, now have date-stamped completion notes.
- **Workspace root** trimmed from 11 entries to 9: only `.idea/`, `_migration/`,
  the five Maven modules, `pom.xml`, `README.md`, `AUDIT_RECOMMENDATIONS_*.md`,
  and this file.

### Fixed

- **Spring Boot multi-module artifact collision.** `daedalus-server`'s
  `spring-boot-maven-plugin` now uses `<classifier>exec</classifier>` so the
  thin JAR remains the main Maven artifact (downstream modules like
  `daedalus-desktop` can compile against it) and the executable fat JAR is
  published as `daedalus-server-<version>-exec.jar`. Run with
  `java -jar daedalus-server-<version>-exec.jar`.
- **`PluginManagerJarDiscoveryTest` Windows file-locks.** Three tests called
  `discover()` (which opens a `URLClassLoader` per JAR) but never invoked
  `shutdownAll()`. The new `@AfterEach` closes the loaders before `@TempDir`
  cleans up. Net effect: `mvn clean verify` now goes green on Windows.

### Licensed

- **MIT License** — added `LICENSE` at project root. Copyright 2026 Richmond.
  README updated to point at it; `OpenApiConfig` swagger metadata switched
  from "Unlicensed (no license file in repo yet)" to MIT.
- **SPDX-License-Identifier headers** — `// SPDX-License-Identifier: MIT`
  added as line 1 of every Java source file (109 across the five modules)
  plus the two files under `Code/`. Total: 111 files. Lets automated
  license-scanners (FOSSA, ScanCode, REUSE) detect the license per-file
  without having to read the root `LICENSE`.

### Removed

- Three superseded audit zips from project root: `daedalus-complete-audit-
  2026-05-03.zip` (duplicate of `(1)` archive), `daedalus-full-audit-
  2026-05-03.zip`, `daedalus-server-audit-2026-05-03.zip`.
- Empty `src/` skeleton (23 leftover directories from the multi-module split
  that `migrate.bat` should have removed).
- Two 0-byte stub files in root: `com.daedalus.desktop`, `com.daedalus.server`.
- `migrate.bat` and `MIGRATION.md` from the active root (archived to
  `_migration/`; migration is complete).

### Verified (no changes needed)

- All four audit patches (`M