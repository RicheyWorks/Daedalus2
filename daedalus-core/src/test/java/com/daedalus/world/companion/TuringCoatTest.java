// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.daedalus.world.companion.TuringCoat.Genes;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;

class TuringCoatTest {
    private static final int N = TuringCoat.SIZE;

    @Test
    void starterLinesGrowTheirCoats() {
        for (long s = 0; s < 3; s++) {
            assertThat(TuringCoat.coat(TuringCoat.SPOTTED_LINE, s).pattern()).isEqualTo("Spots");
            assertThat(TuringCoat.coat(TuringCoat.STRIPED_LINE, s).pattern()).isEqualTo("Stripes");
            assertThat(TuringCoat.coat(TuringCoat.LABYRINTH_LINE, s).pattern()).isEqualTo("Labyrinth");
            assertThat(TuringCoat.coat(TuringCoat.PLAIN_LINE, s).pattern()).isEqualTo("None");
        }
    }

    @Test
    void growIsDeterministicPerSeed() {
        assertThat(TuringCoat.grow(TuringCoat.SPOTTED_LINE, 7)).isEqualTo(TuringCoat.grow(TuringCoat.SPOTTED_LINE, 7));
        assertThat(TuringCoat.grow(TuringCoat.SPOTTED_LINE, 7)).isNotEqualTo(TuringCoat.grow(TuringCoat.SPOTTED_LINE, 8));
    }

    @Test
    void labyrinthBreedsTrueAndSpotsStayPatchy() {
        for (long s = 0; s < 4; s++) {
            Genes spot = TuringCoat.breed(TuringCoat.SPOTTED_LINE, TuringCoat.SPOTTED_LINE, s);
            Genes lab = TuringCoat.breed(TuringCoat.LABYRINTH_LINE, TuringCoat.LABYRINTH_LINE, s);
            assertThat(TuringCoat.coat(spot, s).pattern()).isIn("Spots", "Stripes");
            assertThat(TuringCoat.coat(lab, s).pattern()).isEqualTo("Labyrinth");
        }
    }

    @Test
    void plainTimesLabyrinthGivesPatchyHybrids() {
        for (long s = 0; s < 4; s++) {
            Genes pup = TuringCoat.breed(TuringCoat.PLAIN_LINE, TuringCoat.LABYRINTH_LINE, s);
            assertThat(TuringCoat.coat(pup, s).pattern()).isIn("Spots", "Stripes");
        }
    }

    @Test
    void breedingIsSymmetricBoundedAndClamped() {
        Genes a = TuringCoat.SPOTTED_LINE;
        Genes b = TuringCoat.LABYRINTH_LINE;
        for (long s = 0; s < 200; s++) {
            Genes p = TuringCoat.breed(a, b, s);
            assertThat(p).isEqualTo(TuringCoat.breed(b, a, s));
            assertThat(Math.abs(p.feed() - (a.feed() + b.feed()) / 2)).isLessThanOrEqualTo(TuringCoat.MUTATION);
            assertThat(Math.abs(p.kill() - (a.kill() + b.kill()) / 2)).isLessThanOrEqualTo(TuringCoat.MUTATION);
        }
        Genes edge = new Genes(TuringCoat.FEED_MIN, TuringCoat.KILL_MAX);
        for (long s = 0; s < 50; s++) {
            Genes p = TuringCoat.breed(edge, edge, s);
            assertThat(p.feed()).isBetween(TuringCoat.FEED_MIN, TuringCoat.FEED_MIN + TuringCoat.MUTATION);
            assertThat(p.kill()).isBetween(TuringCoat.KILL_MAX - TuringCoat.MUTATION, TuringCoat.KILL_MAX);
        }
    }

    @Test
    void genesValidated() {
        assertThatThrownBy(() -> new Genes(0.5, 0.06)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Genes(0.03, 0.01)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Genes(Double.NaN, 0.06)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void classifierOnSyntheticSkins() {
        Genes g = TuringCoat.SPOTTED_LINE;
        assertThat(TuringCoat.classify(new double[N * N], g).pattern()).isEqualTo("None");
        double[] full = new double[N * N];
        java.util.Arrays.fill(full, 1.0);
        assertThat(TuringCoat.classify(full, g).pattern()).isEqualTo("Labyrinth");
        double[] dots = new double[N * N];
        for (int y = 0; y < N; y += 4) {
            for (int x = 0; x < N; x += 4) {
                dots[y * N + x] = 1.0;
            }
        }
        var d = TuringCoat.classify(dots, g);
        assertThat(d.pattern()).isEqualTo("Spots");
        assertThat(d.patches()).isEqualTo((N / 4) * (N / 4));
        double[] bands = new double[N * N];
        for (int y = 0; y < N; y++) {
            if (y % 16 < 4) {
                for (int x = 0; x < N; x++) {
                    bands[y * N + x] = 1.0;
                }
            }
        }
        var b = TuringCoat.classify(bands, g);
        assertThat(b.pattern()).isEqualTo("Stripes");
        assertThat(b.patches()).isEqualTo(4);
        assertThat(b.largestShare()).isEqualTo(0.25);
    }

    @Test
    void grownCoatFeedsTonicBrewer() throws Exception {
        Path p = Path.of("..", "tools", "islands", "kennel-isle", "tonics.json");
        TonicBrewer brewer = new TonicBrewer(TonicBook.load(Files.exists(p) ? p
            : Path.of("tools", "islands", "kennel-isle", "tonics.json")));
        List<String> herbs = List.of("Furfern", "Pawmint", "Barkbalm");
        String lab = TuringCoat.coat(TuringCoat.LABYRINTH_LINE, 0).pattern();
        String plain = TuringCoat.coat(TuringCoat.PLAIN_LINE, 0).pattern();
        assertThat(brewer.brew(herbs, lab, "other", 1, false)).isPresent();
        assertThat(brewer.brew(herbs, plain, "other", 1, false)).isPresent();
    }
}
