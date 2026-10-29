// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class LotDrawsTest {

    private static List<int[]> parties(int n, int k) {
        List<int[]> out = new ArrayList<>();
        for (int mask = 0; mask < (1 << n); mask++) {
            if (Integer.bitCount(mask) == k) {
                int[] p = new int[k];
                int j = 0;
                for (int i = 0; i < n; i++) {
                    if ((mask >> i & 1) != 0) {
                        p[j++] = i;
                    }
                }
                out.add(p);
            }
        }
        Comparator<int[]> colex = (x, y) -> {
            for (int i = x.length - 1; i >= 0; i--) {
                if (x[i] != y[i]) {
                    return Integer.compare(x[i], y[i]);
                }
            }
            return 0;
        };
        out.sort(colex);
        return out;
    }

    @Test
    void rankUnrankNextMatchBruteForce() {
        for (int n = 0; n <= 12; n++) {
            for (int k = 0; k <= n; k++) {
                List<int[]> all = parties(n, k);
                assertThat(BigInteger.valueOf(all.size())).isEqualTo(LotDraws.binom(n, k));
                for (int r = 0; r < all.size(); r++) {
                    int[] p = all.get(r);
                    assertThat(LotDraws.rank(p)).isEqualTo(BigInteger.valueOf(r));
                    assertThat(LotDraws.unrank(k, BigInteger.valueOf(r))).isEqualTo(p);
                    java.util.Optional<int[]> nx = LotDraws.next(p, n);
                    if (r + 1 < all.size()) {
                        assertThat(nx).isPresent();
                        assertThat(nx.get()).isEqualTo(all.get(r + 1));
                    } else {
                        assertThat(nx).isEmpty();
                    }
                }
            }
        }
    }

    @Test
    void largeRoundTrip() {
        SplittableRandom rnd = new SplittableRandom(309);
        for (int t = 0; t < 300; t++) {
            int k = rnd.nextInt(1, 40);
            int[] p = rnd.ints(0, 4000).distinct().limit(k).sorted().toArray();
            assertThat(LotDraws.unrank(k, LotDraws.rank(p))).isEqualTo(p);
        }
    }

    @Test
    void questAndBounds() {
        assertThat(LotDraws.quest(new int[] {0, 2, 3}, BigInteger.valueOf(2))).isTrue();
        assertThat(LotDraws.quest(new int[] {0, 2, 3}, BigInteger.valueOf(3))).isFalse();
        assertThat(LotDraws.QUEST_ID).isEqualTo("q_lot_draws");
        assertThatThrownBy(() -> LotDraws.rank(new int[] {2, 2})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LotDraws.unrank(1, BigInteger.valueOf(LotDraws.MAX_CREW))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LotDraws.next(new int[] {5}, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}