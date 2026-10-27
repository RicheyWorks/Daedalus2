// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ChainWeld.Grade;
import org.junit.jupiter.api.Test;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ChainWeldTest {

    private static boolean extend(int[][] links, boolean[] used, int at, int left) {
        if (left == 0) {
            return true;
        }
        for (int i = 0; i < links.length; i++) {
            if (!used[i] && (at < 0 || links[i][0] == at)) {
                used[i] = true;
                if (extend(links, used, links[i][1], left - 1)) {
                    used[i] = false;
                    return true;
                }
                used[i] = false;
            }
        }
        return false;
    }

    @Test
    void matchesBruteForceOnSeededLinkSets() {
        int found = 0;
        for (long seed = 0; seed < 400; seed++) {
            int sockets = 1 + (int) (seed % 4);
            int m = (int) (seed % 8);
            int[][] links = ChainWeld.links(seed, sockets, m);
            boolean truth = extend(links, new boolean[m], -1, m);
            Optional<int[]> got = ChainWeld.eulerPath(sockets, links);
            assertThat(got.isPresent()).as("seed %d", seed).isEqualTo(truth);
            if (truth) {
                found++;
                assertThat(ChainWeld.isChain(links, got.get())).as("seed %d chain", seed).isTrue();
                assertThat(ChainWeld.grade(sockets, links, got.get())).isEqualTo(Grade.WELDED);
            } else {
                assertThat(ChainWeld.grade(sockets, links, null)).isEqualTo(Grade.WELDED);
            }
        }
        assertThat(found).isBetween(50, 399);
    }

    @Test
    void knownLinkSets() {
        int[][] path = {{0, 1}, {1, 2}, {2, 0}, {0, 3}};
        assertThat(ChainWeld.eulerPath(4, path)).hasValueSatisfying(o -> assertThat(o).containsExactly(0, 1, 2, 3));
        assertThat(ChainWeld.eulerPath(4, new int[][] {{0, 1}, {2, 3}})).isEmpty();
        assertThat(ChainWeld.eulerPath(3, new int[][] {{0, 1}, {0, 2}})).isEmpty();
        assertThat(ChainWeld.eulerPath(2, new int[0][])).hasValueSatisfying(o -> assertThat(o).isEmpty());
        assertThatThrownBy(() -> ChainWeld.eulerPath(2, new int[][] {{0, 5}}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        int[][] path = {{0, 1}, {1, 2}};
        assertThat(ChainWeld.grade(3, path, new int[] {1, 0})).isEqualTo(Grade.SNAPPED);
        assertThat(ChainWeld.grade(3, path, null)).isEqualTo(Grade.SNAPPED);
        assertThat(ChainWeld.grade(3, path, new int[] {0, 0})).isEqualTo(Grade.SNAPPED);
        assertThat(ChainWeld.grade(3, path, new int[] {0})).isEqualTo(Grade.SNAPPED);
        for (Grade g : Grade.values()) {
            assertThat(ChainWeld.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(ChainWeld.QUEST_ID).isEqualTo("q_chain_weld");
        assertThat(ChainWeld.links(2, 3, 5)).isDeepEqualTo(ChainWeld.links(2, 3, 5));
        assertThatThrownBy(() -> ChainWeld.links(1, 0, 2)).isInstanceOf(IllegalArgumentException.class);
    }
}
