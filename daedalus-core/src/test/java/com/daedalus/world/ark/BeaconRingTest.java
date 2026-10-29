// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class BeaconRingTest {

    private static boolean all(long[][] p, double[] c) {
        for (long[] q : p) {
            if (!BeaconRing.contains(c, q)) {
                return false;
            }
        }
        return true;
    }

    /** Brute force: smallest covering circle among every pair-diameter and triple circle. */
    private static double brute(long[][] p) {
        double best = p.length == 1 ? 0 : Double.MAX_VALUE;
        for (int i = 0; i < p.length; i++) {
            for (int j = i + 1; j < p.length; j++) {
                double[] c = {(p[i][0] + p[j][0]) / 2.0, (p[i][1] + p[j][1]) / 2.0,
                    Math.hypot(p[i][0] - p[j][0], p[i][1] - p[j][1]) / 2};
                if (all(p, c)) {
                    best = Math.min(best, c[2]);
                }
                for (int k = j + 1; k < p.length; k++) {
                    double[] t = BeaconRing.three(p[i], p[j], p[k]);
                    if (all(p, t)) {
                        best = Math.min(best, t[2]);
                    }
                }
            }
        }
        return best;
    }

    private static long[][] random(SplittableRandom rnd, int n, int span) {
        long[][] p = new long[n][];
        for (int i = 0; i < n; i++) {
            p[i] = new long[] {rnd.nextInt(2 * span + 1) - span, rnd.nextInt(2 * span + 1) - span};
        }
        return p;
    }

    @Test
    void matchesBruteForce() {
        SplittableRandom rnd = new SplittableRandom(444);
        for (int t = 0; t < 300; t++) {
            long[][] p = random(rnd, 1 + rnd.nextInt(25), t % 2 == 0 ? 20 : 1_000_000);
            double[] c = BeaconRing.circle(p, t);
            assertThat(all(p, c)).isTrue();
            assertThat(c[2]).isCloseTo(brute(p), within(1e-6 * Math.max(1, c[2])));
        }
    }

    @Test
    void largeSetIsCoveredAndSeedFree() {
        long[][] p = random(new SplittableRandom(4440), 100_000, 1_000_000);
        double[] a = BeaconRing.circle(p, 1);
        double[] b = BeaconRing.circle(p, 2);
        assertThat(all(p, a)).isTrue();
        assertThat(a[2]).isCloseTo(b[2], within(1e-6 * a[2]));
        int[] edge = BeaconRing.boundary(p, a);
        assertThat(edge.length).isBetween(2, 4);
    }

    @Test
    void knownSmallCases() {
        double[] c = BeaconRing.circle(new long[][] {{0, 0}, {4, 0}, {2, 1}}, 7);
        assertThat(c[0]).isCloseTo(2, within(1e-9));
        assertThat(c[1]).isCloseTo(0, within(1e-9));
        assertThat(c[2]).isCloseTo(2, within(1e-9));
        double[] tri = BeaconRing.circle(new long[][] {{0, 0}, {6, 0}, {0, 8}, {1, 1}}, 3);
        assertThat(tri[2]).isCloseTo(5, within(1e-9));
        assertThat(BeaconRing.circle(new long[][] {{5, 5}}, 1)[2]).isZero();
        assertThat(BeaconRing.circle(new long[][] {{0, 0}, {1, 0}, {2, 0}, {3, 0}}, 1)[2]).isCloseTo(1.5, within(1e-9));
    }

    @Test
    void questAndBounds() {
        long[][] p = {{0, 0}, {6, 0}, {0, 8}};
        assertThat(BeaconRing.quest(p, 5)).isTrue();
        assertThat(BeaconRing.quest(p, 4)).isFalse();
        assertThat(BeaconRing.QUEST_ID).isEqualTo("q_beacon_ring");
        assertThatThrownBy(() -> BeaconRing.circle(new long[0][], 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BeaconRing.circle(new long[][] {{0, 2_000_000}}, 1)).isInstanceOf(IllegalArgumentException.class);
    }
}