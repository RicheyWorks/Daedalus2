// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The heuristic lens (ADR-007 idea 8).
 *
 * <p>This feature reports a <em>theorem</em>, not a trend, so the tests check the theorem rather
 * than sampling agreement: with an admissible heuristic A* must expand every cell whose
 * {@code f = g* + h} is below the optimal cost, and can never expand one above it. Both
 * directions are asserted against a real recorded A* run, which also makes the pair a live
 * admissibility check on the heuristics themselves.
 */
class HeuristicLensServiceTest {

    private MazeGenerationService gen;
    private HeuristicLensService lens;

    @BeforeEach
    void setUp() {
        gen = new MazeGenerationService(
                new GeneratorRegistry(List.of(
                        new RecursiveBacktrackerGenerator(), new DungeonGenerator())),
                event -> { }, new SimpleMeterRegistry());
        lens = new HeuristicLensService(gen, 16_384);
    }

    @Test
    void unknownMaze_isNull_soTheControllerCan404() {
        assertThat(lens.forMaze(UUID.randomUUID(), HeuristicLensService.Heuristic.MANHATTAN))
                .isNull();
    }

    @Test
    void everyMandatoryCellIsExpanded_andNothingAboveTheOptimalCostEverIs() {
        // The whole claim, on both generators and both ADMISSIBLE heuristics. INFLATED is
        // excluded deliberately rather than by oversight: it overestimates on purpose, so it
        // violates this theorem by construction, and that violation is the subject of its own
        // test below. Looping over Heuristic.values() here would quietly turn a proof into a
        // failing assertion the moment a deliberately-broken heuristic joined the enum.
        var admissible = new HeuristicLensService.Heuristic[] {
            HeuristicLensService.Heuristic.MANHATTAN, HeuristicLensService.Heuristic.LANDMARK};
        for (String generator : new String[] {"recursive-backtracker", "dungeon"}) {
            for (var heuristic : admissible) {
                var cached = gen.generate(generator, 21, 21, 7L);

                var l = lens.forMaze(cached.metadata().id(), heuristic);

                assertThat(l.expandedAboveOptimal())
                        .as("%s/%s expanded a cell above the optimal cost, which an admissible "
                                + "heuristic makes impossible", generator, heuristic)
                        .isZero();
                assertThat(l.actualExpansions())
                        .as("%s/%s must expand at least the mandatory band", generator, heuristic)
                        .isGreaterThanOrEqualTo(l.mustExpand());
                assertThat(l.actualExpansions())
                        .as("%s/%s cannot expand more than the mandatory band plus every tie",
                                generator, heuristic)
                        .isLessThanOrEqualTo(l.mustExpand() + l.tie());
            }
        }
    }

    @Test
    void theBandsPartitionTheGrid() {
        var cached = gen.generate("dungeon", 21, 21, 7L);

        var l = lens.forMaze(cached.metadata().id(), HeuristicLensService.Heuristic.MANHATTAN);

        assertThat(l.mustExpand() + l.tie() + l.never()).isEqualTo(l.reachable());
        int counted = 0;
        for (int[] row : l.bands()) {
            for (int band : row) {
                if (band != HeuristicLensService.BAND_UNREACHABLE) {
                    counted++;
                }
            }
        }
        assertThat(counted).isEqualTo(l.reachable());
        assertThat(l.reachable())
                .as("a dungeon is mostly rock, so the grid must be bigger than the reachable set")
                .isLessThan(l.rows() * l.cols());
    }

    @Test
    void aSharperHeuristicShrinksTheMandatoryBandAndTheRealWork() {
        // The measurable form of "a better heuristic". Manhattan leaves almost the whole maze
        // below the optimal cost; the landmark heuristic leaves none of it, and A* does less.
        var cached = gen.generate("recursive-backtracker", 31, 31, 7L);

        var manhattan = lens.forMaze(cached.metadata().id(),
                HeuristicLensService.Heuristic.MANHATTAN);
        var landmark = lens.forMaze(cached.metadata().id(),
                HeuristicLensService.Heuristic.LANDMARK);

        assertThat(manhattan.mustExpand())
                .as("Manhattan puts nearly every cell below the optimal cost on a perfect maze")
                .isGreaterThan(800);
        assertThat(landmark.mustExpand())
                .as("the landmark heuristic is sharp enough to leave no mandatory cells at all")
                .isLessThan(manhattan.mustExpand());
        assertThat(landmark.actualExpansions())
                .as("and the smaller band shows up as real work saved")
                .isLessThan(manhattan.actualExpansions());
        assertThat(manhattan.optimalCost())
                .as("the optimal cost is a property of the maze, not of the heuristic")
                .isEqualTo(landmark.optimalCost());
    }

    @Test
    void theTieBandCanDominate_whichIsWhyItIsReportedSeparately() {
        // On a dungeon the tie band is several times the mandatory one, so tie-breaking decides
        // more of the search than the heuristic does. Folding ties into "must expand" would
        // overstate what the heuristic is responsible for.
        var cached = gen.generate("dungeon", 21, 21, 7L);

        var l = lens.forMaze(cached.metadata().id(), HeuristicLensService.Heuristic.MANHATTAN);

        assertThat(l.tie()).isGreaterThan(l.mustExpand());
        assertThat(l.note()).contains("tie-breaking rule decides more of this search");
    }

    @Test
    void anInadmissibleHeuristicIsCaughtByTheVeryCheckThatIsZeroForTheOthers() {
        // The point of this test is that `expandedAboveOptimal` can be non-zero. Asserting it is
        // zero for admissible heuristics proves nothing on its own — a mutation that simply never
        // incremented the counter survived, because the assertion could only ever confirm zero.
        // INFLATED overestimates by design, so the counter has to fire, and A* pays for it by
        // returning a route that is not the shortest.
        var cached = gen.generate("dungeon", 31, 31, 7L);

        var honest = lens.forMaze(cached.metadata().id(),
                HeuristicLensService.Heuristic.MANHATTAN);
        var inflated = lens.forMaze(cached.metadata().id(),
                HeuristicLensService.Heuristic.INFLATED);

        assertThat(honest.expandedAboveOptimal()).isZero();
        assertThat(inflated.expandedAboveOptimal())
                .as("an overestimating heuristic must push A* above the optimal cost")
                .isPositive();
        assertThat(inflated.actualExpansions())
                .as("that is what it buys — a cheaper search")
                .isLessThan(honest.actualExpansions());
        assertThat(inflated.routeOptimal())
                .as("and what it costs — the answer is no longer a shortest route")
                .isFalse();
        assertThat(inflated.routeLength()).isGreaterThan(inflated.optimalCost());
        assertThat(honest.routeOptimal()).isTrue();
        assertThat(inflated.note()).contains("no longer optimal");
    }

    @Test
    void anOversizedGridIsRefusedWithTheSameCapAsTheDistanceField() {
        var small = new HeuristicLensService(gen, 100);
        var cached = gen.generate("recursive-backtracker", 21, 21, 7L);

        assertThatThrownBy(() -> small.forMaze(cached.metadata().id(),
                HeuristicLensService.Heuristic.MANHATTAN))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("payload cap");
    }
}
