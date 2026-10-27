// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.OreSeamClaim.Claim;
import com.daedalus.world.forge.OreSeamClaim.Grade;
import com.daedalus.world.forge.OreSeamClaim.Run;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class OreSeamClaimTest {

    /** Brute force over every rectangle with 2D prefix sums. */
    private static long brute(int[][] g) {
        int r = g.length;
        int c = g[0].length;
        long[][] p = new long[r + 1][c + 1];
        for (int i = 0; i < r; i++) {
            for (int j = 0; j < c; j++) {
                p[i + 1][j + 1] = g[i][j] + p[i][j + 1] + p[i + 1][j] - p[i][j];
            }
        }
        long best = Long.MIN_VALUE;
        for (int t = 0; t < r; t++) {
            for (int b = t; b < r; b++) {
                for (int l = 0; l < c; l++) {
                    for (int rr = l; rr < c; rr++) {
                        best = Math.max(best, p[b + 1][rr + 1] - p[t][rr + 1] - p[b + 1][l] + p[t][l]);
                    }
                }
            }
        }
        return best;
    }

    @Test
    void bestClaimMatchesBruteForceOnSeededScars() {
        for (long seed = 1; seed <= 300; seed++) {
            int[][] g = OreSeamClaim.scar(seed, 1 + (int) (seed % 9), 1 + (int) (seed % 11), (int) (seed % 15));
            Claim c = OreSeamClaim.bestClaim(g);
            assertThat(c.sum()).as("seed %d", seed).isEqualTo(brute(g));
            assertThat(OreSeamClaim.sum(g, c.top(), c.left(), c.bottom(), c.right())).isEqualTo(c.sum());
        }
    }

    @Test
    void bestRunMatchesBruteForce() {
        for (long seed = 1; seed <= 300; seed++) {
            int[] a = OreSeamClaim.scar(seed * 5L, 1, 1 + (int) (seed % 30), 9)[0];
            Run r = OreSeamClaim.bestRun(a);
            long best = Long.MIN_VALUE;
            for (int i = 0; i < a.length; i++) {
                long s = 0;
                for (int j = i; j < a.length; j++) {
                    s += a[j];
                    best = Math.max(best, s);
                }
            }
            assertThat(r.sum()).isEqualTo(best);
            long s = 0;
            for (int k = r.from(); k <= r.to(); k++) {
                s += a[k];
            }
            assertThat(s).isEqualTo(r.sum());
        }
    }

    @Test
    void handWorkedScars() {
        assertThat(OreSeamClaim.bestRun(new int[] {-2, 1, -3, 4, -1, 2, 1, -5, 4}))
                .isEqualTo(new Run(3, 6, 6));
        assertThat(OreSeamClaim.bestRun(new int[] {-5, -2, -7}).sum()).isEqualTo(-2);
        int[][] g = {{0, -2, -7, 0}, {9, 2, -6, 2}, {-4, 1, -4, 1}, {-1, 8, 0, -2}};
        Claim c = OreSeamClaim.bestClaim(g);
        assertThat(c.sum()).isEqualTo(15);
        assertThat(c).isEqualTo(new Claim(1, 0, 3, 1, 15));
    }

    @Test
    void sameSeedReplays() {
        assertThat(OreSeamClaim.scar(214L, 6, 7, 9)).isDeepEqualTo(OreSeamClaim.scar(214L, 6, 7, 9));
        assertThat(OreSeamClaim.bestClaim(OreSeamClaim.scar(214L, 6, 7, 9)))
                .isEqualTo(OreSeamClaim.bestClaim(OreSeamClaim.scar(214L, 6, 7, 9)));
        assertThat(OreSeamClaim.QUEST_ID).isEqualTo("q_ore_seam_claim");
    }

    @Test
    void gradesLinesAndRejects() {
        assertThat(OreSeamClaim.grade(20, 20)).isEqualTo(Grade.RICH);
        assertThat(OreSeamClaim.grade(15, 20)).isEqualTo(Grade.FAIR);
        assertThat(OreSeamClaim.grade(14, 20)).isEqualTo(Grade.BUST);
        assertThat(OreSeamClaim.grade(-5, -2)).isEqualTo(Grade.BUST);
        assertThatThrownBy(() -> OreSeamClaim.grade(21, 20)).isInstanceOf(IllegalArgumentException.class);
        assertThat(OreSeamClaim.forgemasterLine(-1, 5)).contains("dug more");
        assertThatThrownBy(() -> OreSeamClaim.bestRun(new int[0])).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> OreSeamClaim.bestClaim(new int[][] {{1, 2}, {3}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> OreSeamClaim.sum(new int[][] {{1}}, 0, 0, 1, 0))
                .isInstanceOf(IllegalArgumentException.class);
    }
}
