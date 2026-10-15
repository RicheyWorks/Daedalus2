# Java cabinet bounded source package — 2026-10-15

This completes the selected source package in existing [PR152](https://github.com/RicheyWorks/Daedalus2/pull/152).
It does not complete either original application or establish installed/native play.
Owner: pootscoot-desktop-games. Only codex-play-guard operates Unreal.

## Pins and ownership

- Previous PR152 documentation head: `89ece41824b9132403ac0bfffae15343b08b13f8`;
  earlier Blackjack implementation: `4f63c5b04dbac43a625c64741132f61e8719813c`.
- Sudoku mode implementation: `4d5577dc5659a9a26a9130e70cef68c2e5915ece`;
  first documentation checkpoint: `0dff5841862d993d2bbd4a96c884a22d698cf0dc`.
- Additional UI/input/status implementation:
  `c7b3f3e28f759b5408a69ff00f2fde025b3d650b`, two files, +104/-10.
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
| Sudoku undo/redo and navigation | `client/src/main/java/com/xai/sudokupro/ui/BoardView.java:209–235` | Ctrl+Z/Y call existing actor commands; Home/End and Page Up/Down select row/column ends | Existing clamped arrow movement, physical digit keys, local pencil editing and broader accessibility are not full original parity |
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

Independent source review found no blocking defect. Static checks passed 110
body/declaration/dispatch/order invariants with 56 baseline methods unchanged.
The actor and public header are byte-identical to mode commit4d5577dc in the
second increment; protocol and Build.cs remain unchanged from 89ece418. These
are source checks, not compiled/behavioral tests. The first mode checkpoint's
77 checks/61 unchanged methods remain historical evidence of that checkpoint.

No compiler, UHT, behavioral tests, service traffic, credentials, editor, placement
or native gameplay ran. The earlier added reflected mode function requires a
later supported UHT/module build. Historical PR55, Java facade, portable DLL or
Mines/HUD evidence does not transfer to this package.

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

Full original coverage and missing daily/social/puzzle/economy flows, persistence,
plugins, side bets, advice, achievements, themes, characters and audio remain in
[capability-coverage.md](capability-coverage.md). They require their real existing
Java interfaces and owner coordination; this package creates no substitute service,
reward, account provider, wallet or deployment.
