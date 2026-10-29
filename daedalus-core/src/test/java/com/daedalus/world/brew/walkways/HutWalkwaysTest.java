// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.walkways;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.walkways.HutWalkways.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class HutWalkwaysTest {
    /** Brute force: every set of n-1 walkways that joins all huts. */
    static int brute(HutWalkways h) {
        int n = h.huts();
        List<int[]> all = new ArrayList<>();
        for (int a = 0; a < n; a++) {
            for (int b = a + 1; b < n; b++) {
                all.add(new int[] {a, b});
            }
        }
        int best = Integer.MAX_VALUE;
        for (int mask = 0; mask < (1 << all.size()); mask++) {
            if (Integer.bitCount(mask) != n - 1) {
                continue;
            }
            int[] parent = new int[n];
            for (int i = 0; i < n; i++) {
                parent[i] = i;
            }
            int total = 0;
            int joins = 0;
            for (int e = 0; e < all.size(); e++) {
                if ((mask & (1 << e)) != 0) {
                    int[] w = all.get(e);
                    total += h.planks(w[0], w[1]);
                    int a = w[0];
                    int b = w[1];
                    while (parent[a] != a) {
                        a = parent[a];
                    }
                    while (parent[b] != b) {
                        b = parent[b];
                    }
                    if (a != b) {
                        parent[a] = b;
                        joins++;
                    }
                }
            }
            if (joins == n - 1) {
                best = Math.min(best, total);
            }
        }
        return best;
    }

    /** Hut 0 sits near all others (1, 2, 2); a walk from hut to hut 0-1-2-3 costs 1 + 9 + 3 = 13; the best is 5. */
    static HutWalkways marsh() {
        return new HutWalkways(new int[][] {{0, 1, 2, 2}, {1, 0, 9, 9}, {2, 9, 0, 3}, {2, 9, 3, 0}});
    }

    @Test
    void seededMarshIsDeterministic() {
        HutWalkways a = HutWalkways.seeded(1);
        HutWalkways b = HutWalkways.seeded(1);
        assertEquals(a.huts(), b.huts());
        assertEquals(a.cheapest(), b.cheapest());
        assertThrows(IllegalArgumentException.class, () -> new HutWalkways(new int[][] {{0, 1}, {2, 0}}));
        assertThrows(IllegalArgumentException.class, () -> new HutWalkways(new int[][] {{0}}));
    }

    @Test
    void cheapestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            HutWalkways h = HutWalkways.seeded(seed);
            assertEquals(brute(h), h.cheapest(), "Prim == brute force, seed " + seed);
        }
    }

    @Test
    void hutToHutWalkIsNotCheapest() {
        HutWalkways h = marsh();
        assertEquals(5, h.cheapest());
        assertEquals(Outcome.DEAR, h.lay("p", List.of(new int[] {0, 1}, new int[] {1, 2}, new int[] {2, 3})));
        assertEquals(13, h.laid());
    }

    @Test
    void brokenNetworkEarnsNoCredit() {
        HutWalkways h = marsh();
        h.survey("s");
        assertEquals(Outcome.BROKEN, h.lay("l1", List.of(new int[] {0, 1}, new int[] {0, 2})));
        assertEquals(KeeperWalkwayLines.BROKEN, h.talk("t1"));
        assertEquals("lay", h.quest().currentStep().type(), "no credit for a broken network");
    }

    @Test
    void guards() {
        HutWalkways h = marsh();
        assertEquals(Outcome.IGNORED, h.lay("", List.of()));
        assertEquals(Outcome.NOT_THERE, h.lay("e0", List.of(new int[] {0, 4})));
        assertEquals(Outcome.NOT_THERE, h.lay("e0", List.of(new int[] {2, 2})));
        assertEquals(Outcome.BROKEN, h.lay("e1", List.of()));
        assertEquals(Outcome.DUPLICATE, h.lay("e1", List.of(new int[] {0, 1})));
    }

    @Test
    void questDearThenWellThenKeeper() {
        HutWalkways h = marsh();
        assertEquals(String.format(KeeperWalkwayLines.GREETING, 4), h.talk("t0"));
        h.survey("s0");
        assertEquals(Outcome.DEAR, h.lay("l1", List.of(new int[] {0, 1}, new int[] {1, 2}, new int[] {2, 3})));
        assertEquals(String.format(KeeperWalkwayLines.DEAR, 13, 5), h.talk("t1"));
        assertEquals(Outcome.WELL, h.lay("l2", List.of(new int[] {0, 1}, new int[] {0, 2}, new int[] {0, 3})));
        assertEquals(KeeperWalkwayLines.THANKS, h.talk("t2"));
        assertNull(h.quest().currentStep());
        assertEquals(KeeperWalkwayLines.DONE, h.talk("t3"));
    }
}
