// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class TwinLogsTest {

    private static String randomLog(SplittableRandom rnd, int n, String alphabet) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) {
            sb.append(alphabet.charAt(rnd.nextInt(alphabet.length())));
        }
        return sb.toString();
    }

    /** Brute force: overlapping occurrences by scanning every start. */
    private static long bruteCount(String s, String p) {
        long c = 0;
        for (int i = 0; i + p.length() <= s.length(); i++) {
            if (s.startsWith(p, i)) {
                c++;
            }
        }
        return c;
    }

    /** Brute force: length of the longest common substring. */
    private static int bruteShared(String a, String b) {
        int best = 0;
        for (int i = 0; i < b.length(); i++) {
            for (int j = i + best + 1; j <= b.length(); j++) {
                if (a.contains(b.substring(i, j))) {
                    best = j - i;
                } else {
                    break;
                }
            }
        }
        return best;
    }

    @Test
    void occurrencesMatchBruteForceScan() {
        SplittableRandom rnd = new SplittableRandom(513L);
        for (int trial = 0; trial < 80; trial++) {
            String s = randomLog(rnd, rnd.nextInt(60), "ab c");
            TwinLogs tl = new TwinLogs(s);
            assertThat(tl.states()).isLessThanOrEqualTo(Math.max(1, 2 * s.length()));
            for (int q = 0; q < 30; q++) {
                String p = randomLog(rnd, 1 + rnd.nextInt(5), "ab cd");
                assertThat(tl.occurrences(p)).as("'%s' in '%s'", p, s).isEqualTo(bruteCount(s, p));
            }
            assertThat(tl.occurrences("")).isEqualTo(s.length() + 1L);
        }
    }

    @Test
    void sharedPassageMatchesBruteForce() {
        SplittableRandom rnd = new SplittableRandom(31L);
        for (int trial = 0; trial < 120; trial++) {
            String a = randomLog(rnd, rnd.nextInt(40), "abc");
            String b = randomLog(rnd, rnd.nextInt(40), "abcd");
            String p = new TwinLogs(a).sharedPassage(b);
            assertThat(p.length()).as("'%s' vs '%s'", a, b).isEqualTo(bruteShared(a, b));
            assertThat(a).contains(p);
            assertThat(b).contains(p);
        }
    }

    @Test
    void handWorkedLogsAndDesk() {
        TwinLogs tl = new TwinLogs("wind from the west, wind from the north");
        assertThat(tl.occurrences("wind")).isEqualTo(2);
        assertThat(tl.occurrences("the ")).isEqualTo(2);
        assertThat(tl.occurrences("south")).isZero();
        assertThat(tl.occurrences("\u00e9")).isZero();
        assertThat(new TwinLogs("aaaa").occurrences("aa")).isEqualTo(3);
        assertThat(tl.sharedPassage("calm, wind from the east")).isEqualTo(", wind from the ");
        assertThat(tl.desk("calm, wind from the east")).contains("16 characters");
        assertThat(tl.desk("zzz")).contains("agree on nothing");
        assertThat(new TwinLogs("").sharedPassage("abc")).isEmpty();
        assertThat(new TwinLogs(null).states()).isEqualTo(1);
    }

    @Test
    void questAndBadInput() {
        assertThat(TwinLogs.QUEST_ID).isEqualTo("q_twin_logs");
        assertThat(TwinLogs.quest("rum ration doubled", "ration halved", "ration ")).isTrue();
        assertThat(TwinLogs.quest("rum ration doubled", "ration halved", "ration")).isFalse();
        assertThat(TwinLogs.quest("abcxyz", "xyzabc", "xyz")).isTrue();
        assertThat(TwinLogs.quest("abc", "abc", null)).isFalse();
        assertThatThrownBy(() -> new TwinLogs("tab\there")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new TwinLogs("x".repeat(TwinLogs.MAX_LOG + 1)))
            .isInstanceOf(IllegalArgumentException.class);
    }
}