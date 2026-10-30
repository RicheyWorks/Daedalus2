// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.RuneMend.Grade;
import com.daedalus.world.forge.RuneMend.Strike;
import org.junit.jupiter.api.Test;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RuneMendTest {

    /** Brute force: breadth-first search over single edits drawn from the runes present in either string. */
    private static int bfs(String a, String b) {
        StringBuilder al = new StringBuilder();
        for (char c : (a + b).toCharArray()) {
            if (al.indexOf(String.valueOf(c)) < 0) {
                al.append(c);
            }
        }
        int maxLen = Math.max(a.length(), b.length());
        Map<String, Integer> dist = new HashMap<>();
        Deque<String> q = new ArrayDeque<>();
        dist.put(a, 0);
        q.add(a);
        while (!q.isEmpty()) {
            String s = q.poll();
            int d = dist.get(s);
            if (s.equals(b)) {
                return d;
            }
            for (int i = 0; i <= s.length(); i++) {
                if (i < s.length()) {
                    visit(s.substring(0, i) + s.substring(i + 1), d, dist, q, maxLen);
                }
                for (int k = 0; k < al.length(); k++) {
                    char c = al.charAt(k);
                    visit(s.substring(0, i) + c + s.substring(i), d, dist, q, maxLen);
                    if (i < s.length()) {
                        visit(s.substring(0, i) + c + s.substring(i + 1), d, dist, q, maxLen);
                    }
                }
            }
        }
        throw new AssertionError("unreachable");
    }

    private static void visit(String t, int d, Map<String, Integer> dist, Deque<String> q, int maxLen) {
        if (t.length() <= maxLen && !dist.containsKey(t)) {
            dist.put(t, d + 1);
            q.add(t);
        }
    }

    @Test
    void distanceMatchesBreadthFirstSearchOnSeededGarbles() {
        for (long seed = 1; seed <= 200; seed++) {
            String mark = RuneMend.garble(seed, "", 1 + (int) (seed % 4)).replace(" ", "");
            String g = RuneMend.garble(seed * 7L, mark, (int) (seed % 4));
            assertThat(RuneMend.distance(mark, g)).as("seed %d", seed).isEqualTo(bfs(mark, g));
        }
    }

    @Test
    void scriptIsShortestAndRebuildsTheTarget() {
        for (long seed = 1; seed <= 300; seed++) {
            String mark = RuneMend.garble(seed, "", 3 + (int) (seed % 8));
            String g = RuneMend.garble(seed * 3L, mark, (int) (seed % 6));
            List<Strike> s = RuneMend.script(g, mark);
            assertThat(RuneMend.apply(g, s)).isEqualTo(mark);
            assertThat(RuneMend.cost(s)).isEqualTo(RuneMend.distance(g, mark));
            assertThat(RuneMend.distance(g, mark)).isLessThanOrEqualTo((int) (seed % 6));
            assertThat(RuneMend.distance(g, mark)).isEqualTo(RuneMend.distance(mark, g));
        }
    }

    @Test
    void handWorkedMarks() {
        assertThat(RuneMend.distance("KITTEN", "SITTING")).isEqualTo(3);
        assertThat(RuneMend.distance("", "ABD")).isEqualTo(3);
        assertThat(RuneMend.distance("FORGE", "FORGE")).isZero();
        List<String> marks = List.of("HEPHAESTUS", "DAEDALUS", "ICARUS");
        assertThat(RuneMend.nearest(marks, "DAEDLUS")).isEqualTo(1);
        assertThat(RuneMend.nearest(List.of("AB", "BA"), "AA")).isZero();
        assertThatThrownBy(() -> RuneMend.nearest(List.of(), "A")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void sameSeedReplays() {
        assertThat(RuneMend.garble(205L, "HEPHAESTUS", 3)).isEqualTo(RuneMend.garble(205L, "HEPHAESTUS", 3));
        assertThat(RuneMend.garble(205L, "HEPHAESTUS", 0)).isEqualTo("HEPHAESTUS");
        assertThat(RuneMend.QUEST_ID).isEqualTo("q_rune_mend");
        assertThatThrownBy(() -> RuneMend.garble(1L, "A", -1)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesAndLines() {
        assertThat(RuneMend.grade("KITTEN", "SITTING", "SITTING", 3)).isEqualTo(Grade.CLEAN);
        assertThat(RuneMend.grade("KITTEN", "SITTING", "SITTING", 5)).isEqualTo(Grade.ROUGH);
        assertThat(RuneMend.grade("KITTEN", "SITTING", "SITTIN", 2)).isEqualTo(Grade.WRONG_MARK);
        assertThat(RuneMend.forgemasterLine(Grade.WRONG_MARK)).contains("somebody else");
    }
}
