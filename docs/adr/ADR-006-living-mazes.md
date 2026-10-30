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
- `/topic/maze/{id}/state` carries three frame shapes (`GeneratedFrame`,
  `MutationFrame`, `TrafficFrame`); subscribers must branch on shape. The web
  UI does; external consumers are told via `generatorId` / `tick` /
  `congestedCells`.
- Solved paths and leaderboard times refer to the maze *as it was* — accepted for v1 and
  visible in the UI (it re-solves on every mutation).
- Wall *closing* (mazes getting harder) is deliberately out of scope: it needs a
  connectivity proof per closure. **Re-fire trigger:** if Option 3 or 7 is built, revisit
  closing with a cut-vertex check. **Fired 2026-08-17** — both options had shipped; the
  proof is a spanning-forest complement (cut-*edge*, not cut-vertex — the wording above
  named the wrong object). See [ADR-008](ADR-008-living-mazes-hardening.md).
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
10. [x] Roadmap follow-ups, fourth batch (2026-07-30): maze crossbreeding (5) shipped —
        patch-inheritance genome plus Kruskal connectivity repair (the repair is
        load-bearing, teeth-proven); spectator mode (6) shipped — read-only session
        snapshot endpoint behind a `#session=` permalink, live over the existing STOMP
        player frames
11. [x] Roadmap complete (2026-07-30): campaign mode (10) shipped, and it did turn out to be a
        composition rather than a subsystem — one endpoint, because a campaign is a table of
        contents over the API the earlier nine ideas already built. Stage mazes are
        deterministic per `(campaignSeed, index)` and stage ids are stable, which is what makes
        the per-maze leaderboards (idea 4) and ghosts (idea 8) apply per stage for free; late
        stages simply *declare* the living (1) and traffic (3) hazards and the client turns them
        on through the existing opt-in endpoints.

        Difficulty ordering came from the theory module via a new `DifficultyGrader`, and the
        two findings worth remembering are both about measurement discipline:

        - **Ordering must be measured, not reasoned about.** Dead ends per *cell* looks like the
          natural difficulty signal and inverts the small end of the ladder (a 3×3 grades above
          a 5×5). Per *perimeter* fixes it. Found by printing scores, not by thinking harder.
        - **A single-seed test of a randomised ladder is not a test.** Asserting monotonicity on
          one campaign seed passed while the ladder actually walked backwards on 15 of 40 seeds.
          Worse, after the fix the same test still passed with the fix *deleted* — the
          headroom rule is inert at the default config (60/60 either way) and only load-bearing
          at longer ladders (0/60 → 53/60 at ten stages), so the test that pins it had to be
          written at that config. Both numbers are in the code, and the 53/60 is stated rather
          than rounded up: a strictly rising ladder is a measured property of the *default*
          configuration, not a guarantee for every setting.

        Also recorded, since it cost real trust: this roadmap's middle batches were verified with
        `-Dspotbugs.skip`, which hid three findings including a genuine non-atomic
        `volatile` increment in `LivingMazeService`. The gate is green with SpotBugs and
        Checkstyle enabled; skipping a project's own quality gate to move faster is exactly the
        kind of shortcut this ADR's other entries were written to avoid.

12. [x] Consolidation pass (2026-07-30). Two defects in the freshly-shipped roadmap code, both
        found by measuring what the features actually did rather than by reading them:

        - **Campaign planning treated a shared, bounded resource as scratch space.** Grading
          candidates through the normal generate path cached all 54 of them and announced each
          one, so 89% of a campaign's planning work evicted mazes real users were playing and
          told every plugin about mazes that were never served. A feature can be entirely
          correct in its own output and still be a bad citizen of the system it runs in; the
          campaign response looked perfect throughout.
        - **Crossbreeding's "full connectivity" guarantee was quietly deleting a generator's
          defining trait.** Connecting every *cell* rather than every *room* carved away 100%
          of a dungeon parent's rock. The guarantee was never wrong, it was aimed at the wrong
          set — and the honest fix needed a second insight, that habitability has to come from
          the patch's donor parent rather than the stitched grid, because inheriting four edges
          independently can seal a cell both parents had carved.

        The pattern worth keeping from both: the bug was in the part nobody looks at. Neither
        would have shown up in a response body, a screenshot, or a passing test suite, and both
        were found by writing a throwaway probe that counted something.

13. [x] Audit pass (2026-07-30). Having been burned twice by tests that passed for the wrong
        reason, the suite itself was put on trial: six semantic breaks injected one at a time
        (walk through walls, BFS made LIFO, seeds ignored, leaderboard inverted, rate limiting
        off, half of all recorded expansions dropped), each with a full test run and restore.
        All six were caught — the good news, and worth recording as plainly as the failures.

        Two lessons that generalise:

        - **A guarantee can be pinned overall and unpinned where you work.** Two of the six
          survived a *module-scoped* run: `LeaderboardEntry`'s ordering and `SearchRecorder`'s
          fidelity live in core, and every test of them lived in the server module. Whole-reactor
          CI was green either way, so nothing was broken — but `mvn -pl daedalus-core test`, the
          command you actually run while editing core, accepted a worst-first leaderboard and a
          recorder that discarded half its data. Both modules now guard their own invariants.
        - **Pick the metric by measuring, not by name.** Writing the fidelity test, the
          obvious-sounding `cellsVisited` disagreed with the recording by up to 17 expansions;
          `cellsExplored` was the intended counterpart, and the exact relationship
          (`cellsExplored - recorded ∈ {0, 1}`, because the goal's neighbours are never
          requested) only became clear after sweeping 324 solves. A test asserting the
          plausible-looking equality would have failed honestly and been "fixed" by loosening it
          into something that no longer caught anything.

        The two code defects this pass turned up were both small and both echoes of the previous
        batch — a third `==` on a cell cost one function away from the two already fixed, and the
        same volatile-increment shape in the service SpotBugs hadn't flagged. Defect classes
        travel in packs; when one is found, the honest move is to grep for its siblings rather
        than fix the reported instance and move on.

14. [x] Session-lock audit (2026-07-30). The one loose end from the audit above: this roadmap
        added two listeners (traffic occupancy, ghost recording) to a publish path that runs
        while the per-session lock is held, so the question "what does that cost now?" was one
        this work had made worse and never answered.

        Measured, the concern mostly dissolves. A move is ~1.4µs with no listeners and ~1.3µs
        with traffic tracking — the added listeners are free within noise. The ghost recorder's
        trail copy is the only real cost (876µs at the 5,000-move cap) and it runs once, on the
        winning move, blocking nothing after it. Lock ordering is always session→trail with no
        reverse path, so there is no deadlock. **No code change was warranted**, which is a
        legitimate outcome and worth recording as one rather than manufacturing a fix.

        What the measuring did turn up is that the property making this design safe at all —
        per-session scope, so a blocked listener delays only its own player — was defended by
        nothing. Widening the lock to `synchronized (this)` broke a single test out of 186, and
        only after that test existed. It exists now.

        Two methodology notes, both earned by getting it wrong first:

        - **Anchor concurrency mutations precisely.** `GameSessionService` has two
          `synchronized (s)` blocks and `join()`'s comes first, so a first-match replace patched
          the wrong method and produced a confident, meaningless "nothing catches this" result.
        - **A concurrency test you have never watched fail is not yet a test.** The first version
          gave the blocked listener a safety valve equal to the bystander's patience; the valve
          released the lock just as the bystander was still waiting, so the move succeeded and
          the test passed against a genuine global lock. Deliberately breaking the code to watch
          the test go red is the only thing that distinguishes a guarantee from a decoration.

15. [x] End-to-end sweep (2026-07-30). Every feature here was verified in the batch that built
        it, and the later consolidation work then modified services the earlier features depend
        on — `LivingMazeService`, `TrafficService`, `MazeBreeder`. Nothing had ever exercised all
        ten at once, so `sweep/` now does: 14 API checks and 16 browser checks against a running
        server. Both are green, including the flag-off and flag-on multiplayer paths.

        The interesting part was the failures, none of which were where they appeared to be.
        Four first-run "failures" were the sweep asserting contracts I had invented rather than
        read — an illegal agent step answers 400 by documentation, ASCII is content-negotiated
        rather than a `/ascii` path, `join` 404s by design with the flag off, and `move` answers
        `200` with a boolean body, so status-only checking read a correctly-refused wall-teleport
        as an accepted one. **A test that fails against correct behaviour is a bug in the test,
        and writing it teaches you the contract you did not actually know.**

        Then one check flaked: passed, failed, passed. The tempting read is "CI noise". Chased
        instead, it was a real client race — with STOMP unavailable the maze polls, and the poll
        assigned its fetched maze after an await without re-checking currency, so switching maze
        mid-flight reinstated the one you had just left. Forced deterministically by delaying the
        old maze's response, it leaves the player on the previous maze under the new maze's
        leaderboard heading. **Every flake is a race until proven otherwise**; this roadmap's
        last real defect was found by refusing to re-run until green.

16. [x] Hardening (2026-08-17). The re-fire trigger above fired once traffic and fog-of-war
        were both live. `Sealer` closes extra passages without disconnecting the habitable
        graph; `POST /live?seal=` is the opt-in so v1 `/live` stays erosion-only. The
        interesting correction is in ADR-008: the trigger asked for a cut-vertex check and
        the operation removes an edge.
