// SPDX-License-Identifier: MIT

package com.daedalus.theory;

import com.daedalus.engine.MazeGenerator;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.AldousBroderGenerator;
import com.daedalus.engine.generators.ArchimedesGenerator;
import com.daedalus.engine.generators.BinaryTreeGenerator;
import com.daedalus.engine.generators.BoruvkasGenerator;
import com.daedalus.engine.generators.EllersGenerator;
import com.daedalus.engine.generators.GaussGenerator;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.GrowingTreeGenerator;
import com.daedalus.engine.generators.HilbertCurveGenerator;
import com.daedalus.engine.generators.HuntAndKillGenerator;
import com.daedalus.engine.generators.KrakenGenerator;
import com.daedalus.engine.generators.KruskalsGenerator;
import com.daedalus.engine.generators.LightningGenerator;
import com.daedalus.engine.generators.MortonCurveGenerator;
import com.daedalus.engine.generators.OldestPickGenerator;
import com.daedalus.engine.generators.PrimsGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.engine.generators.RecursiveDivisionGenerator;
import com.daedalus.engine.generators.SidewinderGenerator;
import com.daedalus.engine.generators.TuringGenerator;
import com.daedalus.engine.generators.WilsonsGenerator;
import com.daedalus.model.AlgorithmDescriptor;
import com.daedalus.model.MazeStats;
import com.daedalus.theory.ComplexityAnalyzer.Measurement;
import com.daedalus.theory.ComplexityAnalyzer.Report;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Exercises {@link ComplexityAnalyzer}: the deterministic measurement of a single generator, the
 * full sweep over a registry, resilience to a throwing generator, and the lockable (timing-free)
 * CSV / JSON report shape.
 *
 * <p>Pure daedalus-core: JUnit 5 + AssertJ, no Spring / server / plugin runtime.
 */
class ComplexityAnalyzerTest {

    private static final long SEED = 42L;

    // ---------- single-generator measurement ----------

    @Test
    void measure_isDeterministic_andCapturesStats_forAStatEmittingGenerator() {
        Measurement a = ComplexityAnalyzer.measure(new PrimsGenerator(), 16, 16, SEED);
        Measurement b = ComplexityAnalyzer.measure(new PrimsGenerator(), 16, 16, SEED);

        assertThat(a.generatorId()).isEqualTo("prims");
        assertThat(a.rows()).isEqualTo(16);
        assertThat(a.cols()).isEqualTo(16);
        assertThat(a.cellCount()).isEqualTo(256L);
        assertThat(a.success()).isTrue();

        // Prim's tracks visited cells and frontier size, so those are non-zero...
        assertThat(a.cellsVisited()).isPositive();
        assertThat(a.maxFrontierSize()).isPositive();

        // ...and every deterministic counter reproduces exactly across runs (only wall-time varies).
        assertThat(a.cellsVisited()).isEqualTo(b.cellsVisited());
        assertThat(a.maxFrontierSize()).isEqualTo(b.maxFrontierSize());
        assertThat(a.backtrackCount()).isEqualTo(b.backtrackCount());
        assertThat(a.pathLength()).isEqualTo(b.pathLength());
    }

    @Test
    void measure_handlesGeneratorThatEmitsNoStats_asZeros() {
        // A generator that produces a valid grid but never touches MazeStats yields a stable,
        // lock-in-able all-zeros counter row — the analyzer reports exactly what it is given.
        Measurement m = ComplexityAnalyzer.measure(noStatGenerator("no-stats"), 16, 16, SEED);

        assertThat(m.generatorId()).isEqualTo("no-stats");
        assertThat(m.success()).isTrue();
        assertThat(m.cellCount()).isEqualTo(256L);
        assertThat(m.cellsVisited()).isZero();
        assertThat(m.maxFrontierSize()).isZero();
    }

    @Test
    void measure_recordsFailure_whenGeneratorThrows_ratherThanPropagating() {
        Measurement m = ComplexityAnalyzer.measure(throwingGenerator("kaboom"), 32, 32, SEED);

        assertThat(m.generatorId()).isEqualTo("kaboom");
        assertThat(m.success()).isFalse();
        assertThat(m.cellCount()).isEqualTo(1024L);
    }

    // ---------- full sweep ----------

    @Test
    void analyzeAll_coversEveryRegisteredGeneratorAtEverySize_sortedStably() {
        GeneratorRegistry registry = new GeneratorRegistry(List.of(
                new RecursiveBacktrackerGenerator(),
                new PrimsGenerator(),
                new KruskalsGenerator(),
                new BinaryTreeGenerator()));
        ComplexityAnalyzer analyzer = new ComplexityAnalyzer(registry);

        Report report = analyzer.analyzeAll(SEED, 8, 16);

        // 4 generators x 2 sizes.
        assertThat(report.measurements()).hasSize(8);
        assertThat(report.measurements()).extracting(Measurement::generatorId)
                .containsOnly("recursive-backtracker", "prims", "kruskals", "binary-tree");
        assertThat(report.measurements()).extracting(Measurement::cellCount)
                .containsOnly(64L, 256L);
        assertThat(report.measurements()).isSortedAccordingTo(
                Comparator.comparing(Measurement::generatorId).thenComparingLong(Measurement::cellCount));
        assertThat(report.seed()).isEqualTo(SEED);
    }

    @Test
    void analyzeAll_isResilient_whenOneGeneratorThrows() {
        GeneratorRegistry registry = new GeneratorRegistry(List.of(
                new PrimsGenerator(),
                throwingGenerator("kaboom")));
        Report report = new ComplexityAnalyzer(registry).analyzeAll(SEED, 16);

        assertThat(report.measurements()).hasSize(2);
        assertThat(report.measurements()).filteredOn(m -> m.generatorId().equals("kaboom"))
                .singleElement().extracting(Measurement::success).isEqualTo(false);
        assertThat(report.measurements()).filteredOn(m -> m.generatorId().equals("prims"))
                .singleElement().extracting(Measurement::success).isEqualTo(true);
    }

    @Test
    void defaults_areSeed42AndSizes32_64_128() {
        assertThat(ComplexityAnalyzer.DEFAULT_SEED).isEqualTo(42L);
        assertThat(ComplexityAnalyzer.defaultSizes()).containsExactly(32, 64, 128);

        // The zero-arg sweep actually runs those three sizes.
        Report report = new ComplexityAnalyzer(new GeneratorRegistry(List.of(new PrimsGenerator()))).analyzeAll();
        assertThat(report.measurements()).extracting(Measurement::cellCount)
                .containsExactly(1024L, 4096L, 16384L);
    }

    @Test
    void everyBuiltInGenerator_isMeasurableWithoutError() {
        // Mirrors AlgorithmConfig#builtInGenerators — guards that no generator blows up when
        // driven through the analyzer at a real (power-of-two) size.
        GeneratorRegistry registry = new GeneratorRegistry(List.of(
                new RecursiveBacktrackerGenerator(), new PrimsGenerator(), new KruskalsGenerator(),
                new BoruvkasGenerator(), new WilsonsGenerator(), new HuntAndKillGenerator(),
                new RecursiveDivisionGenerator(), new BinaryTreeGenerator(), new SidewinderGenerator(),
                new GrowingTreeGenerator(), new OldestPickGenerator(), new AldousBroderGenerator(),
                new EllersGenerator(), new KrakenGenerator(), new MortonCurveGenerator(),
                new HilbertCurveGenerator(), new LightningGenerator(), new TuringGenerator(),
                new GaussGenerator(), new ArchimedesGenerator()));

        Report report = new ComplexityAnalyzer(registry).analyzeAll(SEED, 32);

        assertThat(report.measurements()).hasSize(20);
        assertThat(report.measurements()).allMatch(Measurement::success);
    }

    // ---------- report serialization ----------

    @Test
    void toCsv_hasHeaderAndOneRowPerMeasurement_withNoTimingColumn() {
        Report report = smallReport();
        String csv = report.toCsv();
        String[] lines = csv.split("\n");

        assertThat(lines[0]).isEqualTo(
                "generatorId,rows,cols,cellCount,cellsVisited,cellsExplored,"
                        + "backtrackCount,maxFrontierSize,pathLength,success");
        assertThat(lines).hasSize(report.measurements().size() + 1);
        assertThat(lines[0]).doesNotContain("elapsed", "nanos", "time");
        // The first data row is the alphabetically-first generator at the smallest size.
        assertThat(lines[1]).startsWith("binary-tree,8,8,64,");
    }

    @Test
    void toJson_isDeterministic_andOmitsTiming() {
        Report report = smallReport();

        assertThat(report.toJson()).isEqualTo(report.toJson()); // stable across calls
        assertThat(report.toJson())
                .startsWith("{")
                .contains("\"seed\": 42")
                .contains("\"generatorId\": \"prims\"")
                .doesNotContain("elapsed", "nanos");
    }

    @Test
    void writeTo_writesBothGoldenFiles_matchingTheInMemoryStrings(@TempDir Path dir) throws Exception {
        Report report = smallReport();

        report.writeTo(dir);

        Path csv = dir.resolve("complexity.csv");
        Path json = dir.resolve("complexity.json");
        assertThat(csv).exists();
        assertThat(json).exists();
        assertThat(Files.readString(csv, StandardCharsets.UTF_8)).isEqualTo(report.toCsv());
        assertThat(Files.readString(json, StandardCharsets.UTF_8)).isEqualTo(report.toJson());
    }

    private static Report smallReport() {
        GeneratorRegistry registry = new GeneratorRegistry(List.of(
                new BinaryTreeGenerator(), new PrimsGenerator()));
        return new ComplexityAnalyzer(registry).analyzeAll(SEED, 8, 16);
    }

    /** A generator that produces a valid grid but never records any stats. */
    private static MazeGenerator noStatGenerator(String id) {
        return new MazeGenerator() {
            @Override
            public String id() {
                return id;
            }

            @Override
            public String displayName() {
                return id;
            }

            @Override
            public AlgorithmDescriptor descriptor() {
                return null;
            }

            @Override
            public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
                return new MazeGrid(rows, cols);
            }
        };
    }

    /** A generator that always throws from {@code generate}, to exercise the failure path. */
    private static MazeGenerator throwingGenerator(String id) {
        return new MazeGenerator() {
            @Override
            public String id() {
                return id;
            }

            @Override
            public String displayName() {
                return id;
            }

            @Override
            public AlgorithmDescriptor descriptor() {
                return null;
            }

            @Override
            public MazeGrid generate(int rows, int cols, long seed, MazeStats stats) {
                throw new IllegalStateException("boom");
            }
        };
    }
}
