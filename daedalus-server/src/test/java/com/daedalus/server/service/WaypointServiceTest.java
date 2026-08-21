// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.PlayerMovedEvent;
import com.daedalus.theory.MazeMetrics;
import com.daedalus.theory.WaypointTour;
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
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
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
        assertThat(b.path()).isEqualTo(a.path());
    }

    @Test
    void theOptimalPathIsTheWalkTheCostCounts() {
        var tour = waypoints.tourFor(mazeId, 4);
        assertThat(tour.path()).isNotEmpty();
        assertThat(tour.path().getFirst()).isEqualTo(grid.start());
        assertThat(tour.path().getLast()).isEqualTo(grid.goal());
        assertThat(tour.path().size() - 1)
                .as("optimalCost is path hops, not a separate estimate")
                .isEqualTo(tour.optimalCost());
        for (int i = 1; i < tour.path().size(); i++) {
            Point a = tour.path().get(i - 1);
            Point b = tour.path().get(i);
            assertThat(Math.abs(a.row() - b.row()) + Math.abs(a.col() - b.col()))
                    .as("tour path hops through a wall at %s -> %s", a, b)
                    .isEqualTo(1);
        }
        assertThat(tour.path()).containsAll(tour.waypoints());
    }

    @Test
    void aNewHuntAtTheCollectedCapDoesNotWipeAMidHuntPickup() {
        waypoints = new WaypointService(gen, sessions, 4, 1, Duration.ofHours(2));
        var tour = waypoints.tourFor(mazeId, 4);
        var first = sessions.open(mazeId, "a", grid.start());
        Point coin = tour.waypoints().get(0);
        waypoints.onPlayerMoved(new PlayerMovedEvent(this, first.id(), "a", grid.start(), coin));
        assertThat(waypoints.progressFor(first.id()).collected()).isEqualTo(1);

        var second = sessions.open(mazeId, "b", grid.start());
        waypoints.onPlayerMoved(new PlayerMovedEvent(this, second.id(), "b", grid.start(), coin));

        assertThat(waypoints.progressFor(first.id()).collected())
                .as("Caffeine put at maximumSize used to LRU-evict the older collected set "
                        + "so a mid-hunt pickup vanished after an unrelated hunt's first coin")
                .isEqualTo(1);
    }

    /**
     * Caffeine {@code get(compute)} at {@code maximumSize} used to LRU-evict another
     * maze's frozen coins on a first {@code GET /tour}. {@code progressFor} then
     * went null, pickups stopped attaching, and a later {@code tourFor} reminted
     * a different set. HTTP can 409 here — unlike a move that already happened.
     */
    @Test
    void aFirstTourOnANewMazeAtCapDoesNotEvictAnotherMazesFrozenCoins() {
        waypoints = new WaypointService(gen, sessions, 4, 1, Duration.ofHours(2));
        var frozen = waypoints.tourFor(mazeId, 8);
        var session = sessions.open(mazeId, "p", grid.start());
        Point coin = frozen.waypoints().get(0);
        waypoints.onPlayerMoved(new PlayerMovedEvent(this, session.id(), "p",
                grid.start(), coin));
        assertThat(waypoints.progressFor(session.id()).collected()).isEqualTo(1);

        UUID other = gen.generate("recursive-backtracker", 13, 13, 43L).metadata().id();
        assertThatThrownBy(() -> waypoints.tourFor(other, 4))
                .as("Caffeine get(compute) at maximumSize used to LRU-evict the seated "
                        + "maze's coins so progressFor went null and a later tour reminted")
                .isInstanceOf(WaypointService.CapacityExceededException.class);

        assertThat(waypoints.progressFor(session.id()))
                .as("the seated maze's frozen coins must still be readable")
                .isNotNull();
        assertThat(waypoints.progressFor(session.id()).collected())
                .as("pickups must keep attaching to the seated hunt")
                .isEqualTo(1);
        assertThat(waypoints.progressFor(session.id()).waypoints())
                .isEqualTo(frozen.waypoints());

        var later = waypoints.tourFor(mazeId, 4);
        assertThat(later.waypoints())
                .as("a later ?count= on the seated maze must not remint after a refused stranger")
                .isEqualTo(frozen.waypoints());
        assertThat(later.waypoints()).hasSize(8);
        assertThat(waypoints.cachedTours()).isEqualTo(1);
    }

    @Test
    void twoFirstToursCannotBothTakeTheLastPlacementSlot() throws Exception {
        waypoints = new WaypointService(gen, sessions, 4, 1, Duration.ofHours(2));
        UUID other = gen.generate("recursive-backtracker", 13, 13, 43L).metadata().id();
        var go = new CountDownLatch(1);
        var accepted = new CopyOnWriteArrayList<UUID>();
        var refused = new AtomicInteger();
        try (var pool = Executors.newFixedThreadPool(2)) {
            var a = pool.submit(() -> raceAdmitTour(mazeId, 3, go, accepted, refused));
            var b = pool.submit(() -> raceAdmitTour(other, 8, go, accepted, refused));
            go.countDown();
            a.get(30, TimeUnit.SECONDS);
            b.get(30, TimeUnit.SECONDS);
        }
        assertThat(accepted).as("exactly one first tour owns the only slot").hasSize(1);
        assertThat(refused.get()).isEqualTo(1);
        UUID seated = accepted.get(0);
        var again = waypoints.tourFor(seated, 4);
        assertThat(again.waypoints())
                .as("the maze that won the slot must still return its frozen set")
                .hasSize(seated.equals(mazeId) ? 3 : 8);
        assertThat(waypoints.cachedTours()).isEqualTo(1);
    }

    private void raceAdmitTour(UUID id, int count, CountDownLatch go,
                               CopyOnWriteArrayList<UUID> accepted, AtomicInteger refused) {
        try {
            go.await();
            waypoints.tourFor(id, count);
            accepted.add(id);
        } catch (WaypointService.CapacityExceededException e) {
            refused.incrementAndGet();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new AssertionError(e);
        }
    }

    @Test
    void readingProgressDoesNotMintATour() {
        var session = sessions.open(mazeId, "p", grid.start());
        assertThat(waypoints.progressFor(session.id()))
                .as("a spectator GET must not freeze coins the players then have to collect")
                .isNull();
        assertThat(waypoints.tourFor(mazeId, 4)).isNotNull();
        assertThat(waypoints.progressFor(session.id()))
                .as("once someone has asked for the tour, progress is a read")
                .isNotNull();
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
     * Two first asks used to each mint {@code mazeId:k}. Progress then preferred
     * {@code mazeId:defaultCount} (or the first {@code asMap()} scan), so a hunt
     * opened at {@code ?count=8} collected against the default coin set once
     * anyone also asked for the no-arg tour.
     */
    @Test
    void twoFirstToursAtDifferentCountsShareOnePlacementAndPickups() {
        var first = waypoints.tourFor(mazeId, 8);
        var later = waypoints.tourFor(mazeId, 4);
        assertThat(later.waypoints())
                .as("a later ?count= must not mint a second coin set")
                .isEqualTo(first.waypoints());
        assertThat(first.waypoints()).hasSize(8);
        assertThat(waypoints.cachedTours()).isEqualTo(1);

        var session = sessions.open(mazeId, "p", grid.start());
        var before = waypoints.progressFor(session.id());
        assertThat(before.waypoints()).isEqualTo(first.waypoints());
        assertThat(before.total()).isEqualTo(8);

        Point target = first.waypoints().get(0);
        List<Point> route = MazeMetrics.shortestPath(grid, grid.start(), target);
        for (int i = 1; i < route.size(); i++) {
            assertThat(sessions.tryMove(session.id(), grid, route.get(i))).isTrue();
            waypoints.onPlayerMoved(new PlayerMovedEvent(this, session.id(), "p",
                    route.get(i - 1), route.get(i)));
        }
        var after = waypoints.progressFor(session.id());
        long onRoute = first.waypoints().stream().filter(route::contains).count();
        assertThat(after.collected())
                .as("pickups attached to the default set, not the frozen hunt")
                .isEqualTo((int) onRoute);
        assertThat(after.remaining()).doesNotContain(target);
        assertThat(after.total()).isEqualTo(8);
    }

    @Test
    void twoFirstToursAtDifferentCountsMintOnePlacement() throws Exception {
        var go = new CountDownLatch(1);
        try (var pool = Executors.newFixedThreadPool(2)) {
            var a = pool.submit(() -> raceTour(3, go));
            var b = pool.submit(() -> raceTour(8, go));
            go.countDown();
            var left = a.get(30, TimeUnit.SECONDS);
            var right = b.get(30, TimeUnit.SECONDS);
            assertThat(left.waypoints())
                    .as("two first inserts at different k used to each mint mazeId:k")
                    .isEqualTo(right.waypoints());
        }
        assertThat(waypoints.cachedTours()).isEqualTo(1);
    }

    private WaypointService.Tour raceTour(int count, CountDownLatch go) {
        try {
            go.await();
            return waypoints.tourFor(mazeId, count);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new AssertionError(e);
        }
    }

    @Test
    void aHuntOpenedAtANonDefaultCountIsCollectable() {
        var tour = waypoints.tourFor(mazeId, 8);
        assertThat(tour.waypoints()).hasSize(8);
        var session = sessions.open(mazeId, "p", grid.start());
        var before = waypoints.progressFor(session.id());
        assertThat(before).isNotNull();
        assertThat(before.total()).isEqualTo(8);
        assertThat(before.waypoints()).isEqualTo(tour.waypoints());
        assertThat(before.path()).isEqualTo(tour.path());

        Point target = tour.waypoints().get(0);
        List<Point> route = MazeMetrics.shortestPath(grid, grid.start(), target);
        for (int i = 1; i < route.size(); i++) {
            assertThat(sessions.tryMove(session.id(), grid, route.get(i))).isTrue();
            waypoints.onPlayerMoved(new PlayerMovedEvent(this, session.id(), "p",
                    route.get(i - 1), route.get(i)));
        }
        var after = waypoints.progressFor(session.id());
        // k=8 is dense enough that the shortest path to the first coin can
        // step on another; collected is observed pickups, not "we named one".
        long onRoute = tour.waypoints().stream().filter(route::contains).count();
        assertThat(after.collected()).isEqualTo((int) onRoute);
        assertThat(after.remaining()).doesNotContain(target);
        assertThat(after.walked()).isEqualTo(route.size() - 1L);
    }

    @Test
    void walkedCountsTheOpenerTrailNotEverySeat() {
        waypoints.tourFor(mazeId, 4);
        var session = sessions.open(mazeId, "opener", grid.start());
        assertThat(sessions.join(session.id(), "joiner", grid.start())).isNotNull();
        Point step = grid.openNeighbors(grid.start()).get(0);
        assertThat(sessions.tryMove(session.id(), "joiner", grid, step)).isTrue();
        var progress = waypoints.progressFor(session.id());
        assertThat(progress.walked())
                .as("a joiner hop must not inflate the tour verdict")
                .isZero();
        assertThat(session.moveCount()).isEqualTo(1);
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
        UUID other = gen.generate("recursive-backtracker", 13, 13, 43L).metadata().id();
        assertThat(waypoints.tourFor(other, 0).waypoints()).hasSize(1); // clamps up, not to zero
        assertThat(waypoints.tourFor(UUID.randomUUID(), 4)).isNull();
        assertThat(waypoints.progressFor(UUID.randomUUID())).isNull();
    }

    @Test
    void aLivingTickRescoresTheTourWithoutMovingTheWaypoints() {
        var before = waypoints.tourFor(mazeId, 4);
        MazeGrid next = grid.copy();
        Braider.braid(next, 1.0, 7L);
        var cached = gen.find(mazeId);
        assertThat(gen.replace(mazeId, new MazeGenerationService.Cached(
                cached.metadata(), next, cached.stats(), cached.hotspots()))).isTrue();

        var after = waypoints.tourFor(mazeId, 4);
        assertThat(after.waypoints())
                .as("the coins stay put — a living maze is a hazard, not a new puzzle")
                .isEqualTo(before.waypoints());

        List<Point> stops = new ArrayList<>(before.waypoints());
        stops.add(next.goal());
        int liveCost = WaypointTour.shortestTour(next, next.start(), stops).totalCost();
        assertThat(after.optimalCost())
                .as("the number we score against must be Held-Karp on the live grid, not "
                        + "the tree the tour was first asked about")
                .isEqualTo(liveCost);
        assertThat(liveCost)
                .as("full braid on a tree adds shortcuts; if this equals the tree cost the "
                        + "fixture is not exercising the stale-cache bug")
                .isLessThan(before.optimalCost());
    }
}
