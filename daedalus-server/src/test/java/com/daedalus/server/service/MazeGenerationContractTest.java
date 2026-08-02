// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.MazeGeneratedEvent;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.theory.MazeMetrics;
import com.github.benmanes.caffeine.cache.Ticker;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The substrate's own contracts. Every feature in this server commits through
 * {@link MazeGenerationService} — generation, the cache, the swap point both tickers use, the
 * adoption path for crossbred mazes, the circuit-breaker fallback — and until mutations were
 * pointed at it, eight of its thirteen guarantees were unpinned. That is the shape of a substrate
 * blind spot: exercised by everything, asserted about by nothing, because each caller tests its
 * own concern and takes the foundation for granted.
 *
 * <p><b>The one worth reading twice.</b> {@code MazeGenerationStartGoalTest} exists <em>because</em>
 * of a real bug: start and goal used to be dropped at fixed corners, and "a dungeon's corners are
 * solid rock, so the served maze was unsolvable and a play session opened inside a wall". Delete
 * {@code placeStartAndGoalAtExtremes} from {@code generate} today and all three of its tests still
 * pass. The dungeon case checks one (generator, size, seed) triple, and at 15×21 seed 7 the
 * corners happen to be carved and connected; the perfect-maze case asserts the route is at least
 * as long as the grid's longer dimension, which a corner-to-corner walk clears on its own. The
 * regression test for the documented bug does not detect the bug's return. So the two assertions
 * below are the ones that do: a sweep of dungeon seeds (corner luck does not hold across twelve),
 * and — for a perfect maze, where the graph is a tree and the double-BFS placement is exact —
 * the route between start and goal must be the maze's diameter, not merely long.
 */
class MazeGenerationContractTest {

    private final List<Object> published = new ArrayList<>();
    private final GeneratorRegistry registry = new GeneratorRegistry(
            List.of(new RecursiveBacktrackerGenerator(), new DungeonGenerator()));

    private MazeGenerationService service() {
        return new MazeGenerationService(registry, published::add, new SimpleMeterRegistry());
    }

    private static int routeLength(MazeGrid grid, Point from, Point to) {
        List<Point> route = new BfsSolver().solve(grid, from, to, new MazeStats());
        return route.isEmpty() ? -1 : route.size() - 1;
    }

    /* ------------------------------------------------------------------ */

    @ParameterizedTest
    @ValueSource(longs = {1L, 2L, 3L, 5L, 7L, 11L, 13L, 17L, 19L, 23L, 42L, 99999L})
    void everyGeneratedDungeonOpensOnCarvedGroundAndCanBeFinished(long seed) {
        var grid = service().generate("dungeon", 15, 21, seed).grid();

        assertThat(grid.openNeighbors(grid.start()))
                .as("seed %d: start is solid rock — a session opens inside a wall", seed)
                .isNotEmpty();
        assertThat(grid.openNeighbors(grid.goal()))
                .as("seed %d: goal is solid rock", seed)
                .isNotEmpty();
        assertThat(routeLength(grid, grid.start(), grid.goal()))
                .as("seed %d: no route between the served start and goal", seed)
                .isPositive();
    }

    @Test
    void aPerfectMazeIsPlayedAcrossItsDiameterRatherThanCornerToCorner() {
        var grid = service().generate("recursive-backtracker", 15, 21, 7L).grid();

        // A perfect maze is a tree, so the double-BFS placement is exact and this is an equality,
        // not a bound. "At least as long as the grid is wide" is not: corner to corner clears
        // that comfortably, which is why the old assertion could not tell the two apart.
        int diameter = MazeMetrics.exactDiameter(grid).distance();
        assertThat(routeLength(grid, grid.start(), grid.goal()))
                .as("start and goal must be the maze's two farthest-apart cells")
                .isEqualTo(diameter);
    }

    @Test
    void adoptFinishesAMazeTheSameWayGenerationDoes() {
        // Crossbred offspring arrive as bare grids with default (corner) start and goal, and the
        // javadoc promises adopt runs generation's finishing steps so they are "indistinguishable
        // from a generated one downstream". Three of those steps, none of them pinned.
        MazeGrid child = registry.require("recursive-backtracker")
                .generate(15, 21, 4242L, new MazeStats());
        child.setStart(new Point(0, 0));
        child.setGoal(new Point(child.rows() - 1, child.cols() - 1));

        var svc = service();
        published.clear();
        var adopted = svc.adopt(child, "crossbreed", 4242L);

        assertThat(routeLength(adopted.grid(), adopted.grid().start(), adopted.grid().goal()))
                .as("an adopted maze gets extremes placement too, or it is playable corner to "
                        + "corner while every generated maze is not")
                .isEqualTo(MazeMetrics.exactDiameter(adopted.grid()).distance());
        assertThat(adopted.metadata().start()).isEqualTo(adopted.grid().start());
        assertThat(svc.find(adopted.metadata().id())).as("adopted mazes are fetchable").isNotNull();
        assertThat(published)
                .as("plugins and the STOMP bridge learn about an adopted maze the same way they "
                        + "learn about a generated one — silence here is a maze nobody is told of")
                .anySatisfy(e -> assertThat(e)
                        .isInstanceOfSatisfying(MazeGeneratedEvent.class, ev ->
                                assertThat(ev.metadata().id()).isEqualTo(adopted.metadata().id())));
    }

    @Test
    void replaceNeverReinsertsAMazeTheCacheHasDropped() {
        var svc = service();
        var cached = svc.generate("recursive-backtracker", 9, 9, 1L);
        UUID gone = UUID.randomUUID();

        assertThat(svc.replace(gone, cached)).as("replace on an unknown id answers false").isFalse();
        // The answer is only half the contract. `put` also returns null for an absent key, so a
        // naive swap satisfies the assertion above while putting the entry back — and both
        // tickers treat false as "stop", leaving a resurrected maze nobody will ever evict or
        // tick again.
        assertThat(svc.find(gone))
                .as("a false answer must mean nothing was written, not that nothing was returned")
                .isNull();
    }

    @Test
    void theMazeCacheExpiresIdleEntriesAndNotOnlyOversizedOnes() {
        FakeClock clock = new FakeClock();
        var svc = new MazeGenerationService(registry, published::add, new SimpleMeterRegistry(),
                5000, Duration.ofHours(2), clock);
        UUID id = svc.generate("recursive-backtracker", 9, 9, 1L).metadata().id();
        assertThat(svc.find(id)).isNotNull();

        clock.advance(Duration.ofHours(3));

        assertThat(svc.find(id))
                .as("size and idle are separate bounds; with only the first, a quiet instance "
                        + "keeps every maze it ever generated until 5,000 more arrive")
                .isNull();
    }

    @Test
    void aHotspotOnTheRowJustPastTheGridIsACallerErrorNotAnIndexCrash() {
        // The check is `>= rows`, and the boundary is the whole point of it: row == rows is the
        // first invalid index, and it is the one an off-by-one lets through. Existing coverage
        // used a comfortably out-of-range cell, which `> rows` catches too.
        var svc = service();
        assertThatThrownBy(() -> svc.generate("recursive-backtracker", 9, 9, 1L,
                List.of(new Hotspot(9, 3, 5.0))))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("outside");
        assertThatThrownBy(() -> svc.generate("recursive-backtracker", 9, 9, 1L,
                List.of(new Hotspot(3, 9, 5.0))))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void theFallbackRethrowsACallerErrorInsteadOfServingADifferentMaze() throws Exception {
        // A bad request that reaches the breaker must still answer 400. Without the rethrow the
        // caller gets 200 and a maze they did not ask for — the failure mode the fallback's own
        // comment describes, and the one no test covered.
        var svc = service();
        Method fallback = MazeGenerationService.class.getDeclaredMethod(
                "fallback", String.class, int.class, int.class, long.class,
                java.util.List.class, Throwable.class);
        fallback.setAccessible(true);
        var callerError = new IllegalArgumentException("unknown generator: nope");

        assertThatThrownBy(() -> fallback.invoke(svc, "nope", 9, 9, 1L, null, callerError))
                .isInstanceOf(InvocationTargetException.class)
                .cause().isSameAs(callerError);
    }

    @Test
    void aGeneratorThatReturnsNullFailsLoudlyRatherThanCachingNothing() {
        // Not a defensive-code formality: generators are a plugin extension point, so "returns
        // null" is third-party behaviour this service has to survive. The guard turns it into a
        // named failure at the source; without it the null flows out as a Cached nobody can
        // read, and the NullPointerException lands in whichever caller touches it first.
        var withBrokenPlugin = new GeneratorRegistry(List.of(new NullGenerator()));
        var svc = new MazeGenerationService(withBrokenPlugin, published::add,
                new SimpleMeterRegistry());

        assertThatThrownBy(() -> svc.generate("null-plugin", 9, 9, 1L))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("null-plugin");
    }

    /** A plugin generator that violates the interface's contract. */
    private static final class NullGenerator implements com.daedalus.engine.MazeGenerator {
        @Override public String id() { return "null-plugin"; }

        @Override public String displayName() { return "Null Plugin"; }

        @Override public com.daedalus.model.AlgorithmDescriptor descriptor() {
            return new com.daedalus.model.AlgorithmDescriptor("null-plugin", "Null Plugin",
                    "generator", "O(1)", "none", "returns nothing at all");
        }

        @Override public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
            return null;
        }
    }

    /** Moves Caffeine's clock without moving the wall clock — as {@code BoundedStoresTest} does. */
    private static final class FakeClock implements Ticker {
        private long nanos;

        @Override
        public long read() {
            return nanos;
        }

        void advance(Duration by) {
            nanos += by.toNanos();
        }
    }
}
