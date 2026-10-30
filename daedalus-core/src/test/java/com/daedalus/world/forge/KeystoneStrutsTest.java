// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.KeystoneStruts.Grade;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class KeystoneStrutsTest {

    private static int components(int n, int[][] e, int skipJoint, int skipEdge) {
        int[] parent = new int[n];
        for (int i = 0; i < n; i++) {
            parent[i] = i;
        }
        for (int i = 0; i < e.length; i++) {
            if (i == skipEdge || e[i][0] == skipJoint || e[i][1] == skipJoint) {
                continue;
            }
            parent[find(parent, e[i][0])] = find(parent, e[i][1]);
        }
        int c = 0;
        for (int i = 0; i < n; i++) {
            if (i != skipJoint && find(parent, i) == i) {
                c++;
            }
        }
        return c;
    }

    private static int find(int[] p, int x) {
        while (p[x] != x) {
            x = p[x];
        }
        return x;
    }

    @Test
    void matchBruteForceRemovalOnSeededRoofs() {
        for (long seed = 0; seed < 250; seed++) {
            int n = 2 + (int) (seed % 12);
            int[][] e = KeystoneStruts.roof(seed, n, (int) (seed % 18));
            int base = components(n, e, -1, -1);
            List<Integer> cuts = new ArrayList<>();
            for (int v = 0; v < n; v++) {
                boolean isolated = true;
                for (int[] x : e) {
                    isolated &= x[0] != v && x[1] != v;
                }
                int after = components(n, e, v, -1);
                if (after > base - (isolated ? 1 : 0)) {
                    cuts.add(v);
                }
            }
            List<Integer> br = new ArrayList<>();
            for (int i = 0; i < e.length; i++) {
                if (components(n, e, -1, i) > base) {
                    br.add(i);
                }
            }
            assertThat(KeystoneStruts.keystones(n, e)).as("seed %d", seed)
                    .containsExactly(cuts.stream().mapToInt(Integer::intValue).toArray());
            assertThat(KeystoneStruts.bridges(n, e)).as("seed %d", seed)
                    .containsExactly(br.stream().mapToInt(Integer::intValue).toArray());
        }
    }

    @Test
    void knownRoofs() {
        int[][] path = {{0, 1}, {1, 2}, {2, 3}};
        assertThat(KeystoneStruts.keystones(4, path)).containsExactly(1, 2);
        assertThat(KeystoneStruts.bridges(4, path)).containsExactly(0, 1, 2);
        int[][] doubled = {{0, 1}, {0, 1}};
        assertThat(KeystoneStruts.bridges(2, doubled)).isEmpty();
        int[][] bowtie = {{0, 1}, {1, 2}, {2, 0}, {2, 3}, {3, 4}, {4, 2}};
        assertThat(KeystoneStruts.keystones(5, bowtie)).containsExactly(2);
        assertThat(KeystoneStruts.bridges(5, bowtie)).isEmpty();
        assertThat(KeystoneStruts.keystones(0, new int[0][])).isEmpty();
        assertThatThrownBy(() -> KeystoneStruts.bridges(2, new int[][] {{1, 1}}))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void gradesLinesAndReplay() {
        int[][] path = {{0, 1}, {1, 2}};
        assertThat(KeystoneStruts.grade(3, path, new int[] {1}, new int[] {0, 1})).isEqualTo(Grade.SOUND);
        assertThat(KeystoneStruts.grade(3, path, new int[] {}, new int[] {0, 1})).isEqualTo(Grade.CRACKED);
        assertThat(KeystoneStruts.grade(3, path, new int[] {1}, new int[] {0})).isEqualTo(Grade.CRACKED);
        for (Grade g : Grade.values()) {
            assertThat(KeystoneStruts.forgemasterLine(g)).startsWith("Forgemaster:");
        }
        assertThat(KeystoneStruts.QUEST_ID).isEqualTo("q_keystone_struts");
        assertThat(KeystoneStruts.roof(5, 6, 9)).isDeepEqualTo(KeystoneStruts.roof(5, 6, 9)).hasNumberOfRows(9);
        assertThatThrownBy(() -> KeystoneStruts.roof(1, 1, 1)).isInstanceOf(IllegalArgumentException.class);
    }
}
