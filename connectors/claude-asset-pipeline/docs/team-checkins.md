# Correlated team check-ins

This caller-invoked helper consumes retained TeamLink assignment messages and
snapshots. It does not poll the hub, send reminders, wake Claude, dispatch work,
or install any hook. Existing TeamLink `/send`, `/ack`, `/wait`, `/pending` and
`reply_to` remain unchanged. A broker message ID proves delivery; an `ack` is a
transport receipt, not task acceptance. Presence/heartbeat never proves work
state. Sender labels are checked against the assignment route but the existing
local hub does not cryptographically authenticate those labels.

Save the actual coordinator-to-worker assignment as `assignment.json`; its body
must contain `assignment_id` and `request_id`. Save an actual retained hub response
as `snapshot.json` with `observed_at_utc` (explicit UTC) and `messages` (unaltered
broker messages). Do not substitute current timestamps for old observations.

From `connectors/claude-asset-pipeline`:

```powershell
python -B -m asset_pipeline.team_checkins --assignment assignment.json --snapshot snapshot.json --state checkin-state.json --start-deadline 2026-10-16T06:45:00Z --checkpoint-seconds 900
python -B harness/team_checkins_test.py
```

The caller supplies a new snapshot after reconnect. IDs are deduplicated with
content hashes; a conflicting replay fails. Replay does not extend a deadline.
The state is specific to the exact assignment bytes and must have one writer.
An exclusive lock rejects simultaneous CLI writers; after an interrupted process,
inspect and reconcile retained state before manually removing a stale lock.
Atomic state publication precedes output; interruption afterward can lose an
advice display, so inspect persisted `reminder_issued` rather than blindly resend.

Qualified replies must come from the assigned worker to its coordinator, with
either the matching body `assignment_id` or `reply_to` referencing the assignment
or an already-correlated reply. An explicit conflicting assignment/request ID is
always refused. Use `type: checkin` and body `status` exactly `START`, `PROGRESS`,
`BLOCKED`, `COMPLETED`, `FAILED` or `CANCELLED`; equivalently use `task.start`,
`task.progress`, `task.blocked`, `task.completed`, `task.failed`, `task.cancelled`.
These are opt-in structured conventions over the existing generic transport,
not a claim that Claude already emits them. Free-form prose remains unqualified.
Progress/completion without START cannot hide a missed acceptance. Terminal state
cannot be reopened. A later coordinator assignment to the same worker marks the
old assignment superseded; old completion never marks the new task done.

START and later qualified checkpoints establish the next deadline from the
retained snapshot's observation time. This is time observed by this caller, not
proof of when the worker performed the action; consume snapshots promptly.
The CLI emits at most one overdue reminder recommendation per assignment, with
correlation IDs and no automatic action. A coordinator decides whether to send it
or escalate; timeout never authorizes reassignment. Persisted state retains IDs,
hashes, deadlines and enum stages only, not raw prose or transcripts.

Actual motivating fixtures: hub message 32822 is Claude's legacy prior-task
check-in replying to 32760. Message 32833 is the next assignment to `unreal-team`,
`assignment_id=prismheart-field-save-fish-request-r1`,
`request_id=claude-prismheart-field-save-20261016T0630Z`. The old check-in cannot
be inferred to START the new assignment. Test fixtures retain these actual IDs,
routes and correlation fields without reproducing the private prose.
