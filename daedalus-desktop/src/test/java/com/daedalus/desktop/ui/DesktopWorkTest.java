// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.Sealer;
import com.daedalus.engine.WeightedMazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.model.GameSession;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import com.daedalus.solver.SolverBudgetExceededException;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.solver.solvers.IDAStarSolver;
import com.daedalus.solver.solvers.SolverRegistry;
import com.daedalus.server.service.GameSessionService;
import com.daedalus.server.service.HeuristicLensService;
import com.daedalus.server.service.LeaderboardService;
import com.daedalus.server.service.LivingMazeService;
import com.daedalus.server.service.TrafficService;
import com.daedalus.theory.MazeMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.BooleanSupplier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The desktop's background work, tested without a JavaFX toolkit.
 *
 * <p>That is the reason {@link DesktopWork} exists as plain {@link java.util.concurrent.Callable}s
 * rather than as {@code Task}s: a Task routes its state transitions through
 * {@code Platform.runLater} and cannot run headless, and this module deliberately carries no
 * TestFX or Monocle. Splitting the work from the wrapper keeps the part with actual behaviour
 * testable and leaves only glue in the controller.
 */
class DesktopWorkTest {

    private MazeGenerationService generation;
    private MazeSolverService solving;
    private DesktopWork work;
    private final AtomicInteger generationsPerformed = new AtomicInteger();

    @BeforeEach
    void setUp() {
        generation = new MazeGenerationService(
                new GeneratorRegistry(List.of(
                        new RecursiveBacktrackerGenerator(), new DungeonGenerator())),
                event -> generationsPerformed.incrementAndGet(), new SimpleMeterRegistry());
        solving = new MazeSolverService(
                new SolverRegistry(List.of(new AStarSolver(), new BfsSolver(),
                        new IDAStarSolver())),
                event -> { }, new SimpleMeterRegistry());
        work = new DesktopWork(generation, solving);
    }

    @Test
    void theGenerateJobDoesNothingUntilItIsCalled() throws Exception {
        // The point of returning a Callable is that construction is free and the work happens on
        // whichever thread runs it. If building the job did the generating, moving it to a Task
        // would have changed nothing at all — the freeze would just have moved to the click.
        var job = work.generateJob("recursive-backtracker", 21, 21, 7L);

        // Asserting the job is non-null proves nothing — that was the first version of this
        // test, and a mutation that generated eagerly and returned the finished maze from the
        // lambda survived it untouched. The service publishes an event per generation, so the
        // counter is the observable difference between lazy and eager.
        assertThat(generationsPerformed)
                .as("building the job must not do the work; otherwise the freeze just moves "
                        + "from the Task to the button click")
                .hasValue(0);

        var cached = job.call();

        assertThat(generationsPerformed).hasValue(1);
        assertThat(cached.grid().rows()).isEqualTo(21);
        assertThat(generation.find(cached.metadata().id())).isNotNull();
    }

    @Test
    void aBraidOpensDeadEndsOnTheSameSeed() throws Exception {
        var tree = work.generateJob("recursive-backtracker", 21, 31, 7L, null, 0.0).call();
        var loops = work.generateJob("recursive-backtracker", 21, 31, 7L, null, 0.8).call();
        assertThat(tree.braid()).isNull();
        assertThat(loops.braid()).isEqualTo(0.8);
        assertThat(openPassages(loops.grid()))
                .as("0.8 braid must open dead ends the tree kept closed")
                .isGreaterThan(openPassages(tree.grid()));
    }

    @Test
    void theFieldJobIsZeroAtTheGoal() throws Exception {
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        DesktopPaint.Field field = work.fieldJob(cached.grid()).call();
        var goal = cached.grid().goal();
        var start = cached.grid().start();
        assertThat(field).isNotNull();
        assertThat(field.distances()[goal.row()][goal.col()]).isZero();
        assertThat(field.distances()[start.row()][start.col()]).isGreaterThan(0);
        assertThat(field.maxDistance()).isGreaterThan(0);
    }

    @Test
    void aTreeHardestRouteIsTheUniqueWalk() throws Exception {
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        var hardest = work.hardestJob(cached.grid()).call();
        assertThat(hardest.exact()).isTrue();
        assertThat(hardest.path().getFirst()).isEqualTo(cached.grid().start());
        assertThat(hardest.path().getLast()).isEqualTo(cached.grid().goal());
        var shortest = work.solveJob("bfs", cached.grid(), cached.metadata().id()).call();
        assertThat(hardest.path())
                .as("a perfect maze has one simple start-to-goal walk")
                .isEqualTo(shortest.path());
    }

    @Test
    void fiveSanctuariesCoverTheMaze() throws Exception {
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        DesktopPaint.Sanctuaries safe = work.sanctuariesJob(cached.grid()).call();
        assertThat(safe.placements()).hasSize(DesktopPaint.SANCTUARY_K);
        assertThat(safe.worstServed()).isNotNull();
        int nearest = Integer.MAX_VALUE;
        for (var site : safe.placements()) {
            int[][] fromSite = MazeMetrics.distancesFrom(cached.grid(), site);
            int d = fromSite[safe.worstServed().row()][safe.worstServed().col()];
            if (d >= 0 && d < nearest) {
                nearest = d;
            }
        }
        assertThat(nearest)
                .as("the coral ring sits on the cell that owns the covering radius")
                .isEqualTo(safe.coveringRadius());
    }

    @Test
    void aManhattanLensPartitionsEveryReachableCell() throws Exception {
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        DesktopPaint.LensWash lens = work.lensJob(
                cached.metadata().id(), HeuristicLensService.Heuristic.MANHATTAN).call();
        assertThat(lens).isNotNull();
        assertThat(lens.mustExpand() + lens.tie() + lens.never())
                .as("every reachable cell lands in one band")
                .isEqualTo(11 * 11);
        assertThat(lens.routeOptimal()).isTrue();
        int[][] bands = lens.bands();
        for (int[] row : bands) {
            for (int band : row) {
                assertThat(band).isBetween(-1, 2);
            }
        }
    }

    @Test
    void aTreeHasOneChokepoint() throws Exception {
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        DesktopPaint.Cuts cuts = work.cutsJob(cached.grid()).call();
        assertThat(cuts.cutSize())
                .as("a perfect maze has one start-to-goal seal")
                .isEqualTo(1);
        assertThat(cuts.chokepoints()).hasSize(1);
        assertThat(cuts.deadEnds()).isNotEmpty();
    }

    private static int openPassages(MazeGrid grid) {
        int n = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (grid.isOpen(r, c, Direction.EAST)) {
                    n++;
                }
                if (grid.isOpen(r, c, Direction.SOUTH)) {
                    n++;
                }
            }
        }
        return n;
    }

    @Test
    void theSolveJobReturnsARouteForTheMazeItWasGiven() throws Exception {
        var cached = work.generateJob("recursive-backtracker", 21, 21, 7L).call();

        var result = work.solveJob("astar", cached.grid(), cached.metadata().id()).call();

        assertThat(result.path()).isNotEmpty();
        assertThat(result.path().get(0)).isEqualTo(cached.grid().start());
        assertThat(result.path().get(result.path().size() - 1)).isEqualTo(cached.grid().goal());
        assertThat(result.expansions())
                .as("replay records the search so the desktop can wash it like the web")
                .isNotEmpty();
    }

    @Test
    void aRacePitsTheSelectedSolverAgainstARival() throws Exception {
        assertThat(DesktopWork.rivalOf("astar", List.of("astar", "bfs", "ida-star")))
                .isEqualTo("bfs");
        assertThat(DesktopWork.rivalOf("bfs", List.of("astar", "bfs")))
                .isEqualTo("astar");
        assertThat(DesktopWork.rivalOf("astar", List.of("astar"))).isNull();
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        DesktopPaint.Race race = work.raceJob(
                "astar", "bfs", cached.grid(), cached.metadata().id()).call();
        assertThat(race.first().id()).isEqualTo("astar");
        assertThat(race.first().color()).isEqualTo(DesktopPaint.RACE_A);
        assertThat(race.second().id()).isEqualTo("bfs");
        assertThat(race.second().color()).isEqualTo(DesktopPaint.RACE_B);
        assertThat(race.first().expansions()).isNotEmpty();
        assertThat(race.second().expansions()).isNotEmpty();
        assertThat(race.first().path().getLast()).isEqualTo(cached.grid().goal());
    }

    @Test
    void aComparePaintsEveryRegisteredSolverRoute() throws Exception {
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        DesktopPaint.Compare compared = work.compareJob(
                List.of("astar", "bfs", "ida-star"), cached.grid(),
                cached.metadata().id()).call();
        assertThat(compared.lanes()).hasSize(3);
        assertThat(compared.lanes().get(0).id()).isEqualTo("astar");
        assertThat(compared.lanes().get(0).color()).isEqualTo(DesktopPaint.COMPARE[0]);
        assertThat(compared.lanes().get(1).color()).isEqualTo(DesktopPaint.COMPARE[1]);
        for (DesktopPaint.CompareLane lane : compared.lanes()) {
            assertThat(lane.ok()).isTrue();
            assertThat(lane.path().getFirst()).isEqualTo(cached.grid().start());
            assertThat(lane.path().getLast()).isEqualTo(cached.grid().goal());
        }
    }

    @Test
    void aHuntPlacesFiveCoinsOffTheStartAndGoal() throws Exception {
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        DesktopPaint.Hunt hunt = work.huntJob(cached.grid()).call();
        assertThat(hunt.waypoints()).hasSize(DesktopPaint.WAYPOINT_K);
        assertThat(hunt.waypoints()).doesNotContain(cached.grid().start(), cached.grid().goal());
        assertThat(hunt.feasible()).isTrue();
        assertThat(hunt.path().getFirst()).isEqualTo(cached.grid().start());
        assertThat(hunt.path().getLast()).isEqualTo(cached.grid().goal());
        assertThat(hunt.optimalCost()).isEqualTo(hunt.path().size() - 1);
    }

    @Test
    void bringingATreeToLifeOpensDeadEndsOnTheCachedMaze() throws Exception {
        LivingMazeService living = new LivingMazeService(generation, event -> { },
                new SimpleMeterRegistry(), Duration.ofMillis(25), DesktopWork.LIVE_TICKS,
                2, 0.08, 0.0);
        work = new DesktopWork(generation, solving, living);
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        int before = openPassages(cached.grid());
        var status = work.startLive(cached.metadata().id(), 7L);
        assertThat(status.active()).isTrue();
        assertThat(status.ticksRequested()).isEqualTo(DesktopWork.LIVE_TICKS);
        awaitUntil(() -> {
            var snap = work.snapshot(cached.metadata().id());
            return snap != null && openPassages(snap.grid()) > before;
        }, "erosion to open a wall");
        var after = work.snapshot(cached.metadata().id());
        assertThat(after.grid())
                .as("the cache must serve a new snapshot — the well follows replace")
                .isNotSameAs(cached.grid());
        assertThat(openPassages(after.grid())).isGreaterThan(before);
        DesktopPaint.Hunt hunt = work.huntJob(cached.grid()).call();
        DesktopPaint.Hunt retargeted = DesktopPaint.Hunt.retarget(after.grid(), hunt.waypoints());
        assertThat(retargeted.waypoints())
                .as("living ticks must not move the coins")
                .isEqualTo(hunt.waypoints());
        assertThat(retargeted.feasible()).isTrue();
        var treeWalk = work.solveJob("bfs", cached.grid(), cached.metadata().id(), false).call();
        assertThat(treeWalk.expansions())
                .as("quiet follow must skip the search wash")
                .isNull();
        var later = work.solveJob("bfs", after.grid(), after.metadata().id(), false).call();
        assertThat(later.path().getLast()).isEqualTo(after.grid().goal());
        assertThat(later.path().size())
                .as("opening walls can only shorten the unique tree walk")
                .isLessThanOrEqualTo(treeWalk.path().size());
    }

    @Test
    void hardeningABraidClosesExtraPassages() throws Exception {
        LivingMazeService living = new LivingMazeService(generation, event -> { },
                new SimpleMeterRegistry(), Duration.ofMillis(25), DesktopWork.LIVE_TICKS,
                2, 0.0, 0.0);
        work = new DesktopWork(generation, solving, living);
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L, null, 0.8).call();
        int extras = Sealer.closablePassages(cached.grid()).size();
        assertThat(extras)
                .as("0.8 braid must leave loops the sealer can close")
                .isGreaterThan(0);
        var status = work.startLive(cached.metadata().id(), 7L, true);
        assertThat(status.active()).isTrue();
        awaitUntil(() -> {
            var snap = work.snapshot(cached.metadata().id());
            return snap != null && Sealer.closablePassages(snap.grid()).size() < extras;
        }, "hardening to close a loop");
        assertThat(Sealer.closablePassages(work.snapshot(cached.metadata().id()).grid()))
                .as("ADR-008 closes extras; reachability cannot shrink")
                .hasSizeLessThan(extras);
    }

    @Test
    void walkingUnderTrafficBloomsAHotspotOnTheCachedMaze() throws Exception {
        TrafficService traffic = new TrafficService(generation,
                new GameSessionService(event -> { }, new LeaderboardService(null, false)),
                event -> { }, 4.0, 0.80, 200.0, Duration.ofMillis(25), 2, 8,
                new SimpleMeterRegistry());
        work = new DesktopWork(generation, solving, fallbackLiving(), traffic);
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        var id = cached.metadata().id();
        Point start = cached.grid().start();
        assertThat(work.enableTraffic(id).active()).isTrue();
        assertThat(work.snapshot(id).grid()).isInstanceOf(WeightedMazeGrid.class);
        work.occupy(id, start, start);
        awaitUntil(() -> {
            var snap = work.snapshot(id);
            return snap != null && snap.grid().weightOf(start.row(), start.col()) > 1.0;
        }, "occupancy to bloom as cost");
        var after = work.snapshot(id);
        assertThat(after.grid().weightOf(start.row(), start.col())).isGreaterThan(1.0);
        assertThat(after.hotspots())
                .as("congestion IS a hotspot — the coral wash already paints it")
                .anySatisfy(h -> {
                    assertThat(h.row()).isEqualTo(start.row());
                    assertThat(h.col()).isEqualTo(start.col());
                });
    }

    private LivingMazeService fallbackLiving() {
        return new LivingMazeService(generation, event -> { }, new SimpleMeterRegistry(),
                Duration.ofSeconds(2), DesktopWork.LIVE_TICKS, 2, 0.08, 0.0);
    }

    @Test
    void aFasterFinishKeepsTheGhostSeat() throws Exception {
        var cached = work.generateJob("recursive-backtracker", 11, 11, 7L).call();
        var id = cached.metadata().id();
        Point start = cached.grid().start();
        assertThat(DesktopWork.ghostScore(10, 1_000)).isEqualTo(100_000 - 100 - 10);
        assertThat(work.challengeGhost(id, "slow", start, List.of())).isNull();
        DesktopWork.GhostTape first = work.challengeGhost(id, "slow", start, List.of(
                new GameSession.TimedMove(cached.grid().goal(), 4_000)));
        assertThat(first.playerName()).isEqualTo("slow");
        DesktopWork.GhostTape kept = work.challengeGhost(id, "fast", start, List.of(
                new GameSession.TimedMove(cached.grid().goal(), 1_000)));
        assertThat(kept.playerName())
                .as("higher score (fewer hops and less time) keeps the seat")
                .isEqualTo("fast");
        DesktopWork.GhostTape still = work.challengeGhost(id, "later", start, List.of(
                new GameSession.TimedMove(cached.grid().goal(), 8_000)));
        assertThat(still.playerName()).isEqualTo("fast");
        assertThat(work.ghostOf(id).elapsedMs()).isEqualTo(1_000);
    }

    private static void awaitUntil(BooleanSupplier condition, String what) {
        long deadline = System.nanoTime() + Duration.ofSeconds(10).toNanos();
        while (System.nanoTime() < deadline) {
            if (condition.getAsBoolean()) {
                return;
            }
            try {
                Thread.sleep(10);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new AssertionError("interrupted awaiting " + what, e);
            }
        }
        throw new AssertionError("timed out awaiting " + what);
    }

    @Test
    void aSolverGivingUpSurfacesItsOwnExplanation_notAStackTrace() {
        // IDA* refuses on a dungeon of this size. The desktop is a second consumer of the same
        // core exception the REST layer turns into a 422, and it had no handling of its own —
        // this pins that the message a user sees is the one the exception was written to give,
        // rather than a class name or a bare "null".
        MazeGrid dungeon = new DungeonGenerator().generate(25, 25, 1000L, new MazeStats());
        MazeMetrics.placeStartAndGoalAtExtremes(dungeon);
        var adopted = generation.adopt(dungeon, "dungeon", 1000L);

        var job = work.solveJob("ida-star", adopted.grid(), adopted.metadata().id());

        assertThatThrownBy(job::call).isInstanceOf(SolverBudgetExceededException.class);

        String shown = DesktopWork.describeFailure("Solve",
                new SolverBudgetExceededException("ida-star", 5_000_000L));
        assertThat(shown)
                .contains("ida-star")
                .contains("not a statement that the maze is unsolvable")
                .doesNotContain("Solve failed:");
    }

    @Test
    void anUnexpectedFailureKeepsItsIdentity_ratherThanReadingAsRoutine() {
        // The inverse of the case above. A budget refusal is normal and gets its own words; a
        // genuine bug must not be dressed up to look like one, or it never gets reported.
        String shown = DesktopWork.describeFailure("Generation",
                new IllegalStateException("generator returned null grid: broken"));

        assertThat(shown).isEqualTo("Generation failed: generator returned null grid: broken");
    }

    @Test
    void aWrappedFailureIsUnwrapped_becauseThatIsHowATaskReportsIt() {
        // Task.getException() hands back what the Callable threw, but a job run through a
        // Future arrives wrapped. Reporting "ExecutionException: null" to a user would be
        // useless, so the cause is unwrapped before it reaches the status bar.
        String shown = DesktopWork.describeFailure("Solve",
                new ExecutionException(new SolverBudgetExceededException("ida-star", 42L)));

        // `contains("ida-star")` was the first version and it could not fail: an
        // ExecutionException's own message is the cause's toString, so the wrapped text
        // contains every substring the unwrapped text does. The difference is what is NOT
        // there — no wrapper class name, and no "Solve failed:" prefix, because a budget
        // refusal is not a crash.
        assertThat(shown).isEqualTo(new SolverBudgetExceededException("ida-star", 42L).getMessage());
        assertThat(shown)
                .doesNotContain("SolverBudgetExceededException")
                .doesNotContain("Solve failed:");
    }

    @Test
    void aFailureWithNoMessageStillSaysSomethingUseful() {
        String shown = DesktopWork.describeFailure("Generation", new NullPointerException());

        assertThat(shown).isEqualTo("Generation failed: NullPointerException");
    }
}
