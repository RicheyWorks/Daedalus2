# Java cabinet bounded source package — 2026-10-15

This completes the selected source package in existing [PR152](https://github.com/RicheyWorks/Daedalus2/pull/152).
It does not complete either original application or establish installed/native play.
Owner: pootscoot-desktop-games. Only codex-play-guard operates Unreal.

## Current continuation: deliberate Blackjack table reopen

Source `7c4ae40d027bd6e17f80c08661297b28d6571db2` continues published `3c89e767a35bc63f6cc9ae184eb9fa5ad2d14f93` in existing draft PR152.
The gap was independently traced before editing: Java already implements
`GET /v1/blackjack/sessions/{id}`, but the cabinet could only create, refresh a
previously accepted native ID or recover an uncertain create. Local close/configure
forgets that ID and bearer, leaving a still-active Java table unreachable through
the UI. This source package adds the deliberate existing-session path.

The latest parent continuation authorizes the next bounded lane package. Ownership
request32318 and START32320 (2026-10-15 20:35 UTC, minute precision) record the exact
existing four PR152 files. Bounded hub reconciliation found no competing Java
actor/Slate claim; no separate owner-confirmation reply is claimed. No other lane,
backend, shared protocol, HTTP task, controller or editor authority is taken.

| Implemented capability | Actual existing source/interface | Cabinet binding and limit |
|---|---|---|
| Query an existing table | BlackJackPro8a4dccfb `arcade-bridge/.../BridgeServer.java:131–144`, `BridgeService.java:78,124–128` | Additive OpenBlackjackSession reuses existing BlackjackRead/SendHttp. GET only; no create, delete or command replay |
| One eligibility contract | Existing actor auth/mode/task/guard/uncertainty/table state; Java route's canonical lowercase UUID | Pure CanOpenBlackjackSession is used by Open and Slate; preflight refusals cannot reset the table or retained recovery data |
| Stable query identity | Existing guard generation/ticket, ApplyBlackjack and atomic visible snapshot commit | Private RequestedBlackjackId is captured before read, checked before acceptance and shared across initial GET/refresh/retry/create reconciliation. It never becomes a reflected accepted ID merely by being entered |
| Deliberate capture/reopen controls | Existing editable field, local-user focus and guarded Button path | Entered table ID, local Use received ID fill and Reopen table attempt feedback. No custom clipboard, durable history or automatic reopening |
| Unavailable session handling | Existing validated NOT_FOUND/SESSION_CLOSED error path | Also handles requested-only targets; no fake received snapshot, result, bankroll or reward |

First retained source checkpoint: `dfca418e216e961b62f48a87c5eb62d7b2ba9bc9`.
Final `7c4ae40d` explicitly compares the captured target with case sensitivity.
Four existing actor/Slate files change; exact diff and pins are in manifestv6.
The public additions require the sole operator's later supported UHT/module build.
Shared protocol/SessionGuard, HTTP worker/limits/redirect policy, game rules,
original Java source, existing saves and keyboard dispatch are preserved.

After preflight passes, Open resets the inactive view before dispatch. If local
dispatch itself cannot start, it returns false with no received table; it does
not restore that earlier inactive display. A true return means the read was
requested locally, not that Java accepted the ID or returned a table.

This closes a source binding gap, with unmeasured product impact: a player who
records a received ID can request the same still-active table after reconfiguring
the local bearer. It is not durable desktop round resume, provider/account mapping
or per-player isolation. Java's shared launch bearer authorizes all process-local
sessions. GET refreshes idle activity but not the absolute lifetime. Closed,
expired and service-restart-lost tables remain unavailable; no gameplay state is
stored by this addition. Create, uncertain-create recovery and Open stay distinct.

Independent source review and the packet audit are recorded in manifestv6.
Current evidence is manual branch review, exact source pins and `git diff --check`.
No counted text suite, tests, build, UHT, service traffic, credentials, editor or
runtime action ran. There is no measured performance or native-play improvement.

### Manual reopen branch review and deferred acceptance

These rows describe inspected source, **not executed behavior/native tests**.

| Branch / combination | Source result | Deferred acceptance |
|---|---|---|
| Canonical ID and local prerequisites | CanOpenBlackjackSession shares the exact actor/UI gate: current Blackjack mode, configured token, valid loopback origin and canonical lowercase UUID. Empty/short/long/uppercase/whitespace/slash/non-ASCII values fail before reset. | Exercise valid/invalid IDs, origin, credentials and mode. Verify preflight refusal leaves model/recovery data untouched; a later local-dispatch failure may clear the inactive view. |
| Pending HTTP or guard work | Both private task presence and Guard.PendingKind must be clear. A timed-out canceled task that has not finished still blocks Open. | Delay worker completion/callbacks; no concurrent request, reset or lost recovery context. |
| Unknown create or uncertain mutation | Open rejects bUnknownBlackjackCreate and Guard.HasUncertainOutcome before any reset. Retained create request/body and current mutation identity remain available to existing recovery. | Lose create/command/close replies; Open cannot bypass reconciliation or cause a new mutation. |
| Existing live received table | Open refuses even the same entered ID while a nonclosed received table exists. Use existing Refresh while attached. End closes the table; existing local-close/configuration detachment remains possible and does not end it remotely. | Try same/different IDs in all live phases, including unknown command outcome; Open must not abandon the attached table or bypass its revision floor. |
| Local cabinet close and reconfiguration | Close still forgets bearer/received/target state. Reopening needs configuration again and a previously recorded ID. No automatic retained-session provider or durable save was added. | Record ID, close, configure, reopen before expiry; verify no credentials or session history persisted. |
| Accepted local Open, pending response and edited field | Open begins a new guard generation/read, captures RequestedBlackjackId and resets the accepted view. Editable text and local attempt feedback never publish identity or retarget the captured request. | Delay the reply and edit the field; accepted received ID must be the captured target only. |
| Successful visible snapshot | ApplyBlackjack checks requested and existing accepted IDs plus monotone revision, full visible DTO and secrecy before atomic model/View commit. Initial Open starts without another table's revision floor. Gameplay waits for Guard.Snapshot. | Compare full current snapshot/revision/legal actions with Java; initial lower revision of a different permitted table is accepted only after explicit Open. |
| Wrong identity, malformed or secret-bearing reply | Existing envelope/visible DTO/secrecy validation plus captured ID rejects the reply before publishing a received table. No gameplay, result or credit change is inferred. | Inject wrong ID, missing/invalid fields, hidden dealer/future shoe fields and invalid revision; confirm no partial commit. |
| Timeout and bounded safe retries | Initial Open, explicit refresh, create reconciliation and CoreTick retries share ReadBlackjackSnapshot. It uses the private captured target (accepted-ID fallback), existing read budget and ticket generation; field edits cannot change it. | Exercise both existing retries, exhaustion, late completion and explicit later retry; count GET only, no command replay. |
| Closed/expired/not-found reply | Only the existing validated 409 SESSION_CLOSED or 404 NOT_FOUND envelope marks unavailable. A requested-only target qualifies for this path, but View.SessionId stays empty and no final result is fabricated. | Check valid versus malformed error bodies, Java closure/expiry/restart and explicit later Start/Open decisions. |
| Authorization, redirect and other failures | Existing permanent authorization/redirect handling and bounded transient read retry remain unchanged. Failed Open keeps private target for safe read recovery, but no received identity; explicit Open can retry after safe work ends. | Check 401/403, redirects, 5xx, connection loss and malformed success; reconfigure via existing cancellation path when required. |
| Fresh create and explicit create recovery | Fresh Start clears captured target; successful Apply binds the created ID before existing follow-up read. Exact request-ID create recovery and revision checks remain. Open never generates a request ID or sends POST/DELETE. | Open/fail then fresh Start; close then Start; uncertain-create replay followed by read; no stale target or fabricated fresh session. |
| Cancel/configure/mode change and stale callbacks | CancelTransport clears target with existing guard generation/secrets policy. Old callback tickets fail Guard.Current. Fresh Open resets accepted state only after eligibility passes. | Cancel/close/reconfigure/change mode with pending and completed tasks; no old table can revive. |
| Use received ID and keyboard focus | Ready nonbusy received table can fill its ID locally and focus the opening user's field. No network, custom clipboard, note/hint reset or automatic Open. Existing direct-board shortcut handlers are unchanged. | Verify local fill, standard field selection/copy/typing, focused buttons, modifiers/repeats/controllers/other user and close restoration. |

## Historical continuation: received session identity and recovery

Source `6e28706693319c53170dda3d545c12f8cf5f95c7` continues published head `c0cacb261a960ea71de239f644be4db4f91310fb` in the same draft PR152.
Exactly the two private Java Slate files change (+207/-8). Assignment32249 and
START32308 (2026-10-15 20:12:09 UTC) bound this work. The actor/public API,
protocol, Build.cs, original games, transport, saves and rules remain unchanged.
The previous cabinet already displayed a received game ID; this package clarifies
that row and separates it from requested input rather than claiming it was absent.

| Completed source deliverable | Existing interface reused | Source boundary |
|---|---|---|
| Received identity and entered-ID workspace | `State.SessionId`, `Cells/Givens`, `GetState`, existing editable ID field | Current/last received ID is separate from text; entered equality is not acceptance. Only Blackjack displays received Revision; Sudoku has no projected board version |
| Deliberate Use current ID | Existing ready owned Sudoku state and `SEditableTextBox::SetText`; local-user `SetUserFocus` | Field fill only, no request/clipboard/reset. Requires ready, nonbusy, nonsync, owner and complete received board |
| Refresh and create recovery | Existing `RefreshSnapshot` and `RetryBlackjackCreate` | Public predicates are candidates; actor private request/guard state decides. Bool true means locally requested, not receipt or success. No new endpoint or mutation replay |
| Start/Open/Resume attempt feedback | Existing `StartSudokuGameWithModes`, `OpenSudokuGame`, `ResumeSudokuGame`, `StartBlackjackSession` | Captures entered ID before request; preserves prior note/hint reset semantics and supported Blackjack Start after definite create refusal |
| Selected-cell inspection | Received `Cells/Givens`, existing `CanEnterSudokuDigit`, `PencilMask` and pending hint identity | Answers/clues and native entry availability are distinct from local pencil edits. Received notes, local overrides, explicit zero and hidden marks are labelled truthfully |
| Shared state-derived guidance | Existing busy, Ready, NeedsSync, owner, remote-closed, solved/time-up and phase fields | Describes current recovery choices without inventing a server state, wallet, conflict receipt or persistent session history |

Independent review by the existing `java_package_gap_review` worker found no
blocking source defect. It read actor private guard branches and the public state
contract, and verified corrections preserving fresh Blackjack Start after definite
refusal, game-specific identity guidance and separation of received answers from
local notes. The installed UE5.8 header supports the focus call; this is source
evidence only. `git diff --check` passes. No new regex-count suite, tests, build,
UHT, services, credentials, editor or native action ran. Earlier 57/14, 110/56 and
77/61 counts below are historical checkpoints, not current behavioral evidence.

### Manual source branch review and later acceptance matrix

Every row below was manually reviewed in source; **none was executed as a
behavioral/native test**. Public enabled state cannot expose every actor-private
in-flight/recovery condition. Retained requested Sudoku IDs may also exist while
the displayed received ID is empty. Source inspection cannot prove timing,
rendered layout, actual focus, typing, network recovery or persistence.

| Branch / combination | Manually reviewed source result | Deferred acceptance |
|---|---|---|
| No credentials / no received ID | Account guidance; refresh/recovery/start candidates disabled. Entered ID cannot imply receipt. | Configure then connect using approved disposable credentials; no credentials exercised here. |
| Configured but no received board/table | Game-specific New/Open/Resume or Start guidance. Incomplete Sudoku shape does not become accepted identity. | Observe bootstrap and transport refusal without fabricated received ID. |
| Busy with known or unknown ID | Wait guidance; action candidates disabled. Known identity is last received, not a new receipt. | Delay callbacks and verify no duplicate operation or changed input target. |
| Ready owned complete Sudoku; entered ID differs or matches | Received ID and entered text remain separate. Matching text only reports equality. Use current ID requires ready/nonbusy/nonsync/owner/81-cell shape. | Check both text cases and absence of automatic Open/Resume. |
| Use current ID | Only SetText, local feedback and local-user field focus; no actor request, clipboard, note reset or hint reset. | Inspect field focus, keyboard typing and unchanged notes/selection/hint after fill. |
| Empty / over-256-character ID; otherwise actor-refused Open/Resume | UI length gate refuses empty/oversize. Actor remains final authority for private work/guard state. No accepted identity is inferred from editable text. | Check boundaries and actor false result; no remote side effect or note reset on local refusal. |
| Accepted local New/Open/Resume then delayed success or failure | Exact entered ID captured for local-attempt feedback. Accepted call resets presentation as before; later failure cannot restore prior notes or claim board acceptance. Hint target clears on entry attempt as before. | Check same/different IDs, later failure, and field edits while pending. Notes reset at local acceptance, not successful receipt. |
| NeedsSync with known ID; hidden HTTP/request still active | Refresh candidate follows current public identity/owner/credential/closed gates. RefreshSnapshot may still return false for private pending work. True feedback says requested only. | Exercise actor refusal and delayed acceptance; preserve notes and pending hint target. |
| Blackjack NeedsSync with empty ID | Recover is a candidate only. Unknown create with retained request may retry; definite create refusal can share this public shape and refuse recovery. Fresh Start keeps the previous supported gate; actor blocks unknown creates. | Exercise both private branches, recover true/false and fresh Start after definite 4xx; no automatic mutation replay. |
| Closed or expired Blackjack table | RemoteClosed disables refresh/recovery and permits existing Start candidate; status stays visible. Closed guard/private state can still refuse an attempted action. | Verify remote close/expiry and fresh Start through the existing actor. |
| Wrong Sudoku owner / selected-mode mismatch | Wrong owner disables refresh/fill/entry. Mode mismatch disables new common actions and Save gate, and suppresses mismatched local feedback. Actor APIs remain final. | Exercise local selection/state mismatch and wrong-owner reply; no stale action reaches another game. |
| Selected clue / empty cell / filled answer / unavailable entry | Inspection uses received Cells/Givens plus existing CanEnterSudokuDigit. Pencil/answer mode and gated states are described without changing legality. | Compare inspection with actor-enabled entry in ready, busy, solved, time-up and disconnected states. |
| Local override / received snapshot notes / zero / hidden notes | Received answer is independent of note origin. Local edits and received masks are labelled separately; explicit zero stays none; notes behind filled answers remain retained and described as hidden. | Check same-ID refresh/undo/refusal and all existing note reset boundaries. |
| Hint pending / direct board focus / forms/buttons | Refresh, recovery and local fill do not reset hint/selection/notes. Existing key handlers and direct-board/user gates remain unchanged; fill deliberately focuses the ID field for the owning Slate user. | Check H/Cancel/Buy identity lifecycle, direct keys versus typed text, another local user, repeats/modifiers/controllers and close cleanup. |
| Revision and feedback freshness | Only Blackjack displays the received Revision. Sudoku default zero is not a server version. Last local action remains an attempt record, separate from received status/identity. | Confirm layout and wording during all asynchronous transitions; no successful receipt inferred from queued action. |

## Historical local Sudoku editing continuation

Historical source `da2b4a84e357114181cbdb65093628d595cda2a7` continues published
head `9fad7509b5e317807f2627d06807e6a8a1b73a2a` in the same draft PR. Exactly
the two existing private Slate files change (+207/-20). The actor, reflected
public API, protocol, Build.cs, saves, clock and all Blackjack rules/commands are
byte-identical to that baseline. Reconciliation32213–32216 and claims32218–32220
preceded edits. No conflicting Java-client claim or interface change was observed;
no explicit owner acceptance is claimed. Saved-source status:32227.

| Completed source deliverable | Existing pinned Sudoku implementation | Native binding and limit |
|---|---|---|
| Shared digit/erase entry | `client/src/main/java/com/xai/sudokupro/ui/BoardView.java:260–324` | Pad, typed characters and Backspace/Delete share `EnterSudokuDigit`; existing bCanAct/clue/digit gates remain; only an answer change calls existing SubmitSudokuMove |
| Pencil mode and retention | `BoardView.java:83–90,286–310,440–445`; `BoardCell.java:78–87` | N/Space/checkbox toggles view-local marks on empty cells; answers hide notes; same-ID snapshots retain them; erase clears notes before equal-value early return |
| Existing snapshot marks | Previous native `State.PencilMasks` display | Untouched cells still read snapshot masks. Local toggle/erase establishes a per-cell override, including zero, so later snapshots cannot resurrect an erased note. This is an explicit native compatibility adaptation |
| Notes presentation | `client/src/main/java/com/xai/sudokupro/ui/BoardCell.java:46–87` | Nine fixed note positions, bold clues, row/column/value/note tooltips; actual layout/accessibility acceptance remains open |
| Keyboard and selection | `BoardView.java:182–249` | First empty selection, wrapping arrows, existing end keys; ASCII typed digits allow layouts needing Shift; Sudoku physical-digit dispatch is removed to avoid a second submission. Blackjack physical shortcuts stay unchanged |
| Board feedback | `BoardView.java:637–680`; `server/src/main/resources/static/play/app.js:910–932,1155–1168` | Confirmed filled count, remaining-digit counts and duplicate/selected/same-digit/peer/clue colors. Counts and duplicates are display-only; they never decide legality, completion or rewards. Native server-conflict metadata is still absent |

Notes are not saved or sent to Java. An **accepted local** New/Open/Resume
request clears them immediately, even when the later authentication/read fails;
successful account configuration and widget close also clear them. A locally
refused request/invalid Configure leaves the active note context intact. The
context binds only to a nonempty accepted SessionId with 81 cells/givens, never
the requested text ID or a partial bootstrap. A transient empty view does not
seed notes. Direct external Blueprint calls are unchanged; an externally changed
accepted ID resets the context, but same-ID external reentry has no new reset
notification. This package adds no cross-game cache or durable-note contract.

Source review found no blocking defect. The added input/grid/tick APIs were read
in installed UE5.8 headers. 57 static source checks pass; 14 existing Slate method
bodies, including Blackjack dispatch/settings and hint confirmation, are unchanged.
No compiler, behavioral tests, service, editor or native operation ran. Earlier
110/56 and 77/61 results below remain historical source checkpoints.

## Pins and ownership

- Previous PR152 documentation head: `89ece41824b9132403ac0bfffae15343b08b13f8`;
  earlier Blackjack implementation: `4f63c5b04dbac43a625c64741132f61e8719813c`.
- Sudoku mode implementation: `4d5577dc5659a9a26a9130e70cef68c2e5915ece`;
  first documentation checkpoint: `0dff5841862d993d2bbd4a96c884a22d698cf0dc`.
- Additional UI/input/status implementation:
  `c7b3f3e28f759b5408a69ff00f2fde025b3d650b`, two files, +104/-10.
- Local editing implementation: `da2b4a84e357114181cbdb65093628d595cda2a7`;
  preceding package head `9fad7509b5e317807f2627d06807e6a8a1b73a2a`.
- Overall new runtime diff from 89ece418 touches only
  `Public/DaedalusJavaArcade.h`, `Private/DaedalusJavaArcade.cpp`,
  `Private/SDaedalusJavaArcade.h` and `Private/SDaedalusJavaArcade.cpp`, under
  `engines/unreal/DaedalusLink/Source/DaedalusLink/`.
- Reconciliation requests 32159–32161, initial claims 32167–32169 and extension
  claims 32190–32192 were sent. No conflicting Java-client claim was observed;
  no explicit other-owner acceptance is claimed. Existing PR55 and the separate
  dirty full-link checkout remain untouched. No desktop, Mines, Hero, HUD,
  controller/settings module, backend, protocol or transport ownership is taken.

Exact final SHA256/blob pins are in
[blackjack-capabilities.integration.json](blackjack-capabilities.integration.json).
Prior PR152 Blackjack additions are not established installed. The later operator
must reconcile the full PR against its current accepted source, preserving newer
owners; these files are not a whole-plugin replacement or rollback instruction.

## Existing implementation to cabinet binding

| Capability | Existing source interface | Binding in this package | Remaining boundary |
|---|---|---|---|
| Sudoku Chaos, Mirror, Time Attack | Sudoku973c73a3 `SudokuGameController:65–81`, `ServerApi:147–154`, `GameService:288–308` | Additive `StartSudokuGameWithModes`; three next-game checkboxes; captures before async bootstrap; current modes from accepted snapshot | No recommended-difficulty fetch; no rule/clock rewrite |
| Open existing owned board | Same source `ServerApi.getGame`, native `OpenSudokuGame` | Explicit ID Open button beside existing Resume | Saved-game list and authoritative End remain absent |
| Sudoku undo/redo and navigation | `client/src/main/java/com/xai/sudokupro/ui/BoardView.java:182–249` | Ctrl+Z/Y call existing actor commands; wrapped arrows, end keys and typed digits; local pencil entry above | Physical-controller and broader accessibility/native behavior remain unverified |
| Keyboard hint confirmation | `BoardView.java:342–345,477–503` | H shows Buy/Cancel, bound to the current game ID; confirm clears target and rechecks canAct; New/Open/Resume/Configure clear the prompt | Uses original unknown-price fallback; wallet/price fetch absent. Explicit labeled Hint button still purchases directly |
| Blackjack action/chip keys | Blackjack8a4dccfb `swing/.../ui/swing/TableKeys.java:30–60`, `gdx-core/.../gdx/TableKeys.java:28–53`, `TableScreen.java:1168–1188` | Existing `IsBlackjackActionLegal` / `SubmitBlackjackAction`; consumed disabled keys; I additionally checks insuranceAcceptAllowed | B/21+3 has no facade command. M/menu remains unbound; Escape retains cabinet close |
| Service and local status | Existing reflected state and actor GetState | Status/message/hints stay visible when local Configure validation fails; confirmed Sudoku hintCount shown | No new HTTP errors parsed or successful receipt inferred |
| Insurance decision wording | Blackjack `core/.../engine/TableLabels.java:105–108` | Confirmed INSURANCE phase plus first-hand blackjack flag selects prompt | No premium/payout calculation; Java owns decisions |

Blackjack keys: Enter deal; R rebet; H hit; S stand; D double; P split;
U surrender; C clear; I accept insurance/even money; N decline; 1–5 or numpad
bet 1/5/25/100/500; L reload (GDX). Only the opening user's directly focused
board/table dispatches shortcuts. Text fields/buttons keep their own events;
repeats, controller events, Alt/Command and Blackjack Ctrl/Shift are excluded.
No web controller is copied: verified `daedalus-pad/1` is a web consumer contract,
not a native Slate transport.

## Source evidence and deferred acceptance

The preceding c7b3f3e2 source review found no blocking defect. Its static checks passed 110
body/declaration/dispatch/order invariants with 56 baseline methods unchanged.
The actor and public header are byte-identical to mode commit4d5577dc in the
second increment; protocol and Build.cs remain unchanged from 89ece418. These
are source checks, not compiled/behavioral tests. The first mode checkpoint's
77 checks/61 unchanged methods remain historical evidence of that checkpoint.

No compiler, UHT, behavioral tests, service traffic, credentials, editor, placement
or native gameplay ran. The earlier added reflected mode function requires a
later supported UHT/module build. Historical PR55, Java facade, portable DLL or
Mines/HUD evidence does not transfer to this package. Historical local-editing source
had the separate 57-check preservation audit described above; current recovery
evidence is the manual review matrix, with no new behavioral suite.

At a later separately authorized validation/intake slot, use the existing harness
and approved disposable Java services. Do not reserve a slot ahead of ingestion.

1. Reconcile all four PR152 files with the accepted native baseline and companion
   PR62 adoption. Preserve current desktop/Mines/R2 and other app owners. Perform
   the sole operator's supported generated-code/module build/load route.
2. Check eight Sudoku mode combinations, difficulty bounds, ordinary API defaults,
   refused/busy requests, choices during bootstrap and canceled/replaced callbacks.
   Compare accepted flags and clock with Java, then timed save/resume without
   extending time. Open/Resume must keep the entered ID and owner enforcement.
3. Check text-box typing, focused buttons, another local user, repeats, modifiers
   and controller events. Confirm only direct board/table keys submit one command;
   recognized illegal Blackjack actions submit none. Exercise I with unavailable
   insurance acceptance, N decline and both chip key groups.
4. H must only show confirmation; Cancel sends nothing; Buy sends one existing
   request to the same current game. New/Open/Resume/Configure and closed/expired
   boards must not reuse an old prompt. Check Ctrl+Z/Y and selection end keys.
5. Fail Configure while an existing session is active, then refresh/disconnect it:
   actor status/message and hints must remain visible beside validation text.
   Compare hintCount, insurance prompt, rules, shoe, hands, outcomes and stats with
   the same authoritative snapshot. Verify no hidden dealer/future-shoe data.
6. Record actual viewport readability/layering, local-player focus, close/EndPlay,
   save/recovery behavior and exact installed source. No source-only result counts
   as visible or persistence acceptance. Include the current manual matrix above
   for received/entered IDs, local fill, hidden recovery refusals and cell inspection.
7. For local editing, toggle each note twice; erase notes-only cells without a move;
   preserve notes behind answers and after refused entries/undo/redo/same-ID
   snapshots; ensure an explicit zero override cannot fall back to old snapshot
   notes. Verify untouched snapshot marks still update. Confirm new IDs and accepted
   UI entries/configuration clear context, including same-ID/failed remote entry.
8. Type digits using number row, numpad and a Shift-digit layout: exactly one entry
   per character, none in text fields/from other users/repeats/modifiers. Check
   N/Space/checkbox, initial first-empty/full-board fallback, arrow wrapping and
   notes-only erase in solved/expired/disconnected states (no changes allowed).
   Compare colors/counts with confirmed values and measure actual notes readability;
   no local duplicate/count may prevent a Java move or infer completion.

Full original coverage and missing daily/social/puzzle/economy flows, persistence,
plugins, side bets, advice, achievements, themes, characters and audio remain in
[capability-coverage.md](capability-coverage.md). They require their real existing
Java interfaces and owner coordination; this package creates no substitute service,
reward, account provider, wallet or deployment.
