// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.currents;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.currents.SeaCurrents.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class SeaCurrentsTest {
    /** Brute force: the cheapest over every simple route from a to b. */
    static long brute(SeaCurrents s, int a, int b, boolean[] seen) {
        if (a == b) {
            return 0;
        }
        seen[a] = true;
        long best = SeaCurrents.NONE;
        for (int c = 0; c < s.coves(); c++) {
            if (!seen[c] && s.current(a, c) != null) {
                long rest = brute(s, c, b, seen);
                if (rest != SeaCurrents.NONE) {
                    best = Math.min(best, s.current(a, c) + rest);
                }
            }
        }
        seen[a] = false;
        return best;
    }

    /** Straight 0-3 costs 4; 0-1 costs 5 but 1-2 helps by -6, then 2-3 costs 2: total 1. */
    static SeaCurrents sea() {
        return new SeaCurrents(4, List.of(new int[] {0, 3, 4}, new int[] {0, 1, 5}, new int[] {1, 2, -6},
                new int[] {2, 3, 2}));
    }

    @Test
    void seededSeaIsDeterministic() {
        assertEquals(SeaCurrents.seeded(6).coves(), SeaCurrents.seeded(6).coves());
        assertEquals(SeaCurrents.seeded(6).cost(SeaCurrents.seeded(6).to()),
                SeaCurrents.seeded(6).cost(SeaCurrents.seeded(6).to()));
        assertThrows(IllegalArgumentException.class, () -> new SeaCurrents(1, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new SeaCurrents(3, List.of(new int[] {2, 2, 1})));
    }

    @Test
    void costsMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            SeaCurrents s = SeaCurrents.seeded(seed);
            assertFalse(s.whirlpool(), "seeded seas run forward only, seed " + seed);
            for (int c = 0; c < s.coves(); c++) {
                assertEquals(brute(s, 0, c, new boolean[s.coves()]), s.cost(c),
                        "Bellman-Ford == brute force, seed " + seed + " cove " + c);
            }
        }
    }

    @Test
    void helpingCurrentBeatsStraight() {
        SeaCurrents s = sea();
        assertEquals(4L, s.current(0, 3));
        assertEquals(1, s.cost(3));
        assertEquals(SeaCurrents.NONE, new SeaCurrents(3, List.of(new int[] {0, 1, 1})).cost(2));
    }

    @Test
    void costlyBrokenAndWhirlpoolEarnNoCredit() {
        SeaCurrents s = sea();
        s.chart("c");
        assertEquals(Outcome.COSTLY, s.sail("s0", List.of(0, 3)));
        assertEquals(String.format(KeeperCurrentLines.COSTLY, 4, 1), s.talk("t0"));
        assertEquals(Outcome.BROKEN, s.sail("s1", List.of(0, 2, 3)));
        assertEquals(KeeperCurrentLines.BROKEN, s.talk("t1"));
        assertEquals("sail", s.quest().currentStep().type(), "no credit for a costly or broken sail");
        SeaCurrents w = new SeaCurrents(3, List.of(new int[] {0, 1, 1}, new int[] {1, 0, -2}, new int[] {1, 2, 1}));
        assertTrue(w.whirlpool());
        assertEquals(Outcome.WHIRLPOOL, w.sail("w", List.of(0, 1, 2)));
        assertEquals(KeeperCurrentLines.WHIRLPOOL, w.talk("tw"));
    }

    @Test
    void guards() {
        SeaCurrents s = sea();
        assertEquals(Outcome.IGNORED, s.sail("", List.of(0, 3)));
        assertEquals(Outcome.IGNORED, s.sail("e", null));
        assertEquals(Outcome.BROKEN, s.sail("e0", List.of(1, 2, 3)), "must start at cove 0");
        assertEquals(Outcome.CHEAPEST, s.sail("e1", List.of(0, 1, 2, 3)));
        assertEquals(Outcome.DUPLICATE, s.sail("e1", List.of(0, 1, 2, 3)));
    }

    @Test
    void questCostlyThenCheapestThenKeeper() {
        SeaCurrents s = sea();
        assertEquals(String.format(KeeperCurrentLines.GREETING, 4, 3), s.talk("t0"));
        s.chart("c0");
        assertEquals(Outcome.COSTLY, s.sail("s1", List.of(0, 3)));
        assertEquals(Outcome.CHEAPEST, s.sail("s2", List.of(0, 1, 2, 3)));
        assertEquals(KeeperCurrentLines.THANKS, s.talk("t2"));
        assertNull(s.quest().currentStep());
        assertEquals(KeeperCurrentLines.DONE, s.talk("t3"));
    }
}
