// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.winds;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.winds.FairWinds.Outcome;
import org.junit.jupiter.api.Test;

class FairWindsTest {
    /** Brute force over every unbroken run of at least one day. */
    static int brute(FairWinds w) {
        int best = Integer.MIN_VALUE;
        for (int a = 0; a < w.days(); a++) {
            int s = 0;
            for (int b = a; b < w.days(); b++) {
                s += w.wind(b);
                best = Math.max(best, s);
            }
        }
        return best;
    }

    @Test
    void seededAlmanacIsDeterministic() {
        FairWinds w = FairWinds.seeded(3);
        assertTrue(w.days() >= 5 && w.days() <= 14);
        assertEquals(w.best(), FairWinds.seeded(3).best());
        assertThrows(IllegalArgumentException.class, () -> new FairWinds(new int[0]));
    }

    @Test
    void bestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            FairWinds w = FairWinds.seeded(seed);
            assertEquals(brute(w), w.best(), "Kadane == brute force, seed " + seed);
            int[] r = w.bestRun();
            int s = 0;
            for (int i = r[0]; i <= r[1]; i++) {
                s += w.wind(i);
            }
            assertEquals(w.best(), s, "best run sums to best, seed " + seed);
        }
    }

    @Test
    void crossingAFoulDayCanPay() {
        FairWinds w = new FairWinds(new int[] {4, -1, 5});
        assertEquals(8, w.best());
    }

    @Test
    void allFoulPicksTheMildestDay() {
        FairWinds w = new FairWinds(new int[] {-5, -2, -7});
        assertEquals(-2, w.best());
        assertEquals(Outcome.WELL, w.sail("s", 1, 1));
    }

    @Test
    void weakRunEarnsNoCredit() {
        FairWinds w = new FairWinds(new int[] {4, -1, 5});
        assertEquals(Outcome.IGNORED, w.sail("", 0, 2));
        assertEquals(Outcome.NOT_THERE, w.sail("e0", 2, 1));
        assertEquals(Outcome.NOT_THERE, w.sail("e0", 0, 3));
        w.read("r");
        assertEquals(Outcome.WEAK, w.sail("e1", 2, 2));
        assertEquals(Outcome.DUPLICATE, w.sail("e1", 0, 2));
        assertEquals("sail", w.quest().currentStep().type(), "no credit for a weak run");
    }

    @Test
    void questWeakThenWellThenKeeper() {
        FairWinds w = new FairWinds(new int[] {4, -1, 5});
        assertEquals(String.format(KeeperWindLines.GREETING, 3), w.talk("t0"));
        w.read("r0");
        assertEquals(Outcome.WEAK, w.sail("s1", 0, 0));
        assertEquals(String.format(KeeperWindLines.WEAK, 0, 0, 4, 8), w.talk("t1"));
        assertEquals(Outcome.WELL, w.sail("s2", 0, 2));
        assertEquals(KeeperWindLines.THANKS, w.talk("t2"));
        assertNull(w.quest().currentStep());
        assertEquals(KeeperWindLines.DONE, w.talk("t3"));
    }
}
