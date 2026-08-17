# ADR-011: Incremental SSSP — measured, then declined

**Status:** Decided — **declined**
**Date:** 2026-08-17
**Deciders:** RicheyWorks
**Resolves:** ADR-001 appendix item 5 ("incremental / D\*Lite-style SSSP — measure
before it is assumed necessary")

## Question

Living mazes, traffic, and weighted hotspots all change the graph under a walker's
feet. The UI re-solves on every mutation frame. The naive answer is a full Dijkstra
per tick. Incremental SSSP (D\*Lite) repairs only the affected subtree. Is the
naive answer already cheap enough that the repair is not worth its surface?

## What a living tick actually does

`LivingMazeService` fires every **2 s** (`daedalus.living.tick-interval`). A tick
copies the snapshot, opens a fraction of dead-end walls, optionally closes a
fraction of extras, and drifts hotspot costs. The web UI re-fetches and re-solves.
That re-solve is the quantity incremental SSSP would replace.

Campaign stages are roughly 9–30 on a side. The complexity lab sweeps to 128.
Those are the sizes that matter; 512² is the scale at which parallel generation
was already declined.

## Method

`docs/evaluations/IncrementalSsspEval.java` — core-only, not in the reactor, not
in CI. Median of 21 Dijkstra recomputes after an 8-iteration warm-up, on this
machine (Java 22.0.2, Windows 11, 24 CPUs), 2026-08-17. Four mutations × four
sizes. The column that decides the question is **recomputes that fit in one 2 s
tick**, not the absolute microsecond figure.

| mutation | 16 | 32 | 64 | 128 |
|---|---:|---:|---:|---:|
| erode prims | 145 µs / 14k× | 103 µs / 19k× | 148 µs / 14k× | 207 µs / 10k× |
| erode backtracker | 68 µs / 29k× | 74 µs / 27k× | 54 µs / 37k× | **2.0 ms / 1.0k×** |
| harden braided | 107 µs / 19k× | 57 µs / 35k× | 8 µs / 241k× | 95 µs / 21k× |
| drift weights | 118 µs / 17k× | 74 µs / 27k× | 206 µs / 10k× | 242 µs / 8k× |

(median µs / how many of those fit in a 2 s tick)

## Decision

**Decline.** The worst cell in the table — recursive-backtracker at 128², the
longest-corridor generator at a size the API barely serves — is **two
milliseconds**, a thousand times faster than the ticker. At the sizes a campaign
or a `/live` call actually uses, a recompute is a tenth of a millisecond.

D\*Lite is not a small patch. It keeps a search tree, invalidates on edge
insert, edge delete, and weight change (a living tick does all three), and
repairs. That surface cannot pay for itself against a 200 µs baseline. Shipping
it would be the d-ary heap again: a textbook improvement on a quantity that is
not the bottleneck.

The UI already re-solves from scratch. That is the correct architecture, not a
placeholder.

## Re-fire

Re-measure, do not assume, if any of these become true:

- the tick interval drops far enough that 2 ms is a visible fraction of it
  (per-request data-plane routing, not a 2 s animation)
- a consumer regularly solves ≥256² living mazes
- a solve is measured as the bottleneck of a request, not of a tick

Until then the appendix item is closed.
