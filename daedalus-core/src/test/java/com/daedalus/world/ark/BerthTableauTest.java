// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class BerthTableauTest {

    private static void partitions(int n, int max, List<Integer> cur, List<int[]> out) {
        if (n == 0) {
            out.add(cur.stream().mapToInt(Integer::intValue).toArray());
            return;
        }
        for (int k = Math.min(n, max); k >= 1; k--) {
            cur.add(k);
            partitions(n - k, k, cur, out);
            cur.remove(cur.size() - 1);
        }
    }

    private static int brute(int[] shape, int n, int[] perm, boolean[] used, int depth) {
        if (depth == n) {
            int[][] b = new int[shape.length][];
            int p = 0;
            for (int r = 0; r < shape.length; r++) {
                b[r] = new int[shape[r]];
                for (int c = 0; c < shape[r]; c++) {
                    b[r][c] = perm[p++];
                }
            }
            return BerthTableau.isStandard(b) ? 1 : 0;
        }
        int total = 0;
        for (int v = 1; v <= n; v++) {
            if (!used[v]) {
                used[v] = true;
                perm[depth] = v;
                total += brute(shape, n, perm, used, depth + 1);
                used[v] = false;
            }
        }
        return total;
    }

    @Test
    void hookCountMatchesEveryFillingUpToSeven() {
        for (int n = 1; n <= 7; n++) {
            List<int[]> shapes = new ArrayList<>();
            partitions(n, n, new ArrayList<>(), shapes);
            BigInteger sumSquares = BigInteger.ZERO;
            BigInteger fact = BigInteger.ONE;
            for (int i = 2; i <= n; i++) {
                fact = fact.multiply(BigInteger.valueOf(i));
            }
            for (int[] shape : shapes) {
                BigInteger f = BerthTableau.count(shape);
                assertThat(f).isEqualTo(BigInteger.valueOf(brute(shape, n, new int[n], new boolean[n + 1], 0)));
                sumSquares = sumSquares.add(f.multiply(f));
            }
            assertThat(sumSquares).isEqualTo(fact);
        }
    }

    @Test
    void knownCounts() {
        assertThat(BerthTableau.count(new int[] {3, 2})).isEqualTo(BigInteger.valueOf(5));
        assertThat(BerthTableau.count(new int[] {5, 5})).isEqualTo(BigInteger.valueOf(42));
        assertThat(BerthTableau.count(new int[] {3, 3, 3})).isEqualTo(BigInteger.valueOf(42));
    }

    @Test
    void questAndGuards() {
        assertThat(BerthTableau.QUEST_ID).isEqualTo("q_berth_tableau");
        assertThat(BerthTableau.quest(new int[] {2, 1}, 2)).isTrue();
        assertThat(BerthTableau.quest(new int[] {2, 1}, 3)).isFalse();
        assertThat(BerthTableau.isStandard(new int[][] {{1, 3}, {2}})).isTrue();
        assertThat(BerthTableau.isStandard(new int[][] {{1, 2}, {3, 1}})).isFalse();
        assertThatThrownBy(() -> BerthTableau.count(new int[] {1, 2})).isInstanceOf(IllegalArgumentException.class);
    }
}