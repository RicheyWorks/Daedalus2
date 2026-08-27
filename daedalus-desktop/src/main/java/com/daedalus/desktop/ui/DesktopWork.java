// SPDX-License-Identifier: MIT

package com.daedalus.desktop.ui;

import com.daedalus.api.dto.Hotspot;
import com.daedalus.engine.MazeGrid;
import com.daedalus.model.GameSession;
import com.daedalus.model.Point;
import com.daedalus.plugin.events.AgentSteppedEvent;
import com.daedalus.server.service.HeuristicLensService;
import com.daedalus.server.service.LivingMazeService;
import com.daedalus.server.service.MazeGenerationService;
import com.daedalus.server.service.MazeSolverService;
import com.daedalus.server.service.TrafficService;
import com.daedalus.solver.SolverBudgetExceededException;
import com.daedalus.engine.Braider;
import com.daedalus.theory.LongestPath;
import com.daedalus.theory.MazeFlow;
import com.daedalus.theory.MazeMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentHashMap;

/**
 * The two long-running desktop operations, as plain {@link Callable}s that know nothing about
 * JavaFX.
 *
 * <h3>Why this class exists</h3>
 *
 * <p>{@link MainController} used to call the generation and solver services inline from its
 * {@code @FXML} handlers, on the JavaFX Application Thread, under a documented assumption:
 * <em>"Generation and solve are fast enough at the Spinner-bounded sizes (≤ 128² = 16 384 cells)
 * that we don't background them; if a later change pushes that into the multi-second range, wrap
 * the calls in a Task."</em>
 *
 * <p>Twenty features later, an audit re-measured that assumption at the spinner's own maximum.
 * The trigger condition it named had been met three times over:
 *
 * <pre>
 *   hunt-and-kill generate, 128x128    1101 ms
 *   IDA* solve, perfect 128x128        1783 ms   (spends its node budget, then refuses)
 *   IDA* solve, dungeon 128x128        1518 ms   (same)
 * </pre>
 *
 * <p>Every one of those is the window frozen — no repaint, no input, and on some desktops the
 * "application is not responding" overlay. Nobody had done anything wrong: the assumption was
 * true when written, the code that invalidated it lives in another module, and no test watches
 * wall-clock. That is exactly the shape of assumption worth re-measuring rather than re-reading.
 *
 * <p><b>Why plain Callables and not Tasks.</b> The desktop module deliberately has no TestFX or
 * Monocle — the existing tests say so outright, and pulling a headless toolkit in to cover glue
 * would be a poor trade. A {@code javafx.concurrent.Task} cannot be exercised without an
 * initialised toolkit, because its state transitions go through {@code Platform.runLater}. Plain
 * callables can be run and asserted on any thread, so the work is testable here and
 * {@link MainController} keeps only the thin wrapper that genuinely needs JavaFX.
 */
@Component
public class DesktopWork {

    /** Same tick count the web {@code /live?ticks=30} button asks for. */
    public static final int LIVE_TICKS = 30;

    /** Same seal factor the web Harden checkbox sends as {@code seal=0.08}. */
    public static final double HARDEN_SEAL = 0.08;

    /** Occupancy source for desktop walks — traffic treats agents and players the same. */
    private static final UUID WALKER = UUID.fromString("aaaaaaaa-bbbb-cccc-dddd-000000000001");

    private final MazeGenerationService generation;
    private final MazeSolverService solving;
    private final HeuristicLensService lens;
    private final LivingMazeService living;
    private final TrafficService traffic;
    private final ConcurrentHashMap<UUID, GhostTape> ghosts = new ConcurrentHashMap<>();

    public DesktopWork(MazeGenerationService generation, MazeSolverService solving) {
        this(generation, solving, fallbackLiving(generation), null);
    }

    public DesktopWork(MazeGenerationService generation, MazeSolverService solving,
                       LivingMazeService living) {
        this(generation, solving, living, null);
    }

    @Autowired
    public DesktopWork(MazeGenerationService generation, MazeSolverService solving,
                       LivingMazeService living, TrafficService traffic) {
        this.generation = generation;
        this.solving = solving;
        this.lens = new HeuristicLensService(generation, 16_384);
        this.living = living;
        this.traffic = traffic;
    }

    private static LivingMazeService fallbackLiving(MazeGenerationService generation) {
        return new LivingMazeService(generation, event -> { }, new SimpleMeterRegistry(),
                Duration.ofSeconds(2), LIVE_TICKS, 2, 0.08, 0.0);
    }

    /** Bring the cached maze to life — same Braider ticks as the web Bring to life button. */
    public LivingMazeService.LiveStatus startLive(UUID mazeId, long seed) {
        return startLive(mazeId, seed, false);
    }

    /**
     * {@code harden} is ADR-008: close extra passages each tick so a braid
     * can tighten, not only open. Same 0.08 the web sends on first Live.
     */
    public LivingMazeService.LiveStatus startLive(UUID mazeId, long seed, boolean harden) {
        return living.start(mazeId, LIVE_TICKS, seed, harden ? HARDEN_SEAL : 0.0);
    }

    public LivingMazeService.LiveStatus liveStatus(UUID mazeId) {
        return living.status(mazeId);
    }

    /** Latest swapped snapshot — living ticks replace the cache in place. */
    public MazeGenerationService.Cached snapshot(UUID mazeId) {
        return generation.find(mazeId);
    }

    /** Same occupancy intake as a fog agent step — the well has no session seat. */
    public void occupy(UUID mazeId, Point from, Point to) {
        if (traffic == null || mazeId == null || to == null) {
            return;
        }
        traffic.onAgentStepped(new AgentSteppedEvent(this, mazeId, WALKER,
                from == null ? to : from, to));
    }

    public TrafficService.TrafficStatus enableTraffic(UUID mazeId) {
        return traffic.enable(mazeId);
    }

    public TrafficService.TrafficStatus trafficStatus(UUID mazeId) {
        return traffic.status(mazeId);
    }

    /**
     * Best finished walk on a maze. Same score formula as a web session
     * complete — higher keeps the seat, empty trails are not ghost material.
     */
    public record GhostTape(UUID mazeId, String playerName, long score, long elapsedMs,
                            Point start, List<GameSession.TimedMove> moves) {
        public GhostTape {
            moves = moves == null ? List.of() : List.copyOf(moves);
        }
    }

    /** Same 100_000 − 10·hops − elapsed/100 floor as {@code GameSessionService}. */
    public static long ghostScore(int hops, long elapsedMs) {
        return Math.max(0L, 100_000L - hops * 10L - elapsedMs / 100L);
    }

    public GhostTape challengeGhost(UUID mazeId, String playerName, Point start,
                                    List<GameSession.TimedMove> moves) {
        if (mazeId == null || start == null || moves == null || moves.isEmpty()) {
            return ghostOf(mazeId);
        }
        long elapsedMs = moves.get(moves.size() - 1).tMs();
        GhostTape fresh = new GhostTape(mazeId, playerName, ghostScore(moves.size(), elapsedMs),
                elapsedMs, start, moves);
        ghosts.merge(mazeId, fresh,
                (incumbent, next) -> next.score() > incumbent.score() ? next : incumbent);
        return ghosts.get(mazeId);
    }

    public GhostTape ghostOf(UUID mazeId) {
        return mazeId == null ? null : ghosts.get(mazeId);
    }

    /** Generate a maze off the FX thread. */
    public Callable<MazeGenerationService.Cached> generateJob(
            String generatorId, int rows, int cols, long seed) {
        return generateJob(generatorId, rows, cols, seed, null);
    }

    /** Weighted generate — {@code null} or empty hotspots stay the uniform-cost contract. */
    public Callable<MazeGenerationService.Cached> generateJob(
            String generatorId, int rows, int cols, long seed,
            List<Hotspot> hotspots) {
        return generateJob(generatorId, rows, cols, seed, hotspots, 0.0);
    }

    /** Same braid pass as the web / tournament — zero stays a tree. */
    public Callable<MazeGenerationService.Cached> generateJob(
            String generatorId, int rows, int cols, long seed,
            List<Hotspot> hotspots, double braid) {
        return () -> generation.generate(generatorId, rows, cols, seed, hotspots, braid);
    }

    /** Distance field from the goal — same sweep the web heat map uses. */
    public Callable<DesktopPaint.Field> fieldJob(MazeGrid grid) {
        return () -> DesktopPaint.Field.of(MazeMetrics.distancesFrom(grid, grid.goal()));
    }

    /** Min-cut passages and dead ends — same overlay as the web Analyze button. */
    public Callable<DesktopPaint.Cuts> cutsJob(MazeGrid grid) {
        return () -> {
            MazeFlow.MinCut cut = MazeFlow.minCutStartToGoal(grid);
            return new DesktopPaint.Cuts(cut.cutSize(), cut.cutEdges(), Braider.deadEnds(grid));
        };
    }

    /** Longest simple start→goal walk — same gold route as the web Hardest button. */
    public Callable<LongestPath.LongPath> hardestJob(MazeGrid grid) {
        return () -> LongestPath.hardestRoute(grid);
    }

    /** k-center safe points — same mint discs as the web Place sanctuaries button. */
    public Callable<DesktopPaint.Sanctuaries> sanctuariesJob(MazeGrid grid) {
        return () -> DesktopPaint.Sanctuaries.of(grid);
    }

    /**
     * The other solver in an arena. Prefers BFS against A*, then A*, then
     * whoever else is registered — desktop has no rival combo.
     */
    public static String rivalOf(String selected, List<String> ids) {
        if (selected == null || ids == null) {
            return null;
        }
        List<String> others = new ArrayList<>();
        for (String id : ids) {
            if (id != null && !id.equals(selected)) {
                others.add(id);
            }
        }
        if (others.isEmpty()) {
            return null;
        }
        if (others.contains("bfs")) {
            return "bfs";
        }
        if (others.contains("astar")) {
            return "astar";
        }
        return others.get(0);
    }

    /** k-center coins and the Held-Karp corridor — same hunt as the web Tour button. */
    public Callable<DesktopPaint.Hunt> huntJob(MazeGrid grid) {
        return () -> DesktopPaint.Hunt.of(grid);
    }

    /**
     * Every registered solver's route — same compare as the web table,
     * painted together so consensus is a brighter corridor.
     */
    public Callable<DesktopPaint.Compare> compareJob(
            List<String> ids, MazeGrid grid, UUID mazeId) {
        return () -> {
            List<DesktopPaint.CompareLane> lanes = new ArrayList<>();
            if (ids == null) {
                return new DesktopPaint.Compare(lanes);
            }
            int color = 0;
            for (String id : ids) {
                if (id == null || id.isBlank()) {
                    continue;
                }
                String ink = DesktopPaint.COMPARE[color % DesktopPaint.COMPARE.length];
                color++;
                try {
                    var result = solving.solve(id, grid, grid.start(), grid.goal(), mazeId, false);
                    lanes.add(new DesktopPaint.CompareLane(id, ink, result.path(), true));
                } catch (SolverBudgetExceededException refused) {
                    lanes.add(new DesktopPaint.CompareLane(id, ink, List.of(), false));
                }
            }
            return new DesktopPaint.Compare(lanes);
        };
    }

    /** Two recorded searches — same blue / gold arena as the web Race button. */
    public Callable<DesktopPaint.Race> raceJob(
            String firstId, String secondId, MazeGrid grid, UUID mazeId) {
        return () -> {
            var first = solving.solve(firstId, grid, grid.start(), grid.goal(), mazeId, true);
            var second = solving.solve(secondId, grid, grid.start(), grid.goal(), mazeId, true);
            return new DesktopPaint.Race(
                    new DesktopPaint.RaceLane(firstId, DesktopPaint.RACE_A,
                            first.expansions(), first.path()),
                    new DesktopPaint.RaceLane(secondId, DesktopPaint.RACE_B,
                            second.expansions(), second.path()));
        };
    }

    /** Three A* bands — same wash as the web Heuristic lens button. */
    public Callable<DesktopPaint.LensWash> lensJob(
            UUID mazeId, HeuristicLensService.Heuristic which) {
        return () -> {
            HeuristicLensService.Lens raw = lens.forMaze(mazeId, which);
            if (raw == null) {
                return null;
            }
            return new DesktopPaint.LensWash(raw.bands(), raw.mustExpand(), raw.tie(),
                    raw.never(), raw.actualExpansions(), raw.routeLength(),
                    raw.optimalCost(), raw.routeOptimal());
        };
    }

    /** Solve a maze off the FX thread, with the recorded expansion order the web paints. */
    public Callable<MazeSolverService.Result> solveJob(
            String solverId, MazeGrid grid, UUID mazeId) {
        return solveJob(solverId, grid, mazeId, true);
    }

    /**
     * {@code replay} false is a quiet re-solve — living and traffic ticks
     * refresh the ribbon without a second search wash.
     */
    public Callable<MazeSolverService.Result> solveJob(
            String solverId, MazeGrid grid, UUID mazeId, boolean replay) {
        return () -> solving.solve(solverId, grid, grid.start(), grid.goal(), mazeId, replay);
    }

    /**
     * Turn a failure into something worth putting in a status bar.
     *
     * <p>A solver giving up on its node budget is not a crash and should not read like one: it
     * is the cost guard doing its job, and the exception already carries a message written to be
     * understood outside the API layer. Anything else keeps its class name, because an unexpected
     * failure that pretends to be routine is how a bug goes unreported.
     */
    public static String describeFailure(String action, Throwable failure) {
        Throwable cause = failure instanceof java.util.concurrent.ExecutionException
                ? failure.getCause() : failure;
        if (cause instanceof SolverBudgetExceededException budget) {
            return budget.getMessage();
        }
        String message = cause == null ? null : cause.getMessage();
        return action + " failed: "
                + (message == null || message.isBlank()
                        ? cause == null ? "unknown error" : cause.getClass().getSimpleName()
                        : message);
    }
}
