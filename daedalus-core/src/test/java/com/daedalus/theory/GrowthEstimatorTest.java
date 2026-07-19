// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.PrimsGenerator;
import com.daedalus.theory.ComplexityAnalyzer.Measurement;
import com.daedalus.theory.ComplexityAnalyzer.Report;
import com.daedalus.theory.GrowthEstimator.GrowthClass;
import com.daedalus.theory.GrowthEstimator.GrowthFit;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/**
 * {@link GrowthEstimator} against inputs whose growth is known by construction (linear,
 * quadratic, n log n, constant, no-data), then one real {@link ComplexityAnalyzer} sweep to
 * confirm it produces a definite verdict on live generator counts.
 */
class GrowthEstimatorTest {

    // ---------- synthetic data with a known shape ----------

    @Test
    void linearData_classifiesAsLinear_withExponentNearOne() {
        GrowthFit fit = GrowthEstimator.fit("lin", "w",
                points("lin", n -> 3 * n, 100, 200, 400, 800), Measurement::cellsVisited);

        assertThat(fit.growthClass()).isEqualTo(GrowthClass.LINEAR);
        assertThat(fit.growthClass().label()).isEqualTo("O(n)");
        assertThat(fit.exponent()).isCloseTo(1.0, within(0.05));
        assertThat(fit.rSquared()).isCloseTo(1.0, within(1e-6));
        assertThat(fit.points()).isEqualTo(4);
    }

    @Test
    void quadraticData_classifiesAsQuadratic_withExponentNearTwo() {
        GrowthFit fit = GrowthEstimator.fit("quad", "w",
                points("quad", n -> 2 * n * n, 100, 200, 400, 800), Measurement::cellsVisited);

        assertThat(fit.growthClass()).isEqualTo(GrowthClass.QUADRATIC);
        assertThat(fit.exponent()).isCloseTo(2.0, within(0.05));
        assertThat(fit.rSquared()).isCloseTo(1.0, within(1e-6));
    }

    @Test
    void nLogNData_classifiesAsNLogN() {
        GrowthFit fit = GrowthEstimator.fit("nlogn", "w",
                points("nlogn", n -> Math.round(n * (Math.log(n) / Math.log(2))), 256, 1024, 4096, 16384),
                Measurement::cellsVisited);

        assertThat(fit.growthClass()).isEqualTo(GrowthClass.N_LOG_N);
        assertThat(fit.exponent()).isGreaterThan(1.0);
    }

    @Test
    void constantData_classifiesAsConstant() {
        GrowthFit fit = GrowthEstimator.fit("const", "w",
                points("const", n -> 500L, 100, 200, 400, 800), Measurement::cellsVisited);

        assertThat(fit.growthClass()).isEqualTo(GrowthClass.CONSTANT);
        assertThat(fit.exponent()).isCloseTo(0.0, within(0.05));
    }

    @Test
    void allZeroMetric_isUnknown() {
        GrowthFit fit = GrowthEstimator.fit("silent", "w",
                points("silent", n -> 0L, 100, 200, 400), Measurement::cellsVisited);

        assertThat(fit.growthClass()).isEqualTo(GrowthClass.UNKNOWN);
        assertThat(fit.rSquared()).isNaN();
        assertThat(fit.toString()).contains("insufficient data");
    }

    @Test
    void tooFewDistinctSizes_isUnknown() {
        List<Measurement> sameSize = List.of(m("x", 256, 10), m("x", 256, 20));
        GrowthFit fit = GrowthEstimator.fit("x", "w", sameSize, Measurement::cellsVisited);

        assertThat(fit.growthClass()).isEqualTo(GrowthClass.UNKNOWN);
    }

    // ---------- grouping ----------

    @Test
    void classify_groupsByGenerator_preservingOrder() {
        List<Measurement> mixed = new ArrayList<>();
        mixed.addAll(points("lin", n -> 3 * n, 100, 200, 400));
        mixed.addAll(points("quad", n -> 2 * n * n, 100, 200, 400));

        List<GrowthFit> fits = GrowthEstimator.classifyVisited(mixed);

        assertThat(fits).extracting(GrowthFit::generatorId).containsExactly("lin", "quad");
        assertThat(fits).extracting(GrowthFit::growthClass)
                .containsExactly(GrowthClass.LINEAR, GrowthClass.QUADRATIC);
        assertThat(GrowthEstimator.toTable(fits)).contains("lin", "quad", "O(n)", "O(n^2)");
    }

    // ---------- real sweep ----------

    @Test
    void realSweep_yieldsADefiniteVerdictForPrims() {
        Report report = new ComplexityAnalyzer(new GeneratorRegistry(List.of(new PrimsGenerator())))
                .analyzeAll(42L, 16, 32, 64);

        List<GrowthFit> fits = GrowthEstimator.classifyVisited(report.measurements());

        assertThat(fits).singleElement().satisfies(fit -> {
            assertThat(fit.generatorId()).isEqualTo("prims");
            assertThat(fit.points()).isEqualTo(3);
            assertThat(fit.growthClass()).isNotEqualTo(GrowthClass.UNKNOWN);
            assertThat(fit.rSquared()).isGreaterThanOrEqualTo(0.90);
        });
    }

    // ---------- helpers ----------

    private interface WorkOf {
        long apply(long n);
    }

    private static List<Measurement> points(String id, WorkOf work, long... sizes) {
        List<Measurement> out = new ArrayList<>(sizes.length);
        for (long n : sizes) {
            out.add(m(id, n, work.apply(n)));
        }
        return out;
    }

    private static Measurement m(String id, long cellCount, long visited) {
        return new Measurement(id, 0, 0, cellCount, visited, 0, 0, 0, 0, true, 0);
    }
}
