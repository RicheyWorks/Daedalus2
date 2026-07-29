<!-- Paste-ready GitHub issue for the LoadBalancerPro tracker.
     TITLE (copy into the title field):
     Add `topologyNodeId` to `ServerStateVector`
     BODY below the line. Source of truth: docs/upstream-requests-loadbalancerpro.md
     (this file is a verbatim extraction; if they diverge, the source wins). -->

**Problem.** `ServerStateVector` describes a server (`serverId`, in-flight count, weight, p95/p99
latency, error rate) but carries **no notion of where that server sits in a topology**. Daedalus
reasons about graphs whose nodes are servers; without a join key, there is nothing to map a graph
node onto a `ServerStateVector` and back.

**Suggested change.** Add an optional field, e.g. `Optional<String> topologyNodeId` (or a plain
nullable `String`), defaulted so existing constructors keep compiling. It needs no meaning inside
LoadBalancerPro — it is an opaque handle owned by whatever produced the topology.

**Why not reuse `serverId`.** They are different identities. `serverId` names a *process*;
`topologyNodeId` names a *position*. A server can be replaced without moving, and a node can be
re-homed without the server changing. Conflating them breaks as soon as either happens.

**If declined.** Callers must maintain an external `Map<String, String>` alongside every routing
call, which is exactly the kind of side-table that goes stale silently.
