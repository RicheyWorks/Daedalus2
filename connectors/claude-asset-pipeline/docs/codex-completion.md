# Codex completion observer

This helper consumes retained results from supported Codex tools and sends
correlated terminal notifications through the existing TeamLink. It never
assigns work, changes ownership, launches a worker, or declares native success.

## Actual collector boundary

The available mcp__codex_app__wait_threads and read_thread tools observe real
Codex task/turn state. They are tools available to the calling assistant, not
runtime Python APIs. An authorized tool-calling coordinator must collect
results, retain the envelope below, and invoke this helper. There is no
autonomous collector or guaranteed parent push in this package.

Official Codex documentation describes
[notify](https://learn.chatgpt.com/docs/config-file/config-advanced#notifications)
with agent-turn-complete and
[app-server turn events](https://learn.chatgpt.com/docs/app-server).
Those are distinct integration surfaces. This host already has a computer-use
notification hook; this change does not replace it, attach to a private app
connection, or configure a new event subscriber.

Retain the exact request and full raw MCP result from an actual tool call:

~~~json
{
  "schema": "daedalus.codex-tool-observation.v1",
  "tool": "mcp__codex_app__wait_threads",
  "request": {"targets": [{"threadId": "ACTUAL_TASK_ID"}], "timeoutMs": 0},
  "observed_at_utc": "ACTUAL_UTC_AFTER_CALL",
  "result": {"content": [{"type": "text", "text": "EXACT_TOOL_JSON"}], "isError": false}
}
~~~

The raw-file SHA256 binds local provenance; it is not an OpenAI signature or
authentication of a hand-authored file. Only a trusted collector should supply
observations. Keep raw results outside version control: read_thread may contain
private prose and command text. Notifications include IDs/status/hashes only.

The parser consumes the observed schemaVersion1 tool shapes: wait polls with
thread.status and latestTurn, or newest-first read turns. A wake, completed tool
marker, final-looking text, popup, timedOut:false, or presence heartbeat alone
is never completion. Explicit completed/failed/interrupted turn status plus a
valid terminal timestamp is required. Interrupted maps to cancelled; unknown
or contradictory evidence cannot authorize another job.

## Use and coordinator acceptance

Run from connectors/claude-asset-pipeline, with standard-library Python3.10+:

~~~text
python harness/codex_completion_test.py
python -m asset_pipeline.codex_completion observe --state PRIVATE_STATE --snapshot RAW.json --task TASK_ID --turn ASSIGNED_TURN_ID
python -m asset_pipeline.codex_completion deliver --state PRIVATE_STATE --snapshot FRESH_CURRENT.json --key EVENT_KEY
python -m asset_pipeline.codex_completion status --state PRIVATE_STATE --snapshot FRESH_CURRENT.json --key EVENT_KEY
~~~

Historical terminal observations can be recorded after reconnect. For a missed
older turn, collect read_thread history containing that exact assigned turn and
use --turn; a newer running turn remains busy. Delivery/status require a current
observation at most60 seconds old. Before any separately authorized next
assignment, collect again: a saved eligibility result is not a lease, an atomic
allocation, or proof that no newer turn began afterward.

Destination is the authorized pootscoot-coordination TeamLink coordinator.
The observer sends codex.turn.terminal from codex-completion-observer, using
the stable SHA256 of taskID+turnID as body.event_key.

1. /send success proves server delivery only.
2. Existing broker ack proves transport handling, not semantic START or DONE.
3. The coordinator explicitly sends codex.completion.ack back to
   codex-completion-observer, with:

~~~json
{"event_key":"KEY","task_id":"TASK_ID","turn_id":"TURN_ID",
 "notification_id":123,"decision":"received"}
~~~

The observer reads that correlated message back from the durable hub log and
retains its ID. Only semantic acceptance plus a fresh idle snapshot of the same
successful turn sets may_offer_next_task. Failed/cancelled/unknown outcomes need
operator review. Nothing actually dispatches work.

## Durability, replay and uncertainty

Receipts use fsynced temporary bytes and atomic create-new hard links, with no
overwrite fallback. Unsupported filesystems fail closed. This is not a claim of
Windows directory power-loss durability. Treat a post-publication exception as
uncertain and inspect retained records.

The state directory keeps event, send-intent, delivery and acknowledgment records.
A durable intent precedes sending. Replays use existing delivery records; after
a lost response, bounded log catch-up matches the exact sender/destination/type
and body before recording delivery. If no matching message is found, delivery
remains uncertain with no automatic resend. The running broker's UID idempotency
is not assumed. Keep this state directory across reconnects.

JSON input/record limit is1MiB; log catch-up is at most10 pages of200 messages.
Exhausting that bound requires reconciliation. Concurrent consumers race on
exclusive intent publication; only the winner sends. Do not delete intents to
force a retry. The local hub is the existing trusted coordination boundary, not
cryptographic sender authentication.

Generic team check-ins must likewise distinguish delivery, broker ACK, explicit
semantic START/checkpoint/DONE and newer active work. Plain check-in prose is not
parsed as an executable state transition. This package does not install Claude
reminders or reassign ownership; coordinator check-in handling remains with its
existing owner.

## Unified worker status and finite local listener

The additive worker_status module composes Team Codex's actual PR172 reducer,
source SHA25687421d4813b3b51cae02b8f8e55e0daf15e097249efbc4c1094142ccdff0846a.
It neither copies that parser nor changes the broker. Until PR172 is integrated,
provide its exact source using --checkins-module; a missing/different pin fails
before import. The verified bytes are executed directly. This dependency is
source composition, not an assertion that PR172 is installed or merged.

Register a retained real coordinator assignment, then supply retained hub
snapshots or use the existing local /wait route. For example, from the package:

~~~powershell
python -B -m asset_pipeline.worker_status --state PATH_TO_OWN_STATE --checkins-module PATH_TO_PR172_TEAM_CHECKINS --assignment ACTUAL_ASSIGNMENT_JSON --start-deadline EXPLICIT_UTC --listen-seconds 10 --wait-seconds 5 --max-waits 3 --notify
~~~

Optional --snapshot accepts {observed_at_utc, messages}; --codex TASK=PATH accepts
up to32 actual supported-tool envelopes described above. These are explicit
caller inputs, never an invented Python MCP API. No autonomous Codex collector
or authoritative Claude session-status API is available in this integration.
An authorized tool caller must refresh Codex observations; after60 seconds their
current status becomes unknown/stale. The listener cannot wake the parent/model.

Claude uses the exact assigned broker route and PR172's qualified status reports.
PROGRESS requires START. BLOCKED/COMPLETED/FAILED/CANCELLED can be retained when
START was missed, with acceptance_missing:true and semantic_start:false. A real
blocker must not disappear because acceptance was absent. These are owner reports,
not proof of a Claude session terminal event, authenticated account ownership or
completed tests. Include explicit body.reported_at_utc ending Z or +00:00 and
body.session_id. Offsetless broker ts, presence, unknown aliases, free prose and
transport ACK cannot provide freshness or semantic START. Missing report time
produces unknown freshness; reports expire after the assignment checkpoint
interval (default900 seconds). Newer assignments suppress old completed status;
register a new explicit assignment in a separate state directory, or opt into
--follow-assignments for tracking-only adoption of actual newer coordinator
assignments to the SAME known worker. This archives the old metadata, resets its
witness and uses the normal reducer on the new actual assignment; it sends no
job, changes no ownership and never follows aliases or worker self-assignment.
The original bootstrap assignment remains the restart identity. New tracked
assignments get an observer checkpoint deadline one checkpoint interval after
capture; this is not an invented worker promise. Failed/cancelled outcomes and
missing START require coordinator review; no self-report authorizes next work.
Session metadata must be an identifier, never a session URL, prompt or transcript.
Cloud hook support does not establish an installed hook: the actual configured
MCP server/tool, runtime hook/session IDs and delivered event must be verified by
the Claude owner before using that path. No hook configuration is written here.
UserPromptSubmit means turn started; Stop alone is response-ended/outcome unknown,
and SessionEnd is not successful task completion. These are not normalized into
qualified job completion by this self-report adapter.

Rows report working/finished/blocked/unknown, freshness, reason, task/session/turn,
source SHA and source authority. may_assign is always false. Acknowledgment does
not refresh status. Current status must be reconciled again before dispatch.

The finite listener allows up to28800 requested seconds (8hours)/12000 waits, each wait at
most25 seconds plus the existing client's bounded HTTP timeout. It catches up
all log routes before and after waits so a newer coordinator assignment cannot
be hidden by recipient filtering. Existing /wait also updates broker presence;
presence is never used as work-state evidence. No ACK, registration, heartbeat,
ownership transfer, process inspection or worker dispatch is performed.
Disconnects produce unknown status and bounded1/2/4/8-second reconnect backoff.
Files, messages and retained state are bounded; overflow stops for reconciliation.
Do not remove a stale writer.lock without checking the previous owner/operation.
An overnight invocation can explicitly request --listen-seconds 28800
--wait-seconds 25 --max-waits 1200 --follow-assignments --notify. Start it only
after the prior same-state instance has actually exited and released writer.lock.
This is one ordinary bounded process, not an OS service, autostart entry or
indefinite guarantee. The existing 1MiB state/catch-up bounds may stop it earlier.

Only completion, blocker or stale/disconnect/checkpoint decisions enter the
durable outbox. Identical working updates generate no notification. Stable task,
session/turn and semantic-message identities deduplicate replay and refreshed
observations; no broker UID guarantee is assumed. Queue delivery uses the same
immutable send-intent/reconciliation path as Codex completion above. Retained
history is not a new assignment and does not imply current availability.

New notices have type worker.status.actionable. A coordinator may separately
acknowledge with type worker.status.ack and body containing event_key, owner,
task_id, session_id, notification_id and decision: received, all matching the
notice. Broker transport ACK is recorded separately. --ack-key EVENT_KEY reads
both proofs; --notify is required to send, and retries of uncertain send intents
remain disabled. The listener queues requests for human/coordinator decisions;
it does not send reminders to workers or issue unchanged model pings.

For the composed focused suite, set DAEDALUS_CHECKINS_SOURCE to the same pinned
PR172 source and run python -B harness/codex_completion_test.py. These synthetic
checks use temporary files/fake TeamLink; live acceptance and timings must be
reported separately. No token or performance savings are inferred from design.

## Verification checkpoint

On16 October2026, the focused suite passed31 tests in0.294 seconds. A real
supported-tool observation was consumed through the CLI and delivered as local
TeamLink notification32840; transport ACK32842 and separately authored coordinator
semantic ACK32843 were read back and retained. Replaying delivery returned the
original message ID without resending. A fresh supported snapshot showed a newer
turn in progress, and next-task eligibility remained false despite both ACKs.
Raw tool results and local acceptance receipts are retained outside the repository.
This verifies the assisted tool-caller/consumer/coordinator path, not an autonomous
collector, parent wake-up service, or overnight scheduler.

## Bounded reported-status profiles (source successor to PR171)

`--profiles COORDINATOR_OWNED_JSON` adds 1..32 explicit owner profiles. The original
`--assignment` CLI and `Status` implementation remain available. Profile mode
composes the same frozen PR172 reducer and PR171 observer/delivery implementation;
it adds no daemon, new polling loop, collector, model wake or assignment service.
This source change does not adopt or restart any running watcher or use its state.

The coordinator must author the profile file and retain each actual assignment.
One active profile per owner prevents ambiguous aliases; assignment IDs may be
shared by different owners because all durable scopes include owner/provider and
the bootstrap assignment/request. Merely naming pootscoot, codex-play-guard,
buckwild-sol, team-codex or unreal-team grants no route, task identity or send
permission. Hub reports never supply file paths, add profiles or choose recipients.
The fixed report route is that configured owner to pootscoot-coordination. The
assignment must be an actual retained coordinator-to-owner ping/task.assign with
structured assignment_id and request_id; broker route labels are not authentication.

Synthetic format illustration only; substitute retained real records and supported
tool output before any separately authorized use:

~~~json
{
  "schema": "daedalus.worker-status-profiles.v1",
  "coordinator": "pootscoot-coordination",
  "profiles": [
    {
      "owner": "example-owner",
      "provider": "codex",
      "assignment": {
        "id": 10,
        "from": "pootscoot-coordination",
        "to": "example-owner",
        "type": "task.assign",
        "body": {"assignment_id": "example-job", "request_id": "example-request"}
      },
      "start_deadline": "2026-10-16T12:00:00Z",
      "checkpoint_seconds": 900,
      "follow_assignments": false,
      "notify": false
    }
  ]
}
~~~

All fields above are explicit and required. A Codex profile may additionally bind
`"codex": {"task_id": "ACTUAL_RETAINED_THREAD_ID", "snapshot": "TRUSTED_TOOL_OUTPUT_PATH"}`.
This tool binding belongs to the configured bootstrap assignment. Observing a newer
coordinator assignment clears cached tool observations and suppresses that old binding,
including when automatic tracking of the replacement is disabled;
it cannot relabel an old completed turn as the new job. A new tool binding requires
an explicit coordinator profile in a separate state directory. Structured owner
reports may still follow independently.
No thread ID is derived from the owner name or self-reported session. Tool paths
come only from this trusted configuration; profile mode refuses legacy `--codex`,
`--start-deadline` and `--follow-assignments` overrides. The configuration digest
is pinned to its own new state directory; a changed registry requires a separate
state directory. Do not point profile mode at the live legacy watcher state.

~~~powershell
python -B -m asset_pipeline.worker_status --state NEW_OWN_STATE --checkins-module EXACT_PR172_SOURCE --profiles COORDINATOR_OWNED_JSON --snapshot RETAINED_HUB_SNAPSHOT
~~~

This queues local decisions without sending. A notice requires BOTH the explicit
CLI `--notify` and that owner's `notify:true` profile. Notifications still go only
to the fixed coordinator route through the existing immutable send-intent path.
No worker reminders, presence/ACK registration or automatic work dispatch occurs.
The existing finite listener may be explicitly selected with its unchanged bounds;
this assignment does not launch one. Real process adoption and live acceptance
remain separate from these source/synthetic results.

Each profile has its own reducer, cursor, deadline, missed-START flag, witnesses,
assignment history, deduplication outbox and ACK records. Only configured owners'
actual coordinator assignments can supersede/follow their state. Foreign routes,
conflicting assignment/request identities and historical replays cannot establish
START. Prose-only reports remain UNKNOWN. A BLOCKED/result report can be retained
without inventing START; checkpoint advice is a separate immutable decision so it
cannot rewrite a previously queued status notice. Replaying an event or recovering
an uncertain intent never automatically sends again. Configured-owner filtering
never hides newer coordinator assignments from the existing reducer.

A structured report is always `outcome_authority:owner-self-report`, including
when its configured provider is codex. Its source is
`structured-owner-self-report-not-session-terminal-api`; working/finished describe
the reported assignment, not authoritative session state or proof of idle.
Missing timestamps, stale reports and disconnection remain UNKNOWN. An optional
configured supported-tool row is separate, with
`outcome_authority:supported-tool-observation` and the original 60-second/turn
rules. Neither source sets `may_assign:true`.

Before creating any new send intent, profile delivery rechecks the current event
identity. A stale result, newer turn or superseding assignment withholds an old
queued completion. A retained uncertain intent is only reconciled using the frozen
observer; it is never retried. Delivery and ACKs do not refresh the evidence.

A `worker.status.ack` must include event_key, notification_id and decision:received,
plus all eight matching fields: profile_id, provider, owner, assignment_id, task_id,
session_id, turn_id and source. Null identity fields must be explicitly present.
Transport ACK is separate. ACKing one owner/assignment cannot accept another;
acknowledgment never authorizes a next assignment. `--ack-key` resolves only a
uniquely retained configured-owner event.

Focused synthetic tests use temporary state and FakeLink only. No live POST,
PID/state/intake/lock mutation, native call, private API or hook is part of their
acceptance. The frozen source pins remain codex_completion.py SHA256
8069c7fa0b40f95ad7adf1f489ca28d802bd21210bba95af9abb86fbe89cd408 and
team_checkins.py SHA25687421d4813b3b51cae02b8f8e55e0daf15e097249efbc4c1094142ccdff0846a.
Successor source verification: the focused run passed 46 synthetic tests in
1.761 seconds (30 existing WorkerStatusTest cases and16 FanoutTest cases), using
only temporary state and FakeLink. An additional actual `--profiles` CLI run with
two synthetic retained profiles/reports exited0: Codex-owner completion remained
owner-self-report with missing START and may_assign:false; prose-only Claude stayed
UNKNOWN. It queued one local decision and delivered zero notices with `--notify`
absent. Both frozen dependencies and all executable/test inputs stayed unchanged.
These are source/synthetic checks, not live fanout acceptance, supported-tool
collection, measured savings or adoption into the existing watcher process.