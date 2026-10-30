// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class EchoAnvilTest {

    private static int[] naive(String s, int window, int maxLen) {
        List<Integer> out = new ArrayList<>();
        int n = s.length();
        int i = 0;
        while (i < n) {
            int bestLen = 0;
            int bestOff = 0;
            int cap = Math.min(maxLen, n - 1 - i);
            for (int off = 1; off <= Math.min(window, i); off++) {
                int len = 0;
                while (len < cap && s.charAt(i - off + len) == s.charAt(i + len)) {
                    len++;
                }
                if (len > bestLen) {
                    bestLen = len;
                    bestOff = off;
                }
            }
            if (bestLen < EchoAnvil.MIN_MATCH) {
                bestLen = 0;
                bestOff = 0;
            }
            out.add(bestOff);
            out.add(bestLen);
            out.add((int) s.charAt(i + bestLen));
            i += bestLen + 1;
        }
        return out.stream().mapToInt(Integer::intValue).toArray();
    }

    @Test
    void matchesNaiveAndRoundTrips() {
        for (long seed = 0; seed < 300; seed++) {
            String s = EchoAnvil.pattern(seed, (int) (seed % 150));
            int window = 1 + (int) (seed % 40);
            int maxLen = EchoAnvil.MIN_MATCH + (int) (seed % 20);
            int[] t = EchoAnvil.encode(s, window, maxLen);
            assertThat(t).containsExactly(naive(s, window, maxLen));
            assertThat(EchoAnvil.decode(t)).isEqualTo(s);
        }
        String big = EchoAnvil.pattern(9, 100_000);
        assertThat(EchoAnvil.decode(EchoAnvil.encode(big, 4096, 258))).isEqualTo(big);
    }

    @Test
    void knownValues() {
        assertThat(EchoAnvil.encode("aaaaaaa", 16, 16)).containsExactly(0, 0, 'a', 1, 5, 'a');
        assertThat(EchoAnvil.encode("abcabcabcx", 16, 16)).containsExactly(0, 0, 'a', 0, 0, 'b', 0, 0, 'c', 3, 6, 'x');
        assertThat(EchoAnvil.encode("", 4, 4)).isEmpty();
        assertThat(EchoAnvil.decode(new int[] {0, 0, 'a', 1, 5, 'a'})).isEqualTo("aaaaaaa");
    }

    @Test
    void grades() {
        int[] t = EchoAnvil.encode("tink tink", 8, 8);
        assertThat(EchoAnvil.grade("tink tink", t)).isEqualTo(EchoAnvil.Grade.ECHOED);
        assertThat(EchoAnvil.grade("tink tank", t)).isEqualTo(EchoAnvil.Grade.DULL);
        assertThat(EchoAnvil.grade("x", new int[] {5, 2, 'x'})).isEqualTo(EchoAnvil.Grade.DULL);
        assertThat(EchoAnvil.forgemasterLine(EchoAnvil.Grade.ECHOED)).contains("Forgemaster");
        assertThat(EchoAnvil.forgemasterLine(EchoAnvil.Grade.DULL)).contains("dull");
        assertThat(EchoAnvil.QUEST_ID).isEqualTo("q_echo_anvil");
    }
}
