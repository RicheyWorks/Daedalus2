// SPDX-License-Identifier: MIT

package com.daedalus.util;

import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Structural guard for {@link DSU}'s near-constant amortized cost (CLRS Ch. 21 disjoint sets,
 * Ch. 17 amortized analysis): {@link DSU#find} must actually <em>compress</em> the path it walks,
 * and {@link DSU#union} must merge by rank.
 *
 * <p>Why reflection: the rest of {@link DSUTest} covers behaviour, and behaviour alone cannot see
 * this. If someone simplified {@code find} into a plain root-walk without the rewrite pass, every
 * correctness test would still pass — the structure would just silently degrade from
 * inverse-Ackermann to O(n) per operation. Reading {@code parent} directly is the only way to
 * assert the optimization is still there.
 */
class DSUPathCompressionTest {

    @Test
    void find_rewritesTheWalkedPathToPointAtTheRoot() throws Exception {
        DSU dsu = new DSU(8);

        // Build a depth-2 tree using equal-rank merges:
        //   union(0,1) -> 1 under 0 (rank[0] = 1)
        //   union(2,3) -> 3 under 2 (rank[2] = 1)
        //   union(0,2) -> equal ranks, so 2 goes under 0 (rank[0] = 2)
        // leaving the chain 3 -> 2 -> 0.
        dsu.union(0, 1);
        dsu.union(2, 3);
        dsu.union(0, 2);

        int root = dsu.find(0);
        assertThat(parentOf(dsu, 3)).isEqualTo(2).isNotEqualTo(root); // still two hops from the root

        dsu.find(3);

        assertThat(parentOf(dsu, 3)).isEqualTo(root); // compressed: now one hop
    }

    @Test
    void union_byRank_putsTheShallowTreeUnderTheTallerOne() throws Exception {
        DSU dsu = new DSU(8);

        dsu.union(0, 1);  // {0,1} has rank 1
        dsu.union(0, 2);  // singleton {2} (rank 0) must go under the taller root, not vice versa

        assertThat(parentOf(dsu, 2)).isEqualTo(dsu.find(0));
        assertThat(dsu.connected(1, 2)).isTrue();
    }

    private static int parentOf(DSU dsu, int index) throws Exception {
        Field field = DSU.class.getDeclaredField("parent");
        field.setAccessible(true);
        return ((int[]) field.get(dsu))[index];
    }
}
