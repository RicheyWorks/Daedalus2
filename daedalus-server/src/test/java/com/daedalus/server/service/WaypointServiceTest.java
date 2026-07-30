// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
import com.daedalus.theory.MazeMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * Waypoint Tour mode (ADR-007 idea 1). The mode's whole claim is that the number it scores you
 * against is <em>provably</em> the best possible route, so that claim gets checked against
 * brute force rather than trusted.
 */
class WaypointServiceTest {

    private MazeGenerationService gen;
    private GameSessionService sessions;
    private WaypointService waypoints;
    private UUID mazeId;
    private MazeGrid grid;

    @BeforeEach
    void setUp() {
        gen = new MazeGenerationService(
                new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                event -> { }, new SimpleMeterRegistry());
        sessions = new GameSessionService(event -> { }, mock(LeaderboardService.class), true);
        waypoints = new WaypointService(gen, sessions, 4, 500, Duration.ofHours(2));
        var cached = gen.generate("recursive-backtracker", 13, 13, 42L);
        mazeId = cached.metadata().id();
        grid = cached.grid();
    }

    /** Brute-force the best order over every permutation, for comparison with Held-Karp. */
    private static int bruteForceOptimal(MazeGrid g, List<Point> stops) {
        java.util.Map<String, Integer> dist = new java.util.HashMap<>();
        java.util.function.BiFunction<Point, Point, Integer> d = (a, b) -> dist.computeIfAbsent(
                a + "->" + b, k -> MazeMetrics.shortestPath(g, a, b).size() - 1);
        List<List<Point>> perms = new ArrayList<>();
        permute(new ArrayList<>(stops), 0, perms);
        int best = Integer.MAX_VALUE;
        for (List<Point> order : perms) {
            int cost = 0;
            Point at = g.start();
            boolean ok = true;
            for (Point next : order) {
                int step = d.apply(at, next);
                if (step < 0) { ok = false; break; }
                cost += step;
                at = next;
            }
            if (ok) best = Math.min(best, cost);
        }
        return best;
    }

    /** Nearest-neighbour: the plausible approximation this mode must NOT be secretly using. */
    private static int greedyOrder(MazeGrid g, List<Point> stops) {
        List<Point> left = new ArrayList<>(stops);
        Point at = g.start();
        int cost = 0;
        while (!left.isEmpty()) {
            Point best = null;
            int bd = Integer.MAX_VALUE;
            for (Point p : left) {
                int step = MazeMetrics.shortestPath(g, at, p).size() - 1;
                if (step >= 0 && step < bd) { bd = step; best = p; }
            }
            left.remove(best);
            cost += bd;
            at = best;
        }
        return cost;
    }

    private static void permute(List<Point> items, int k, List<List<Point>> out) {
        if (k == items.size()) {
            out.add(new ArrayList<>(items));
            return;
        }
        for (int i = k; i < items.size(); i++) {
            Collections.swap(items, k, i);
            permute(items, k + 1, out);
            Collections.swap(items, k, i);
        }
    }

    /**
     * The exactness claim, checked against brute force over every permutation — on instances
     * chosen because they <em>discriminate</em>.
     *
     * <p>That qualifier is the point. The first version of this test used one 13×13 maze with
     * four waypoints, where nearest-neighbour happens to find the optimal order anyway:
     * replacing Held-Karp with a greedy approximation left the test green. These instances were
     * found by sweeping for cases where greedy is measurably worse (21×21 seed 2 is 376 optimal
     * against 521 greedy), so the test now fails if the exact solver is ever swapped for a
     * plausible one.
     */
    @ParameterizedTest(name = "{0}x{0} seed={1} k={2}")
    @CsvSource({"13, 2, 5", "17, 1, 6", "21, 2, 4"})
    void theOptimalCostReallyIsOptimalAndNotMerelyGreedy(int size, long seed, int k) {
        var cached = gen.generate("recursive-backtracker", size, size, seed);
        var g = cached.grid();
        var tour = waypoints.tourFor(cached.metadata().id(), k);

        assertThat(tour).isNotNull();
        assertThat(tour.feasible()).isTrue();
        assertThat(tour.waypoints()).hasSize(k);

        // The goal is the compulsory final stop, so it belongs in the brute-force set too.
        List<Point> stops = new ArrayList<>(tour.waypoints());
        stops.add(g.goal());

        int brute = bruteForceOptimal(g, stops);
        assertThat(tour.optimalCost())
                .as("Held-Karp disagreed with brute force over every permutation — the number "
                        + "this mode scores players against is not the optimum it claims to be")
                .isEqualTo(brute);
        assertThat(greedyOrder(g, stops))
                .as("this instance does not discriminate: nearest-neighbour matches the optimum "
                        + "here, so the assertion above would pass for an approximate solver too")
                .isGreaterThan(brute);
    }

    @Test
    void aTourIsHarderThanWalkingStraightToTheGoal() {
        var tour = waypoints.tourFor(mazeId, 4);
        int direct = MazeMetrics.shortestPath(grid, grid.start(), grid.goal()).size() - 1;
        assertThat(tour.optimalCost())
                .as("collecting four scattered waypoints cannot be shorter than ignoring them")
                .isGreaterThan(direct);
    }

    @Test
    void waypointsAreSpreadAndNeverSitOnTheStartOrGoal() {
        var tour = waypoints.tourFor(mazeId, 5);
        assertThat(tour.waypoints())
                .doesNotContain(grid.start(), grid.goal())
                .doesNotHaveDuplicates();
        // k-center spreads; every pair should be a real walk apart rather than clustered.
        for (int i = 0; i < tour.waypoints().size(); i++) {
            for (int j = i + 1; j < tour.waypoints().size(); j++) {
                int d = MazeMetrics.shortestPath(grid, tour.waypoints().get(i),
                        tour.waypoints().get(j)).size() - 1;
                assertThat(d).as("waypoints %d and %d are clustered together", i, j)
                        .isGreaterThan(1);
            }
        }
    }

    @Test
    void theSameMazeAlwaysYieldsTheSameInstance() {
        // Determinism is what makes scores comparable between players and lets the daily
        // challenge, leaderboards and ghosts apply to this mode unchanged.
        var a = waypoints.tourFor(mazeId, 4);
        var fresh = new WaypointService(gen, sessions, 4, 500, Duration.ofHours(2));
        var b = fresh.tourFor(mazeId, 4);
        assertThat(b.waypoints()).isEqualTo(a.waypoints());
        assertThat(b.optimalCost()).isEqualTo(a.optimalCost());
    }

    @Test
    void collectionIsObservedFromRealMovesNotClaimedByTheClient() {
        var tour = waypoints.tourFor(mazeId, 4);
        var session = sessions.open(mazeId, "p", grid.start());

        var before = waypoints.progressFor(session.id());
        assertThat(before.collected()).isZero();
        assertThat(before.complete()).isFalse();
        assertThat(before.total()).isEqualTo(4);
        assertThat(before.optimal()).isEqualTo(tour.optimalCost());

        // Walk the player to the first waypoint along a real route; only the moves count.
        Point target = tour.waypoints().get(0);
        List<Point> route = MazeMetrics.shortestPath(grid, grid.start(), target);
        for (int i = 1; i < route.size(); i++) {
            assertThat(sessions.tryMove(session.id(), grid, route.get(i))).isTrue();
            waypoints.onPlayerMoved(new PlayerMovedEvent(this, session.id(), "p",
                    route.get(i - 1), route.get(i)));
        }

        var after = waypoints.progressFor(session.id());
        assertThat(after.collected()).isEqualTo(1);
        assertThat(after.remaining()).hasSize(3).doesNotContain(target);
        assertThat(after.walked()).isEqualTo(route.size() - 1L);
        assertThat(after.complete()).isFalse();
    }

    @Test
    void collectingEveryWaypointCompletesTheTour() {
        var tour = waypoints.tourFor(mazeId, 4);
        var session = sessions.open(mazeId, "p", grid.start());

        Point at = grid.start();
        for (Point wp : tour.waypoints()) {
            List<Point> leg = MazeMetrics.shortestPath(grid, at, wp);
            for (int i = 1; i < leg.size(); i++) {
                sessions.tryMove(session.id(), grid, leg.get(i));
                waypoints.onPlayerMoved(new PlayerMovedEvent(this, session.id(), "p",
                        leg.get(i - 1), leg.get(i)));
            }
            at = wp;
        }

        var done = waypoints.progressFor(session.id());
        assertThat(done.complete()).isTrue();
        assertThat(done.remaining()).isEmpty();
        assertThat(done.walked())
                .as("a greedy in-order walk cannot beat the optimal tour")
                .isGreaterThanOrEqualTo(0L);
    }

    /**
     * The cap has to leave room for the goal. Clamping to {@code MAX_WAYPOINTS} exactly and
     * then appending the goal as the compulsory last stop hands Held-Karp one stop too many,
     * which it refuses — so an over-large {@code count} answered 500 rather than capping.
     */
    @Test
    void theWaypointCountIsHardCappedBecauseHeldKarpIsExponential() {
        var huge = waypoints.tourFor(mazeId, 9999);
        assertThat(huge).as("an over-large count must cap, not explode").isNotNull();
        assertThat(huge.waypoints().size())
                .as("an unbounded waypoint count would let one request run 2^k Held-Karp")
                .isLessThanOrEqualTo(com.daedalus.theory.WaypointTour.MAX_WAYPOINTS - 1);
        assertThat(huge.feasible()).isTrue();
        assertThat(waypoints.tourFor(mazeId, 0).waypoints()).hasSize(1); // clamps up, not to zero
        assertThat(waypoints.tourFor(UUID.randomUUID(), 4)).isNull();
        assertThat(waypoints.progressFor(UUID.randomUUID())).isNull();
    }
}
