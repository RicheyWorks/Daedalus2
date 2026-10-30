// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.NestingCrucibles.Grade;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class NestingCruciblesTest {

    private static int quadraticLis(int[] a) {
        int[] f = new int[a.length];
        int best = 0;
        for (int i = 0; i < a.length; i++) {
            f[i] = 1;
            for (int j = 0; j < i; j++) {
                if (a[j] < a[i]) {
                    f[i] = Math.max(f[i], f[j] + 1);
                }
            }
            best = Math.max(best, f[i]);
        }
        return best;
    }

    /** Brute force over every subset: the largest subset that can be ordered into a strict nest. */
    private static int bruteNest(int[][] p) {
        int best = 0;
        for (int mask = 0; mask < (1 << p.length); mask++) {
            boolean ok = true;
            for (int i = 0; i < p.length && ok; i++) {
                for (int j = i + 1; j < p.length && ok; j++) {
                    if ((mask >> i & 1) == 1 && (mask >> j & 1) == 1) {
                        ok = NestingCrucibles.fits(p[i], p[j]) || NestingCrucibles.fits(p[j], p[i]);
                    }
                }
            }
            if (ok) {
                best = Math.max(best, Integer.bitCount(mask));
            }
        }
        return best;
    }

    @Test
    void lisMatchesQuadraticDpAndIsStrictlyIncreasing() {
        for (long seed = 1; seed <= 300; seed++) {
            SplittableRandom r = new SplittableRandom(seed);
            int[] a = new int[(int) (seed % 40)];
            for (int i = 0; i < a.length; i++) {
                a[i] = r.nextInt(1 + (int) (seed % 25));
            }
            List<Integer> s = NestingCrucibles.lis(a);
            assertThat(s).as("seed %d", seed).hasSize(quadraticLis(a));
            for (int k = 1; k < s.size(); k++) {
                assertThat(s.get(k)).isGreaterThan(s.get(k - 1));
                assertThat(a[s.get(k)]).isGreaterThan(a[s.get(k - 1)]);
            }
        }
    }

    @Test
    void nestMatchesBruteForceOnSeededPiles() {
        for (long seed = 1; seed <= 300; seed++) {
            int[][] p = NestingCrucibles.pile(seed, 1 + (int) (seed % 13), 2 + (int) (seed % 9));
            List<Integer> n = NestingCrucibles.nest(p);
            assertThat(n).as("seed %d", seed).hasSize(bruteNest(p));
            assertThat(NestingCrucibles.grade(p, n)).isEqualTo(Grade.NESTED);
        }
    }

    @Test
    void equalWidthsNeverNest() {
        int[][] p = {{3, 1}, {3, 2}, {3, 3}, {4, 4}};
        assertThat(NestingCrucibles.nest(p)).hasSize(2);
        assertThat(NestingCrucibles.grade(p, List.of(0, 1))).isEqualTo(Grade.BROKEN);
        assertThat(NestingCrucibles.grade(p, List.of(0, 3))).isEqualTo(Grade.NESTED);
        assertThat(NestingCrucibles.grade(new int[][] {{1, 1}, {2, 2}, {3, 3}}, List.of(0, 2))).isEqualTo(Grade.LOOSE);
    }

    @Test
    void sameSeedReplays() {
        assertThat(NestingCrucibles.pile(210L, 12, 9)).isDeepEqualTo(NestingCrucibles.pile(210L, 12, 9));
        assertThat(NestingCrucibles.nest(NestingCrucibles.pile(210L, 12, 9)))
                .isEqualTo(NestingCrucibles.nest(NestingCrucibles.pile(210L, 12, 9)));
        assertThat(NestingCrucibles.QUEST_ID).isEqualTo("q_nesting_crucibles");
    }

    @Test
    void linesEdgesAndRejects() {
        assertThat(NestingCrucibles.lis(new int[0])).isEmpty();
        assertThat(NestingCrucibles.nest(new int[0][])).isEmpty();
        assertThat(NestingCrucibles.lis(new int[] {5, 5, 5})).hasSize(1);
        assertThat(NestingCrucibles.forgemasterLine(Grade.BROKEN, 0)).contains("crack");
        assertThatThrownBy(() -> NestingCrucibles.nest(new int[][] {{1}})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> NestingCrucibles.pile(1L, -1, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}
