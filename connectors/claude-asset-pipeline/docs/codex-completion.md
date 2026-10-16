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
