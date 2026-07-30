# ADR-006: Living Mazes — and the ten-idea slate it was chosen from

**Status:** Accepted
**Date:** 2026-07-30
**Deciders:** RicheyWorks (repo owner)

## Context

Daedalus2 at 1.2.0-SNAPSHOT is a *complete but static* system. The deep audit for this ADR
walked every seam the project has grown: 10 generators and 10 solvers behind registries, a
graph seam with a search recorder, weighted grids with hotspot costs, a braiding
post-processor, STOMP topics with per-destination authorization, bounded Caffeine stores,
a plugin SPI proven end-to-end, replay animation in the web UI, sessions with multiplayer
and a leaderboard. Every one of those is a noun. What the project lacks is a **verb**: after
`generate`, a maze is a frozen artifact. Nothing in the system ever changes an existing maze,
so the STOMP `/state` topic fires exactly once per maze, the replay machinery animates only
the past, and the weighted-cost engine models a world that never moves.

The audit question was: *what ten things would make this project alive and more useful* —
exercising machinery the repo already paid for, rather than bolting on unrelated features.

## Decision

Build **Living Mazes v1 ("erosion")**: `POST /api/v1/maze/{id}/live` schedules bounded
mutation ticks. Each tick copies the cached grid, opens a fraction of its dead-end walls
(the core `Braider`, reused as an erosion primitive), drifts hotspot costs on weighted
grids (clamped to the API's `[1, 1000]` domain), atomically swaps the immutable snapshot
into the maze cache, and publishes a new `MazeMutatedEvent` that the WebSocket bridge
forwards as a `MutationFrame` on `/topic/maze/{id}/state`. The web UI re-fetches on each
frame and quietly re-solves, so the drawn route visibly adapts as the maze breathes.
The other nine ideas are recorded below as the roadmap they now form.

## Options Considered

### Option 1: Living Mazes — erosion ticks (CHOSEN)

| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium — one service, one endpoint, one event, one frame; core already has `Braider` |
| Cost | Low — no new dependencies; single-thread scheduler; bounded runs |
| Scalability | Bounded by construction (`daedalus.living.max-concurrent`, per-run tick caps) |
| Team familiarity | High — reuses copy-on-write, STOMP bridge, rate-limit template patterns from this repo |

**Pros:** literally makes mazes alive; erosion (only *opening* walls) preserves
connectivity by construction, so a live maze can never strand a player; deterministic
(seeded per tick) so the same maze erodes the same way; exercises weighted costs, STOMP,
and the cache honestly. **Cons:** mazes only get easier over time (v1 never *closes*
walls — closing needs a connectivity proof per closure); a solved path goes stale each
tick (mitigated: UI re-solves).

### Option 2: Solver Arena — live head-to-head races

| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium — server-paced replay of two recordings over STOMP |
| Cost | Low |
| Scalability | One scheduled stream per race; needs the same concurrency bound as Option 1 |
| Team familiarity | High — SearchRecorder already captures expansion order |

**Pros:** spectacular demo (BFS floods vs A* beelines in real time); zero core changes.
**Cons:** presentation-layer feature — the *system* stays static; the compare table
already tells the story numerically.

### Option 3: Traffic simulation — occupancy feeds cost

Player/agent occupancy raises cell weights; routes detour around crowds, costs decay over
time. | Complexity Medium-High | Cost Low | Scalability needs decay bookkeeping per maze |
Familiarity High (weighted grids just landed). **Pros:** closes the loop between play and
routing; genuinely novel emergent behavior. **Cons:** needs sustained multi-player traffic
to be visible at all — a portfolio deploy rarely has it; best built *after* mazes can
already change (Option 1 supplies the mutation plumbing).

### Option 4: Daily maze — seeded challenge with shared leaderboard

Date-derived seed, one maze everyone plays, leaderboard partition per day.
| Complexity Low | Cost Low | Scalability trivial | Familiarity High.
**Pros:** cheap, sticky, proven pattern (Wordle effect). **Cons:** no new machinery —
it's a convention over existing endpoints; leaderboard partitioning is the only real work.

### Option 5: Maze DNA — crossbreeding generators

Split-inherit topology from two parent mazes, mutation rate as a parameter.
| Complexity Medium | Cost Low | Scalability fine | Familiarity Medium.
**Pros:** playful API (`POST /maze/breed?a=&b=`); showcases the grid model. **Cons:**
stitched offspring need connectivity repair (a real algorithmic problem); novelty
outweighs usefulness; weakest test story of the ten.

### Option 6: Spectator mode — shareable read-only session links

| Complexity Low-Medium | Cost Low | Scalability fine | Familiarity High (topics + authz interceptor exist).
**Pros:** social; permalinks already exist for mazes, extending to sessions is symmetric.
**Cons:** the per-destination authorization work is the feature — mostly security surface,
little visible payoff until multiplayer sees real use.

### Option 7: Fog-of-war agent API — the maze as an RL-style benchmark

`POST /maze/{id}/agent` opens a walker session that only reveals the 4 neighbor cells;
step budget enforced; leaderboard for programmatic solvers. | Complexity Medium | Cost Low |
Scalability fine | Familiarity Medium. **Pros:** turns Daedalus into a *benchmark* others
can code against — the strongest "more useful" candidate; curl-able like the ASCII endpoint.
**Cons:** its killer version wants mazes that change mid-walk… which is Option 1 first.

### Option 8: Session time-travel — ghost runs

Record moves with timestamps; replay a past run as a translucent ghost racing you.
| Complexity Medium | Cost Low-Medium (per-session move log, bounded) | Familiarity High
(MazeReplay pattern). **Pros:** classic racing-game joy; reuses replay drawing. **Cons:**
needs the move log store + TTL story first; UI-heavy; static system stays static.

### Option 9: Analytics overlay — chokepoints and heatmaps

Surface `theory` metrics (min-cut edges, betweenness proxy, dead-end density) as a canvas
overlay. | Complexity Low-Medium | Cost Low | Familiarity High. **Pros:** the theory module
finally reaches the UI; teaches graph theory visually. **Cons:** read-only lens on a static
artifact; min-cut on braided mazes is the only non-trivial computation.

### Option 10: Campaign mode — procedural descent with adaptive difficulty

Chained mazes, difficulty steered by the player's solve-time percentile; state in the
session store. | Complexity High | Cost Medium | Familiarity Medium. **Pros:** turns a demo
into a game; natural home for every other idea. **Cons:** the largest scope of the ten;
difficulty tuning needs play data the project doesn't have yet.

## Trade-off Analysis

Three forces separated the slate. **(1) Does it change the system or just display it?**
Options 2, 8, 9 are lenses on a static system; 1, 3, 7, 10 change what the system *is*.
**(2) Does it stand on machinery that exists today?** Options 1, 2, 4, 9 reuse this repo's
proven seams end-to-end; 3 and 7 want mutation plumbing that doesn't exist yet; 10 wants
play data. **(3) Is it safe by construction?** Option 1 is the only *mutating* idea with a
free correctness proof: erosion only opens walls, so reachability can never regress —
no connectivity checker needed in v1. That intersection (changes the system + stands on
today's machinery + safe by construction) contains exactly one idea, and it is also the one
that unblocks the best of the rest: traffic simulation (3) and fog-of-war agents (7) both
become dramatically better once mazes can already change under a walker's feet.

## Consequences

- The maze cache stops being append-only: `MazeGenerationService.replace` swaps immutable
  snapshots, and every reader (REST, ASCII, sessions, solvers) picks up the newest grid on
  its next lookup with no locking — readers mid-request keep a consistent old snapshot.
- `/topic/maze/{id}/state` now carries two frame shapes (`GeneratedFrame`, `MutationFrame`);
  subscribers must branch on shape. The web UI does; external consumers are told via the
  frame's self-describing `tick` field.
- Solved paths and leaderboard times refer to the maze *as it was* — accepted for v1 and
  visible in the UI (it re-solves on every mutation).
- Wall *closing* (mazes getting harder) is deliberately out of scope: it needs a
  connectivity proof per closure. **Re-fire trigger:** if Option 3 or 7 is built, revisit
  closing with a cut-vertex check.
- A new always-on scheduler thread exists; bounded by `max-concurrent` and per-run tick caps,
  and every run self-terminates (ticks exhausted, maze settled, or maze evicted).

## Action Items

1. [x] Core: `MazeGrid.copy()` / `WeightedMazeGrid.copy()` (weights preserved)
2. [x] Plugin API: `MazeMutatedEvent`
3. [x] Server: `LivingMazeService` + `POST /api/v1/maze/{id}/live` + `MutationFrame` bridge
4. [x] Config: `daedalus.living.*` + `mazeLive` rate budget (base/test/prod) + templates test
5. [x] UI: mutation frames re-fetch, re-solve, and re-draw; "Bring to life" control
6. [x] Tests: copy semantics, erosion ticks (mutation, connectivity, settling, capacity,
       drift clamp, determinism), endpoint statuses, frame bridge
7. [x] Roadmap follow-ups, first batch (2026-07-30): fog-of-war agents (7) shipped —
       visibility reads the live grid, so living mazes change mid-walk, exactly the
       composition predicted above; daily maze (4) shipped as the quick win
8. [x] Roadmap follow-ups, second batch (2026-07-30): traffic simulation (3) shipped on
       the mutation plumbing (occupancy → cost → routing, decaying); solver arena (2)
       shipped client-side over the replay seam; daily leaderboard partition completed
       idea 4 (per-maze boards)
9. [x] Roadmap follow-ups, third batch (2026-07-30): chokepoint analytics (9) shipped —
       the theory module's min-cut on the product surface, re-analyzed per erosion tick;
       session ghosts (8) shipped — best run per maze replayed as a timed racer
10. [ ] Roadmap remainder: spectator mode (6), maze crossbreeding (5), campaign mode (10)
