// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.solver.MazeSolver;
import com.daedalus.solver.SolverBudgetExceededException;
import com.daedalus.solver.solvers.SolverRegistry;
import com.daedalus.theory.MazeMetrics;
import com.daedalus.theory.SampleStats;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import com.github.benmanes.caffeine.cache.Ticker;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Solver tournament (ADR-007 idea 10) and adversarial seed search (ADR-007 idea 7).
 *
 * <h3>What a tournament is actually for — measured, not assumed</h3>
 *
 * <p>ADR-007 pitched this as "the arena races once; a tournament says which solver is
 * <em>actually</em> better". A probe run before any of this existed says that framing is only
 * half right, and which half depends entirely on the maze:
 *
 * <ul>
 *   <li><b>Perfect mazes: the single race is already correct.</b> Dead-end filling won 30 of 30
 *       on cells explored. Running thirty mazes to learn what one maze said is not insight.</li>
 *   <li><b>Braided mazes: the single race is close to a coin flip.</b> The per-maze winner split
 *       wall-follower 12, dfs 10, trémaux 5, bidirectional 2, dead-end-filling 1.</li>
 * </ul>
 *
 * <p>So the headline this reports is not a ranking. It is <b>how much to trust a ranking</b>:
 * each solver's spread (measured coefficient of variation ranged from BFS's 0.1% to
 * wall-follower's 98.9% on the same braided sample), how often each one actually won, and which
 * neighbouring pairs are statistically <em>indistinguishable</em> — BFS, Dial and Dijkstra came
 * out tied on that sample, which is correct, because all three explore essentially every cell.
 *
 * <h3>Bounded, like everything else here</h3>
 *
 * <p>The work is mazes × solvers, so both are capped and results are cached per request shape.
 * The subtler bound is a solver that refuses: IDA* spends its whole node budget on dungeons and
 * costs about a second each time. Rather than pay that on every maze in the sample, a solver that
 * refuses {@link #REFUSALS_BEFORE_EXCLUSION} times is dropped from the remaining rounds and
 * reported as excluded, with the count. Its partial results are discarded rather than averaged —
 * a mean over "the mazes it happened to survive" is a survivorship-biased number dressed as a
 * measurement.
 */
@Service
public class TournamentService {

    /** Refusals before a solver is dropped from the remaining rounds. */
    public static final int REFUSALS_BEFORE_EXCLUSION = 3;

    /** Smallest sample that supports an interval at all. */
    public static final int MIN_MAZES = 5;

    private final GeneratorRegistry generators;
    private final SolverRegistry solvers;
    private final int maxMazes;
    private final int maxSize;
    private final Cache<String, Tournament> cache;

    @Autowired
    public TournamentService(GeneratorRegistry generators, SolverRegistry solvers,
                             @Value("${daedalus.tournament.max-mazes:24}") int maxMazes,
                             @Value("${daedalus.tournament.max-size:41}") int maxSize,
                             @Value("${daedalus.tournament.max-cached:100}") int maxCached,
                             @Value("${daedalus.tournament.idle-ttl:6h}") Duration idleTtl) {
        this(generators, solvers, maxMazes, maxSize, maxCached, idleTtl, Ticker.systemTicker());
    }

    /**
     * Ticker seam — see {@code BoundedStoresTest.everyCacheWithAnIdleTtlExposesASeamForMovingTheClock}
     * for why every idle-bounded store in this package now has one. Short version: deleting
     * {@code expireAfterAccess} from three different services on three different days left the
     * suite green each time, because no test could move a clock.
     */
    TournamentService(GeneratorRegistry generators, SolverRegistry solvers,
                      int maxMazes, int maxSize, int maxCached, Duration idleTtl, Ticker ticker) {
        this.generators = generators;
        this.solvers = solvers;
        this.maxMazes = maxMazes;
        this.maxSize = maxSize;
        this.cache = Caffeine.newBuilder()
                .maximumSize(maxCached).expireAfterAccess(idleTtl).ticker(ticker).build();
    }

    /**
     * One solver's record over the sample.
     *
     * @param completed  mazes it actually finished — the sample its statistics are computed over
     * @param wins       mazes where this solver explored fewest cells
     * @param optimal    mazes where it returned a shortest route
     * @param refusals   times it gave up on its node budget
     * @param excluded   dropped after too many refusals; its statistics are omitted
     *
     * <p>{@code completed} exists because "excluded" and "produced no data" are not the same
     * thing, and conflating them hides the interesting case. Measured on 19x19 dungeons, IDA*
     * finishes five mazes and then refuses three — publishing a mean over those five would be
     * survivorship bias with an error bar on it, so the statistics are withheld and this count
     * is reported instead, letting a reader see exactly how much was thrown away.
     */
    public record Standing(String solverId, String displayName, SampleStats.Summary work,
                           SampleStats.Summary pathLength, int completed, int wins, int optimal,
                           int refusals, boolean excluded) { }

    /**
     * A pair whose difference does not survive its own error bars.
     *
     * @param meanDifference {@code a} minus {@code b} in cells explored
     */
    public record Tie(String a, String b, double meanDifference, double low, double high) { }

    /**
     * The maze in the sample where one solver does worst against another (ADR-007 idea 7).
     *
     * <p>This is a search over the sample that was already run, not a fresh optimisation: the
     * seeds are deterministic, so the seed reported here regenerates exactly the maze that
     * produced the gap, and anyone can check it.
     */
    public record Adversarial(String solver, String rival, long seed, long solverWork,
                              long rivalWork, double ratio, String note) { }

    public record Tournament(String generatorId, int size, double braid, int mazes, long baseSeed,
                             List<Standing> standings, List<Tie> ties, List<Adversarial> extremes,
                             String note) { }

    /** {@code null} when the generator is unknown, so the controller can 404. */
    /** Cached tournaments — for tests and metrics; see {@code BoundedStoresTest}. */
    public long cachedTournaments() {
        cache.cleanUp();
        return cache.estimatedSize();
    }

    public Tournament run(String generatorId, Integer sizeArg, Integer mazesArg,
                          Double braidArg, Long seedArg) {
        if (generatorId == null || generators.find(generatorId).isEmpty()) {
            return null;
        }
        int size = clamp(sizeArg == null ? 21 : sizeArg, 5, maxSize);
        int mazes = clamp(mazesArg == null ? 16 : mazesArg, MIN_MAZES, maxMazes);
        double braid = braidArg == null ? 0.0 : Math.max(0.0, Math.min(1.0, braidArg));
        long baseSeed = seedArg == null ? 1000L : seedArg;

        String key = generatorId + "|" + size + "|" + mazes + "|" + braid + "|" + baseSeed;
        return cache.get(key, k -> compute(generatorId, size, mazes, braid, baseSeed));
    }

    private Tournament compute(String generatorId, int size, int mazes, double braid,
                               long baseSeed) {
        List<MazeSolver> roster = new ArrayList<>(solvers.all());
        Map<String, List<Double>> work = new LinkedHashMap<>();
        Map<String, List<Double>> paths = new LinkedHashMap<>();
        Map<String, long[]> perMazeWork = new LinkedHashMap<>();
        Map<String, Integer> wins = new LinkedHashMap<>();
        Map<String, Integer> optimal = new LinkedHashMap<>();
        Map<String, Integer> refusals = new LinkedHashMap<>();
        for (MazeSolver s : roster) {
            work.put(s.id(), new ArrayList<>());
            paths.put(s.id(), new ArrayList<>());
            perMazeWork.put(s.id(), new long[mazes]);
            wins.put(s.id(), 0);
            optimal.put(s.id(), 0);
            refusals.put(s.id(), 0);
        }

        for (int i = 0; i < mazes; i++) {
            long seed = baseSeed + i;
            MazeGrid grid = generators.require(generatorId)
                    .generate(size, size, seed, new MazeStats());
            if (braid > 0) {
                Braider.braid(grid, braid, seed);
            }
            MazeMetrics.placeStartAndGoalAtExtremes(grid);
            int shortest = MazeMetrics.shortestPath(grid, grid.start(), grid.goal()).size();

            String winner = null;
            long leastWork = Long.MAX_VALUE;
            for (MazeSolver solver : roster) {
                if (refusals.get(solver.id()) >= REFUSALS_BEFORE_EXCLUSION) {
                    continue;   // already dropped; do not keep paying for its refusals
                }
                MazeStats stats = new MazeStats();
                List<Point> path;
                try {
                    path = solver.solve(grid, grid.start(), grid.goal(), stats);
                } catch (SolverBudgetExceededException gaveUp) {
                    refusals.merge(solver.id(), 1, Integer::sum);
                    continue;
                }
                long explored = stats.cellsExplored();
                perMazeWork.get(solver.id())[i] = explored;
                work.get(solver.id()).add((double) explored);
                paths.get(solver.id()).add((double) path.size());
                if (!path.isEmpty() && path.size() == shortest) {
                    optimal.merge(solver.id(), 1, Integer::sum);
                }
                if (explored < leastWork) {
                    leastWork = explored;
                    winner = solver.id();
                }
            }
            if (winner != null) {
                wins.merge(winner, 1, Integer::sum);
            }
        }

        List<Standing> standings = new ArrayList<>();
        for (MazeSolver solver : roster) {
            int refused = refusals.get(solver.id());
            List<Double> samples = work.get(solver.id());
            boolean excluded = refused >= REFUSALS_BEFORE_EXCLUSION || samples.size() < 2;
            standings.add(new Standing(solver.id(), solver.displayName(),
                    excluded ? null : SampleStats.summarise(toArray(samples)),
                    excluded ? null : SampleStats.summarise(toArray(paths.get(solver.id()))),
                    samples.size(), wins.get(solver.id()), optimal.get(solver.id()),
                    refused, excluded));
        }
        standings.sort(Comparator
                .comparing((Standing s) -> s.excluded())
                .thenComparingDouble(s -> s.excluded() ? Double.MAX_VALUE : s.work().mean()));

        return new Tournament(generatorId, size, braid, mazes, baseSeed, standings,
                tiesAmong(standings, perMazeWork, mazes),
                extremes(standings, perMazeWork, baseSeed),
                note(standings, mazes, braid));
    }

    /**
     * Adjacent pairs in the ranking whose paired difference includes zero. Adjacent only: a
     * ranking is read down the list, so the question a reader has is whether the solver above
     * really beat the one below it, not whether the 2nd beat the 9th.
     */
    private static List<Tie> tiesAmong(List<Standing> standings,
                                       Map<String, long[]> perMazeWork, int mazes) {
        List<Tie> ties = new ArrayList<>();
        List<Standing> ranked = standings.stream().filter(s -> !s.excluded()).toList();
        for (int i = 0; i + 1 < ranked.size(); i++) {
            String a = ranked.get(i).solverId();
            String b = ranked.get(i + 1).solverId();
            SampleStats.Difference d = SampleStats.comparePaired(
                    toDoubles(perMazeWork.get(a), mazes), toDoubles(perMazeWork.get(b), mazes));
            if (!d.distinguishable()) {
                ties.add(new Tie(a, b, round(d.meanDifference()), round(d.low()), round(d.high())));
            }
        }
        return ties;
    }

    /** The best and worst mazes for the top-ranked solver against the runner-up. */
    private static List<Adversarial> extremes(List<Standing> standings,
                                              Map<String, long[]> perMazeWork, long baseSeed) {
        List<Standing> ranked = standings.stream().filter(s -> !s.excluded()).toList();
        if (ranked.size() < 2) {
            return List.of();
        }
        String a = ranked.get(0).solverId();
        String b = ranked.get(1).solverId();
        long[] wa = perMazeWork.get(a);
        long[] wb = perMazeWork.get(b);
        int worst = 0;
        int best = 0;
        for (int i = 1; i < wa.length; i++) {
            if (wa[i] - wb[i] > wa[worst] - wb[worst]) {
                worst = i;
            }
            if (wa[i] - wb[i] < wa[best] - wb[best]) {
                best = i;
            }
        }
        return List.of(
                new Adversarial(a, b, baseSeed + worst, wa[worst], wb[worst],
                        ratio(wa[worst], wb[worst]),
                        "The maze in this sample where " + a + " does worst against " + b
                                + ". Regenerate it with this seed and watch them race."),
                new Adversarial(a, b, baseSeed + best, wa[best], wb[best],
                        ratio(wa[best], wb[best]),
                        "The maze where " + a + " does best against " + b + "."));
    }

    private static String note(List<Standing> standings, int mazes, double braid) {
        StringBuilder note = new StringBuilder();
        List<Standing> ranked = standings.stream().filter(s -> !s.excluded()).toList();
        long winners = ranked.stream().filter(s -> s.wins() > 0).count();
        if (winners <= 1) {
            note.append("One solver won every maze in this sample, so a single race on one maze "
                    + "would have told you the same thing. ");
        } else {
            note.append(winners).append(" different solvers won at least one maze out of ")
                    .append(mazes).append(", so a single race here is close to a coin flip — "
                            + "which is the whole reason to run a tournament. ");
        }
        ranked.stream().filter(s -> s.work().cv() > 50).findFirst().ifPresent(s ->
                note.append(s.solverId()).append(" is the erratic one (spread of ")
                        .append(Math.round(s.work().cv())).append("% of its own mean), which no "
                                + "single race would reveal. "));
        standings.stream().filter(Standing::excluded).forEach(s ->
                note.append(s.solverId()).append(" was excluded after giving up on ")
                        .append(s.refusals()).append(" mazes")
                        .append(s.completed() > 0
                                ? " (it finished " + s.completed() + " first; averaging those "
                                        + "would be survivorship bias, so no statistics are "
                                        + "reported for it). "
                                : ". "));
        if (braid == 0) {
            // Careful with the wording: braid == 0 does NOT mean "perfect maze". A dungeon is
            // unbraided and full of loops, and an earlier version of this sentence cheerfully
            // told dungeon tournaments they were looking at perfect mazes.
            note.append("No braiding was applied to this sample; adding some (braid > 0) makes "
                    + "the comparison markedly less stable, which is worth seeing.");
        }
        return note.toString().trim();
    }

    private static double ratio(long a, long b) {
        return b == 0 ? 0 : round((double) a / b);
    }

    private static double round(double v) {
        return Math.round(v * 100.0) / 100.0;
    }

    private static double[] toArray(List<Double> values) {
        double[] out = new double[values.size()];
        for (int i = 0; i < out.length; i++) {
            out[i] = values.get(i);
        }
        return out;
    }

    private static double[] toDoubles(long[] values, int n) {
        double[] out = new double[n];
        for (int i = 0; i < n; i++) {
            out[i] = values[i];
        }
        return out;
    }

    private static int clamp(int v, int low, int high) {
        return Math.max(low, Math.min(high, v));
    }
}
