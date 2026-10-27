// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.BellowsRefrain.Grade;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class BellowsRefrainTest {

    private static int[] bruteOcc(String t, String p) {
        List<Integer> out = new ArrayList<>();
        for (int i = 0; i + p.length() <= t.length(); i++) {
            if (t.startsWith(p, i)) {
                out.add(i);
            }
        }
        return out.stream().mapToInt(Integer::intValue).toArray();
    }

    private static int brutePeriod(String s) {
        for (int p = 1; p <= s.length(); p++) {
            if (s.length() % p == 0 && s.substring(0, p).repeat(s.length() / p).equals(s)) {
                return p;
            }
        }
        return 0;
    }

    @Test
    void occurrencesAndPeriodMatchBruteForceOnSeededRuns() {
        for (long seed = 0; seed < 300; seed++) {
            int k = 1 + (int) (seed % 3);
            String t = BellowsRefrain.run(seed, (int) (seed % 50), k);
            String p = BellowsRefrain.run(seed * 31 + 7, 1 + (int) (seed % 4), k);
            assertThat(BellowsRefrain.occurrences(t, p)).as("seed %d", seed).containsExactly(bruteOcc(t, p));
            assertThat(BellowsRefrain.period(t)).as("seed %d", seed).isEqualTo(brutePeriod(t));
            String rep = p.repeat(1 + (int) (seed % 5));
            assertThat(BellowsRefrain.period(rep)).isEqualTo(brutePeriod(rep));
        }
    }

    @Test
    void knownRuns() {
        assertThat(BellowsRefrain.prefixFunction("abacaba")).containsExactly(0, 0, 1, 0, 1, 2, 3);
        assertThat(BellowsRefrain.occurrences("aaaa", "aa")).containsExactly(0, 1, 2);
        assertThat(BellowsRefrain.occurrences("hw", "hwo")).isEmpty();
        assertThat(BellowsRefrain.period("hwohwohwo")).isEqualTo(3);
        assertThat(BellowsRefrain.period("hwoh")).isEqualTo(4);
        assertThat(BellowsRefrain.period("")).isZero();
        assertThatThrownBy(() -> BellowsRefrain.occurrences("x", "")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        assertThat(BellowsRefrain.grade("hwhwh", "hwh", new int[] {0, 2})).isEqualTo(Grade.IN_TUNE);
        assertThat(BellowsRefrain.grade("hwhwh", "hwh", new int[] {0})).isEqualTo(Grade.OFF);
        assertThat(BellowsRefrain.grade("hwhwh", "hwh", new int[] {0, 1, 2})).isEqualTo(Grade.OFF);
        for (Grade g : Grade.values()) {
            assertThat(BellowsRefrain.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(BellowsRefrain.QUEST_ID).isEqualTo("q_bellows_refrain");
        assertThat(BellowsRefrain.run(9, 20, 3)).isEqualTo(BellowsRefrain.run(9, 20, 3)).hasSize(20).matches("[hwo]*");
        assertThatThrownBy(() -> BellowsRefrain.run(1, 3, 4)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> BellowsRefrain.run(1, -1, 1)).isInstanceOf(IllegalArgumentException.class);
    }
}
