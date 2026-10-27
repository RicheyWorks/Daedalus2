// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.seawall;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.seawall.SeaWall.Outcome;
import org.junit.jupiter.api.Test;

class SeaWallTest {
    /** Brute force over every span of stones at its lowest height. */
    static int brute(SeaWall w) {
        int best = 0;
        for (int a = 0; a < w.stones(); a++) {
            int low = Integer.MAX_VALUE;
            for (int b = a; b < w.stones(); b++) {
                low = Math.min(low, w.height(b));
                best = Math.max(best, low * (b - a + 1));
            }
        }
        return best;
    }

    static SeaWall wall() {
        return new SeaWall(2, 1, 5, 6, 2, 3);
    }

    @Test
    void seededWallIsDeterministic() {
        SeaWall w = SeaWall.seeded(6);
        assertTrue(w.stones() >= 3 && w.stones() <= 14);
        assertEquals(w.largest(), SeaWall.seeded(6).largest());
        assertThrows(IllegalArgumentException.class, () -> new SeaWall(3, 0));
    }

    @Test
    void largestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            SeaWall w = SeaWall.seeded(seed);
            assertEquals(brute(w), w.largest(), "monotonic stack == brute force, seed " + seed);
        }
    }

    @Test
    void tallestStoneIsNotBest() {
        assertEquals(10, wall().largest());
    }

    @Test
    void overhangEarnsNoCredit() {
        SeaWall w = wall();
        w.measure("m");
        assertEquals(Outcome.OVERHANG, w.fit("f1", 1, 3, 5));
        assertEquals(1, w.lowStone());
        assertEquals(String.format(KeeperWallLines.OVERHANG, 5, 1, 3, 1), w.talk("t1"));
        assertEquals("fit", w.quest().currentStep().type(), "no credit for an overhang");
    }

    @Test
    void guards() {
        SeaWall w = wall();
        assertEquals(Outcome.IGNORED, w.fit("", 0, 1, 1));
        assertEquals(Outcome.NOT_THERE, w.fit("e0", 3, 2, 1));
        assertEquals(Outcome.NOT_THERE, w.fit("e0", 0, 6, 1));
        assertEquals(Outcome.NOT_THERE, w.fit("e0", 0, 1, 0));
        assertEquals(Outcome.SMALL, w.fit("e1", 0, 0, 1));
        assertEquals(Outcome.DUPLICATE, w.fit("e1", 2, 3, 5));
    }

    @Test
    void questSmallThenWellThenKeeper() {
        SeaWall w = wall();
        assertEquals(String.format(KeeperWallLines.GREETING, 6), w.talk("t0"));
        w.measure("m0");
        assertEquals(Outcome.SMALL, w.fit("f1", 3, 3, 6));
        assertEquals(String.format(KeeperWallLines.SMALL, 6, 10), w.talk("t1"));
        assertEquals(Outcome.WELL, w.fit("f2", 2, 3, 5));
        assertEquals(KeeperWallLines.THANKS, w.talk("t2"));
        assertNull(w.quest().currentStep());
        assertEquals(KeeperWallLines.DONE, w.talk("t3"));
    }
}
