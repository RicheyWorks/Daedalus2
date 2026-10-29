// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.DieStamps.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class DieStampsTest {

    private static boolean brute(String p, int i, String t, int j) {
        if (i == p.length()) {
            return j == t.length();
        }
        char c = p.charAt(i);
        if (c == '*') {
            for (int k = j; k <= t.length(); k++) {
                if (brute(p, i + 1, t, k)) {
                    return true;
                }
            }
            return false;
        }
        return j < t.length() && (c == '?' || c == t.charAt(j)) && brute(p, i + 1, t, j + 1);
    }

    @Test
    void matchesBruteForceOnSeededDiesAndCoins() {
        int hits = 0;
        for (long seed = 0; seed < 400; seed++) {
            String die = DieStamps.die(seed, (int) (seed % 9));
            for (int c = 0; c < 15; c++) {
                String coin = DieStamps.coin(seed * 17 + c, c % 10);
                boolean want = brute(die, 0, coin, 0);
                assertThat(DieStamps.matches(die, coin)).as("%s vs %s", die, coin).isEqualTo(want);
                assertThat(DieStamps.matchesDp(die, coin)).as("dp %s vs %s", die, coin).isEqualTo(want);
                assertThat(DieStamps.grade(die, coin, want)).isEqualTo(Grade.STRUCK);
                hits += want ? 1 : 0;
            }
        }
        assertThat(hits).isBetween(100, 5900);
    }

    @Test
    void knownDies() {
        assertThat(DieStamps.matches("f*x", "fuuux")).isTrue();
        assertThat(DieStamps.matches("f?x", "fux")).isTrue();
        assertThat(DieStamps.matches("f?x", "fx")).isFalse();
        assertThat(DieStamps.matches("*", "")).isTrue();
        assertThat(DieStamps.matches("", "")).isTrue();
        assertThat(DieStamps.matches("", "f")).isFalse();
        assertThat(DieStamps.matches("*u*u*", "xuxux")).isTrue();
        assertThat(DieStamps.matches("*fx", "ffxfx")).isTrue();
        assertThatThrownBy(() -> DieStamps.coin(1, -1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        assertThat(DieStamps.grade("f*", "fux", true)).isEqualTo(Grade.STRUCK);
        assertThat(DieStamps.grade("f*", "ufx", true)).isEqualTo(Grade.MISSTRUCK);
        for (Grade g : Grade.values()) {
            assertThat(DieStamps.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(DieStamps.QUEST_ID).isEqualTo("q_die_stamps");
        assertThat(DieStamps.die(6, 7)).isEqualTo(DieStamps.die(6, 7)).hasSize(7);
    }
}
