// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class KnotCodesTest {

    private static int find(int[] p, int x) {
        int r = x;
        while (p[r] != r) {
            r = p[r];
        }
        return r;
    }

    /** Brute force: every labelled tree on n spars as sorted line lists. */
    private static List<int[][]> allTrees(int n) {
        List<int[]> pairs = new ArrayList<>();
        for (int a = 0; a < n; a++) {
            for (int b = a + 1; b < n; b++) {
                pairs.add(new int[] {a, b});
            }
        }
        List<int[][]> out = new ArrayList<>();
        for (int mask = 0; mask < 1 << pairs.size(); mask++) {
            if (Integer.bitCount(mask) != n - 1) {
                continue;
            }
            int[] p = new int[n];
            for (int i = 0; i < n; i++) {
                p[i] = i;
            }
            List<int[]> t = new ArrayList<>();
            boolean ok = true;
            for (int k = 0; k < pairs.size() && ok; k++) {
                if ((mask >> k & 1) == 1) {
                    int x = find(p, pairs.get(k)[0]);
                    int y = find(p, pairs.get(k)[1]);
                    ok = x != y;
                    p[x] = y;
                    t.add(pairs.get(k));
                }
            }
            if (ok) {
                out.add(t.toArray(new int[0][]));
            }
        }
        return out;
    }

    @Test
    void codesAreABijectionOnEveryTreeForSmallN() {
        for (int n = 2; n <= 6; n++) {
            List<int[][]> trees = allTrees(n);
            assertThat(trees).hasSize((int) Math.pow(n, Math.max(0, n - 2)));
            Set<Long> ranks = new HashSet<>();
            for (int[][] t : trees) {
                int[] code = KnotCodes.encode(n, t);
                assertThat(KnotCodes.decode(n, code)).isDeepEqualTo(t);
                long r = KnotCodes.rank(n, code);
                assertThat(KnotCodes.unrank(n, r)).containsExactly(code);
                ranks.add(r);
            }
            assertThat(ranks).hasSize(trees.size());
        }
    }

    @Test
    void randomBigCodesRoundTrip() {
        SplittableRandom rnd = new SplittableRandom(515L);
        for (int trial = 0; trial < 30; trial++) {
            int n = 2 + rnd.nextInt(3000);
            int[] code = new int[n - 2];
            for (int k = 0; k < code.length; k++) {
                code[k] = rnd.nextInt(n);
            }
            int[][] tree = KnotCodes.decode(n, code);
            assertThat(tree).hasNumberOfRows(n - 1);
            assertThat(KnotCodes.encode(n, tree)).containsExactly(code);
        }
    }

    @Test
    void handWorkedRiggingAndBoard() {
        int[][] star = {{0, 1}, {0, 2}, {0, 3}};
        assertThat(KnotCodes.encode(4, star)).containsExactly(0, 0);
        int[][] path = {{0, 1}, {1, 2}, {2, 3}, {3, 4}};
        assertThat(KnotCodes.encode(5, path)).containsExactly(1, 2, 3);
        assertThat(KnotCodes.decode(2, new int[0])).isDeepEqualTo(new int[][] {{0, 1}});
        assertThat(KnotCodes.rank(5, new int[] {1, 2, 3})).isEqualTo(38L);
        assertThat(KnotCodes.board(4, star)).contains("code [0, 0]");
        assertThat(Arrays.toString(KnotCodes.unrank(5, 124L))).isEqualTo("[4, 4, 4]");
    }

    @Test
    void questAndBadInput() {
        int[][] path = {{0, 1}, {1, 2}, {2, 3}};
        assertThat(KnotCodes.QUEST_ID).isEqualTo("q_knot_codes");
        assertThat(KnotCodes.quest(4, path, new int[] {1, 2})).isTrue();
        assertThat(KnotCodes.quest(4, path, new int[] {2, 1})).isFalse();
        assertThat(KnotCodes.quest(4, path, null)).isFalse();
        assertThatThrownBy(() -> KnotCodes.encode(4, new int[][] {{0, 1}, {1, 2}, {2, 0}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KnotCodes.encode(4, new int[][] {{0, 1}, {1, 2}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KnotCodes.encode(4, new int[][] {{0, 1}, {0, 1}, {2, 3}}))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KnotCodes.decode(4, new int[] {0, 4})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KnotCodes.unrank(3, 3L)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> KnotCodes.encode(1, new int[0][])).isInstanceOf(IllegalArgumentException.class);
    }
}