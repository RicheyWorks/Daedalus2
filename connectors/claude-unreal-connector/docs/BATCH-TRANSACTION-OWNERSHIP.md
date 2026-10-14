# Bridge batch transaction ownership

The bridge keeps a batch's transaction owner across generator yields. Other non-READ commands, including SENSITIVE_READ capture commands that create temporary actors, receive a terminal `BUSY` reply before their command function or generator executes:

```json
{"status":"error","code":"BUSY","dispatched":false,"effects":"none"}
```

These fields describe the rejected request. They do not describe earlier work. An asynchronous request can already have an accepted job ID; polling that exact ID returns its terminal BUSY reply. A known pre-dispatch BUSY is not cached as a successful request-ID result, so a later explicit retry can run after the owner releases. There is no automatic retry or deferred queue.

A new batch also receives BUSY while an earlier non-READ generator or bridge remote worker remains outstanding. The game thread registers each remote worker before starting its thread, including workers waiting for the remote lock. A terminal command timeout does not mean its worker stopped.

A dispatched remote receipt must be a dictionary with a literal boolean `success` field. Missing or malformed status becomes retained `REMOTE_EXECUTION_UNCERTAIN`; valid `true` and `false` retain the existing success and reported code-failure behavior. In particular, a worker can publish `done` after a control interrupt without publishing a valid execution receipt.

Two conservative barriers persist across bridge stop/start:

- An unresolved remote outcome prevents a new batch transaction from opening, even after the local worker completes. Ordinary mutable commands outside a batch remain subject to the existing policy and can proceed. This is not global isolation of asynchronous writes.
- A failed batch transaction entry/exit or child finalizer leaves transaction state unknown and blocks all non-READ commands. Any exception while advancing a child generator, except normal `StopIteration`, also latches this barrier and stops `keep_going`: advancement runs finalizers, and a later `close()` can succeed because the generator is already closed. The bridge cannot distinguish a body exception from failed cleanup here. Synchronous item errors retain their existing behavior; no rollback is inferred.

READ commands, socket-side `job_result`, and cached terminal request-ID replies remain available. Existing unknown-command and policy-refusal outcomes retain precedence. Batch ownership releases only after normal completion or cooperative generator finalization; shutdown reuses the lifecycle cleanup and interrupted receipts.

`KeyboardInterrupt` and `SystemExit` settle the dispatched command as `COMMAND_INTERRUPTED` with `effects:"unknown"` and `retryable:false` before being re-raised. The terminal receipt is retained for exact request-ID replay, and a later tick cannot turn the closed generator into a false success. An interrupt during remote thread startup retains the worker record and a remote uncertainty barrier: thread creation may have completed before its startup receipt was interrupted.

There is no reconciliation or barrier-clearing API in this slice. An owner must independently reconcile uncertain editor state before any future recovery mechanism is defined. Reloading the module loses process-local evidence and does not prove that remote/native work ended. Stop/start is not reconciliation, cancellation, or rollback.

The guarantee covers cooperating bridge-owned batch requests and their declared READ metadata. External editor/user changes, unrelated APIs, native asynchronous effects, arbitrary custom generators' private transactions, maliciously misdeclared READ commands, and unloaded process state are outside this guarantee. Existing queue capacity and tick budgets are unchanged; retry fairness is not promised.

Verification uses actual bridge code with fake Unreal and in-memory remote workers. It demonstrates scheduling and receipt behavior, not live Unreal undo-buffer behavior. No installed bridge or shared editor is changed.
