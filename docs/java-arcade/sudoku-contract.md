# SudokuPro Java service contract for Unreal

Source: [RicheyWorks/sudokupro](https://github.com/RicheyWorks/sudokupro), private authorized repository, pinned main commit **973c73a35f8659a17022232f0996d4ffb0095997** (2026-10-10 21:22:29 UTC). This is a source-derived integration contract. No Java service, game rules, source originals, deployments or running editors were changed.

Java remains authoritative for generation, legality, moves, hints and their gem costs, clock, score, completion, persistence and competitive permissions. Unreal supplies an asynchronous HTTP/raw-WebSocket client and presentation. No Java rule rewrite, JNI dependency, Python runtime or embedded JavaFX is required.

## Bootstrap and transport

1. Use a configured approved base URL; HTTP is suitable for an explicit loopback development target, and external credentials require HTTPS/WSS. Never put credentials in cabinet identity, Blueprint state snapshots, URLs or logs.
2. Send HTTP Basic credentials on `GET /api/session`. Its direct response is `{playerId, csrfHeaderName, csrfToken, wsTicket}`. Keep the response cookie jar, including `XSRF-TOKEN` and any session cookie.
3. Mutating REST requests send Basic authentication plus the cookie jar and the returned CSRF header/token (normally `X-XSRF-TOKEN`). A new game returns direct `BoardState`, including its real `gameId`.
4. Connect to `/ws/game?gameId=<RFC3986-percent-encoded ID>` with the native `Authorization: Basic` header. Alternatively a fresh `wsTicket` from session bootstrap can be supplied as `ticket=<encoded token>`; it is single-use and expires after 60 seconds. A bad offered ticket is refused rather than falling back to another identity.
5. Opening a socket does **not** deliver an initial board. Send `{"type":"sync","payload":""}` and reconcile a full board. The existing desktop client uses Basic headers, not tickets, for its socket.

Server authentication can fail after password changes, and revocation closes old sockets. A native client must stop retrying rejected credentials. Do not infer identity from an envelope's `from`: move/board broadcasts use `server`; named errors use the authenticated player; generic exception errors use a socket session ID.

## REST operations used by the first cabinet

| Method and path | Request body | Success response |
|---|---|---|
| `GET /api/session` | none | Direct session object |
| `POST /api/game/new?difficulty=1..5&chaos=<true/false>&mirror=<true/false>&timeAttack=<true/false>` | none | Direct `BoardState` |
| `GET /api/game/{gameId}` | none | Direct `BoardState` |
| `POST /api/game/{gameId}/save` | none | `{"status":"saved","gameId":"..."}` |
| `GET /api/game/saved?limit=1..50` | none | Array of `BoardState` |
| `POST /api/game/{gameId}/resume` | none | Direct `BoardState` |
| `POST /api/game/hint?gameId=<encoded ID>` | none | `{"hint":"..."}` |
| `POST /api/game/{gameId}/end` | none | HTTP 204, empty body |

Normal moves, undo and redo have **no REST endpoint**. The deprecated GET hint alias is outside this adapter; it sunsets October 31, 2026. POST hints are purchases, with no general replay guarantee. Auto-solve and other platform features already exist in Java but are outside this initial native contract.

REST failures are heterogeneous. Controllers commonly use `application/problem+json` with `title`/`detail`, sometimes also `type`. A 401 can be a Basic challenge or a bare response. A busy game is 409 `Game Busy` with `Retry-After: 1`; expiry is 409 `Time's Up` without a retry invitation. Hints can return 402 `Not Enough Gems`. Authentication/database unavailability can return 503 `Database Unavailable` with `Retry-After: 2`. Preserve status and bounded readable detail; never require all failures to share one JSON shape.

## Raw WebSocket messages

Outbound commands omit `from`:

```json
{"type":"move","payload":{"row":0,"col":2,"oldVal":0,"newVal":4}}
{"type":"move","payload":{"row":0,"col":2,"oldVal":4,"newVal":0}}
{"type":"undo","payload":""}
{"type":"redo","payload":""}
{"type":"sync","payload":""}
```

Coordinates are zero-based 0..8. Values are 0..9; zero erases. Java ignores client-supplied source labels and stamps PLAYER. `oldVal` is **not** a compare-and-swap token: Java reads the real prior cell value when applying a move.

Accepted moves broadcast to the sender and peers:

```json
{"type":"move","from":"server","payload":{"row":0,"col":2,"oldVal":0,"newVal":4,"source":"PLAYER"}}
{"type":"error","from":"fixture_player","payload":{"detail":"Invalid move"}}
{"type":"error","from":"fixture_player","payload":{"detail":"Fixture clock expired","timeUp":true}}
{"type":"health","from":"server","payload":"PING"}
```

A full board is `{"type":"board","from":"server","payload":<BoardState>}`. Undo/redo return this same board envelope to all game sockets, with no operation-specific acknowledgement. Other events include `batch_moves`, `join`, `leave`, `chat`, `hint`, `status`, `event` and `gameEnd`.

`gameEnd` contains a human-readable **string**, including when a game is abandoned or expires. It is not victory evidence. Refresh the board and use `solved`/`timeUp`. A time-up error carries no board by itself.

## Player-visible snapshot

`BoardState` has exactly these current fields: `gameId`, `playerId`, `difficulty`, `chaosMode`, `mirrorMode`, `solved`, `lives`, `score`, `hintCount`, `moveCount`, `elapsedSeconds`, `timeLimitSeconds`, `secondsLeft`, `timeUp`, `cells`.

`cells` is 9 rows of 9 cell objects. Each contains `value`, `isGiven`, `lastModified`, `moveSource`, `pencilMarks`, `conflicts`, `hintStrength`, `strategy`, `isEditable`, `playerId`, `displayColor`. `strategy` and cell `playerId` can be null. Source labels are PLAYER, HINT, AUTOSOLVE, INITIAL, CHAOS, UNKNOWN; these are display metadata, not commands or entitlements.

There is no aggregate given mask: derive the 81 clue flags from `isGiven`. The cell-view `isEditable` is false for any filled cell, including a player entry. Protect clues with `isGiven`; still allow erase/replace intent on non-givens and let Java decide it. Cell `playerId` is a synthetic `player_<lastModified>` display label, not account identity. Top-level `BoardState.playerId` is the owner.

The record deliberately excludes hidden solutions. A completed game's fully filled visible grid is legitimate; do not confuse that with a hidden `solution`/`solvedGrid` field. Pencil notes in the existing clients are local presentation; the wire can carry notes, but no pencil-toggle command exists in this contract.

The server clock stays authoritative. Time attack is configured at five minutes per difficulty level by default. Local menu pause, cabinet close, reconnect or resume must not add time.

### Native create-mode binding, source-only — 2026-10-15

Code4d5577dc adds `StartSudokuGameWithModes(Difficulty,Chaos,Mirror,TimeAttack)`.
The original `StartSudokuGame(Difficulty)` remains ordinary all-false creation.
Checkbox choices are local next-game settings, captured by the actor before
asynchronous session bootstrap. The POST reads only those captures; changing a
later UI choice cannot change the in-flight create. No options are sent on
open/resume. The readout uses confirmed `chaosMode`, `mirrorMode` and nonzero
`timeLimitSeconds`; client choices never rewrite the current board or clock.
Source review/static checks are not flag-combination or timed save/resume proof.
Deferred cases: eight combinations at difficulties1/5; invalid/busy refusal;
choices changed across bootstrap; ordinary API compatibility; rejected creation;
Java-confirmed differing flags; timed save/resume without time extension.

## Authority and lifecycle constraints

Free-play boards can be read/spectated by an authenticated client knowing their game ID. Competitive `daily-`, `week-` and `duel-` boards are owner-only reads/joins. Mutations on a socket, hints, save and resume are owner restricted. The initial native cabinet accepts only the authenticated player's own board; spectating is out of scope.

The protocol has no request ID, command ID, board revision or generic idempotency contract. Serialize native mutations, do not infer a purchase or undo acknowledgement from unrelated traffic, and use full resync after reconnect, refusal, uncertainty or a REST assist. Never automatically replay an unknown-outcome move, erase, undo/redo or hint purchase. A matching echo is useful evidence, but cannot prove uniqueness across another device making the same move. An unsolicited board can also arrive while undo is pending.

`handleTextMessage` synchronously calls the Java service and game locks. This supports mutation followed by sync on one socket; it is source evidence, not a measured timing/correlation guarantee. Cross-replica and other-device broadcasts still exist.

Server bounds are 64 KiB text frames, 16 KiB binary frames, 20 messages/second per player with burst 40, eight simultaneous sockets/player, and a separate connect budget (burst 10, refill 0.5/s). Chat is capped at 500 characters. The native client should have one active channel, bounded responses/outbound queues, bounded resync/reconnect attempts, deadlines, generation-checked callbacks, cancellation on close and no error/sync feedback loop. Existing Java reconnect policy uses six attempts with 1/2/4/8/16/30-second delays.

## Fixtures and validation evidence

[sudoku-wire-fixtures.json](sudoku-wire-fixtures.json) contains **synthetic authored examples**, not live captures: four full visible boards, a session bootstrap, REST and socket examples, 32 proposed native board-validation cases and lifecycle cases. Their stricter size, integer, secret-field and own-game checks are **native policy**, not new Java rules or claims about what Java rejects. Display-only fixture puzzles are not new source assets.

Run `python docs/java-arcade/verify_sudoku_fixtures.py`. This checks fixture consistency and the declared local native-validation matrix. It does not test the actual C++ adapter, execute Java tests, authenticate, run sockets or prove a deployed service.

[sudoku-source-evidence.json](sudoku-source-evidence.json) pins 23 inspected Java source/test blobs and 11 source assertions. Existing Java tests read include BoardStateTest (serialized output excludes solution/solvedgrid), SessionCsrfBootstrapTest (cookie/header actually satisfy the CSRF filter), WebSocketControllerTest (anonymous/spectator/source-label guards), WebSocketCredentialTest (revocation), SecurityRulesTest (real security profile) and RewardOwnershipTest. They were **not executed** for this contract work.

The current default-head GitHub CI run 38087377620 was reported failed before its jobs started; a fetched annotation confirms the account payment/spending-limit block. This is not evidence of failing Java assertions or a fresh passing service build.

Primary pinned references: [BoardState](https://github.com/RicheyWorks/sudokupro/blob/973c73a35f8659a17022232f0996d4ffb0095997/model/src/main/java/com/xai/sudokupro/model/api/BoardState.java), [game REST controller](https://github.com/RicheyWorks/sudokupro/blob/973c73a35f8659a17022232f0996d4ffb0095997/server/src/main/java/com/xai/sudokupro/controller/SudokuGameController.java), [raw socket controller](https://github.com/RicheyWorks/sudokupro/blob/973c73a35f8659a17022232f0996d4ffb0095997/server/src/main/java/com/xai/sudokupro/controller/WebSocketController.java), [existing client reconciliation](https://github.com/RicheyWorks/sudokupro/blob/973c73a35f8659a17022232f0996d4ffb0095997/client/src/main/java/com/xai/sudokupro/client/GameClient.java).

Unresolved integration acceptance: concrete service address, approved runtime account setup/Daedalus identity mapping, actual native parser/lifecycle tests, Unreal link/load, packaging and live acceptance. Cabinet identity and any future ownership system remain separate from Sudoku authentication and game rules.
