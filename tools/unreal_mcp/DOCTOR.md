# Verified doctor readback

The existing doctor checks the native MCP settings requested in Claude's H2/H3
harness backlog. Its default invocation only reads:

```powershell
python tools/unreal_mcp/doctor.py
```

The existing opt-in repair command requests the same intended values:

```powershell
python tools/unreal_mcp/doctor.py --fix
```

`--fix` now reads every intended setting again after its setter requests. A setter
acknowledgment alone cannot print `MCP READY` or return zero. For example, if a
request to turn off the background throttle leaves it true, the final readback
still reports `BAD` and the command exits 1. A partial repair, missing property,
wrong JSON value type, malformed reply or read error also remains unsuccessful.
Boolean false and numeric zero are distinct; an integer setting requires an
integer observation. The native setter must also return Boolean true: its
declared contract is successful setting and saving. A false or malformed setter
result remains failure even when in-memory readback matches, because a failed
save can leave those values changed.

Initial section read errors or missing properties prevent repair requests;
unobserved properties are never created by the doctor. Each changed section is
requested at most once. A setter failure or exception stops further writes; the doctor
still attempts final readback, but the failed/uncertain request remains an error
even if the values appear correct. It never retries a setter or rolls settings
back. An already-correct `--fix` run performs no setters or extra read pass.
The existing 30-second client timeout remains unchanged.

`MCP READY` with exit 0 means every requested setting was observed with the
expected type and value, and no request failed. `MCP NOT READY` with exit 1 means
one or more settings are wrong/unverified or a request failed. `MCP DOWN` remains
the connection check's failed result. These observations do not prove that the
editor restarted, the values survived a restart, or any gameplay passed.

This source patch preserves `WANT`, tool names, setting targets and explicit
`--fix` opt-in. It changes no launcher, client, proxy, TMOG/provider or resource
policy. Shipping this patch does not authorize executing the repair command or
installing it in a shared checkout; the current owner retains that workflow.

The regression suite uses fake MCP state and responses only:

```powershell
python -m unittest tools.unreal_mcp.test_doctor -v
```

No live native tool, UI, settings write, restart, Play, job replay or installation
was used for this source-only delivery.
