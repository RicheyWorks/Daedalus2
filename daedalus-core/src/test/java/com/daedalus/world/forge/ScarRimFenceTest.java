// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ScarRimFence.Grade;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ScarRimFenceTest {

    private static boolean onSegment(int[] a, int[] b, int[] p) {
        return ScarRimFence.cross(a, b, p) == 0 && Math.min(a[0], b[0]) <= p[0] && p[0] <= Math.max(a[0], b[0])
                && Math.min(a[1], b[1]) <= p[1] && p[1] <= Math.max(a[1], b[1]);
    }

    private static boolean inTriangle(int[] a, int[] b, int[] c, int[] p) {
        long d1 = ScarRimFence.cross(a, b, p);
        long d2 = ScarRimFence.cross(b, c, p);
        long d3 = ScarRimFence.cross(c, a, p);
        boolean neg = d1 < 0 || d2 < 0 || d3 < 0;
        boolean pos = d1 > 0 || d2 > 0 || d3 > 0;
        return !(neg && pos);
    }

    /** Brute force: a distinct point is a corner iff no segment or triangle of other points covers it. */
    private static Set<String> bruteCorners(int[][] raw) {
        List<int[]> u = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (int[] p : raw) {
            if (seen.add(p[0] + "," + p[1])) {
                u.add(p);
            }
        }
        Set<String> corners = new HashSet<>();
        int n = u.size();
        for (int i = 0; i < n; i++) {
            boolean covered = false;
            for (int a = 0; a < n && !covered; a++) {
                for (int b = a + 1; b < n && !covered; b++) {
                    if (a == i || b == i) {
                        continue;
                    }
                    if (onSegment(u.get(a), u.get(b), u.get(i))) {
                        covered = true;
                    }
                    for (int c = b + 1; c < n && !covered; c++) {
                        if (c != i && ScarRimFence.cross(u.get(a), u.get(b), u.get(c)) != 0
                                && inTriangle(u.get(a), u.get(b), u.get(c), u.get(i))) {
                            covered = true;
                        }
                    }
                }
            }
            if (!covered) {
                corners.add(u.get(i)[0] + "," + u.get(i)[1]);
            }
        }
        return corners;
    }

    private static Set<String> keys(List<int[]> h) {
        Set<String> s = new HashSet<>();
        for (int[] p : h) {
            s.add(p[0] + "," + p[1]);
        }
        return s;
    }

    @Test
    void hullCornersMatchBruteForceOnSeededScars() {
        for (long seed = 1; seed <= 300; seed++) {
            int[][] p = ScarRimFence.shards(seed, 1 + (int) (seed % 14), 3 + (int) (seed % 12));
            List<int[]> h = ScarRimFence.hull(p);
            assertThat(keys(h)).as("seed %d", seed).isEqualTo(bruteCorners(p));
            assertThat(h).hasSize(keys(h).size());
        }
    }

    @Test
    void hullIsCounterClockwiseAndContainsEveryShard() {
        for (long seed = 1; seed <= 200; seed++) {
            int[][] p = ScarRimFence.shards(seed * 13L, 20, 50);
            List<int[]> h = ScarRimFence.hull(p);
            if (h.size() >= 3) {
                assertThat(ScarRimFence.area2(h)).isPositive();
            }
            for (int[] q : p) {
                assertThat(ScarRimFence.inside(h, q)).isTrue();
            }
        }
    }

    @Test
    void handWorkedSquare() {
        int[][] p = {{0, 0}, {4, 0}, {4, 4}, {0, 4}, {2, 2}, {2, 0}, {0, 0}};
        List<int[]> h = ScarRimFence.hull(p);
        assertThat(h).hasSize(4);
        assertThat(h.get(0)).containsExactly(0, 0);
        assertThat(ScarRimFence.perimeter(h)).isEqualTo(16.0);
        assertThat(ScarRimFence.area2(h)).isEqualTo(32);
        assertThat(ScarRimFence.grade(p, List.of(0, 1, 2, 3))).isEqualTo(Grade.TAUT);
        assertThat(ScarRimFence.grade(p, List.of(0, 2, 1, 3))).isEqualTo(Grade.SAGGY);
        assertThat(ScarRimFence.grade(p, List.of(0, 1, 2))).isEqualTo(Grade.BREACHED);
        assertThat(ScarRimFence.forgemasterLine(Grade.BREACHED)).contains("outside");
    }

    @Test
    void sameSeedReplays() {
        assertThat(ScarRimFence.shards(198L, 12, 40)).isDeepEqualTo(ScarRimFence.shards(198L, 12, 40));
        assertThat(keys(ScarRimFence.hull(ScarRimFence.shards(198L, 12, 40))))
                .isEqualTo(keys(ScarRimFence.hull(ScarRimFence.shards(198L, 12, 40))));
        assertThat(ScarRimFence.QUEST_ID).isEqualTo("q_scar_rim_fence");
    }

    @Test
    void degenerateScars() {
        assertThat(ScarRimFence.hull(new int[0][])).isEmpty();
        assertThat(ScarRimFence.hull(new int[][] {{1, 1}, {1, 1}})).hasSize(1);
        assertThat(ScarRimFence.hull(new int[][] {{0, 0}, {1, 1}, {2, 2}})).hasSize(2);
        assertThat(ScarRimFence.perimeter(ScarRimFence.hull(new int[][] {{0, 0}, {3, 4}}))).isEqualTo(10.0);
        assertThatThrownBy(() -> ScarRimFence.hull(new int[][] {{1}})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ScarRimFence.shards(1L, -1, 5)).isInstanceOf(IllegalArgumentException.class);
    }
}
