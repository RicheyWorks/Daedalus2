# Agent handoffs without silent waiting

The broker already delivers long polls immediately. The agents also need to read and act: a successful send, transport pong, terminal watcher or broker receipt does not prove an agent accepted the task. Claude owns the broker, lock API and Unreal integration. Codex owns this additive durable client loop, which works on existing `/log`, `/v1/messages` and `/ack` endpoints without restarting the broker.

Run from `connectors/claude-asset-pipeline`, using a separate state path for each agent:

```powershell
python -m asset_pipeline.live_handoff --me team-codex --state C:/Users/730ri/projects/bot-team/link/sessions/team-codex.json --start-after LAST_HANDLED_ID poll
python -m asset_pipeline.live_handoff --me team-codex --state C:/Users/730ri/projects/bot-team/link/sessions/team-codex.json request --to unreal-team --key ocean-import-001 --ack-within 30 --text "Please accept the Ocean import handoff and name the next action."
python -m asset_pipeline.live_handoff --me unreal-team --state C:/Users/730ri/projects/bot-team/link/sessions/unreal-team.json poll --wait 25
python -m asset_pipeline.live_handoff --me unreal-team --state C:/Users/730ri/projects/bot-team/link/sessions/unreal-team.json respond --id REQUEST_ID --status accepted --text "I own the import; building the current main head first."
```

First use requires an explicit cursor. Use 0 for a complete historical replay or the last message actually handled; never silently initialize at the current tail and discard requests. Poll reads at most 128 log records per call and durably retains up to 256 messages. A full inbox stops cursor advancement before an unretained message. Repeat poll to catch up. New queued requests take priority over accepted work in the compact output.

At every tool/job boundary, poll the inbox. During waits, use the bounded long poll so requests return promptly. Respond `accepted` with the next action, `blocked` with the exact missing input and an alternative action, or `completed` with the commit/proof. Only an explicit agent response creates these states. Ordinary notes and result replies can be marked read with `ack --id ID`, which does not manufacture task acceptance. Requests must use `respond`. `archive-completed` removes locally completed/handled records to free capacity.

Keep one stable request key for uncertain delivery retries. UUID envelopes are saved before sending; the broker deduplicates retries after a lost HTTP response or process restart. Responses also persist their envelope before delivery, and identical retries reuse it. Resuming after a blocked response creates a new event. Completed work cannot move backwards. An OS-backed lock and atomic state replacement prevent competing watcher/respond commands from overwriting a cursor or inbox. The presence of an old `.lock` file alone never means a process is alive.

Human replies sometimes use type `ack` with meaningful text. Those remain visible; only the broker's pure `{id, type}` receipt envelope is hidden from the action inbox. `replay --after ID` rewinds the cursor explicitly while retaining existing work states, then `poll` safely rediscovers messages by ID. Use it for a compatibility repair without editing the state file by hand.

When one next action covers several requests, repeat `--id` on `respond`, for example `respond --id 28937 --id 28957 --status accepted --text "Owning both; build first, then import."` Each request receives its own correlated reply. Mentioning IDs only inside free text cannot update request state. The whole batch is validated and its UUIDs saved before delivery; retry the identical command after an interruption, including partial delivery. Duplicate IDs are collapsed. Acceptance remains an explicit decision by the responding agent.

Operational handoff: poll before starting a job, at every job boundary, and between waits of at most 25 seconds. On a terminal failure, report the actual job ID, failed gate and next owner promptly; on success, attach the job/result path and exact source head. Claim the compute lease before Build.bat or Unreal startup (startup itself runs SDK validation under the global build lock). Release it when the owned process is terminal. A lease or a sentence saying "building" is not evidence that a process is live. While a peer owns compute, continue independent code, tests and documentation.

`status` reports acceptance deadlines and observed acceptance latency. A plain receipt remains overdue when no acceptance arrives. Do not repeatedly resend new copies: inspect the same request, ping the named owner and involve Buffffff once if needed. The local broker trusts its clients' names; logical sender matching is not authentication. This helper does not execute message content, grant an editor lease, wake an idle model or make an idle bot think. Both agents must integrate the poll/respond call into their active tool loop.

The shared `teamlink claim/release/locks` commands remain authoritative for editor and merge leases. Keep branches until all children are merged. For a merge handoff, include PR number, exact head SHA, review scope and current checks; the receiver reports the resulting merge SHA. Distinguish draft state, missing/deleted base, conflict and CI failures from an approval-tool rejection. Address the concrete cause once and continue unblocked work.

Validation: the HTTP harness covers explicit acceptance versus receipt, long-poll wakeup, restart recovery, bounded backlog, uncertain-send deduplication, response retries/resume, logical reply routing and actual CLI round trips. Broker tests remain separate. Passing transport tests does not prove a live Claude response; record the real exchange separately when it occurs.

## Sudoku create-mode source handoff — 2026-10-15

Owner pootscoot-desktop-games, source4d5577dc, existing PR152. Exactly Java actor
public h/private cpp and Java Slate private h/cpp, mode-create/UI regions only.
Original PR152 Blackjack settings/metadata remain preserved; old PR55 worktree and
the unrelated dirty full-link checkout were not changed. Owner reconciliation
32159–32161 and claim32167–32169 precede edits; no competing claim found.
Current root and java_gap_scan completed source review, not a full-team audit.
Existing integration manifest has four before/after pins and the deferred cases.
77 static checks pass,61 existing methods unchanged; new UFUNCTION needs later
UHT/module build. Nothing is installed/native accepted. Preserve accepted184,
Mines, R2 and other owners; no whole-plugin replacement or immediate runtime slot.
Ingestion remains first. Web controller39fa remains reusable for web consumers;
normal Slate controls need no web bridge or duplicate input framework here.

## Java cabinet extended source package — 2026-10-15

Parent's longer-task direction continues existing PR152 rather than creating a
duplicate. Saved mode source4d5577dc/documentation0dff5841, then sourcec7b3f3e2
completed supported original Blackjack keys, Sudoku Open/keyboard confirmation
and status gaps in the same two owned Slate files. Extension claims32190–32192
and saved-source status32201 are recorded; no conflicting Java-client claim was
observed, and no explicit owner clearance response is claimed. Exact four-file
final source pins, full coverage, remaining app gaps and later acceptance are in
docs/java-arcade/blackjack-capabilities.integration.json and
docs/java-arcade/cabinet-source-package.md. Review and 110 static source invariants
pass, 56 baseline methods unchanged; dedicated compiler/tests/native stay deferred.
Preserve the original PR152 Blackjack implementation and current accepted native
source; no whole-plugin overwrite, service traffic, credentials or editor action.
Only the sole operator may later integrate/build/load/accept after ingestion.

## Sudoku local editing source continuation — 2026-10-15

Source da2b4a84 continues the same PR152 from published9fad7509, exactly the two
private Java Slate files +207/-20. Reconciliation32213–32216, claims32218–32220
and saved-source status32227 are recorded; no overlapping claim/interface change
was observed, and no explicit other-owner acceptance is claimed. Local-only
notes, single-path typed/pad entry, wrapping/first-empty selection, 3x3 display
and cosmetic confirmed-board feedback reuse original JavaFX/web implementation.
Actor/public API/transport/guard/protocol/build/persistence remain unchanged.
Current review and57 static source invariants pass (14 unchanged Slate methods),
with no compiler/tests/services/editor/native action. Manifest final source pins
and cabinet-source-package.md record explicit note reset/failure/Blueprint limits,
historical versus current checks, remaining full-app gaps and deferred acceptance.
No note endpoint/cache/durable save, controller bridge, native installation or
runtime slot is created. Preserve accepted native owners; ingestion remains first.

## Java cabinet received-session/recovery source continuation — 2026-10-15

Assignment32249, actual START32308 at20:12:09UTC; source6e287066 continues
existing PR152 published c0cacb26, only private Java Slate h/cpp +207/-8.
Received versus entered identity, local field fill, existing guarded recovery
candidates/bool feedback, and selected-cell answer/clue/note inspection complete
the finite source package. The previous ID row already existed; Sudoku has no
projected revision. Unknown versus definite Blackjack create failure remains an
actor-private decision; fresh Start behavior is preserved. Existing notes/hints/
input, actor/public API/transport/guard/protocol/build/saves/rules stay intact.
Existing java_package_gap_review worker reviewed final source and guard branches:
no blocking defect; three source corrections applied. Manual branch matrix and
four final file pins are in cabinet-source-package.md/manifestv5. Historical
57/14,110/56,77/61 counts are not current behavioral proof; no current suite,
tests/builds/services/credentials/editor/native action. Native focus/layout/typing/
recovery/persistence and full original apps remain open. Only codex-play-guard
may later reconcile/build/load/accept; no operator slot or whole-plugin overwrite.
