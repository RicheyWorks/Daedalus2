# Java cabinet bounded source package — 2026-10-15

This completes the selected source package in existing [PR152](https://github.com/RicheyWorks/Daedalus2/pull/152).
It does not complete either original application or establish installed/native play.
Owner: pootscoot-desktop-games. Only codex-play-guard operates Unreal.

## Local Sudoku editing continuation

Current source `da2b4a84e357114181cbdb65093628d595cda2a7` continues published
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
Mines/HUD evidence does not transfer to this package. Current local-editing source
has the separate 57-check preservation audit described above.

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
   as visible or persistence acceptance.
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
