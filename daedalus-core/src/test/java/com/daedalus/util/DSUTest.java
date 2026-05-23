// SPDX-License-Identifier: MIT

package com.daedalus.util;

import org.junit.jupiter.api.Test;

import java.util.Random;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Unit test for the shared {@link DSU} utility. Locks in the four invariants every union-
 * find structure must obey, plus the bookkeeping properties this implementation adds
 * ({@link DSU#components()}, {@link DSU#sizeOf(int)}, {@link DSU#largestComponent()},
 * {@link DSU#isFullyConnected()}, and the boolean return value of {@link DSU#union}).
 * The randomized stress test at the bottom exercises path compression + union by rank
 * against a brute-force "every key holds its color" oracle and cross-checks both the
 * connectivity and size bookkeeping against it.
 */
class DSUTest {

    // ---------- structural correctness ----------

    @Test
    void freshDsu_everyKeyIsItsOwnSet() {
        DSU dsu = new DSU(5);

        assertThat(dsu.size()).isEqualTo(5);
        assertThat(dsu.components()).isEqualTo(5);
        for (int i = 0; i < 5; i++) {
            assertThat(dsu.find(i)).isEqualTo(i);
        }
        assertThat(dsu.connected(0, 1)).isFalse();
    }

    @Test
    void union_mergesTwoSets_andDecrementsComponentCount() {
        DSU dsu = new DSU(5);

        boolean merged = dsu.union(0, 1);

        assertThat(merged).isTrue();
        assertThat(dsu.connected(0, 1)).isTrue();
        assertThat(dsu.components()).isEqualTo(4);
    }

    @Test
    void union_onAlreadyConnectedKeys_isNoOp_andReturnsFalse() {
        DSU dsu = new DSU(3);
        dsu.union(0, 1);

        boolean merged = dsu.union(1, 0);

        assertThat(merged).isFalse();
        assertThat(dsu.components()).isEqualTo(2);
    }

    @Test
    void connectivity_isTransitive() {
        DSU dsu = new DSU(4);

        dsu.union(0, 1);
        dsu.union(2, 3);
        // before bridging the two pairs
        assertThat(dsu.connected(0, 3)).isFalse();

        dsu.union(1, 2);
        // now 0 ↔ 1 ↔ 2 ↔ 3 are all in one set
        assertThat(dsu.connected(0, 3)).isTrue();
        assertThat(dsu.components()).isEqualTo(1);
    }

    @Test
    void unionAllKeys_collapsesToOneComponent() {
        DSU dsu = new DSU(100);
        for (int i = 1; i < 100; i++) {
            dsu.union(0, i);
        }
        assertThat(dsu.components()).isEqualTo(1);
        for (int i = 0; i < 100; i++) {
            assertThat(dsu.connected(0, i)).isTrue();
        }
    }

    // ---------- size + connectivity bookkeeping ----------

    @Test
    void freshDsu_everyComponentHasSizeOne_andLargestIsOne() {
        DSU dsu = new DSU(4);

        for (int i = 0; i < 4; i++) {
            assertThat(dsu.sizeOf(i)).isEqualTo(1);
        }
        assertThat(dsu.largestComponent()).isEqualTo(1);
        assertThat(dsu.isFullyConnected()).isFalse();
    }

    @Test
    void emptyDsu_largestComponentIsZero_andNotFullyConnected() {
        DSU dsu = new DSU(0);

        assertThat(dsu.largestComponent()).isEqualTo(0);
        // "no components" is not "one component" — guards against a singleton off-by-one.
        assertThat(dsu.isFullyConnected()).isFalse();
    }

    @Test
    void singletonDsu_isFullyConnected_andHasSizeOne() {
        DSU dsu = new DSU(1);

        assertThat(dsu.isFullyConnected()).isTrue();
        assertThat(dsu.sizeOf(0)).isEqualTo(1);
        assertThat(dsu.largestComponent()).isEqualTo(1);
    }

    @Test
    void union_growsBothQueriedSidesToTheMergedSize() {
        DSU dsu = new DSU(5);

        dsu.union(0, 1);
        dsu.union(2, 3);

        // Before bridging: two pairs of size 2, one singleton.
        assertThat(dsu.sizeOf(0)).isEqualTo(2);
        assertThat(dsu.sizeOf(1)).isEqualTo(2);
        assertThat(dsu.sizeOf(2)).isEqualTo(2);
        assertThat(dsu.sizeOf(4)).isEqualTo(1);
        assertThat(dsu.largestComponent()).isEqualTo(2);

        dsu.union(1, 2);   // bridges the two pairs

        // Every member of the bridged set reports size 4.
        for (int k : new int[]{0, 1, 2, 3}) {
            assertThat(dsu.sizeOf(k)).isEqualTo(4);
        }
        assertThat(dsu.sizeOf(4)).isEqualTo(1);  // unchanged
        assertThat(dsu.largestComponent()).isEqualTo(4);
    }

    @Test
    void redundantUnion_doesNotGrowSize() {
        DSU dsu = new DSU(3);
        dsu.union(0, 1);
        int before = dsu.sizeOf(0);

        dsu.union(0, 1);   // already connected — no-op
        dsu.union(1, 0);   // ditto

        assertThat(dsu.sizeOf(0)).isEqualTo(before);
        assertThat(dsu.largestComponent()).isEqualTo(2);
    }

    @Test
    void unionAllKeys_makesEveryKeyReportFullSize_andIsFullyConnected() {
        DSU dsu = new DSU(50);
        for (int i = 1; i < 50; i++) {
            dsu.union(0, i);
        }

        assertThat(dsu.isFullyConnected()).isTrue();
        for (int i = 0; i < 50; i++) {
            assertThat(dsu.sizeOf(i)).isEqualTo(50);
        }
        assertThat(dsu.largestComponent()).isEqualTo(50);
    }

    @Test
    void sizeOf_outOfRange_throwsIndexOutOfBounds() {
        // Funnels through find(), so the same guard applies.
        DSU dsu = new DSU(3);
        assertThatThrownBy(() -> dsu.sizeOf(7))
                .isInstanceOf(IndexOutOfBoundsException.class);
    }

    // ---------- guards ----------

    @Test
    void constructor_rejectsNegativeSize() {
        assertThatThrownBy(() -> new DSU(-1))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("size must be >= 0");
    }

    @Test
    void emptyDsu_hasZeroSize_andZeroComponents() {
        DSU dsu = new DSU(0);
        assertThat(dsu.size()).isEqualTo(0);
        assertThat(dsu.components()).isEqualTo(0);
    }

    @Test
    void find_outOfRange_throwsIndexOutOfBounds() {
        DSU dsu = new DSU(3);
        assertThatThrownBy(() -> dsu.find(5))
                .isInstanceOf(IndexOutOfBoundsException.class);
    }

    // ---------- randomized oracle ----------

    /**
     * Drive {@link DSU} with a stream of random unions, mirror them in a brute-force
     * "every key holds its color" oracle, and assert {@code connected} agrees on every
     * pair sampled. Catches subtle bugs in path compression / rank logic that the
     * targeted tests above would miss (e.g., rank not recovering after a long chain).
     */
    @Test
    void randomizedConnectivity_matchesBruteForceOracle() {
        final int N = 80;
        final int OPS = 500;
        Random rng = new Random(2026_05_06L);

        DSU dsu = new DSU(N);
        int[] color = new int[N];
        for (int i = 0; i < N; i++) color[i] = i;

        for (int op = 0; op < OPS; op++) {
            int a = rng.nextInt(N);
            int b = rng.nextInt(N);
            dsu.union(a, b);

            // Mirror in oracle: paint everyone with color[b]'s old color to color[a]'s color.
            int target = color[a];
            int source = color[b];
            if (target != source) {
                for (int i = 0; i < N; i++) {
                    if (color[i] == source) color[i] = target;
                }
            }
        }

        // Sample many pairs and verify both representations agree on connectivity.
        for (int trial = 0; trial < 1000; trial++) {
            int a = rng.nextInt(N);
            int b = rng.nextInt(N);
            assertThat(dsu.connected(a, b))
                    .as("pair (%d, %d) after random unions", a, b)
                    .isEqualTo(color[a] == color[b]);
        }

        // Verify size bookkeeping against the same oracle: every key's reported component
        // size must equal the number of keys sharing its color, and largestComponent must
        // equal the most-popular color's count.
        int[] colorCount = new int[N];
        int oracleLargest = 0;
        for (int i = 0; i < N; i++) {
            colorCount[color[i]]++;
        }
        for (int c : colorCount) {
            if (c > oracleLargest) oracleLargest = c;
        }
        for (int i = 0; i < N; i++) {
            assertThat(dsu.sizeOf(i))
                    .as("sizeOf(%d) after random unions", i)
                    .isEqualTo(colorCount[color[i]]);
        }
        assertThat(dsu.largestComponent())
                .as("largestComponent after random unions")
                .isEqualTo(oracleLargest);
    }
}
