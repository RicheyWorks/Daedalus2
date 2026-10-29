// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.RuneTrace.Grade;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.TreeSet;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RuneTraceTest {

    private static boolean path(char[][] g, boolean[][] seen, String w, int k, int i, int j) {
        if (i < 0 || i >= g.length || j < 0 || j >= g[i].length || seen[i][j] || g[i][j] != w.charAt(k)) {
            return false;
        }
        if (k == w.length() - 1) {
            return true;
        }
        seen[i][j] = true;
        boolean ok = false;
        for (int di = -1; di <= 1 && !ok; di++) {
            for (int dj = -1; dj <= 1 && !ok; dj++) {
                if (di != 0 || dj != 0) {
                    ok = path(g, seen, w, k + 1, i + di, j + dj);
                }
            }
        }
        seen[i][j] = false;
        return ok;
    }

    private static boolean traceable(char[][] g, String w) {
        for (int i = 0; i < g.length; i++) {
            for (int j = 0; j < g[i].length; j++) {
                if (path(g, new boolean[g.length][g[0].length], w, 0, i, j)) {
                    return true;
                }
            }
        }
        return false;
    }

    @Test
    void matchesPerWordBruteForceOnSeededGrids() {
        int hits = 0;
        for (long seed = 0; seed < 150; seed++) {
            int rows = 1 + (int) (seed % 5);
            int cols = 1 + (int) ((seed / 5) % 5);
            char[][] g = RuneTrace.grid(seed, rows, cols);
            List<String> ws = RuneTrace.words(seed + 99, 40, 6);
            TreeSet<String> want = new TreeSet<>();
            for (String w : ws) {
                if (traceable(g, w)) {
                    want.add(w);
                }
            }
            List<String> got = RuneTrace.findWords(g, ws);
            assertThat(got).as("seed %d", seed).containsExactlyElementsOf(want);
            assertThat(RuneTrace.grade(g, ws, new ArrayList<>(want))).isEqualTo(Grade.TRACED);
            hits += want.size();
        }
        assertThat(hits).isPositive();
    }

    @Test
    void knownGrid() {
        char[][] g = {"oaan".toCharArray(), "etae".toCharArray(), "ihkr".toCharArray(), "iflv".toCharArray()};
        assertThat(RuneTrace.findWords(g, List.of("oath", "pea", "eat", "rain", "eat"))).containsExactly("eat", "oath");
        assertThat(RuneTrace.findWords(new char[][] {{'a', 'b'}}, List.of("aba"))).isEmpty();
        assertThatThrownBy(() -> RuneTrace.findWords(g, List.of(""))).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RuneTrace.findWords(g, List.of("Oath"))).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        char[][] g = {{'f', 'u'}, {'x', 'a'}};
        assertThat(RuneTrace.grade(g, List.of("fua", "ff"), List.of("fua"))).isEqualTo(Grade.TRACED);
        assertThat(RuneTrace.grade(g, List.of("fua", "ff"), List.of("fua", "ff"))).isEqualTo(Grade.SMUDGED);
        for (Grade x : Grade.values()) {
            assertThat(RuneTrace.forgemasterLine(x)).startsWith("Forgemaster:");
        }
        assertThat(RuneTrace.QUEST_ID).isEqualTo("q_rune_trace");
        assertThat(RuneTrace.grid(2, 3, 3)).isDeepEqualTo(RuneTrace.grid(2, 3, 3));
        assertThatThrownBy(() -> RuneTrace.grid(1, 0, 3)).isInstanceOf(IllegalArgumentException.class);
    }
}
