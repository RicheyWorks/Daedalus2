# Quest journal restoration

DQP1 serializes the accepted event history, configured step definitions and reward
claim flag. Restore binds to a caller-supplied player/realm/quest scope and exact
definitions, then replays in a temporary instance. Only successful ordered events
are accepted. Unknown versions, duplicate event IDs, negative/overflow numbers,
changed scopes/definitions, oversized history and trailing input are refused.
Failure leaves the running quest unchanged.

Limits: 32 steps, 128-byte type/target/event IDs, 512 accepted events, 256-byte
scope and 256 KiB input. A claimed reward is valid only after completion. The
serialized flag survives a fresh process in the test; an older legitimate journal
can still rewind state, so the host must protect against rollback/replay.

This is structural validation, not signature verification or client authority.
Only load host-trusted state using an authorized scope. Host storage, backups,
atomic state-and-inventory commit, restart rollback fencing and actual gameplay
binding remain pending. Never grant online rewards from client-uploaded journals.

MSVC /W4 /WX passed 549 ordinary checks, 550 writer checks and 553 reader checks
in separate processes using an actual file. CI repeats cross-process file restore
under GCC/Clang sanitizers and MSVC. The test file adapter is not a production
save service; the core returns a journal for the existing host save mechanism.
