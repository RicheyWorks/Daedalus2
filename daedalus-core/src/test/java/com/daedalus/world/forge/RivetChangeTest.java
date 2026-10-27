// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.RivetChange.Grade;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RivetChangeTest {

    /** Brute force: smallest plate count (or MAX) and number of multisets, by recursion over sizes. */
    private static int bruteFewest(int[] k, int i, int left) {
        if (left == 0) {
            return 0;
        }
        if (i == k.length) {
            return Integer.MAX_VALUE;
        }
        int best = Integer.MAX_VALUE;
        for (int c = 0; c * k[i] <= left; c++) {
            int r = bruteFewest(k, i + 1, left - c * k[i]);
            if (r != Integer.MAX_VALUE) {
                best = Math.min(best, r + c);
            }
        }
        return best;
    }

    private static long bruteWays(int[] k, int i, int left) {
        if (left == 0) {
            return 1;
        }
        if (i == k.length) {
            return 0;
        }
        long n = 0;
        for (int c = 0; c * k[i] <= left; c++) {
            n += bruteWays(k, i + 1, left - c * k[i]);
        }
        return n;
    }

    @Test
    void fewestAndWaysMatchBruteForceOnSeededKits() {
        for (long seed = 1; seed <= 200; seed++) {
            int[] kit = RivetChange.kit(seed, 1 + (int) (seed % 4), 12);
            int len = (int) (seed % 40);
            List<Integer> f = RivetChange.fewest(kit, len);
            assertThat(f.size()).as("seed %d", seed).isEqualTo(bruteFewest(kit, 0, len));
            assertThat(f.stream().mapToInt(Integer::intValue).sum()).isEqualTo(len);
            assertThat(RivetChange.ways(kit, len)).isEqualTo(bruteWays(kit, 0, len));
        }
    }

    @Test
    void canonicalCheckAgreesWithAnExhaustiveSweep() {
        for (long seed = 1; seed <= 200; seed++) {
            int[] kit = RivetChange.kit(seed * 31L, 1 + (int) (seed % 4), 15);
            int firstBad = -1;
            for (int v = 1; v <= 200 && firstBad < 0; v++) {
                if (RivetChange.greedy(kit, v).size() > RivetChange.fewest(kit, v).size()) {
                    firstBad = v;
                }
            }
            assertThat(RivetChange.counterexample(kit)).as("seed %d", seed).isEqualTo(firstBad);
        }
    }

    @Test
    void greedyLosesOnANonCanonicalKitAndWinsOnACanonicalOne() {
        int[] odd = {1, 3, 4};
        assertThat(RivetChange.greedy(odd, 6)).containsExactly(1, 1, 4);
        assertThat(RivetChange.fewest(odd, 6)).containsExactly(3, 3);
        assertThat(RivetChange.counterexample(odd)).isEqualTo(6);
        assertThat(RivetChange.canonical(new int[] {1, 2, 5, 10})).isTrue();
        assertThat(RivetChange.ways(new int[] {1, 2, 5}, 5)).isEqualTo(4);
    }

    @Test
    void sameSeedReplaysTheSameKit() {
        assertThat(RivetChange.kit(191L, 4, 20)).isEqualTo(RivetChange.kit(191L, 4, 20));
        assertThat(RivetChange.kit(191L, 4, 20)[0]).isEqualTo(1);
        assertThat(RivetChange.kit(192L, 4, 20)).isNotEqualTo(RivetChange.kit(191L, 4, 20));
    }

    @Test
    void gradesAndLines() {
        int[] odd = {1, 3, 4};
        assertThat(RivetChange.grade(odd, 6, List.of(3, 3))).isEqualTo(Grade.FLUSH);
        assertThat(RivetChange.grade(odd, 6, List.of(4, 1, 1))).isEqualTo(Grade.LUMPY);
        assertThat(RivetChange.grade(odd, 6, List.of(4, 1))).isEqualTo(Grade.NO_FIT);
        assertThat(RivetChange.grade(odd, 6, List.of(2, 4))).isEqualTo(Grade.NO_FIT);
        assertThat(RivetChange.forgemasterLine(Grade.FLUSH, 2)).contains("2 plates");
        assertThat(RivetChange.QUEST_ID).isEqualTo("q_rivet_change");
    }

    @Test
    void edgeCasesAndRejects() {
        assertThat(RivetChange.fewest(new int[] {3, 5}, 7)).isEmpty();
        assertThat(RivetChange.greedy(new int[] {3, 5}, 7)).isEmpty();
        assertThat(RivetChange.fewest(new int[] {3, 5}, 0)).isEmpty();
        assertThat(RivetChange.ways(new int[] {3, 5}, 0)).isEqualTo(1);
        assertThatThrownBy(() -> RivetChange.fewest(new int[0], 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RivetChange.fewest(new int[] {0}, 3)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RivetChange.kit(1L, 5, 4)).isInstanceOf(IllegalArgumentException.class);
    }
}
