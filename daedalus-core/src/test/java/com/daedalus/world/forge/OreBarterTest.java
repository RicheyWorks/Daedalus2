// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.OreBarter.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class OreBarterTest {

    private static long paths(int[][] e, int u, int target, boolean[] seen, long acc) {
        long best = u == target ? acc : OreBarter.UNREACHABLE;
        for (int[] x : e) {
            if (x[0] == u && !seen[x[1]]) {
                seen[x[1]] = true;
                best = Math.min(best, paths(e, x[1], target, seen, acc + x[2]));
                seen[x[1]] = false;
            }
        }
        return best;
    }

    private static boolean negCycleFrom(int[][] e, int start, int u, boolean[] seen, long acc) {
        for (int[] x : e) {
            if (x[0] != u) {
                continue;
            }
            if (x[1] == start && acc + x[2] < 0) {
                return true;
            }
            if (!seen[x[1]] && x[1] > start) {
                seen[x[1]] = true;
                boolean f = negCycleFrom(e, start, x[1], seen, acc + x[2]);
                seen[x[1]] = false;
                if (f) {
                    return true;
                }
            }
        }
        return false;
    }

    private static boolean[] reach(int n, int[][] e, int src) {
        boolean[] r = new boolean[n];
        r[src] = true;
        for (int k = 0; k < n; k++) {
            for (int[] x : e) {
                r[x[1]] |= r[x[0]];
            }
        }
        return r;
    }

    @Test
    void matchBruteForceOnSeededMarkets() {
        int loops = 0;
        for (long seed = 0; seed < 300; seed++) {
            int n = 1 + (int) (seed % 6);
            int[][] e = OreBarter.routes(seed, n, (int) (seed % 11), -4, 9);
            boolean[] r = reach(n, e, 0);
            boolean neg = false;
            for (int s = 0; s < n; s++) {
                boolean[] seen = new boolean[n];
                neg |= r[s] && negCycleFrom(e, s, s, seen, 0);
            }
            int[] loop = OreBarter.profitLoop(n, e, 0);
            assertThat(loop.length > 0).as("seed %d", seed).isEqualTo(neg);
            if (neg) {
                loops++;
                long total = 0;
                for (int i = 0; i < loop.length; i++) {
                    int a = loop[i];
                    int b = loop[(i + 1) % loop.length];
                    long w = Long.MAX_VALUE;
                    for (int[] x : e) {
                        if (x[0] == a && x[1] == b) {
                            w = Math.min(w, x[2]);
                        }
                    }
                    assertThat(w).as("loop edge seed %d", seed).isNotEqualTo(Long.MAX_VALUE);
                    total += w;
                }
                assertThat(total).isNegative();
                assertThatThrownBy(() -> OreBarter.costs(n, e, 0)).isInstanceOf(IllegalStateException.class);
            } else {
                long[] c = OreBarter.costs(n, e, 0);
                for (int t = 0; t < n; t++) {
                    boolean[] seen = new boolean[n];
                    seen[0] = true;
                    assertThat(c[t]).as("seed %d stall %d", seed, t).isEqualTo(paths(e, 0, t, seen, 0));
                }
            }
        }
        assertThat(loops).isPositive();
    }

    @Test
    void knownMarkets() {
        int[][] e = {{0, 1, 4}, {0, 2, 5}, {2, 1, -3}, {1, 3, 2}};
        assertThat(OreBarter.costs(5, e, 0)).containsExactly(0, 2, 5, 4, OreBarter.UNREACHABLE);
        int[][] swindle = {{0, 1, 1}, {1, 2, -2}, {2, 1, 1}};
        assertThat(OreBarter.profitLoop(3, swindle, 0)).hasSize(2).contains(1, 2);
        int[][] unreachableLoop = {{1, 2, -2}, {2, 1, 1}};
        assertThat(OreBarter.profitLoop(3, unreachableLoop, 0)).isEmpty();
        assertThatThrownBy(() -> OreBarter.costs(2, new int[][] {{0, 5, 1}}, 0))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> OreBarter.costs(2, new int[0][], 3)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        int[][] e = {{0, 1, 3}};
        assertThat(OreBarter.grade(2, e, 0, false, 1, 3)).isEqualTo(Grade.SHREWD);
        assertThat(OreBarter.grade(2, e, 0, false, 1, 2)).isEqualTo(Grade.FLEECED);
        assertThat(OreBarter.grade(2, e, 0, true, 1, 3)).isEqualTo(Grade.FLEECED);
        int[][] swindle = {{0, 1, -1}, {1, 0, -1}};
        assertThat(OreBarter.grade(2, swindle, 0, true, 0, 0)).isEqualTo(Grade.SHREWD);
        for (Grade g : Grade.values()) {
            assertThat(OreBarter.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(OreBarter.QUEST_ID).isEqualTo("q_ore_barter");
        assertThat(OreBarter.routes(2, 5, 7, -3, 3)).isDeepEqualTo(OreBarter.routes(2, 5, 7, -3, 3));
        assertThatThrownBy(() -> OreBarter.routes(1, 0, 1, 0, 1)).isInstanceOf(IllegalArgumentException.class);
    }
}
