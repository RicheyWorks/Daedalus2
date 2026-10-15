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

## Desktop iteration handoff — 2026-10-15, pootscoot-desktop-games

Glowtrail source9f55ac5f: ONLY PacmanGame in Public/DesktopGames/DaedalusDesktopMazeCore.h;
SHA256 F40BECFF5D1ACDD4ADA87581927E49DD2DB9F96B262C50C45FEC09D2E1C314E9.
Living frightened count/next expiry now reach existing Frame and Status bindings.
Twelve static invariants and source review pass; compiler/tests/runtime deferred.
Accepted R2 combined074c519b targeted HUD/keys remain separate component proof.
No installed/editor/build/asset/map/save action; ingestion retains priority.

Named participants: root ACTIVE; minigame_polish_candidate completed source review,
java_minigame_status completed wiring audit, polished_controller_locator completed
pinned module lookup. Historical helpers were not woken or counted as active.
Source lesson/harness proposal is in existing maze_notes/LESSONS-LEARNED; benefits
ESTIMATED, not measured. No full-team audit completion is inferred.
Controller owner requests32117/32128/32129 and coordinator contract32135 resolved
the reusable web pin39fa/a73a. No new adapter is needed for this feedback; the
unexecuted native Portal substitute proposal was withdrawn32144–32146. Existing
input/save/HUD/Mines/Java regions are unchanged. Native controller binding remains
separate; consume existing held/edge APIs, not a replacement mapping framework.
