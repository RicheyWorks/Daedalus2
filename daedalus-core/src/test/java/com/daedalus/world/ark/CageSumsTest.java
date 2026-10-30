// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CageSumsTest {

    private int[] cageOf;
    private char[] ops;
    private int[] targets;

    private static int[][] latin(int n, SplittableRandom rnd) {
        int[] rp = perm(n, rnd);
        int[] cp = perm(n, rnd);
        int[] sp = perm(n, rnd);
        int[][] g = new int[n][n];
        for (int r = 0; r < n; r++) {
            for (int c = 0; c < n; c++) {
                g[r][c] = sp[(rp[r] + cp[c]) % n] + 1;
            }
        }
        return g;
    }

    private static int[] perm(int n, SplittableRandom rnd) {
        int[] p = new int[n];
        for (int i = 0; i < n; i++) {
            p[i] = i;
        }
        for (int i = n - 1; i > 0; i--) {
            int j = rnd.nextInt(i + 1);
            int t = p[i];
            p[i] = p[j];
            p[j] = t;
        }
        return p;
    }

    /** Random cages of 1-3 horizontally adjacent cells, with targets taken from g. */
    private void makeCages(int[][] g, SplittableRandom rnd) {
        int n = g.length;
        cageOf = new int[n * n];
        int[] tmpT = new int[n * n];
        char[] tmpO = new char[n * n];
        int k = 0;
        for (int r = 0; r < n; r++) {
            int c = 0;
            while (c < n) {
                int len = Math.min(n - c, rnd.nextInt(1, 4));
                for (int i = 0; i < len; i++) {
                    cageOf[r * n + c + i] = k;
                }
                int a = g[r][c];
                if (len == 1) {
                    tmpO[k] = '=';
                    tmpT[k] = a;
                } else if (len == 2) {
                    int b = g[r][c + 1];
                    int pick = rnd.nextInt(4);
                    int hi = Math.max(a, b);
                    int lo = Math.min(a, b);
                    if (pick == 0) {
                        tmpO[k] = '+';
                        tmpT[k] = a + b;
                    } else if (pick == 1) {
                        tmpO[k] = '*';
                        tmpT[k] = a * b;
                    } else if (pick == 2 || hi % lo != 0) {
                        tmpO[k] = '-';
                        tmpT[k] = hi - lo;
                    } else {
                        tmpO[k] = '/';
                        tmpT[k] = hi / lo;
                    }
                } else {
                    boolean plus = rnd.nextBoolean();
                    int acc = plus ? 0 : 1;
                    for (int i = 0; i < len; i++) {
                        acc = plus ? acc + g[r][c + i] : acc * g[r][c + i];
                    }
                    tmpO[k] = plus ? '+' : '*';
                    tmpT[k] = acc;
                }
                k++;
                c += len;
            }
        }
        ops = java.util.Arrays.copyOf(tmpO, k);
        targets = java.util.Arrays.copyOf(tmpT, k);
    }

    private long brute(int n, int r, int[][] g) {
        if (r == n) {
            return CageSums.isValid(g, cageOf, ops, targets) ? 1 : 0;
        }
        long total = 0;
        int[] p = new int[n];
        for (int i = 0; i < n; i++) {
            p[i] = i + 1;
        }
        total += permute(n, r, g, p, 0);
        return total;
    }

    private long permute(int n, int r, int[][] g, int[] p, int i) {
        if (i == n) {
            for (int rr = 0; rr < r; rr++) {
                for (int c = 0; c < n; c++) {
                    if (g[rr][c] == p[c]) {
                        return 0;
                    }
                }
            }
            g[r] = p.clone();
            return brute(n, r + 1, g);
        }
        long t = 0;
        for (int j = i; j < n; j++) {
            int x = p[i];
            p[i] = p[j];
            p[j] = x;
            t += permute(n, r, g, p, i + 1);
            p[j] = p[i];
            p[i] = x;
        }
        return t;
    }

    @Test
    void countMatchesBruteForceOverAllLatinSquares() {
        SplittableRandom rnd = new SplittableRandom(380);
        for (int t = 0; t < 40; t++) {
            int n = rnd.nextInt(1, 5);
            int[][] g = latin(n, rnd);
            makeCages(g, rnd);
            long want = brute(n, 0, new int[n][]);
            assertThat(want).isGreaterThanOrEqualTo(1);
            assertThat(CageSums.count(n, cageOf, ops, targets, Long.MAX_VALUE)).isEqualTo(want);
            int[][] s = CageSums.solve(n, cageOf, ops, targets);
            assertThat(CageSums.isValid(s, cageOf, ops, targets)).isTrue();
        }
    }

    @Test
    void solvesFiveByFiveAndQuest() {
        SplittableRandom rnd = new SplittableRandom(5);
        int[][] g = latin(5, rnd);
        makeCages(g, rnd);
        int[][] s = CageSums.solve(5, cageOf, ops, targets);
        assertThat(s.length).isEqualTo(5);
        assertThat(CageSums.quest(s, cageOf, ops, targets)).isTrue();
        assertThat(CageSums.quest(g, cageOf, ops, targets)).isTrue();
        int[][] bad = new int[5][];
        for (int r = 0; r < 5; r++) {
            bad[r] = g[r].clone();
        }
        int x = bad[0][0];
        bad[0][0] = bad[0][1];
        bad[0][1] = x;
        assertThat(CageSums.quest(bad, cageOf, ops, targets)).isFalse();
        assertThat(CageSums.QUEST_ID).isEqualTo("q_cage_sums");
    }

    @Test
    void unsolvableAndBadInput() {
        int[] one = {0, 0, 0, 0};
        assertThat(CageSums.count(2, one, new char[] {'+'}, new int[] {7}, 10)).isZero();
        assertThat(CageSums.solve(2, one, new char[] {'+'}, new int[] {7})).isEmpty();
        assertThat(CageSums.count(2, one, new char[] {'+'}, new int[] {6}, 10)).isEqualTo(2);
        assertThatThrownBy(() -> CageSums.count(6, new int[36], new char[] {'+'}, new int[] {1}, 1))
            .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> CageSums.count(2, one, new char[] {'-'}, new int[] {1}, 1))
            .isInstanceOf(IllegalArgumentException.class);
    }
}
