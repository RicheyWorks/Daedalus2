# Remote execution uncertainty

`execute_python` normally uses Unreal Python Remote Execution. Failure before entering
`run_command` keeps the existing direct fallback: unavailable remote execution, failed
setup, an unavailable lock, or wrapper preparation failure runs the code locally once.
The result identifies this path with `unattended:false` and a fallback note. Explicit
`unattended:false` continues to execute directly. Remote timeouts must be finite and
nonnegative before starting a worker; zero is allowed.

Once `run_command` has been entered, a transport exception cannot establish whether
the engine applied effects. The bridge returns this terminal error and does not rerun
the code locally:

```json
{
  "id": "request id from the envelope",
  "status": "error",
  "code": "REMOTE_EXECUTION_UNCERTAIN",
  "dispatched": true,
  "effects": "unknown",
  "retryable": false,
  "message": "Remote Execution outcome is unknown after OSError: reply lost"
}
```

These fields describe the outer bridge's knowledge. `dispatched:true` means the request
may have entered remote execution, not that engine effects are proven. The same error
is returned when the bridge's timeout expires while its worker is outstanding, including
a worker that could enter remote execution later. `effects:"unknown"` means no automatic
local retry; it does not mean no effects. An explicit remote `success:false` reply keeps
the existing ordinary error behavior, without local replay.

A terminal reply is not quiescence or cancellation. An outstanding worker may finish
or apply effects later. Its late reply cannot replace the already published uncertainty.
Read back affected state before choosing recovery; sending a new request can repeat effects.

With `request_id`, completed uncertainty replies join successful replies in the existing
process-local cache, bounded to 256 retained completion entries. A retained same-ID retry
returns the terminal reply with `replayed:true`, rather than dispatching again. The cache
does not survive process/module restart or eviction. It does not bind request bodies or
deduplicate in-flight requests. There is no exactly-once or durable recovery guarantee.

Acceptance uses the actual bridge with offline fake remote clients and counter effects.
The unit suite has a floor of 20. Five in-memory source mutations require a healthy baseline
and assertion failures; import, compile, and fixture errors cannot count as mutation proof.
The separate transport/walk suites use a test stand-in, and the Daedalus check verifies
registration without Unreal. These checks do not claim live editor acceptance.
