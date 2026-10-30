// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class RiggingLadderTest {

    private static List<String> brute(int n) {
        List<String> out = new ArrayList<>();
        for (int mask = 0; mask < (1 << (2 * n)); mask++) {
            StringBuilder sb = new StringBuilder();
            for (int i = 2 * n - 1; i >= 0; i--) {
                sb.append((mask >> i & 1) == 1 ? 'U' : 'D');
            }
            if (RiggingLadder.isPlan(sb.toString())) {
                out.add(sb.toString());
            }
        }
        Collections.sort(out);
        return out;
    }

    @Test
    void countsRankAndUnrankMatchBruteForce() {
        for (int n = 0; n <= 8; n++) {
            List<String> all = brute(n);
            assertThat(RiggingLadder.count(n)).isEqualTo(BigInteger.valueOf(all.size()));
            for (int k = 0; k < all.size(); k++) {
                assertThat(RiggingLadder.rank(all.get(k))).isEqualTo(BigInteger.valueOf(k));
                assertThat(RiggingLadder.unrank(n, BigInteger.valueOf(k))).isEqualTo(all.get(k));
            }
        }
        assertThat(RiggingLadder.count(30)).isEqualTo(new BigInteger("3814986502092304"));
    }

    @Test
    void modAndLargeRoundTrip() {
        SplittableRandom rnd = new SplittableRandom(280);
        for (int t = 0; t < 120; t++) {
            int n = rnd.nextInt(0, 300);
            long m = rnd.nextLong(1, Integer.MAX_VALUE + 1L);
            assertThat(RiggingLadder.countMod(n, m)).isEqualTo(RiggingLadder.count(n).mod(BigInteger.valueOf(m)).longValue());
        }
        BigInteger total = RiggingLadder.count(150);
        for (int t = 0; t < 40; t++) {
            BigInteger k = BigInteger.ZERO;
            for (int w = 0; w < 6; w++) {
                k = k.shiftLeft(63).add(BigInteger.valueOf(rnd.nextLong(Long.MAX_VALUE)));
            }
            k = k.mod(total);
            String plan = RiggingLadder.unrank(150, k);
            assertThat(RiggingLadder.quest(150, plan)).isTrue();
            assertThat(RiggingLadder.rank(plan)).isEqualTo(k);
        }
    }

    @Test
    void questAndBounds() {
        assertThat(RiggingLadder.quest(2, "UDUD")).isTrue();
        assertThat(RiggingLadder.quest(2, "UUDD")).isTrue();
        assertThat(RiggingLadder.quest(2, "UDDU")).isFalse();
        assertThat(RiggingLadder.quest(3, "UDUD")).isFalse();
        assertThat(RiggingLadder.quest(1, "UX")).isFalse();
        assertThat(RiggingLadder.QUEST_ID).isEqualTo("q_rigging_ladder");
        assertThatThrownBy(() -> RiggingLadder.rank("DU")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RiggingLadder.unrank(3, BigInteger.valueOf(5))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RiggingLadder.countMod(3, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}