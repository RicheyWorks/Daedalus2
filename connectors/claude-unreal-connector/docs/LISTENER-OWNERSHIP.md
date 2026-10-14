# Listener ownership

The bridge remains an IPv4 TCP listener on `127.0.0.1`, using the existing port
selection and backlog. This candidate changes only socket ownership policy and
startup failure handling. It does not alter command permissions, authentication,
editor ownership, remote execution or mutation scheduling.

On Windows, a new socket sets `SO_EXCLUSIVEADDRUSE` before `bind()`. It never
sets `SO_REUSEADDR` or falls back to sharing if exclusive binding is unavailable
or fails. On POSIX, it retains `SO_REUSEADDR` and does not enable `SO_REUSEPORT`.
A competing listener on the same explicit loopback address/port must fail while
the owner is listening. Startup does not probe, close or replace the other owner.

`_create_listener()` keeps the descriptor private until option selection, bind
and listen all succeed. A setup failure closes that new descriptor. Remaining
startup staging, address readback, thread construction/start, tick registration
and logging are protected by the existing cleanup policy. Once published,
failure calls the owner-thread lifecycle cleanup; before publication, failure
closes only the private descriptor. Cleanup failure follows the prerequisite's
retained-handle/retry behavior; it is not proof that resources were released.

This source candidate is stacked on [PR #116](https://github.com/RicheyWorks/Daedalus2/pull/116),
exact commit `9e4b226c49339ccf7245205c8b11e29070e716b1`. Its generation fences,
job settlement and owner-thread shutdown remain unchanged. PR #130 capture
readiness is a separate candidate and is not modified or included in this stack.

## Accepted connections and restart

Closing a listener does not establish that all accepted connections are closed.
This patch does not add accepted-socket tracking or force-close peers. In
particular, it does not guarantee immediate restart on the same Windows port
while accepted connections or transport state remain active. A failed later bind
is returned to the caller; no reuse fallback, forced socket reset, new editor or
automatic port change is attempted.

Standalone tests drain both peers gracefully before testing later restart:
the client shuts down sending, the accepted peer receives EOF and shuts down
sending, and the client receives EOF before both sockets close. A bounded retry
after complete peer shutdown accommodates OS transport cleanup. Restart while
old accepted sockets remain live is deliberately not used as a success criterion.

A separate 20-round Windows probe on BLACKBEARD confirmed competing default and
reuse binds were refused while the exclusive listener remained open. After
listener closure, a new exclusive bind/listen succeeded here while the original
accepted pair was still active. Thus neither continued reservation nor immediate
reuse is assumed universally after listener closure; that observation is specific
to the tested host and socket sequence.

The source basis is Microsoft's
[socket ownership guidance](https://learn.microsoft.com/en-us/windows/win32/winsock/using-so-reuseaddr-and-so-exclusiveaddruse).
It distinguishes Windows sharing from exclusive binding and warns that accepted
connections can outlive listener closure. No third-party implementation was
copied.

## Validation and owner handoff

`python tests/listener_ownership_test.py` uses mocks for Windows/POSIX option
ordering, failure paths and lifecycle state. Its real tests use only OS-selected
ephemeral loopback ports: competing default/reuse binds, owner responsiveness,
graceful accepted-peer shutdown and later restart. Windows CI exercises the
native exclusive option; Linux CI exercises the native POSIX reuse policy.
The separate 21-test lifecycle suite is also retained in focused CI.

These tests launch no editor and call no Unreal API. They do not prove shutdown
of production accepted sockets, native engine quiescence or live editor restart.
Review dependency sequencing with PootScoot and obtain Claude's owner acceptance
before merge or installation. Existing security and lease settings stay intact.
