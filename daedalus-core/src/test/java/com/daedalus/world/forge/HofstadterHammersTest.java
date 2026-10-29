// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashMap;
import java.util.Map;
import java.util.Random;
import org.junit.jupiter.api.Test;

class HofstadterHammersTest {

    private final Map<Integer, Integer> qMemo = new HashMap<>();
    private final Map<Integer, Integer> cMemo = new HashMap<>();

    private int bruteQ(int n) {
        if (n <= 2) {
            return 1;
        }
        Integer m = qMemo.get(n);
        if (m != null) {
            return m;
        }
        int v = bruteQ(n - bruteQ(n - 1)) + bruteQ(n - bruteQ(n - 2));
        qMemo.put(n, v);
        return v;
    }

    private int bruteC(int n) {
        if (n <= 2) {
            return 1;
        }
        Integer m = cMemo.get(n);
        if (m != null) {
            return m;
        }
        int v = bruteC(bruteC(n - 1)) + bruteC(n - bruteC(n - 1));
        cMemo.put(n, v);
        return v;
    }

    @Test
    void matchesRecursiveBruteForce() {
        int[] q = HofstadterHammers.qSequence(3000);
        int[] c = HofstadterHammers.conwaySequence(3000);
        for (int n = 1; n <= 3000; n++) {
            assertThat(q[n]).as("Q%d", n).isEqualTo(bruteQ(n));
            assertThat(c[n]).as("a%d", n).isEqualTo(bruteC(n));
        }
        Random r = new Random(521);
        for (int t = 0; t < 30; t++) {
            int n = 1 + r.nextInt(3000);
            assertThat(HofstadterHammers.q(n)).isEqualTo(q[n]);
            assertThat(HofstadterHammers.conway(n)).isEqualTo(c[n]);
        }
    }

    @Test
    void knownStrikes() {
        int[] q = HofstadterHammers.qSequence(20);
        int[] c = HofstadterHammers.conwaySequence(20);
        int[] wantQ = {1, 1, 2, 3, 3, 4, 5, 5, 6, 6, 6, 8, 8, 8, 10, 9, 10, 11, 11, 12};
        int[] wantC = {1, 1, 2, 2, 3, 4, 4, 4, 5, 6, 7, 7, 8, 8, 8, 8, 9, 10, 11, 12};
        for (int i = 0; i < 20; i++) {
            assertThat(q[i + 1]).isEqualTo(wantQ[i]);
            assertThat(c[i + 1]).isEqualTo(wantC[i]);
        }
        assertThat(q[0]).isZero();
        assertThat(c[0]).isZero();
    }

    @Test
    void conwayStructure() {
        int[] c = HofstadterHammers.conwaySequence(1 << 20);
        for (int k = 1; k <= 20; k++) {
            assertThat(c[1 << k]).as("a(2^%d)", k).isEqualTo(1 << (k - 1));
        }
        for (int n = 1; n < c.length; n++) {
            assertThat(2 * c[n]).isGreaterThanOrEqualTo(n);
            if (n > 1) {
                assertThat(c[n] - c[n - 1]).isBetween(0, 1);
            }
        }
    }

    @Test
    void qStaysInRange() {
        int[] q = HofstadterHammers.qSequence(1_000_000);
        for (int n = 3; n < q.length; n++) {
            assertThat(q[n]).isBetween(1, n);
            assertThat(n - q[n - 1]).isPositive();
        }
    }

    @Test
    void edgesGuardsAndGrades() {
        assertThat(HofstadterHammers.qSequence(0)).containsExactly(0);
        assertThat(HofstadterHammers.conwaySequence(1)).containsExactly(0, 1);
        assertThat(HofstadterHammers.q(1)).isEqualTo(1);
        assertThat(HofstadterHammers.conway(2)).isEqualTo(1);
        assertThatThrownBy(() -> HofstadterHammers.qSequence(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HofstadterHammers.conwaySequence(HofstadterHammers.MAX_N + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HofstadterHammers.q(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HofstadterHammers.conway(0)).isInstanceOf(IllegalArgumentException.class);
        assertThat(HofstadterHammers.grade(HofstadterHammers.Hammer.Q, 15, 10))
                .isEqualTo(HofstadterHammers.Grade.TURNED);
        assertThat(HofstadterHammers.grade(HofstadterHammers.Hammer.CONWAY, 15, 10))
                .isEqualTo(HofstadterHammers.Grade.SLIPPED);
        assertThat(HofstadterHammers.grade(HofstadterHammers.Hammer.CONWAY, 15, 8))
                .isEqualTo(HofstadterHammers.Grade.TURNED);
        for (HofstadterHammers.Grade g : HofstadterHammers.Grade.values()) {
            assertThat(HofstadterHammers.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(HofstadterHammers.QUEST_ID).isEqualTo("q_hofstadter_hammers");
    }
}
