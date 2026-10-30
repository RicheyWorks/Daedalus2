// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.AldousBroderGenerator;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.UnknownAlgorithmException;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.KruskalsGenerator;
import com.daedalus.engine.generators.PrimsGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * The Complexity Lab (ADR-007 idea 2). These tests pin measured <em>facts about the
 * algorithms</em>, not merely that an endpoint returns a number — a lab whose output nobody
 * checks against known algorithm behaviour is a chart generator, not a measurement.
 */
class ComplexityLabServiceTest {

    private ComplexityLabService lab;

    @BeforeEach
    void setUp() {
        var registry = new GeneratorRegistry(List.of(
                new RecursiveBacktrackerGenerator(), new BinaryTreeGenerator(),
                new PrimsGenerator(), new KruskalsGenerator(), new AldousBroderGenerator()));
        lab = new ComplexityLabService(registry, 96, 6, 200, Duration.ofHours(6));
    }

    /**
     * Prim's frontier is a perimeter, so its peak size grows sub-linearly in cell count while
     * Kruskal's — which holds every edge at once — does not. This is the lab earning its keep:
     * two generators that are both "O(n) time" differ sharply in peak memory, and the
     * difference is measured rather than argued.
     */
    @Test
    void primsFrontierGrowsSublinearlyWhileKruskalsDoesNot() {
        var prims = lab.fit("prims", "maxFrontierSize", null);
        var kruskals = lab.fit("kruskals", "maxFrontierSize", null);

        assertThat(prims.instrumented()).isTrue();
        assertThat(kruskals.instrumented()).isTrue();
        assertThat(prims.exponent())
                .as("Prim's peak frontier is the perimeter of a growing blob (~sqrt of area); "
                        + "measured exponent was %s", prims.exponent())
                .isLessThan(0.85);
        assertThat(kruskals.exponent())
                .as("Kruskal's holds the whole edge set, so its peak scales with the grid")
                .isGreaterThan(0.9);
        assertThat(prims.exponent()).isLessThan(kruskals.exponent());
    }

    /**
     * Aldous-Broder buys a uniform spanning tree by random walking until every cell has been
     * seen, which costs cover time — far more exploration than the cells it carves.
     */
    @Test
    void aldousBroderExploresFarMoreThanItCarves() {
        var fit = lab.fit("aldous-broder", "cellsExplored", null);
        var biggest = fit.measured().get(fit.measured().size() - 1);

        assertThat(fit.instrumented()).isTrue();
        assertThat(biggest.value())
                .as("random-walk cover time should dwarf the cell count; explored %d for %d cells",
                        biggest.value(), biggest.cells())
                .isGreaterThan(biggest.cells() * 5);
        assertThat(fit.note()).contains("overdraw");
    }

    /**
     * The honest-reporting case. Most generators instrument only some counters, and fitting a
     * curve through all zeros produces a NaN exponent that rounds to a confident-looking 0.0.
     */
    @Test
    void aMetricTheGeneratorNeverIncrementsIsReportedAsUnmeasuredNotAsZeroGrowth() {
        var fit = lab.fit("binary-tree", "backtrackCount", null);

        assertThat(fit).isNotNull();
        assertThat(fit.instrumented()).isFalse();
        assertThat(fit.claimed())
                .as("an unmeasured metric must not be dressed up as a growth class")
                .isEqualTo("not reported");
        assertThat(fit.note()).contains("does not report");
        assertThat(fit.measured()).isNotEmpty().allSatisfy(p -> assertThat(p.value()).isZero());
    }

    /**
     * cellsVisited is the tempting default and says the same thing about everyone, because a
     * spanning-tree generator carves each cell exactly once. Worth keeping as an invariant
     * check, worth labelling as one.
     */
    @Test
    void cellsVisitedIsAnInvariantCheckAndSaysSoRatherThanPosingAsAComparison() {
        for (String id : List.of("recursive-backtracker", "binary-tree", "prims")) {
            var fit = lab.fit(id, "cellsVisited", null);
            assertThat(fit.claimed()).as("%s", id).isEqualTo("O(n)");
            assertThat(fit.rSquared()).as("%s", id).isGreaterThan(0.99);
            assertThat(fit.exponent()).as("%s", id).isBetween(0.95, 1.10);
            assertThat(fit.note())
                    .as("presenting a metric that is identically n as a complexity result "
                            + "would be a chart that always says the same thing")
                    .contains("by construction");
        }
    }

    @Test
    void fitsAreDeterministicAndBounded() {
        var a = lab.fit("recursive-backtracker", "maxFrontierSize", 7L);
        var fresh = new ComplexityLabService(new GeneratorRegistry(List.of(
                new RecursiveBacktrackerGenerator())), 96, 6, 200, Duration.ofHours(6));
        var b = fresh.fit("recursive-backtracker", "maxFrontierSize", 7L);

        assertThat(b.measured()).isEqualTo(a.measured());
        assertThat(b.exponent()).isEqualTo(a.exponent());
        assertThat(a.measured()).hasSizeLessThanOrEqualTo(6);
        assertThat(a.measured()).allSatisfy(p -> assertThat(p.size()).isLessThanOrEqualTo(96));
    }

    @Test
    void unknownGeneratorsAndMetricsAreRefusedDifferently() {
        // These used to both return null, because the generator lookup sat inside a
        // `catch (RuntimeException) { return null; }`. Collapsing them cost the web layer any
        // chance of telling the caller which of the two they got wrong — and the catch-all would
        // have swallowed an unrelated runtime failure into the same silent "not found".
        assertThatThrownBy(() -> lab.fit("no-such-generator", "cellsVisited", null))
                .isInstanceOf(UnknownAlgorithmException.class)
                .satisfies(e -> assertThat(((UnknownAlgorithmException) e).known())
                        .as("the exception must carry what the caller could have said instead")
                        .isNotEmpty());

        // A metric that is not measured is still a null — nothing was misidentified, the
        // requested measurement simply does not exist.
        assertThat(lab.fit("prims", "no-such-metric", null)).isNull();
        assertThat(lab.metrics()).contains("cellsVisited", "cellsExplored", "maxFrontierSize");
    }
}
