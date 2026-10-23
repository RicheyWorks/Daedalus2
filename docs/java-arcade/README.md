# Java games in Daedalus: local cabinet pilot

`ADaedalusJavaArcade` adds an asynchronous Unreal cabinet for SudokuPro and
BlackJackPro while retaining their Java rules. It derives from the existing
`ADaedalusUsable`; its standalone Slate overlay does not pause Java's game clock.
There is no Java rules rewrite or embedded JavaFX window.

## Source and ownership

| Component | Pinned source / deliverable |
| --- | --- |
| Daedalus native baseline | `ddbf5b372e0d8543df85408684d27efa849d42c9` |
| Sudoku server and desktop | [sudokupro](https://github.com/RicheyWorks/sudokupro/tree/973c73a35f8659a17022232f0996d4ffb0095997), `973c73a35f8659a17022232f0996d4ffb0095997` |
| Blackjack unchanged core | [BlackJackPro](https://github.com/RicheyWorks/BlackJackPro/tree/1ec1801ac635e62945072974cbe8c78398a17849), `1ec1801ac635e62945072974cbe8c78398a17849` |
| Additive Blackjack API | [draft PR62](https://github.com/RicheyWorks/BlackJackPro/pull/62), `a4d5987a94a5cb53ed161f1778030907f64c356e` |

PR55 now incorporates the approved PR53 dependency and current-main fixes;
its focused review is stacked on that existing owner's branch. See
[verification-followup.md](verification-followup.md) for full linking, disposable
Java services and exact acceptance limits.

Original desktop projects, Python games, the dirty Buff Blackjack checkout,
shared Unreal work, audio integration and source game saves remain untouched.
The facade compiles against the visible Buff core API, but none of that checkout's
32 tracked changes was imported. A combined production release needs an agreed
source pin from its owner. This change does not implement entitlements, NFTs,
payments or multiplayer authentication.

## Use after service and Unreal acceptance

1. Run the existing Sudoku service with its Java 17, PostgreSQL, Redis and Flyway
   dependencies, or build the Blackjack PR62 distribution with a supported Java
   runtime. No services, accounts or dependencies are provisioned by the cabinet.
2. Place separate `ADaedalusJavaArcade` actors and set `Game` to Sudoku or
   Blackjack. Each actor has its own `CabinetId`, independent of account/session
   IDs and future purchase entitlements.
3. Keep origins exact `http://127.0.0.1:<port>` (defaults 8080 and 8091).
   Paths, queries, fragments, userinfo, hostnames and non-loopback addresses are
   rejected. This pilot assumes trusted direct local Java endpoints.
4. Use the normal Daedalus interaction prompt. Enter the existing Sudoku account
   username/password or the Blackjack launch bearer. Masked fields clear after
   configuration; secrets are private transient memory, never actor properties,
   DTO fields, save data or logs. Close/property changes forget them.
5. Sudoku: create a difficulty 1–5 board, refresh saved games and explicitly resume
   a selected board, or open/resume an explicit own game ID;
   select cells and enter/erase digits, undo/redo, save or refresh. Hint is an
   explicit button and may spend the Java account's existing virtual gems.
   A solved or expired board shows Java's result with Save, Refresh, Review board
   and New classic puzzle (same difficulty). Save explicitly before starting
   another puzzle. Enter / pad A from the finished board focuses result controls;
   arrows / D-pad still review cells. A result is revealed once after a reconciled
   board arrives; refreshing or saving does not pull the view away from review.
   Hint requests keep board feedback in view while Java replies. Read board
   feedback, F7 or right-stick click revisits the current outcome and last hint
   without requesting or charging for another hint. Failed requests keep their
   current status above any retained earlier hint.
   Blackjack: create a session, choose Java-approved chips, deal, hit, stand,
   double, split, surrender, choose insurance, or end the session. Credits are
   simulated, initially 1000, and cannot be cashed out.
   Expand Change table options for explicit rule Enable/Disable, deck-count and
   split-hand-limit commands. Each is gated by Java's current legal actions;
   apply one choice and wait for its reply. Return to table resumes play shortcuts
   and reveals the active table or recovery message. These controls show commands, with no
   checked values or assumed defaults because the visible snapshot omits settings.

Blackjack build and launch (from its repository):

```powershell
.\gradlew.bat :arcade-bridge:test :arcade-bridge:installDist
# Supply DAEDALUS_BLACKJACK_TOKEN securely in this process before launching.
.\arcade-bridge\build\install\arcade-bridge\bin\arcade-bridge.bat --port 8091
```

The distribution contains jars, launch scripts and the existing MIT notice,
not a bundled Java runtime. Its token must match `[A-Za-z0-9_-]{32,128}`. One
shared bearer authorizes all sessions in this local process; serialized session
locking is concurrency control, not per-player identity or entitlement isolation.

## State, authorization and uncertainty

Java decides generation, legality, clocks, score, hints, completion, Blackjack
dealing/settlement and credit changes. Unreal validates bounded typed DTOs and
projects presentation state. Reflected state excludes Sudoku solutions, the
live dealer hole card and derived dealer totals, future shoe order and RNG.
Source ownership and action legality are checked before sending; Java remains
the final authority. Unknown/malformed snapshots are applied atomically or refused.

The shared portable guard allows one operation in flight, zero queued work,
generation/serial rejection of stale callbacks, a ten-second timeout and at most
two bounded read retries. Mutations are never automatically replayed. HTTP uses
engine libcurl on workers with redirects/proxies disabled, response/header/depth
bounds and cancellation; UObject delivery happens on the game thread. The Unreal
WebSocket API cannot disable redirects publicly, so its exact derived local
origin is limited to the verified direct Sudoku endpoint. This is not a remote
or untrusted-host transport guarantee.

The Sudoku saved-board picker uses a separate bounded read channel with the same
guard and HTTP worker. It resolves the current account with `GET /api/session`,
then requests `GET /api/game/saved?limit=10`. It validates every complete board,
rejects mixed owners or duplicate IDs, and publishes only ID/progress metadata.
The complete list has a 640 KiB response cap; bootstrap and live-board reads retain
their existing 64 KiB cap. Row count and JSON depth remain bounded.
The service contract provides no ordering or pagination guarantee; manual game-ID
entry remains available. Loading, errors and a confirmed empty list have distinct
messages. Choosing an item does not resume it. Explicit resume requires current
list membership and an idle board channel with no unresolved mutation outcome.
Browsing leaves the current board, socket, cookies and reconciliation guard intact.
Changing credentials, game or origin invalidates cached metadata and old replies.

Sudoku reuses its existing REST/raw-WebSocket service. It has no request IDs or
revision receipt, and `oldVal` is not compare-and-swap. After a normal move plus
sync, board traffic triggers a fresh correlated read-only HTTP snapshot; a board
event alone never unlocks actions. This restores known current state, not proof
that one unique move executed. Timeout/disconnect/refusal/uncertain responses
retain a warning and require manual refresh; no move, undo or hint replay occurs.
An uncorrelated `gameEnd` message never grants victory or a local reward.

Blackjack uses API v1 request IDs and expected revisions. Historical create
replies are followed by a current GET before play. An unknown create retains its
exact ID for explicit recovery, rather than opening another session. Commands
with reused IDs/different bodies or stale revisions are refused by Java; bounded
idempotency records persist only for that server lifetime. Explicit end sends
DELETE. Closing the overlay cancels native work and forgets secrets; if Java
cannot be reached, its sessions expire after 15 idle minutes or one hour absolute.

## Deliberate first-pilot limits

- Standalone local overlay and placeholder mesh only. Disposable local Java
  service checks and isolated DLL linking are recorded in the follow-up;
  editor import, packaged runtime, multiplayer and in-world acceptance are pending.
- Sudoku pencil toggle, auto-solve, competitive and spectator UI are deferred.
  Saved-list browsing and explicit own save/resume IDs use existing endpoints.
- Blackjack rule/deck/split-limit commands are available in Slate; confirmed
  current-value display needs a settings readback contract. 21+3, chatter,
  achievements and persistence are not exposed.
- No account provider, Java runtime bundling or service deployment is included.
- The native actor requires installed UE modules WebSockets and engine libcurl.

## Validation evidence

- **1,330 portable checks** pass strict MSVC C++17 `/W4 /WX /permissive-` and CTest.
  Independent LLVM 19 frontend/core analyzer found no issue. These execute shared
  typed-state/lifecycle policy, not Unreal JSON handlers or network callbacks.
- **32/32 synthetic Sudoku fixture policy cases** pass, with 11 source assertions
  recorded against 23 pinned Java blobs; these are not server execution tests.
- Native source preflight and whitespace checks pass.
- Blackjack PR62: **33/33 Java tests**, 9,600 seeded source-engine comparisons,
  strict Buff API compilation and `installDist` pass. Source core is unchanged.
- Isolated UHT/UBT/object evidence is recorded in
  [unreal-compile.json](unreal-compile.json). Object compilation does not prove
  plugin linking/loading, packaged play or live authentication.

The focused CI matrix checks GCC/Clang with ASan/UBSan and MSVC plus fixtures and
preflight. It does not substitute for an Unreal runner or live owner acceptance.
At publication, Blackjack Actions run
[38452658577](https://github.com/RicheyWorks/BlackJackPro/actions/runs/38452658577)
was blocked before runner execution by GitHub billing/spending limits; no remote
green result is claimed. Native final-head CI is recorded in the PR handoff.

The later saved-picker slice has a separate `sudoku_saved_games` portable target
covering account-scoped, atomic metadata projection. Its offline checks do not
exercise Unreal JSON callbacks, Slate, authentication or the live Java service;
those need native acceptance before activating the picker.

## Blender and acceptance handoff

Use [character-brief.md](character-brief.md) for the original cabinet, Sudoku
board and dealer presentation. It is a scoped handoff, not an art/import claim.
The live owner should test both approved local services, bad/revoked credentials,
disconnect during a mutation, same-ID create recovery, stale revisions,
hole-card secrecy, hint charging, save/resume, expired sessions and overlay
focus/close/pawn destruction in world. Keep PR51's eleven native Python-game
cabinets in the separate live acceptance queue.
