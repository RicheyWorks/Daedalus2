// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class RiggingCountTest {

    private static int find(int[] p, int x) {
        int r = x;
        while (p[r] != r) {
            r = p[r];
        }
        return r;
    }

    /** Brute force: count (n-1)-line subsets that connect all spars with no loop. */
    private static long bruteTrees(int n, int[][] lines) {
        int e = lines.length;
        long total = 0;
        for (int mask = 0; mask < 1 << e; mask++) {
            if (Integer.bitCount(mask) != n - 1) {
                continue;
            }
            int[] p = new int[n];
            for (int i = 0; i < n; i++) {
                p[i] = i;
            }
            boolean ok = true;
            for (int k = 0; k < e && ok; k++) {
                if ((mask >> k & 1) == 1) {
                    int a = find(p, lines[k][0]);
                    int b = find(p, lines[k][1]);
                    ok = a != b;
                    p[a] = b;
                }
            }
            if (ok) {
                total++;
            }
        }
        return total;
    }

    private static int[][] completeLines(int n) {
        List<int[]> out = new ArrayList<>();
        for (int a = 0; a < n; a++) {
            for (int b = a + 1; b < n; b++) {
                out.add(new int[] {a, b});
            }
        }
        return out.toArray(new int[0][]);
    }

    @Test
    void randomDecksMatchBruteForceEnumeration() {
        SplittableRandom rnd = new SplittableRandom(512L);
        for (int trial = 0; trial < 120; trial++) {
            int n = 1 + rnd.nextInt(7);
            int e = rnd.nextInt(13);
            int[][] lines = new int[e][];
            for (int k = 0; k < e; k++) {
                lines[k] = new int[] {rnd.nextInt(n), rnd.nextInt(n)};
            }
            assertThat(RiggingCount.count(n, lines)).as("trial %d", trial)
                .isEqualTo(BigInteger.valueOf(bruteTrees(n, lines)));
        }
    }

    @Test
    void completeDecksFollowCayleyEvenWhenHuge() {
        for (int n = 1; n <= 7; n++) {
            assertThat(RiggingCount.count(n, completeLines(n))).isEqualTo(RiggingCount.complete(n));
            assertThat(RiggingCount.complete(n)).isEqualTo(BigInteger.valueOf(bruteTrees(n, completeLines(n))));
        }
        assertThat(RiggingCount.count(30, completeLines(30))).isEqualTo(BigInteger.valueOf(30).pow(28));
    }

    @Test
    void handWorkedDecksAndLocker() {
        int[][] cycle = {{0, 1}, {1, 2}, {2, 3}, {3, 0}};
        assertThat(RiggingCount.count(4, cycle)).isEqualTo(BigInteger.valueOf(4));
        int[][] doubled = {{0, 1}, {0, 1}, {1, 2}};
        assertThat(RiggingCount.count(3, doubled)).isEqualTo(BigInteger.valueOf(2));
        assertThat(RiggingCount.count(3, new int[][] {{0, 1}, {2, 2}})).isEqualTo(BigInteger.ZERO);
        assertThat(RiggingCount.count(1, new int[0][])).isEqualTo(BigInteger.ONE);
        assertThat(RiggingCount.locker(4, cycle)).contains("4 riggings");
        assertThat(RiggingCount.locker(2, new int[0][])).contains("cannot all be rigged");
    }

    @Test
    void questAndBadInput() {
        int[][] cycle = {{0, 1}, {1, 2}, {2, 0}};
        assertThat(RiggingCount.QUEST_ID).isEqualTo("q_rigging_count");
        assertThat(RiggingCount.quest(3, cycle, BigInteger.valueOf(3))).isTrue();
        assertThat(RiggingCount.quest(3, cycle, BigInteger.TWO)).isFalse();
        assertThat(RiggingCount.quest(3, cycle, null)).isFalse();
        assertThatThrownBy(() -> RiggingCount.count(0, cycle)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RiggingCount.count(2, cycle)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RiggingCount.count(3, new int[][] {{0}})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RiggingCount.complete(201)).isInstanceOf(IllegalArgumentException.class);
    }
}