// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.CourierCharts.Grade;
import org.junit.jupiter.api.Test;

import java.util.Arrays;

import static com.daedalus.world.forge.CourierCharts.NO_PATH;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class CourierChartsTest {

    private static long[] relaxFrom(long[][] m, int s) {
        int n = m.length;
        long[] d = new long[n];
        Arrays.fill(d, NO_PATH);
        d[s] = 0;
        for (int round = 0; round < n; round++) {
            for (int u = 0; u < n; u++) {
                for (int v = 0; v < n; v++) {
                    if (d[u] != NO_PATH && m[u][v] != NO_PATH && d[u] + m[u][v] < d[v]) {
                        d[v] = d[u] + m[u][v];
                    }
                }
            }
        }
        return d;
    }

    @Test
    void costsAndRoutesMatchBruteForce() {
        for (long seed = 0; seed < 150; seed++) {
            int n = (int) (seed % 12);
            long[][] m = CourierCharts.paths(seed, n, 10 + (int) (seed % 50), 9);
            CourierCharts c = new CourierCharts(m);
            for (int a = 0; a < n; a++) {
                long[] d = relaxFrom(m, a);
                for (int b = 0; b < n; b++) {
                    assertThat(c.cost(a, b)).as("seed %d %d->%d", seed, a, b).isEqualTo(d[b]);
                    int[] r = c.route(a, b);
                    if (d[b] == NO_PATH) {
                        assertThat(r).isEmpty();
                    } else {
                        assertThat(c.grade(m, a, b, r)).as("route seed %d", seed).isEqualTo(Grade.SWIFT);
                    }
                }
            }
        }
    }

    @Test
    void knownChartAndBadInput() {
        long[][] m = {{NO_PATH, 4, 1}, {NO_PATH, NO_PATH, NO_PATH}, {NO_PATH, 2, NO_PATH}};
        CourierCharts c = new CourierCharts(m);
        assertThat(c.cost(0, 1)).isEqualTo(3);
        assertThat(c.route(0, 1)).containsExactly(0, 2, 1);
        assertThat(c.route(1, 1)).containsExactly(1);
        assertThat(c.cost(1, 0)).isEqualTo(NO_PATH);
        assertThat(c.route(1, 0)).isEmpty();
        assertThatThrownBy(() -> new CourierCharts(new long[][] {{0, 1}})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CourierCharts(new long[][] {{0, -1}, {0, 0}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> c.cost(0, 3)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        long[][] m = {{NO_PATH, 4, 1}, {NO_PATH, NO_PATH, NO_PATH}, {NO_PATH, 2, NO_PATH}};
        CourierCharts c = new CourierCharts(m);
        assertThat(c.grade(m, 0, 1, new int[] {0, 2, 1})).isEqualTo(Grade.SWIFT);
        assertThat(c.grade(m, 0, 1, new int[] {0, 1})).isEqualTo(Grade.LOST);
        assertThat(c.grade(m, 0, 1, new int[] {0, 1, 2, 1})).isEqualTo(Grade.LOST);
        assertThat(c.grade(m, 1, 0, new int[] {1, 0})).isEqualTo(Grade.LOST);
        assertThat(c.grade(m, 0, 1, new int[0])).isEqualTo(Grade.LOST);
        for (Grade g : Grade.values()) {
            assertThat(CourierCharts.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(CourierCharts.QUEST_ID).isEqualTo("q_courier_charts");
        assertThat(CourierCharts.paths(6, 7, 40, 5)).isDeepEqualTo(CourierCharts.paths(6, 7, 40, 5));
        assertThatThrownBy(() -> CourierCharts.paths(1, 2, 50, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
