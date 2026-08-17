// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
import com.daedalus.theory.FacilityPlacement;
import com.daedalus.theory.WaypointTour;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.github.benmanes.caffeine.cache.Ticker;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Waypoint Tour mode (ADR-007 idea 1) — the project's exact TSP solver, made playable.
 *
 * <p>A maze gets a set of waypoints; the player must collect them all and reach the goal. The
 * interesting part is that the server knows the <em>provably optimal</em> collection order:
 * {@link WaypointTour} runs Held-Karp over the waypoint set, so a finished run can be scored
 * against a number that is not an estimate. "You walked 87 steps, the best possible route is
 * 64" is a fact, not a heuristic.
 *
 * <p><b>Placement is k-center, not random.</b> Waypoints come from
 * {@link FacilityPlacement#kCenter}, whose farthest-first greedy is exactly the "spread these
 * out" algorithm — random placement clumps, and a clumped tour is a boring tour. This also
 * gives placement for free from an algorithm the codebase already had and never surfaced.
 *
 * <p><b>Deterministic and server-owned.</b> Waypoints derive from the maze alone, so every
 * player on a given maze solves the same instance. That is what makes the comparison against
 * optimal meaningful between players, and it is why the daily challenge, per-maze leaderboards,
 * ghosts and campaign stages all work in this mode without changing any of them.
 *
 * <p><b>Living mazes keep the coins and move the score (ADR-014).</b> Placement is frozen
 * the first time a maze is asked for a tour. The Held-Karp cost is not: a living tick
 * opens or closes passages under the same waypoints, so a cached {@code optimalCost} would
 * become a lie. {@link #tourFor} always rescores against the cache's current grid.
 *
 * <p><b>Progress is observed, not trusted.</b> Collection is tracked here by listening to
 * {@link PlayerMovedEvent} — the same seam traffic uses — rather than accepting a client's
 * claim about which waypoints it picked up. A client can render whatever it likes; the
 * server's count is the one that scores.
 *
 * <p><b>Bounded</b> (house rule): waypoint count is capped at {@link WaypointTour#MAX_WAYPOINTS}
 * because Held-Karp is {@code O(2^k · k²)}; tours and per-session progress live in Caffeine
 * caches sized by {@code daedalus.waypoint.*}.
 */
@Service
public class WaypointService {

    /** A maze's waypoint set and the best possible route through it. */
    public record Tour(UUID mazeId, List<Point> waypoints, List<Point> optimalOrder,
                       int optimalCost, boolean feasible) {}

    /**
     * How a session is doing against that optimum.
     *
     * @param walked    steps the player has actually taken
     * @param optimal   steps the optimal tour needs (collect everything, then reach the goal)
     * @param collected waypoints reached so far
     * @param complete  every waypoint collected — the run counts as a tour only then
     */
    public record Progress(UUID sessionId, int collected, int total, long walked,
                           int optimal, boolean complete, List<Point> remaining) {}

    private final MazeGenerationService gen;
    private final GameSessionService sessions;
    private final int defaultCount;

    /** Frozen placements — the Held-Karp score is recomputed against the live grid. */
    private final Cache<String, List<Point>> placements;
    private final Cache<UUID, Set<Point>> collected;

    @Autowired
    public WaypointService(MazeGenerationService gen,
                           GameSessionService sessions,
                           @Value("${daedalus.waypoint.count:5}") int defaultCount,
                           @Value("${daedalus.waypoint.max-tours:500}") long maxTours,
                           @Value("${daedalus.waypoint.idle-ttl:2h}") Duration idleTtl) {
        this(gen, sessions, defaultCount, maxTours, idleTtl, Ticker.systemTicker());
    }

    /**
     * Ticker seam — see {@code BoundedStoresTest.everyCacheWithAnIdleTtlExposesASeamForMovingTheClock}
     * for why every idle-bounded store in this package now has one. Short version: deleting
     * {@code expireAfterAccess} from three different services on three different days left the
     * suite green each time, because no test could move a clock.
     */
    WaypointService(MazeGenerationService gen,
                    GameSessionService sessions,
                    int defaultCount,
                    long maxTours,
                    Duration idleTtl,
                    Ticker ticker) {
        this.gen = gen;
        this.sessions = sessions;
        this.defaultCount = clamp(defaultCount);
        this.placements = Caffeine.newBuilder().maximumSize(maxTours)
                .expireAfterAccess(idleTtl).ticker(ticker).build();
        this.collected = Caffeine.newBuilder().maximumSize(maxTours)
                .expireAfterAccess(idleTtl).ticker(ticker).build();
    }

    /**
     * Held-Karp is exponential in the stop count, and the cap is a hard limit rather than
     * advice. Note the {@code - 1}: the goal is a compulsory final stop, so it occupies one of
     * the solver's slots. Clamping to {@code MAX_WAYPOINTS} exactly and then appending the goal
     * hands the solver {@code MAX_WAYPOINTS + 1} stops, which it rejects — turning "you asked
     * for too many waypoints" into a 500 instead of a quietly capped tour.
     */
    private static int clamp(int count) {
        return Math.max(1, Math.min(WaypointTour.MAX_WAYPOINTS - 1, count));
    }

    /** Cached tours — for tests and metrics; see {@code BoundedStoresTest}. */
    public long cachedTours() {
        placements.cleanUp();
        return placements.estimatedSize();
    }

    public int defaultCount() {
        return defaultCount;
    }

    /**
     * The maze's waypoints (frozen on first ask) and the optimal tour on the <em>current</em>
     * grid. Living ticks change the score, not the coins.
     *
     * @return {@code null} when the maze is unknown (the controller answers 404)
     */
    public Tour tourFor(UUID mazeId, Integer count) {
        var cached = gen.find(mazeId);
        if (cached == null) {
            return null;
        }
        int k = clamp(count == null ? defaultCount : count);
        List<Point> waypoints = placements.get(mazeId + ":" + k,
                key -> place(cached.grid(), k));
        return score(mazeId, cached.grid(), waypoints);
    }

    private static List<Point> place(MazeGrid grid, int k) {
        // Ask for k+2 and drop start/goal: k-center's first pick is an extreme cell, which is
        // frequently the start or the goal, and a waypoint sitting on either is not a waypoint.
        var placement = FacilityPlacement.kCenter(grid, k + 2);
        return placement.facilities().stream()
                .filter(p -> !p.equals(grid.start()) && !p.equals(grid.goal()))
                .limit(k)
                .toList();
    }

    private static Tour score(UUID mazeId, MazeGrid grid, List<Point> waypoints) {
        // The tour must end at the goal, so the goal is the final compulsory stop: solving over
        // waypoints alone would score a route that stops wherever the last pickup happens to be.
        List<Point> stops = new java.util.ArrayList<>(waypoints);
        stops.add(grid.goal());
        var tour = WaypointTour.shortestTour(grid, grid.start(), stops);
        return new Tour(mazeId, waypoints, tour.order(), tour.totalCost(), tour.feasible());
    }

    /** Records a pickup when a player steps onto a waypoint of their session's maze. */
    @EventListener
    public void onPlayerMoved(PlayerMovedEvent e) {
        var session = sessions.find(e.sessionId());
        if (session == null) {
            return;
        }
        List<Point> waypoints = placements.getIfPresent(session.mazeId() + ":" + defaultCount);
        if (waypoints == null || !waypoints.contains(e.to())) {
            return; // not a waypoint maze, or not a waypoint cell
        }
        collected.asMap()
                .computeIfAbsent(e.sessionId(), id -> java.util.Collections.synchronizedSet(
                        new LinkedHashSet<>()))
                .add(e.to());
    }

    /**
     * A session's progress against the optimal tour.
     *
     * @return {@code null} when the session or its maze is unknown
     */
    public Progress progressFor(UUID sessionId) {
        var session = sessions.find(sessionId);
        if (session == null) {
            return null;
        }
        Tour tour = tourFor(session.mazeId(), null);
        if (tour == null) {
            return null;
        }
        Set<Point> got = collected.getIfPresent(sessionId);
        Set<Point> snapshot = got == null ? Set.of() : Set.copyOf(got);
        List<Point> remaining = tour.waypoints().stream()
                .filter(p -> !snapshot.contains(p))
                .toList();
        return new Progress(sessionId, snapshot.size(), tour.waypoints().size(),
                session.moveCount(), tour.optimalCost(), remaining.isEmpty(), remaining);
    }
}
