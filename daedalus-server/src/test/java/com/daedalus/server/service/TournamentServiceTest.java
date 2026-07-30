// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.solver.solvers.AStarSolver;
import com.daedalus.solver.solvers.BfsSolver;
import com.daedalus.solver.solvers.DfsSolver;
import com.daedalus.solver.solvers.DialSolver;
import com.daedalus.solver.solvers.DijkstraSolver;
import com.daedalus.solver.solvers.IDAStarSolver;
import com.daedalus.solver.solvers.SolverRegistry;
import com.daedalus.solver.solvers.WallFollowerSolver;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Solver tournament (ADR-007 idea 10) and adversarial seeds (idea 7).
 *
 * <p>The claim under test is not "the ranking is right" — it is that the tournament reports
 * <em>how much the ranking can be trusted</em>. So the tests pin the two things a naive version
 * would get wrong: solvers that are genuinely tied must be reported as tied rather than ranked
 * 1st and 2nd out of noise, and a solver that gives up must be excluded rather than averaged over
 * the mazes it happened to survive.
 */
class TournamentServiceTest {

    private TournamentService tournaments;

    @BeforeEach
    void setUp() {
        var generators = new GeneratorRegistry(List.of(
                new RecursiveBacktrackerGenerator(), new DungeonGenerator()));
        var solvers = new SolverRegistry(List.of(
                new AStarSolver(), new BfsSolver(), new DfsSolver(), new DijkstraSolver(),
                new DialSolver(), new WallFollowerSolver(), new IDAStarSolver()));
        tournaments = new TournamentService(generators, solvers, 24, 41, 100, Duration.ofHours(6));
    }

    @Test
    void anUnknownGeneratorIsNull_soTheControllerCan404() {
        assertThat(tournaments.run("no-such-generator", 21, 8, 0.0, 1000L)).isNull();
    }

    @Test
    void solversThatExploreEveryCellAreReportedAsTied_notRanked() {
        // BFS, Dijkstra and Dial all sweep the whole maze, so their means differ by rounding at
        // most. Presenting that as a 1-2-3 finish would be a ranking invented from noise; the
        // paired interval spans zero and they must appear in `ties`.
        var t = tournaments.run("recursive-backtracker", 21, 12, 0.0, 1000L);

        List<String> tiedPairs = t.ties().stream().map(x -> x.a() + "~" + x.b()).toList();
        assertThat(tiedPairs)
                .as("all-cells-explored solvers must be reported as indistinguishable: %s",
                        t.standings().stream().map(s -> s.solverId()
                                + (s.excluded() ? " (excluded)" : "=" + s.work().mean())).toList())
                .anyMatch(p -> p.contains("bfs") || p.contains("dial") || p.contains("dijkstra"));
    }

    @Test
    void aSolverThatGivesUpIsExcluded_notAveragedOverTheMazesItSurvived() {
        // 19x19 dungeons are deliberately chosen over 21x21: measured, IDA* FINISHES FIVE of them
        // before its third refusal, where at 21x21 it mostly refuses from the start. That
        // distinction is the whole test. With no completed mazes, "excluded" and "no data" are
        // indistinguishable and a broken implementation passes — a mutation that published
        // statistics whenever at least two samples existed survived the 21x21 version of this
        // test. Here there ARE five samples, and publishing a mean over them would be
        // survivorship bias with an error bar on it.
        var t = tournaments.run("dungeon", 19, 12, 0.0, 1000L);

        var ida = t.standings().stream()
                .filter(s -> s.solverId().equals("ida-star")).findFirst().orElseThrow();
        assertThat(ida.excluded()).isTrue();
        assertThat(ida.refusals()).isEqualTo(TournamentService.REFUSALS_BEFORE_EXCLUSION);
        assertThat(ida.completed())
                .as("this configuration must exercise the partial-data case, not the no-data one")
                .isGreaterThanOrEqualTo(2);
        assertThat(ida.work())
                .as("statistics over only the mazes a solver survived are survivorship bias")
                .isNull();
        assertThat(ida.pathLength()).isNull();
        assertThat(t.note()).contains("ida-star").contains("survivorship");
        assertThat(t.standings()).as("everyone else still competes").hasSizeGreaterThan(5);
    }

    @Test
    void excludedSolversSortLast_soTheRankingStaysReadable() {
        var t = tournaments.run("dungeon", 21, 10, 0.0, 1000L);

        int firstExcluded = -1;
        for (int i = 0; i < t.standings().size(); i++) {
            if (t.standings().get(i).excluded()) {
                firstExcluded = i;
                break;
            }
        }
        assertThat(firstExcluded).isGreaterThan(0);
        assertThat(t.standings().subList(firstExcluded, t.standings().size()))
                .allMatch(s -> s.excluded());
    }

    @Test
    void theSampleIsDeterministic_soAReportedSeedCanBeChecked() {
        // The whole value of the adversarial seed is that someone can regenerate that maze. If
        // the sample moved between runs, the seed would point at nothing in particular.
        var first = tournaments.run("recursive-backtracker", 21, 8, 0.3, 4242L);
        var second = new TournamentService(
                new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                new SolverRegistry(List.of(new AStarSolver(), new BfsSolver(), new DfsSolver())),
                24, 41, 100, Duration.ofHours(6))
                .run("recursive-backtracker", 21, 8, 0.3, 4242L);

        assertThat(first.extremes()).isNotEmpty();
        // Different rosters, same mazes: the shared solvers must see identical work.
        double aStarFirst = first.standings().stream()
                .filter(s -> s.solverId().equals("astar")).findFirst().orElseThrow()
                .work().mean();
        double aStarSecond = second.standings().stream()
                .filter(s -> s.solverId().equals("astar")).findFirst().orElseThrow()
                .work().mean();
        assertThat(aStarFirst).isEqualTo(aStarSecond);
    }

    @Test
    void theAdversarialSeedIsRealAndPointsAtTheWidestGap() {
        var t = tournaments.run("recursive-backtracker", 21, 12, 0.4, 1000L);

        assertThat(t.extremes()).hasSize(2);
        var worst = t.extremes().get(0);
        var best = t.extremes().get(1);
        assertThat(worst.seed()).isBetween(t.baseSeed(), t.baseSeed() + t.mazes() - 1);
        assertThat(best.seed()).isBetween(t.baseSeed(), t.baseSeed() + t.mazes() - 1);
        // Strict, and on distinct mazes. A weaker `>=` passed even when both extremes were
        // computed with the same comparison and collapsed onto one maze — a mutation that
        // searched for the minimum twice survived, because min >= min is perfectly true.
        assertThat(worst.seed())
                .as("the widest and narrowest gaps must be different mazes")
                .isNotEqualTo(best.seed());
        assertThat(worst.solverWork() - worst.rivalWork())
                .as("the 'worst' maze must be strictly worse for the leader than the 'best' one")
                .isGreaterThan(best.solverWork() - best.rivalWork());
    }

    @Test
    void winsAndOptimalCountsStayInsideTheSample() {
        var t = tournaments.run("recursive-backtracker", 21, 12, 0.0, 1000L);

        int totalWins = t.standings().stream().mapToInt(s -> s.wins()).sum();
        assertThat(totalWins).isEqualTo(12);
        assertThat(t.standings()).allSatisfy(s -> {
            assertThat(s.wins()).isBetween(0, 12);
            assertThat(s.optimal()).isBetween(0, 12);
            assertThat(s.completed()).isBetween(0, 12);
        });
    }

    @Test
    void theNoteSaysWhetherASingleRaceWouldHaveDoneJustAsWell() {
        var perfect = tournaments.run("recursive-backtracker", 21, 12, 0.0, 1000L);
        var braided = tournaments.run("recursive-backtracker", 21, 12, 0.5, 1000L);

        long perfectWinners = perfect.standings().stream().filter(s -> s.wins() > 0).count();
        long braidedWinners = braided.standings().stream().filter(s -> s.wins() > 0).count();

        assertThat(perfectWinners)
                .as("on perfect mazes one solver takes every maze, so a single race suffices")
                .isEqualTo(1);
        assertThat(perfect.note()).contains("single race");
        assertThat(braidedWinners)
                .as("braiding is what makes a single race unreliable — that is the whole feature")
                .isGreaterThan(1);
        assertThat(braided.note()).contains("coin flip");
    }

    @Test
    void aDungeonIsNotDescribedAsAPerfectMaze() {
        // The first version of this note said "these are perfect mazes" whenever braid was zero,
        // which is false for a dungeon — unbraided and full of loops.
        var t = tournaments.run("dungeon", 21, 8, 0.0, 1000L);

        assertThat(t.note()).doesNotContain("perfect maze");
        assertThat(t.note()).contains("No braiding");
    }

    @Test
    void argumentsAreClampedRatherThanTrusted() {
        assertThat(tournaments.run("recursive-backtracker", 9999, 9999, 5.0, 1L).size())
                .isEqualTo(41);
        assertThat(tournaments.run("recursive-backtracker", 9999, 9999, 5.0, 1L).mazes())
                .isEqualTo(24);
        assertThat(tournaments.run("recursive-backtracker", 21, 1, -2.0, 1L).mazes())
                .isEqualTo(TournamentService.MIN_MAZES);
        assertThat(tournaments.run("recursive-backtracker", 21, 1, -2.0, 1L).braid()).isZero();
    }
}
