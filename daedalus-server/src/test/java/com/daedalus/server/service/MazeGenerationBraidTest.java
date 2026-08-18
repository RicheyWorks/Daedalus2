// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.GeneratorRegistry;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.MazeStats;
import com.daedalus.model.Point;
import com.daedalus.theory.MazeMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;

/**
 * Generate-time braid is the same pass the tournament already ran. Without it,
 * "load the adversarial maze" rebuilt the spanning tree and the race was a
 * different question — the interesting braid is exactly when a single race
 * becomes a coin flip.
 */
class MazeGenerationBraidTest {

    private MazeGenerationService service() {
        return new MazeGenerationService(
                new GeneratorRegistry(List.of(new RecursiveBacktrackerGenerator())),
                mock(ApplicationEventPublisher.class),
                new SimpleMeterRegistry());
    }

    @Test
    void braidZeroIsTheTreeTheOldCallersAlreadyGot() {
        var svc = service();
        var tree = svc.generate("recursive-backtracker", 21, 21, 7L);
        var explicit = svc.generate("recursive-backtracker", 21, 21, 7L, null, 0.0);

        assertThat(fingerprint(explicit.grid())).isEqualTo(fingerprint(tree.grid()));
    }

    @Test
    void aBraidedGenerateMatchesTheTournamentRecipe() {
        long seed = 1005L;
        double braid = 0.4;
        MazeGrid expected = new RecursiveBacktrackerGenerator()
                .generate(21, 21, seed, new MazeStats());
        Braider.braid(expected, braid, seed);
        MazeMetrics.placeStartAndGoalAtExtremes(expected);

        var served = service().generate("recursive-backtracker", 21, 21, seed, null, braid);
        var tree = service().generate("recursive-backtracker", 21, 21, seed, null, 0.0);

        assertThat(fingerprint(served.grid()))
                .as("generate(braid) must be generate → braid(seed) → extremes, "
                        + "or Load it is a different maze than the sample raced")
                .isEqualTo(fingerprint(expected));
        assertThat(fingerprint(served.grid()))
                .as("a no-op braid would still match the recipe and lie about loops")
                .isNotEqualTo(fingerprint(tree.grid()));
        assertThat(deadEnds(served.grid()))
                .as("braid opens dead ends; a label-only braid leaves the tree's count")
                .isLessThan(deadEnds(tree.grid()));
        assertThat(served.braid())
                .as("the cache must remember the factor or GET /maze cannot tell a tree from 0.4")
                .isEqualTo(braid);
        assertThat(tree.braid())
                .as("zero is omitted — a 0.0 field would make every old maze look newly braided")
                .isNull();
    }

    @Test
    void theSameSeedAndBraidAreDeterministic() {
        var svc = service();
        var a = svc.generate("recursive-backtracker", 15, 15, 11L, null, 0.8);
        var b = svc.generate("recursive-backtracker", 15, 15, 11L, null, 0.8);
        assertThat(fingerprint(a.grid())).isEqualTo(fingerprint(b.grid()));
    }

    private static String fingerprint(MazeGrid grid) {
        StringBuilder sb = new StringBuilder();
        sb.append(grid.start()).append('|').append(grid.goal()).append('|');
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                sb.append(grid.openNeighbors(new Point(r, c)).size());
            }
        }
        return sb.toString();
    }

    private static int deadEnds(MazeGrid grid) {
        int n = 0;
        for (int r = 0; r < grid.rows(); r++) {
            for (int c = 0; c < grid.cols(); c++) {
                if (grid.openNeighbors(new Point(r, c)).size() == 1) {
                    n++;
                }
            }
        }
        return n;
    }
}
