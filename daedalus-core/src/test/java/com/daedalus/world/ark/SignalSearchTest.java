// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class SignalSearchTest {

    private static String randomLog(SplittableRandom rnd, int n, int alphabet) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) {
            sb.append((char) ('a' + rnd.nextInt(alphabet)));
        }
        return sb.toString();
    }

    private static String naiveRepeat(String s) {
        for (int len = s.length() - 1; len > 0; len--) {
            for (int i = 0; i + len <= s.length(); i++) {
                String sub = s.substring(i, i + len);
                if (s.indexOf(sub, i + 1) >= 0) {
                    return sub;
                }
            }
        }
        return "";
    }

    @Test
    void findMatchesNaive() {
        SplittableRandom rnd = new SplittableRandom(286);
        for (int t = 0; t < 400; t++) {
            String log = randomLog(rnd, rnd.nextInt(0, 120), rnd.nextInt(1, 4));
            String pat = randomLog(rnd, rnd.nextInt(1, 5), 3);
            List<Integer> want = new ArrayList<>();
            for (int i = log.indexOf(pat); i >= 0; i = log.indexOf(pat, i + 1)) {
                want.add(i);
            }
            assertThat(SignalSearch.find(log, pat)).as("log=%s pat=%s", log, pat).isEqualTo(want);
        }
    }

    @Test
    void longestRepeatMatchesNaive() {
        SplittableRandom rnd = new SplittableRandom(1286);
        for (int t = 0; t < 300; t++) {
            String log = randomLog(rnd, rnd.nextInt(0, 60), rnd.nextInt(1, 5));
            assertThat(SignalSearch.longestRepeat(log)).as("log=%s", log).isEqualTo(naiveRepeat(log));
        }
        assertThat(SignalSearch.longestRepeat("banana")).isEqualTo("ana");
        assertThat(SignalSearch.longestRepeat("abc")).isEmpty();
    }

    @Test
    void questAndBounds() {
        assertThat(SignalSearch.quest("aaaa", "aa", 3)).isTrue();
        assertThat(SignalSearch.quest("redbluered", "red", 2)).isTrue();
        assertThat(SignalSearch.quest("redbluered", "red", 1)).isFalse();
        assertThat(SignalSearch.find("ab", "abc")).isEmpty();
        assertThat(SignalSearch.QUEST_ID).isEqualTo("q_signal_search");
        assertThatThrownBy(() -> SignalSearch.find("ab", "")).isInstanceOf(IllegalArgumentException.class);
    }
}