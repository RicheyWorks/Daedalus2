// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class WeirdHoardsTest {

    private static List<Integer> divs(int n) {
        List<Integer> d = new ArrayList<>();
        for (int i = 1; i < n; i++) {
            if (n % i == 0) {
                d.add(i);
            }
        }
        return d;
    }

    private static boolean dpSemiperfect(int n) {
        boolean[] can = new boolean[n + 1];
        can[0] = true;
        for (int d : divs(n)) {
            for (int s = n; s >= d; s--) {
                can[s] |= can[s - d];
            }
        }
        return can[n];
    }

    private static boolean backtrack(List<Integer> d, int i, int left) {
        if (left == 0) {
            return true;
        }
        if (i < 0 || left < 0) {
            return false;
        }
        return backtrack(d, i - 1, left - d.get(i)) || backtrack(d, i - 1, left);
    }

    @Test
    void matchesBooleanDpBruteForce() {
        List<Long> weird = new ArrayList<>();
        for (int n = 1; n <= 15_000; n++) {
            List<Integer> d = divs(n);
            int s = 0;
            for (int x : d) {
                s += x;
            }
            boolean semi = dpSemiperfect(n);
            assertThat(WeirdHoards.isAbundant(n)).as("abundant %d", n).isEqualTo(s > n);
            assertThat(WeirdHoards.isSemiperfect(n)).as("semi %d", n).isEqualTo(semi);
            assertThat(WeirdHoards.properDivisors(n)).hasSize(d.size());
            if (s > n && !semi) {
                weird.add((long) n);
            }
        }
        assertThat(WeirdHoards.weirdUpTo(15_000)).isEqualTo(weird);
    }

    @Test
    void matchesBacktrackingOnSmallHoards() {
        for (int n = 1; n <= 400; n++) {
            List<Integer> d = divs(n);
            assertThat(WeirdHoards.isSemiperfect(n)).as("n=%d", n).isEqualTo(backtrack(d, d.size() - 1, n));
        }
    }

    @Test
    void knownWeirdHoards() {
        assertThat(WeirdHoards.weirdUpTo(15_000)).containsExactly(70L, 836L, 4030L, 5830L, 7192L, 7912L, 9272L,
                10430L, 10570L, 10792L, 10990L, 11410L, 11690L, 12110L, 12530L, 12670L, 13370L, 13510L, 13790L,
                13930L, 14770L);
        assertThat(WeirdHoards.weirdUpTo(69)).isEmpty();
        assertThat(WeirdHoards.properDivisors(70)).containsExactly(1L, 2L, 5L, 7L, 10L, 14L, 35L);
        assertThat(WeirdHoards.isSemiperfect(945)).isTrue();
        assertThat(WeirdHoards.isWeird(945)).isFalse();
    }

    @Test
    void sweepsAndBigHoards() {
        Random r = new Random(480);
        for (int t = 0; t < 40; t++) {
            long n = 6L * (1 + r.nextInt(WeirdHoards.MAX_N / 6));
            assertThat(WeirdHoards.isSemiperfect(n)).as("6k=%d", n).isTrue();
            assertThat(WeirdHoards.isWeird(n)).isFalse();
        }
        for (long n = 15_001; n <= 15_400; n++) {
            assertThat(WeirdHoards.isSemiperfect(n)).as("n=%d", n).isEqualTo(dpSemiperfect((int) n));
        }
        assertThat(WeirdHoards.isWeird(9_999_991)).isFalse();
        assertThat(WeirdHoards.isAbundant(WeirdHoards.MAX_N)).isTrue();
        assertThat(WeirdHoards.isSemiperfect(WeirdHoards.MAX_N)).isTrue();
    }

    @Test
    void edgesGuardsGradesAndLines() {
        assertThat(WeirdHoards.properDivisors(1)).isEmpty();
        assertThat(WeirdHoards.isSemiperfect(1)).isFalse();
        assertThat(WeirdHoards.isSemiperfect(6)).isTrue();
        assertThat(WeirdHoards.weirdUpTo(0)).isEmpty();
        assertThatThrownBy(() -> WeirdHoards.isWeird(0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> WeirdHoards.isWeird(WeirdHoards.MAX_N + 1L))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> WeirdHoards.weirdUpTo(WeirdHoards.MAX_LIST + 1))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(WeirdHoards.grade(70, true)).isEqualTo(WeirdHoards.Grade.TURNED);
        assertThat(WeirdHoards.grade(12, true)).isEqualTo(WeirdHoards.Grade.SLIPPED);
        assertThat(WeirdHoards.grade(12, false)).isEqualTo(WeirdHoards.Grade.TURNED);
        for (WeirdHoards.Grade g : WeirdHoards.Grade.values()) {
            assertThat(WeirdHoards.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(WeirdHoards.QUEST_ID).isEqualTo("q_weird_hoards");
    }
}
