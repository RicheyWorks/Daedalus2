# Verification follow-up: thirteen cabinets

Recovery update (2026-10-14): PR53 merged, then deleting its base branch
automatically closed PR55 without merging it. The same PR55 is recovered against
`main`, preserving delivered `5f35983130f55a183906382a6881282ab6663147` and normally
merging main snapshot `1ee121e0fd41302889f54bed0c3caaefacd92214` without conflicts.
All five Java client runtime files, Build.cs, both portable test files and the
pinned source/fixture/compile/full-link evidence remain identical; see
[stack recovery proof](stack-recovery.json). Fresh CI results belong to the final
recovery head in the PR body. The existing 43-action DLL proof retains its original
106-input manifest; this recovery does not claim a fresh Unreal build, loading or
in-world Play. Historical stack wording below describes the earlier handoff.

The approved PR53 dependency at `7427deffef766ce6e6ef83e6d1acd33cbe680938`
and current main at `d57a388e7ae59b804d033b52c76e2b8df529d5d6` were incorporated
without conflicts into PR55's isolated feature branch. PR55 is stacked on
`codex/realm-production-queue` while the existing Claude owner controls the
parent/main merge and editor imports. This reuses PR53's immutable DIC reader,
five-realm catalog endpoint and fixture repair; no duplicate Java implementation
or manual realm semantic change was made.

## Native linking

The first full build compiled all runtime units but failed the DLL link on
294 unresolved libcurl transitive symbols. Its failed snapshot/logs are retained.
The scoped `Build.cs` correction explicitly adds `nghttp2`, `OpenSSL` and `zlib`
alongside `libcurl`; the installed engine's libcurl dependency declarations are
private and do not supply those libraries to this plugin's direct calls.

The corrected second composite linked a real Win64 DLL with **41/41 UBT actions**,
99 verified inputs, and SHA-256
`878D5D15633B4B49814ABA2C4A16EC422A852C2D4ADF74FF77E274394E6E3CDB`
(7,602,176 bytes). Its pins were main `d57a388e`, PR51 `d29329b7`, PR55 `86849757`
and the explicit build fix. That historical result is retained separately from
the final dependency-complete source check at
`ecd81a2560a183eff73c532a7374835e37510f9c` plus PR51's eleven runtime additions.

The final dependency-complete composite passed **43/43 actions**, with **106** unchanged inputs and no extra source patches. Its Win64 DLL is 7,645,696 bytes, SHA-256 `DF174A531A6AABD2BD5BACDCF43843750950A85DEA7E70B2A3186ED655560EA6`. Full-source results and hashes are recorded in `full-link-proof.json` and
`full-link-source-manifest.json`. No editor, hot reload, plugin load, packaging,
or live game acceptance is inferred from linking. UBT used its local UBA executor
with remote execution disabled and `[NoUba]` actions/task cache. It still emitted
the standard diagnostic `Trace.uba` in local AppData; no engine/source/editor
configuration was changed to suppress that default.

## Disposable Java services

- **Blackjack: 41 direct HTTP checks**, using distribution jars compiled at
  `a4d5987a94a5cb53ed161f1778030907f64c356e`, fresh child-only bearer, cleared
  child environment, no proxies/redirects and simulated credits. Tool/docs/proof
  are published in [PR62](https://github.com/RicheyWorks/BlackJackPro/pull/62),
  head `8a4dccfbc359be628b5766ea1b7082410baefe1c`. The owned process exited and
  test port was independently confirmed closed. The generated batch launcher,
  native callbacks and per-user multiplayer identity were not tested.
- **Sudoku: 27 real HTTP/WebSocket checkpoints**, one passing targeted JUnit
  test, source `973c73a35f8659a17022232f0996d4ffb0095997`, real auth/JPA/domain,
  H2 memory and mocked Redis. See [proof and reproduction](sudoku-disposable/README.md).
  One hint charged five synthetic account gems. All owned listeners/JVMs stopped.
  Real PostgreSQL/Redis/cross-replica operation remain prerequisites.

Original projects, game rules, real account credentials, shared Java services,
existing editor sessions and the audio lane remain untouched.

## CI and acceptance ownership

PR53's exact repair head passed full CI
[38455103477](https://github.com/RicheyWorks/Daedalus2/actions/runs/38455103477),
including reactor/API/examples/Windows, plus Engines and Portal checks. That did
not by itself clear PR55's old failure. PR55's final-head checks after dependency
adoption are recorded in its PR body; no checks were skipped or weakened.

PR62's tool/docs head had one automatic CI attempt
[38457480954](https://github.com/RicheyWorks/BlackJackPro/actions/runs/38457480954),
blocked before execution by account billing/spending-limit checks. No manual
rerun or billing/settings change was attempted.

All **13 cabinets** are recorded in row 6 of the established Claude-owned
`bot-team/BOARD/UNREAL-QUEUE.md`: Pong, Dungeon, Asteroids, Football, Pacman,
Sega Shooter, Shadow Ninja, Star Shooter, Dodge Ball, Contra, Zelda, Sudoku and
Blackjack. Queue entry and exact-pin handoffs were sent to `unreal-team`,
`team-codex`, `buffffff` and `blender-team`. This formal queued request relies on
the accepted editor lane; per-item Claude acknowledgment and live acceptance
remain pending. No editor lease or speculative art scope was assigned.
