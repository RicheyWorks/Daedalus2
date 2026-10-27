// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.HammerEcho.Echo;
import com.daedalus.world.forge.HammerEcho.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class HammerEchoTest {

    private static boolean pal(String s, int i, int j) {
        for (int a = i, b = j - 1; a < b; a++, b--) {
            if (s.charAt(a) != s.charAt(b)) {
                return false;
            }
        }
        return true;
    }

    @Test
    void longestAndCountMatchBruteForceOnSeededRuns() {
        for (long seed = 0; seed < 300; seed++) {
            String s = HammerEcho.run(seed, (int) (seed % 40), 1 + (int) (seed % 4));
            int best = 0;
            int bestFrom = 0;
            long cnt = 0;
            for (int i = 0; i < s.length(); i++) {
                for (int j = i + 1; j <= s.length(); j++) {
                    if (pal(s, i, j)) {
                        cnt++;
                        if (j - i > best) {
                            best = j - i;
                            bestFrom = i;
                        }
                    }
                }
            }
            Echo e = HammerEcho.longest(s);
            assertThat(e.length()).as("seed %d", seed).isEqualTo(best);
            assertThat(e.from()).as("earliest, seed %d", seed).isEqualTo(bestFrom);
            assertThat(HammerEcho.count(s)).as("seed %d", seed).isEqualTo(cnt);
        }
    }

    @Test
    void knownRuns() {
        assertThat(HammerEcho.longest("babad")).isEqualTo(new Echo(0, 3));
        assertThat(HammerEcho.longest("cbbd")).isEqualTo(new Echo(1, 3));
        assertThat(HammerEcho.longest("")).isEqualTo(new Echo(0, 0));
        assertThat(HammerEcho.count("aaa")).isEqualTo(6);
        assertThat(HammerEcho.count("abc")).isEqualTo(3);
    }

    @Test
    void gradesAndLines() {
        String s = "xabacabay";
        assertThat(HammerEcho.grade(s, new Echo(1, 8))).isEqualTo(Grade.TRUE);
        assertThat(HammerEcho.grade(s, new Echo(1, 4))).isEqualTo(Grade.FALSE);
        assertThat(HammerEcho.grade("aaaaxyz", new Echo(0, 3))).isEqualTo(Grade.FAINT);
        assertThat(HammerEcho.grade(s, new Echo(0, 2))).isEqualTo(Grade.FALSE);
        assertThat(HammerEcho.grade(s, new Echo(5, 99))).isEqualTo(Grade.FALSE);
        for (Grade g : Grade.values()) {
            assertThat(HammerEcho.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(HammerEcho.QUEST_ID).isEqualTo("q_hammer_echo");
    }

    @Test
    void seededReplayIsDeterministicAndValidated() {
        assertThat(HammerEcho.run(42, 30, 3)).isEqualTo(HammerEcho.run(42, 30, 3)).hasSize(30).matches("[abc]*");
        assertThatThrownBy(() -> HammerEcho.run(1, -1, 2)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HammerEcho.run(1, 3, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> HammerEcho.run(1, 3, 5)).isInstanceOf(IllegalArgumentException.class);
    }
}
