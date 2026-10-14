# Durable pipeline progress

Host-only changes, existing one-line JSON bridge envelope preserved. Each request now uses a
unique echoed ID. Successful replies require matching identity, valid status and an explicit
result field. Results retain their exact parsed values; a false/null result is not converted
into success. Non-object, mismatched, truncated, nonfinite or oversized responses fail explicitly.
Replies are bounded to64MiB, matching the installed Blender bridge line ceiling.

wire.call optionally accepts a host receipt and progress callback. State writes occur before
connection/send: prepared, not-dispatched on connection failure, outcome-unknown before send,
reply-received for validated success, error-received for a correlated error envelope. Partial
send/timeout/malformed response retains unknown. No network retry is introduced.

CLI --report publishes initial export state, completed export and transport checkpoints atomically.
The import snapshot path/hash and request ID exist before the mutation request is sent. If a
checkpoint cannot be written before dispatch, the call stops rather than mutating without a receipt.
A host killed after send leaves unknown evidence for reconciliation. This is observation state,
not a cancellation/replay service or a persistent bridge queue. Remote job tracking remains separate.

No installed bridge, broker or editor changed. Poot owns scene_snapshot/scene_verify producer
schema and lifecycle; these changes validate only the already documented transport envelope.
