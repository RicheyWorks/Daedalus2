// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.AnvilRota.Grade;
import com.daedalus.world.forge.AnvilRota.Rota;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class AnvilRotaTest {

    /** Brute force over every permutation. */
    private static long brute(int[][] c, int s, boolean[] used) {
        if (s == c.length) {
            return 0;
        }
        long best = Long.MAX_VALUE;
        for (int j = 0; j < c.length; j++) {
            if (!used[j]) {
                used[j] = true;
                best = Math.min(best, c[s][j] + brute(c, s + 1, used));
                used[j] = false;
            }
        }
        return best;
    }

    @Test
    void hungarianMatchesBruteForceOnSeededRotas() {
        for (long seed = 1; seed <= 300; seed++) {
            int n = 1 + (int) (seed % 8);
            int[][] c = AnvilRota.table(seed, n, 1 + (int) (seed % 30));
            Rota r = AnvilRota.assign(c);
            assertThat(r.hours()).as("seed %d", seed).isEqualTo(brute(c, 0, new boolean[n]));
            assertThat(AnvilRota.hours(c, r.jobs())).isEqualTo(r.hours());
        }
    }

    @Test
    void greedyNeverBeatsHungarianAndLosesOnSeededRotas() {
        int[][] c = {{1, 2}, {2, 100}};
        assertThat(AnvilRota.greedy(c).hours()).isEqualTo(101);
        assertThat(AnvilRota.assign(c).hours()).isEqualTo(4);
        int losses = 0;
        for (long seed = 1; seed <= 200; seed++) {
            int[][] t = AnvilRota.table(seed, 6, 20);
            long g = AnvilRota.greedy(t).hours();
            long b = AnvilRota.assign(t).hours();
            assertThat(g).isGreaterThanOrEqualTo(b);
            if (g > b) {
                losses++;
            }
        }
        assertThat(losses).isPositive();
    }

    @Test
    void largeRotaRunsAndIsAPermutation() {
        int[][] c = AnvilRota.table(195L, 60, 1000);
        Rota r = AnvilRota.assign(c);
        assertThat(new ArrayList<>(r.jobs())).containsExactlyInAnyOrderElementsOf(range(60));
        assertThat(r.hours()).isLessThanOrEqualTo(AnvilRota.greedy(c).hours());
    }

    private static List<Integer> range(int n) {
        List<Integer> l = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            l.add(i);
        }
        return l;
    }

    @Test
    void sameSeedReplays() {
        assertThat(AnvilRota.table(195L, 7, 20)).isDeepEqualTo(AnvilRota.table(195L, 7, 20));
        assertThat(AnvilRota.assign(AnvilRota.table(195L, 7, 20))).isEqualTo(AnvilRota.assign(AnvilRota.table(195L, 7,
                20)));
        assertThat(AnvilRota.QUEST_ID).isEqualTo("q_anvil_rota");
    }

    @Test
    void gradesAndLines() {
        assertThat(AnvilRota.grade(100, 100)).isEqualTo(Grade.TIGHT);
        assertThat(AnvilRota.grade(110, 100)).isEqualTo(Grade.LOOSE);
        assertThat(AnvilRota.grade(111, 100)).isEqualTo(Grade.SLACK);
        assertThatThrownBy(() -> AnvilRota.grade(99, 100)).isInstanceOf(IllegalArgumentException.class);
        int[][] c = {{1, 2}, {2, 100}};
        assertThat(AnvilRota.forgemasterLine(AnvilRota.greedy(c), 4)).contains("idle");
    }

    @Test
    void edgeCasesAndRejects() {
        assertThat(AnvilRota.assign(new int[0][]).hours()).isZero();
        assertThatThrownBy(() -> AnvilRota.assign(new int[][] {{1, 2}})).isInstanceOf(IllegalArgumentException.class);
        int[][] c = {{1, 2}, {3, 4}};
        assertThatThrownBy(() -> AnvilRota.hours(c, List.of(0, 0))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> AnvilRota.hours(c, List.of(0))).isInstanceOf(IllegalArgumentException.class);
    }
}
