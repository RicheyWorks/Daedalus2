// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.urn;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;
import org.junit.jupiter.api.Test;

class PearlJarTest {

    private static final PolyaUrn LAPLACE = new PolyaUrn(1, 1, 1);

    @Test
    void oneAndOneGivesAUniformCount() {
        double[] p = LAPLACE.whiteCounts(20);
        assertThat(p).hasSize(21);
        for (double x : p) {
            assertThat(x).isCloseTo(1.0 / 21, within(1e-12));
        }
        assertThat(LAPLACE.nextWhite(0, 0)).isEqualTo(0.5);
        assertThat(LAPLACE.nextWhite(7, 10)).isCloseTo(8.0 / 12, within(1e-15));
        assertThat(LAPLACE.expectedShare()).isEqualTo(0.5);
        assertThat(LAPLACE.shareBetween(20, 0, 1)).isCloseTo(1.0, within(1e-12));
        assertThat(LAPLACE.white() + LAPLACE.black() + LAPLACE.add()).isEqualTo(3);
    }

    @Test
    void countsAreBetaBinomial() {
        PolyaUrn urn = new PolyaUrn(2, 3, 1);
        double[] p = urn.whiteCounts(6);
        double sum = 0;
        for (int k = 0; k <= 6; k++) {
            double exact = choose(6, k) * beta(2 + k, 3 + 6 - k) / beta(2, 3);
            assertThat(p[k]).isCloseTo(exact, within(1e-12));
            sum += p[k] * k;
        }
        assertThat(sum / 6).isCloseTo(urn.expectedShare(), within(1e-12));
        double[] plain = new PolyaUrn(1, 3, 0).whiteCounts(4);
        assertThat(plain[2]).isCloseTo(6 * 0.25 * 0.25 * 0.75 * 0.75, within(1e-12));
    }

    @Test
    void seededDrawsAgreeWithTheExactOdds() {
        PolyaUrn urn = new PolyaUrn(2, 3, 1);
        double[] p = urn.whiteCounts(6);
        double[] est = PearlDraws.simulate(urn, 6, 2, 2026, 20_000);
        assertThat(p[2]).isBetween(est[1], est[2]);
        assertThat(est[0]).isCloseTo(p[2], within(0.015));
        assertThat(PearlDraws.simulate(urn, 6, 2, 2026, 20_000)).containsExactly(est);
        assertThat(PearlDraws.draw(urn, 0, new OddsRng(1))).isZero();
        int trials = 12_000;
        int[] inBand = new int[PearlJarQuest.BANDS];
        for (int t = 0; t < trials; t++) {
            inBand[PearlJarQuest.bandOf(PearlDraws.draw(LAPLACE, PearlJarQuest.DRAWS, OddsRng.forTrial(31, t)))]++;
        }
        PearlJarQuest bands = new PearlJarQuest();
        for (int b = 0; b < PearlJarQuest.BANDS; b++) {
            double[] ci = Intervals.wilson(inBand[b], trials);
            assertThat(bands.bandChance(b)).isBetween(ci[0], ci[1]);
        }
    }

    @Test
    void rejectsBadInput() {
        assertThatThrownBy(() -> new PolyaUrn(0, 1, 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new PolyaUrn(1, 1, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LAPLACE.nextWhite(3, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LAPLACE.whiteCounts(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LAPLACE.shareBetween(5, 0.6, 0.4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PearlDraws.draw(LAPLACE, -1, new OddsRng(1)))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PearlDraws.simulate(LAPLACE, 3, 1, 1, 0)).isInstanceOf(IllegalArgumentException.class);
        PearlJarQuest q = new PearlJarQuest();
        assertThatThrownBy(() -> q.choose(3, 1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void questThirdsAreEven() {
        PearlJarQuest q = new PearlJarQuest();
        assertThat(q.stage()).isEqualTo(PearlJarQuest.Stage.CHOOSING);
        assertThat(q.whites()).isEqualTo(-1);
        for (int b = 0; b < 3; b++) {
            assertThat(q.bandChance(b)).isCloseTo(1.0 / 3, within(1e-12));
        }
        assertThat(PearlJarQuest.bandOf(0)).isZero();
        assertThat(PearlJarQuest.bandOf(6)).isZero();
        assertThat(PearlJarQuest.bandOf(7)).isEqualTo(1);
        assertThat(PearlJarQuest.bandOf(20)).isEqualTo(2);
        assertThat(q.keeperLine()).contains("lowest third 33%").contains("middle 33%").contains("top 33%");
        assertThat(LAPLACE.shareBetween(20, 0, 7.0 / 22)).isCloseTo(1.0 / 3, within(1e-12));
        int right = 0;
        for (long s = 0; s < 300; s++) {
            PearlJarQuest t = new PearlJarQuest();
            PearlJarQuest.Stage end = t.choose(1, s);
            assertThat(t.stage()).isEqualTo(end);
            if (end == PearlJarQuest.Stage.RIGHT_BAND) {
                right++;
                assertThat(PearlJarQuest.bandOf(t.whites())).isEqualTo(1);
                assertThat(t.keeperLine()).contains("as you said");
            } else {
                assertThat(t.keeperLine()).contains("remembers");
            }
        }
        assertThat(right).isBetween(75, 125);
        q.choose(0, 9);
        assertThatThrownBy(() -> q.choose(0, 9)).isInstanceOf(IllegalStateException.class);
    }

    private static double choose(int n, int k) {
        double c = 1;
        for (int i = 0; i < k; i++) {
            c = c * (n - i) / (i + 1);
        }
        return c;
    }

    private static double beta(int a, int b) {
        return fact(a - 1) * fact(b - 1) / fact(a + b - 1);
    }

    private static double fact(int n) {
        double f = 1;
        for (int i = 2; i <= n; i++) {
            f *= i;
        }
        return f;
    }
}
