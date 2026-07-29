# ADR-005: Single-Instance Posture — What Is Process-Local, and What Scaling Out Costs

**Status:** Accepted (documents the current posture; the *externalization design* within is
Proposed and dormant until the trigger below fires)
**Date:** 2026-07-29
**Deciders:** Richmond (RicheyWorks)
**Prompted by:** the 2026-07-29 back-end audit, which bounded the in-memory stores and noted
their process-locality as the remaining design-level observation

---

## Context

Three pieces of server state live in process memory, deliberately:

1. **Game sessions** — a Caffeine cache (`daedalus.session.*` bounds). Never externalized;
   Redis plays no part even when enabled.
2. **The maze cache** — a Caffeine cache (`daedalus.maze.cache.*` bounds). A maze exists on
   the instance that generated it, nowhere else.
3. **The leaderboard's serving path** — reads hit Redis when enabled, but the in-memory set
   is the fallback and the only store in the default profile. Writes go to both.

Additionally the **STOMP broker is the simple in-memory broker**: a subscriber connected to
instance A never receives a frame published on instance B.

This is not an oversight; it is the deployment model the code is honest about. A second
instance behind a load balancer today would give players 404s on their own sessions (opened
on the other instance), solvers 404s on the other instance's mazes, half-blind live frames,
and per-instance leaderboards in the default profile.

## Decision

**Stay single-instance, and say so out loud.** No session externalization, no broker relay,
no distributed cache is built now. The engine's actual consumers (the desktop host, the
examples, LoadBalancerPro integration work) are all embedded or single-process; horizontal
scale has no customer, and speculative distribution is the most expensive kind of
speculation — it taxes every request path to serve a deployment that doesn't exist.

**The trigger that reopens this:** a real deployment wanting a second instance (or
zero-downtime deploys, which are the same problem wearing a nicer shirt).

## The externalization path, recorded while the reasoning is fresh

When the trigger fires, the order of work is:

1. **Sessions move to Redis** (`RedisTemplate` is already wired and optional). `GameSession`
   is small and Jackson-friendly; the per-session lock in `tryMove` becomes a Redis
   `WATCH`/Lua compare-and-set or a per-session distributed lock — the check-then-act race
   `GameSessionServiceConcurrencyTest` pins does not vanish by distribution, it gets worse.
   That test's invariants (contiguous event chain, exactly-one completion) are the
   acceptance bar for whatever replaces the lock.
2. **Maze cache stays process-local but becomes reconstructible.** Mazes are deterministic
   from `(generatorId, rows, cols, seed)` — all four are in `MazeMetadata`. Store the recipe
   in Redis, regenerate on cache miss on whichever instance is asked. Cheaper and more
   honest than shipping grids around.
3. **STOMP moves to a broker relay** (`enableStompBrokerRelay` toward RabbitMQ/ActiveMQ) so
   frames published anywhere reach subscribers everywhere. `StompSubscriptionAuthorizationInterceptor`
   is unaffected — it runs on the inbound channel of whichever instance holds the socket,
   and session ownership will already be in Redis per step 1.
4. **Leaderboard** is already dual-written; the change is trusting Redis as primary and
   demoting the in-memory set to a read-through cache.

Sticky sessions at the load balancer are the tempting shortcut and are rejected here in
advance: they turn every deploy into a session massacre and leave step 3 unsolved anyway.

## Consequences

- Operators get one honest constraint to know — *one instance at a time* — instead of a
  half-distributed system that fails mysteriously at two.
- The bounded stores from the audit are sized for that one instance and documented next to
  their knobs; nothing about this ADR changes them.
- When scale-out work starts, it starts from a written plan whose hardest part (the session
  lock's distributed replacement) is already named, with an existing concurrency test as its
  acceptance bar.
