# Durable parent relay extension

Add `codex_parent_relay.py` beside existing `asset_pipeline/codex_completion.py`.
It composes that parser and immutable create-new records; it does not replace
`worker_status`, the collector, TeamLink, or the broker. Use a new dedicated
state directory. Existing state and source files have not been changed.

The exact authorized parent ID is explicit runtime configuration, never discovered
from prose. Configuration is not permission to send:
the external caller must independently possess user authorization and capability.

Supported external tool-caller seam:

1. Call `ParentRelay.capture(retained_supported_observation, worker_id, event_type)`.
   The existing supported-tool parser supplies current-turn identity, actual
   terminal provenance, source tool and source hash. Types are `working`,
   `completed`, `idle`, `blocked`; failed/cancelled native turns are actionable
   blocked outcomes, not invented successful completion. Idle requires a terminal
   successful turn and explicit idle state. No CPU, toast or heartbeat inference.
2. Collect a fresh supported `read_thread` or `wait_threads` observation. Call
   `prepare(key, fresh_path, send_tool_available=actual_capability)` in the local
   harness. Missing capability retains pending without an intent. Stale evidence,
   a newer working turn, or a changed state refuses preparation.
3. If and only if `request` is non-null, the authorized model/tool caller invokes
   the returned real `mcp__codex_app__send_message_to_thread` request once. The
   Python module cannot call MCP. Durable exclusive intent precedes that call.
4. Persist the **exact** request/result envelope outside Git:

   ```json
   {"schema":"daedalus.parent-tool-result.v1",
    "tool":"mcp__codex_app__send_message_to_thread",
    "request":{"threadId":"EXACT_PARENT","prompt":"EXACT_PREPARED_PROMPT"},
    "observed_at_utc":"ACTUAL_UTC_AFTER_CALL","result":{}}
   ```

   Pass its path to `record_result`. A supplied `qualify_send(payload,target)`
   adapter must validate the actual supported tool response contract and return
   its actual receipt identifier. No positive response schema is guessed here.
   Missing/undefined/errors/unrecognized results stay uncertain. Tool acceptance
   is distinct from parent receipt. An automatic-review rejection is durable
   `denied`, still parent-pending, with no retry/reset API. It requires materially
   new authorization and a separately reviewed action; do not bypass it.
5. A separately authored semantic parent ACK must be retrieved through actual
   supported `read_thread` evidence, not broker ACK, sender acceptance, an idle
   label, prose from another task, or automatic platform task return. Call
   `record_parent_ack(key, retained_parent_read, actual_ack_turn_id)`. The selected
   completed parent turn must contain a final agent message whose entire JSON is:

   ```json
   {"schema":"daedalus.parent-worker-ack.v1","event_key":"EXACT_KEY",
    "parent_thread_id":"EXACT_PARENT","task_id":"EXACT_WORKER",
    "turn_id":"EXACT_WORKER_TURN","decision":"received"}
   ```

The durable states separately expose captured, pending, send-accepted, uncertain,
denied, and actual semantic parent acknowledgment. Reconnect/replay retains those
records. An existing intent never generates another request, including a crash
before a tool call or after a lost response. Reconcile actual parent evidence;
never remove an intent to force retry. Event keys bind exact parent, worker,
turn and semantic event type. Refreshed observation timestamps do not duplicate
that event. No result authorizes assignment, runs a model, installs a service or
promises unattended operation. Source hashes bind retained local provenance,
not cryptographic tool authenticity; external collectors/qualifiers are trusted.

Manual fallback: `notice(key)` returns a compact IDs/states/hashes-only packet for
an exact, human-approved final delivery through an authorized existing channel.
Displaying or returning that packet leaves parent receipt unproven until the
correlated parent ACK is read. Such an ACK may establish receipt after manual
delivery or an uncertain tool response without rewriting the original send state.
Do not use manual delivery as an indirect workaround for a denied action.

A live cross-thread notice attempted during development was explicitly denied by
automatic approval review; no parent acceptance, read or turn ID was returned.
An earlier parent's receipt of a different handoff cannot acknowledge that notice.
Raw request/result evidence remains local and is excluded from this source change.
No additional parent send has been performed for this extension.

The initially inspected observer at commit
`cfdce37231adb0ee4dc9d85b0aa219132c45674e` explicitly documents a bounded
tool-caller lifecycle, no autonomous completion subscription, and no guaranteed
cloud-parent adapter. Its worker-status listener output is historical and finite;
current service activity is unverified. A self `read_thread` succeeded during
this work, while `wait_threads` explicitly refuses waiting on the calling thread.
An existing authorized external coordinator must collect this worker's terminal
transition. Those runtime gaps remain even after this durable outbox is added.

Final dependency validation uses the actual existing PR171 head
`f887315446f0e700a1b170592e13f4e3bed11eeb` in the parent's isolated
isolated checkout. Its parser and immutable Observer
interfaces used here are unchanged; removed timing wrappers/collector are not
dependencies of this extension. No removed source has been restored.

Focused tests use only synthetic supported-tool envelopes, temporary dedicated
state and a synthetic positive-response qualifier. From this connector directory:

```powershell
python -B -S -m unittest harness.test_codex_parent_relay harness.test_directed_inbox
```

Import the module as `asset_pipeline.codex_parent_relay`. The companion
`asset_pipeline.directed_inbox.inspect_batch` prioritizes directed messages,
identifies body-only misrouting and correlates replies without sending, ACKing,
or consuming unhandled messages through a global broker cursor. It composes the
existing TeamLink route contract; it does not add another inbox or work queue.
The caller owns live collection and any separately authorized real delivery.
Raw communication and observation evidence remains outside Git.

Observed validation against exact dependency `f887315446f0e700a1b170592e13f4e3bed11eeb`:
the first sandbox run exited1 with21 setup errors at the existing `os.link`
publication primitive (`PermissionError`, WinError5), before relay assertions.
The separately permitted host run of the same focused offline command passed
all21 tests in0.642seconds, exit0, using the unchanged hard-link primitive.
No engine, parent send, network, service, or broker operations were performed.
Source review also found and repaired a mutable ACK-file validation race; the
hash-swap regression test passed. These are synthetic adapter tests, not proof
of current automatic capture, real parent acceptance or an installed service.
