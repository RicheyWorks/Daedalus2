// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class GearTrainTest {

    private static int closer(long p1, long q1, long p2, long q2, long a, long b) {
        BigInteger d1 = BigInteger.valueOf(Math.abs(p1 * b - a * q1)).multiply(BigInteger.valueOf(q2));
        BigInteger d2 = BigInteger.valueOf(Math.abs(p2 * b - a * q2)).multiply(BigInteger.valueOf(q1));
        return d1.compareTo(d2);
    }

    @Test
    void matchesExhaustiveSearch() {
        SplittableRandom rnd = new SplittableRandom(265);
        for (int t = 0; t < 3000; t++) {
            long a = rnd.nextLong(0, 2000);
            long b = rnd.nextLong(1, 2000);
            long n = rnd.nextLong(1, 40);
            long bp = 0;
            long bq = 1;
            for (long q = 1; q <= n; q++) {
                for (long p = 0; p <= n; p++) {
                    int c = closer(p, q, bp, bq, a, b);
                    if (c < 0 || (c == 0 && p * bq < bp * q)) {
                        bp = p;
                        bq = q;
                    }
                }
            }
            GearTrain.Ratio g = GearTrain.best(a, b, n);
            assertThat(g.p() * bq).as("%d/%d n=%d", a, b, n).isEqualTo(bp * g.q());
            assertThat(g.p()).isLessThanOrEqualTo(n);
            assertThat(g.q()).isBetween(1L, n);
        }
    }

    @Test
    void classicApproximations() {
        assertThat(GearTrain.best(314_159_265L, 100_000_000L, 1000)).isEqualTo(new GearTrain.Ratio(355, 113));
        assertThat(GearTrain.best(314_159_265L, 100_000_000L, 10)).isEqualTo(new GearTrain.Ratio(3, 1));
        assertThat(GearTrain.best(6, 4, 100)).isEqualTo(new GearTrain.Ratio(3, 2));
        assertThat(GearTrain.best(0, 7, 5)).isEqualTo(new GearTrain.Ratio(0, 1));
        assertThat(GearTrain.best(1_000_000_000L, 1, 50)).isEqualTo(new GearTrain.Ratio(50, 1));
    }

    @Test
    void pathsRoundTrip() {
        assertThat(GearTrain.path(3, 7)).isEqualTo("LLRR");
        assertThat(GearTrain.path(1, 1)).isEmpty();
        assertThat(GearTrain.path(4, 1)).isEqualTo("RRR");
        for (long p = 1; p < 50; p++) {
            for (long q = 1; q < 50; q++) {
                GearTrain.Ratio r = GearTrain.fromPath(GearTrain.path(p, q));
                assertThat(r.p() * q).isEqualTo(p * r.q());
            }
        }
        assertThatThrownBy(() -> GearTrain.fromPath("RX")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void questAndBounds() {
        assertThat(GearTrain.quest(314_159_265L, 100_000_000L, 1000, 355, 113)).isTrue();
        assertThat(GearTrain.quest(314_159_265L, 100_000_000L, 1000, 22, 7)).isFalse();
        assertThat(GearTrain.quest(1, 2, 10, 5, 10)).isTrue();
        assertThat(GearTrain.quest(1, 2, 4, 5, 10)).isFalse();
        assertThat(GearTrain.QUEST_ID).isEqualTo("q_gear_train");
        assertThatThrownBy(() -> GearTrain.best(1, 0, 5)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GearTrain.path(0, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}
