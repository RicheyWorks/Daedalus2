# ADR-012: Multiplayer join grants STOMP on owned sessions

**Status:** Decided — **accepted**
**Date:** 2026-08-17
**Deciders:** RicheyWorks
**Composition of:** multiplayer sessions (2026-07-28) and per-destination STOMP
authorization (2026-07-28). Those two shipped independently and did not compose.

## Question

`POST /session/{id}/join` puts a named piece on the board. An owned session's
`/topic/session/{id}/player` topic admitted only the opening token's subject.
A second authenticated client could move over REST and never see the other
player's frames. Same-browser WASD still worked because it shared the owner's
connection. Does join grant the feed, or is that a different feature?

## Decision

**Join with a verified subject grants `SUBSCRIBE`.** `GameSession` keeps a
subject allowlist: the owner at open, plus every subject that joins with a
token. `StompSubscriptionAuthorizationInterceptor` asks
`session.maySubscribe(subject)` instead of owner-equality.

What stays the same, on purpose:

- Unowned sessions (dev/desktop, no credentials) still have no claim to
  enforce. Anyone may subscribe.
- Unknown session ids are still allowed — refusing would be an existence
  oracle.
- Maze and plugin topics stay open. They carry no per-user data.
- An anonymous join still gets a seat. It does not get an owned session's
  feed. Display name is not identity.
- Rejoin of an existing name keeps that player's position and does **not**
  add a new subject. First claimant of a display name keeps the STOMP seat;
  repeating the name with a different token is not a way in.
- Subjects are not written into `SessionResponse`. The allowlist is not a
  public roster.
- Cap is `GameSession.MAX_PLAYERS` (8, including the opener). A session is
  not a lobby. Full and completed both answer 409 from `/join`.

The web UI's `#session=` permalink stays read-only until the spectator
clicks **Join this session**, which POSTs `/join` and drops read-only.

## Why not a shared spectator role

A public watch-the-game topic would be a third feature. The bug was that
two shipped features did not compose for the person who had already been
admitted to the board. Extending the allowlist is the smallest close.

## Re-fire

A named spectator role, or Redis-serialized `GameSession` objects that would
have to carry the allowlist across instances (ADR-005 is still single-instance).
Until then this is closed.
