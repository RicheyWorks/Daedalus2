// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.GrateSlide.Grade;
import org.junit.jupiter.api.Test;

import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.SplittableRandom;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class GrateSlideTest {

    /** Distance from the goal to every reachable grate, by BFS over int[] states. */
    private static Map<String, Integer> reach(int rows, int cols) {
        Map<String, Integer> d = new HashMap<>();
        ArrayDeque<int[]> q = new ArrayDeque<>();
        int[] g = GrateSlide.goal(rows, cols);
        d.put(Arrays.toString(g), 0);
        q.add(g);
        while (!q.isEmpty()) {
            int[] s = q.poll();
            int dist = d.get(Arrays.toString(s));
            for (char m : "UDLR".toCharArray()) {
                Optional<int[]> t = GrateSlide.apply(s, rows, cols, String.valueOf(m));
                if (t.isPresent() && d.putIfAbsent(Arrays.toString(t.get()), dist + 1) == null) {
                    q.add(t.get());
                }
            }
        }
        return d;
    }

    @Test
    void parityAndOptimumMatchReachabilityOnSeededShuffles() {
        int[][] shapes = {{2, 2}, {2, 3}, {3, 2}, {3, 3}, {1, 4}, {2, 4}};
        for (int[] sh : shapes) {
            Map<String, Integer> d = reach(sh[0], sh[1]);
            SplittableRandom r = new SplittableRandom(sh[0] * 31L + sh[1]);
            for (int trial = 0; trial < 40; trial++) {
                int[] t = GrateSlide.goal(sh[0], sh[1]);
                for (int i = t.length - 1; i > 0; i--) {
                    int j = r.nextInt(i + 1);
                    int x = t[i];
                    t[i] = t[j];
                    t[j] = x;
                }
                Integer want = d.get(Arrays.toString(t));
                assertThat(GrateSlide.solvable(t, sh[0], sh[1])).as(Arrays.toString(t)).isEqualTo(want != null);
                if (want == null) {
                    assertThat(GrateSlide.solve(t, sh[0], sh[1])).isEmpty();
                    continue;
                }
                String moves = GrateSlide.solve(t, sh[0], sh[1]).orElseThrow();
                assertThat(moves).hasSize(want);
                assertThat(GrateSlide.apply(t, sh[0], sh[1], moves).orElseThrow())
                        .containsExactly(GrateSlide.goal(sh[0], sh[1]));
                assertThat(GrateSlide.grade(t, sh[0], sh[1], moves)).isEqualTo(Grade.RESTORED);
            }
        }
    }

    @Test
    void knownGrates() {
        assertThat(GrateSlide.solve(new int[] {1, 2, 3, 4, 5, 6, 7, 0, 8}, 3, 3)).hasValue("R");
        assertThat(GrateSlide.solvable(new int[] {2, 1, 3, 4, 5, 6, 7, 8, 0}, 3, 3)).isFalse();
        assertThat(GrateSlide.solvable(GrateSlide.scramble(9, 4, 4, 200), 4, 4)).isTrue();
        assertThat(GrateSlide.solve(new int[] {8, 6, 7, 2, 5, 4, 3, 0, 1}, 3, 3).orElseThrow()).hasSize(31);
        assertThatThrownBy(() -> GrateSlide.solve(GrateSlide.goal(4, 4), 4, 4))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> GrateSlide.solvable(new int[] {1, 1, 0, 2}, 2, 2))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        int[] t = {1, 2, 3, 4, 5, 6, 7, 0, 8};
        assertThat(GrateSlide.grade(t, 3, 3, "R")).isEqualTo(Grade.RESTORED);
        assertThat(GrateSlide.grade(t, 3, 3, "RLR")).isEqualTo(Grade.JAMMED);
        assertThat(GrateSlide.grade(t, 3, 3, "D")).isEqualTo(Grade.JAMMED);
        for (Grade g : Grade.values()) {
            assertThat(GrateSlide.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(GrateSlide.QUEST_ID).isEqualTo("q_grate_slide");
        assertThat(GrateSlide.scramble(3, 3, 3, 30)).containsExactly(GrateSlide.scramble(3, 3, 3, 30));
    }
}
