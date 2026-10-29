// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.trails;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.trails.HillTrails.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class HillTrailsTest {
    /** Brute force: the shortest over every simple path from a to b. */
    static int brute(HillTrails h, int a, int b, boolean[] seen) {
        if (a == b) {
            return 0;
        }
        seen[a] = true;
        int best = HillTrails.NONE;
        for (int c = 0; c < h.huts(); c++) {
            if (!seen[c] && c != a && h.trail(a, c) != HillTrails.NONE) {
                int rest = brute(h, c, b, seen);
                if (rest != HillTrails.NONE && (best == HillTrails.NONE || h.trail(a, c) + rest < best)) {
                    best = h.trail(a, c) + rest;
                }
            }
        }
        seen[a] = false;
        return best;
    }

    /** The straight trail 0-3 is 10; 0-1-2-3 is 6. */
    static HillTrails hill() {
        return new HillTrails(4, List.of(new int[] {0, 3, 10}, new int[] {0, 1, 2}, new int[] {1, 2, 2},
                new int[] {2, 3, 2}));
    }

    @Test
    void seededHillIsDeterministic() {
        assertEquals(HillTrails.seeded(3).huts(), HillTrails.seeded(3).huts());
        assertEquals(HillTrails.seeded(3).dist(0, HillTrails.seeded(3).to()),
                HillTrails.seeded(3).dist(0, HillTrails.seeded(3).to()));
        assertThrows(IllegalArgumentException.class, () -> new HillTrails(1, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new HillTrails(3, List.of(new int[] {1, 1, 2})));
    }

    @Test
    void allPairsMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            HillTrails h = HillTrails.seeded(seed);
            for (int a = 0; a < h.huts(); a++) {
                for (int b = 0; b < h.huts(); b++) {
                    assertEquals(brute(h, a, b, new boolean[h.huts()]), h.dist(a, b),
                            "Floyd-Warshall == brute force, seed " + seed + " " + a + "-" + b);
                }
            }
        }
    }

    @Test
    void straightTrailIsNotShortest() {
        HillTrails h = hill();
        assertEquals(10, h.trail(0, 3));
        assertEquals(6, h.dist(0, 3));
        assertEquals(HillTrails.NONE, new HillTrails(3, List.of(new int[] {0, 1, 1})).dist(0, 2));
    }

    @Test
    void longAndBrokenEarnNoCredit() {
        HillTrails h = hill();
        h.survey("s");
        assertEquals(Outcome.LONG, h.walk("w0", List.of(0, 3)));
        assertEquals(String.format(KeeperTrailLines.LONG, 10, 6), h.talk("t0"));
        assertEquals(Outcome.BROKEN, h.walk("w1", List.of(0, 2, 3)));
        assertEquals(KeeperTrailLines.BROKEN, h.talk("t1"));
        assertEquals("walk", h.quest().currentStep().type(), "no credit for a long or broken walk");
    }

    @Test
    void guards() {
        HillTrails h = hill();
        assertEquals(Outcome.IGNORED, h.walk("", List.of(0, 3)));
        assertEquals(Outcome.IGNORED, h.walk("e", null));
        assertEquals(Outcome.BROKEN, h.walk("e0", List.of(1, 2, 3)), "must start at hut 0");
        assertEquals(Outcome.SHORTEST, h.walk("e1", List.of(0, 1, 2, 3)));
        assertEquals(Outcome.DUPLICATE, h.walk("e1", List.of(0, 1, 2, 3)));
    }

    @Test
    void questLongThenShortestThenKeeper() {
        HillTrails h = hill();
        assertEquals(String.format(KeeperTrailLines.GREETING, 4, 0, 3), h.talk("t0"));
        h.survey("s0");
        assertEquals(Outcome.LONG, h.walk("w1", List.of(0, 3)));
        assertEquals(Outcome.SHORTEST, h.walk("w2", List.of(0, 1, 2, 3)));
        assertEquals(KeeperTrailLines.THANKS, h.talk("t2"));
        assertNull(h.quest().currentStep());
        assertEquals(KeeperTrailLines.DONE, h.talk("t3"));
    }
}
