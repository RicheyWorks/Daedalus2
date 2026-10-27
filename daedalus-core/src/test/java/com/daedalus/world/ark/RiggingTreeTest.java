// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;
import org.junit.jupiter.api.Test;

class RiggingTreeTest {

    private static boolean isTree(int n, List<int[]> es) {
        int[] parent = new int[n];
        for (int i = 0; i < n; i++) {
            parent[i] = i;
        }
        for (int[] e : es) {
            int a = find(parent, e[0]);
            int b = find(parent, e[1]);
            if (a == b) {
                return false;
            }
            parent[a] = b;
        }
        return true;
    }

    private static int find(int[] p, int x) {
        while (p[x] != x) {
            x = p[x];
        }
        return x;
    }

    private static String key(int[][] es) {
        List<String> s = new ArrayList<>();
        for (int[] e : es) {
            s.add(Math.min(e[0], e[1]) + "-" + Math.max(e[0], e[1]));
        }
        s.sort(null);
        return s.toString();
    }

    @Test
    void bruteForceEveryTreeUpToSeven() {
        for (int n = 2; n <= 7; n++) {
            List<int[]> all = new ArrayList<>();
            for (int a = 0; a < n; a++) {
                for (int b = a + 1; b < n; b++) {
                    all.add(new int[] {a, b});
                }
            }
            int m = all.size();
            int trees = 0;
            Set<String> seqs = new HashSet<>();
            for (int mask = 0; mask < (1 << m); mask++) {
                if (Integer.bitCount(mask) != n - 1) {
                    continue;
                }
                List<int[]> es = new ArrayList<>();
                for (int i = 0; i < m; i++) {
                    if ((mask >> i & 1) != 0) {
                        es.add(all.get(i));
                    }
                }
                if (!isTree(n, es)) {
                    continue;
                }
                trees++;
                int[][] arr = es.toArray(new int[0][]);
                int[] seq = RiggingTree.encode(n, arr);
                assertThat(seqs.add(Arrays.toString(seq))).isTrue();
                assertThat(key(RiggingTree.decode(seq))).isEqualTo(key(arr));
            }
            assertThat((long) trees).isEqualTo(RiggingTree.count(n));
        }
    }

    @Test
    void randomSequencesRoundTrip() {
        SplittableRandom rnd = new SplittableRandom(324);
        for (int t = 0; t < 2000; t++) {
            int n = rnd.nextInt(2, 60);
            int[] seq = new int[n - 2];
            for (int i = 0; i < seq.length; i++) {
                seq[i] = rnd.nextInt(n);
            }
            int[][] es = RiggingTree.decode(seq);
            assertThat(isTree(n, Arrays.asList(es))).isTrue();
            assertThat(RiggingTree.encode(n, es)).containsExactly(seq);
        }
    }

    @Test
    void questAndGuards() {
        assertThat(RiggingTree.QUEST_ID).isEqualTo("q_rigging_tree");
        int[][] star = {{0, 1}, {0, 2}, {0, 3}};
        assertThat(RiggingTree.quest(4, star, new int[] {0, 0})).isTrue();
        assertThat(RiggingTree.quest(4, star, new int[] {0, 1})).isFalse();
        assertThat(RiggingTree.count(10)).isEqualTo(100_000_000L);
        assertThatThrownBy(() -> RiggingTree.encode(4, new int[][] {{0, 1}, {1, 0}, {2, 3}}))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RiggingTree.decode(new int[] {5})).isInstanceOf(IllegalArgumentException.class);
    }
}