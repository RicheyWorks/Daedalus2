// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class CoverLotsTest {

    @Test
    void countMatchesBruteForceSubsets() {
        SplittableRandom rnd = new SplittableRandom(371);
        for (int t = 0; t < 300; t++) {
            int slots = rnd.nextInt(1, 8);
            int n = rnd.nextInt(1, 15);
            int[][] lots = new int[n][];
            for (int r = 0; r < n; r++) {
                List<Integer> s = new ArrayList<>();
                for (int c = 0; c < slots; c++) {
                    if (rnd.nextInt(3) == 0) {
                        s.add(c);
                    }
                }
                if (s.isEmpty()) {
                    s.add(rnd.nextInt(slots));
                }
                lots[r] = s.stream().mapToInt(Integer::intValue).toArray();
            }
            long want = 0;
            for (int mask = 0; mask < (1 << n); mask++) {
                int[] pick = new int[Integer.bitCount(mask)];
                int k = 0;
                for (int r = 0; r < n; r++) {
                    if ((mask >> r & 1) != 0) {
                        pick[k++] = r;
                    }
                }
                if (CoverLots.isExact(slots, lots, pick)) {
                    want++;
                }
            }
            assertThat(CoverLots.count(slots, lots, Long.MAX_VALUE)).isEqualTo(want);
            int[] got = CoverLots.solve(slots, lots);
            assertThat(got.length > 0).isEqualTo(want > 0);
            if (want > 0) {
                assertThat(CoverLots.isExact(slots, lots, got)).isTrue();
            }
        }
    }

    @Test
    void dominoTilingsAgreeWithDeckPlanks() {
        for (int h = 1; h <= 4; h++) {
            for (int w = 1; w <= 6; w++) {
                List<int[]> lots = new ArrayList<>();
                for (int r = 0; r < h; r++) {
                    for (int c = 0; c < w; c++) {
                        if (c + 1 < w) {
                            lots.add(new int[] {r * w + c, r * w + c + 1});
                        }
                        if (r + 1 < h) {
                            lots.add(new int[] {r * w + c, (r + 1) * w + c});
                        }
                    }
                }
                long got = CoverLots.count(h * w, lots.toArray(new int[0][]), Long.MAX_VALUE);
                assertThat(BigInteger.valueOf(got)).isEqualTo(DeckPlanks.count(h, w));
            }
        }
    }

    @Test
    void questAndGuards() {
        assertThat(CoverLots.QUEST_ID).isEqualTo("q_cover_lots");
        int[][] lots = {{0, 1}, {2}, {1, 2}, {0}};
        assertThat(CoverLots.quest(3, lots, new int[] {0, 1})).isTrue();
        assertThat(CoverLots.quest(3, lots, new int[] {0, 2})).isFalse();
        assertThat(CoverLots.solve(3, new int[][] {{0}, {1}})).isEmpty();
        assertThatThrownBy(() -> CoverLots.count(2, new int[][] {{}}, 1)).isInstanceOf(IllegalArgumentException.class);
    }
}