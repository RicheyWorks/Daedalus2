// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.GuildLineage.Grade;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class GuildLineageTest {

    private static int naiveDepth(int[] p, int start) {
        int v = start;
        int d = 0;
        while (p[v] >= 0) {
            v = p[v];
            d++;
        }
        return d;
    }

    private static int naiveLca(int[] p, int a0, int b0) {
        int a = a0;
        int b = b0;
        int da = naiveDepth(p, a0);
        int db = naiveDepth(p, b0);
        while (da > db) {
            a = p[a];
            da--;
        }
        while (db > da) {
            b = p[b];
            db--;
        }
        while (a != b) {
            if (p[a] < 0) {
                return -1;
            }
            a = p[a];
            b = p[b];
        }
        return a;
    }

    @Test
    void matchesNaiveWalkOnSeededLineages() {
        for (long seed = 0; seed < 120; seed++) {
            int n = 1 + (int) (seed % 40);
            int[] p = GuildLineage.lineage(seed, n);
            GuildLineage g = new GuildLineage(p);
            for (int a = 0; a < n; a++) {
                assertThat(g.depth(a)).isEqualTo(naiveDepth(p, a));
                for (int b = 0; b < n; b++) {
                    int m = naiveLca(p, a, b);
                    assertThat(g.lca(a, b)).as("seed %d (%d,%d)", seed, a, b).isEqualTo(m);
                    assertThat(g.distance(a, b)).isEqualTo(naiveDepth(p, a) + naiveDepth(p, b) - 2 * naiveDepth(p, m));
                }
                int x = a;
                for (int k = 0; k <= naiveDepth(p, a) + 1; k++) {
                    assertThat(g.kthAncestor(a, k)).isEqualTo(k > naiveDepth(p, a) ? -1 : x);
                    x = k < naiveDepth(p, a) ? p[x] : x;
                }
            }
        }
    }

    @Test
    void forestAndBadInput() {
        GuildLineage g = new GuildLineage(new int[] {-1, 0, -1, 2});
        assertThat(g.lca(1, 3)).isEqualTo(-1);
        assertThat(g.distance(1, 3)).isEqualTo(-1);
        assertThat(g.lca(3, 3)).isEqualTo(3);
        assertThatThrownBy(() -> new GuildLineage(new int[] {1, 0})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new GuildLineage(new int[] {0})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new GuildLineage(new int[] {5})).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> g.lca(0, 9)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> g.kthAncestor(0, -1)).isInstanceOf(IllegalArgumentException.class);
        assertThat(new GuildLineage(new int[0])).isNotNull();
    }

    @Test
    void gradesLinesAndReplay() {
        GuildLineage g = new GuildLineage(new int[] {-1, 0, 0, 1});
        assertThat(g.grade(3, 2, 0, 3)).isEqualTo(Grade.KIN);
        assertThat(g.grade(3, 2, 1, 3)).isEqualTo(Grade.STRANGER);
        assertThat(g.grade(3, 2, 0, 2)).isEqualTo(Grade.STRANGER);
        for (Grade x : Grade.values()) {
            assertThat(GuildLineage.forgemasterLine(x)).startsWith("Forgemaster:");
        }
        assertThat(GuildLineage.QUEST_ID).isEqualTo("q_guild_lineage");
        assertThat(GuildLineage.lineage(8, 30)).isEqualTo(GuildLineage.lineage(8, 30)).hasSize(30);
        assertThatThrownBy(() -> GuildLineage.lineage(1, -1)).isInstanceOf(IllegalArgumentException.class);
    }
}
