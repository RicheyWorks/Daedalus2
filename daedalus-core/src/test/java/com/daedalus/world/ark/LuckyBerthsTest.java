// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class LuckyBerthsTest {

    /** Naive sieve that really removes list entries. */
    private static List<Integer> naive(int n) {
        List<Integer> l = new ArrayList<>();
        for (int v = 1; v <= n; v += 2) {
            l.add(v);
        }
        for (int i = 1; i < l.size(); i++) {
            int step = l.get(i);
            if (step > l.size()) {
                break;
            }
            List<Integer> keep = new ArrayList<>();
            for (int j = 0; j < l.size(); j++) {
                if ((j + 1) % step != 0) {
                    keep.add(l.get(j));
                }
            }
            l = keep;
        }
        return l;
    }

    @Test
    void sieveMatchesNaive() {
        for (int n : new int[] {1, 2, 3, 10, 99, 100, 1000, 4321, 20_000}) {
            int[] got = LuckyBerths.upTo(n);
            List<Integer> want = naive(n);
            assertThat(got.length).as("n=%d", n).isEqualTo(want.size());
            for (int i = 0; i < got.length; i++) {
                assertThat(got[i]).isEqualTo(want.get(i));
            }
        }
    }

    @Test
    void firstTerms() {
        int[] l = LuckyBerths.upTo(33);
        assertThat(l).containsExactly(1, 3, 7, 9, 13, 15, 21, 25, 31, 33);
        assertThat(LuckyBerths.isLucky(49)).isEqualTo(naive(49).contains(49));
        assertThat(LuckyBerths.isLucky(5)).isFalse();
    }

    @Test
    void primesAndTwins() {
        List<Integer> lucky = naive(5000);
        List<Integer> want = new ArrayList<>();
        for (int v : lucky) {
            boolean p = v > 1;
            for (int d = 2; d * d <= v && p; d++) {
                p = v % d != 0;
            }
            if (p) {
                want.add(v);
            }
        }
        assertThat(LuckyBerths.luckyPrimes(5000)).isEqualTo(want);
        for (int s : LuckyBerths.twins(5000)) {
            assertThat(lucky).contains(s, s + 2);
        }
        assertThat(LuckyBerths.twins(10)).containsExactly(1, 7);
        assertThat(LuckyBerths.upTo(2_000_000).length).isPositive();
    }

    @Test
    void questAndBounds() {
        int want = naive(99).size();
        assertThat(LuckyBerths.quest(100, want)).isTrue();
        assertThat(LuckyBerths.quest(100, want + 1)).isFalse();
        assertThat(LuckyBerths.countBelow(1)).isZero();
        assertThat(LuckyBerths.QUEST_ID).isEqualTo("q_lucky_berths");
        assertThatThrownBy(() -> LuckyBerths.upTo(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> LuckyBerths.upTo(2_000_001)).isInstanceOf(IllegalArgumentException.class);
    }
}