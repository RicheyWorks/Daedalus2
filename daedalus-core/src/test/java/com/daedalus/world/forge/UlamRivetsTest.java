// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class UlamRivetsTest {

    private static List<Integer> brute(int limit) {
        List<Integer> s = new ArrayList<>(List.of(1, 2));
        for (int c = 3; c <= limit; c++) {
            int ways = 0;
            for (int i = 0; i < s.size(); i++) {
                for (int j = i + 1; j < s.size(); j++) {
                    if (s.get(i) + s.get(j) == c) {
                        ways++;
                    }
                }
            }
            if (ways == 1) {
                s.add(c);
            }
        }
        return s;
    }

    @Test
    void matchesBruteForce() {
        List<Integer> want = brute(1500);
        int[] got = UlamRivets.upTo(1500);
        assertThat(got.length).isEqualTo(want.size());
        for (int i = 0; i < got.length; i++) {
            assertThat(got[i]).isEqualTo(want.get(i).intValue());
            assertThat(UlamRivets.nth(i + 1)).isEqualTo(got[i]);
        }
        for (int x = 1; x <= 300; x++) {
            assertThat(UlamRivets.isUlam(x)).isEqualTo(want.contains(x));
        }
        assertThat(UlamRivets.countBelow(1501)).isEqualTo(want.size());
    }

    @Test
    void knownValues() {
        assertThat(UlamRivets.upTo(30)).containsExactly(1, 2, 3, 4, 6, 8, 11, 13, 16, 18, 26, 28);
        assertThat(UlamRivets.nth(100)).isEqualTo(690);
        assertThat(UlamRivets.isUlam(5)).isFalse();
        assertThat(UlamRivets.upTo(0)).isEmpty();
        assertThat(UlamRivets.upTo(1)).containsExactly(1);
    }

    @Test
    void grades() {
        assertThat(UlamRivets.grade(7, 11)).isEqualTo(UlamRivets.Grade.TRUE);
        assertThat(UlamRivets.grade(7, 10)).isEqualTo(UlamRivets.Grade.LOOSE);
        assertThat(UlamRivets.forgemasterLine(UlamRivets.Grade.TRUE)).contains("Forgemaster");
        assertThat(UlamRivets.forgemasterLine(UlamRivets.Grade.LOOSE)).contains("loose");
        assertThat(UlamRivets.QUEST_ID).isEqualTo("q_ulam_rivets");
    }
}
