// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CargoSumsTest {

    @Test
    void combosMatchBruteForceSubsets() {
        for (int cells = 1; cells <= 9; cells++) {
            for (int sum = 1; sum <= 45; sum++) {
                int want = 0;
                for (int mask = 0; mask < 512; mask++) {
                    int s = 0;
                    for (int i = 0; i < 9; i++) {
                        if ((mask >> i & 1) != 0) {
                            s += i + 1;
                        }
                    }
                    if (Integer.bitCount(mask) == cells && s == sum) {
                        want++;
                    }
                }
                assertThat(CargoSums.combos(sum, cells)).hasSize(want);
            }
        }
        assertThat(CargoSums.forced(3, 2)).isEqualTo((1 << 1) | (1 << 2));
        assertThat(CargoSums.forced(23, 3)).isEqualTo((1 << 6) | (1 << 8) | (1 << 9));
    }

    private static int brute(int cells, int[][] runs, int[] sums) {
        int total = 1;
        for (int i = 0; i < cells; i++) {
            total *= 9;
        }
        int[] dg = new int[cells];
        int n = 0;
        for (int code = 0; code < total; code++) {
            int x = code;
            for (int i = 0; i < cells; i++) {
                dg[i] = x % 9 + 1;
                x /= 9;
            }
            if (CargoSums.isFilled(runs, sums, dg)) {
                n++;
            }
        }
        return n;
    }

    @Test
    void twoByThreeBlocksMatchBruteForce() {
        int[][] runs = {{0, 1, 2}, {3, 4, 5}, {0, 3}, {1, 4}, {2, 5}};
        SplittableRandom rnd = new SplittableRandom(370);
        for (int t = 0; t < 25; t++) {
            int[] dg = new int[6];
            int[] sums = new int[runs.length];
            for (int i = 0; i < 6; i++) {
                dg[i] = rnd.nextInt(1, 10);
            }
            for (int r = 0; r < runs.length; r++) {
                for (int c : runs[r]) {
                    sums[r] += dg[c];
                }
            }
            int want = brute(6, runs, sums);
            assertThat(CargoSums.count(6, runs, sums, 1_000_000)).isEqualTo(want);
            int[] got = CargoSums.solve(6, runs, sums);
            assertThat(got.length > 0).isEqualTo(want > 0);
            if (want > 0) {
                assertThat(CargoSums.isFilled(runs, sums, got)).isTrue();
            }
        }
    }

    @Test
    void questAndGuards() {
        assertThat(CargoSums.QUEST_ID).isEqualTo("q_cargo_sums");
        int[][] runs = {{0, 1}, {0}, {1}};
        assertThat(CargoSums.quest(runs, new int[] {4, 1, 3}, new int[] {1, 3})).isTrue();
        assertThat(CargoSums.quest(runs, new int[] {4, 2, 2}, new int[] {2, 2})).isFalse();
        assertThat(CargoSums.combos(46, 9)).isEmpty();
        assertThatThrownBy(() -> CargoSums.combos(5, 10)).isInstanceOf(IllegalArgumentException.class);
    }
}