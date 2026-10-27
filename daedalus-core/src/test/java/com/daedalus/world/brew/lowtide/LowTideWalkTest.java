// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lowtide;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.lowtide.LowTideWalk.Outcome;
import org.junit.jupiter.api.Test;

class LowTideWalkTest {
    /** Brute force: scan every window and every hour in it. */
    static int brute(LowTideWalk w, int start) {
        int m = 0;
        for (int i = start; i < start + w.walkHours(); i++) {
            m = Math.max(m, w.level(i));
        }
        return m;
    }

    /** Hours 5,1,7,2,2,3,8,0,6 with a 3-hour walk: the lowest single hour (0) is a trap; hours 3-5 peak at 3. */
    static LowTideWalk almanac() {
        return new LowTideWalk(3, 5, 1, 7, 2, 2, 3, 8, 0, 6);
    }

    @Test
    void seededAlmanacIsDeterministic() {
        LowTideWalk a = LowTideWalk.seeded(2);
        LowTideWalk b = LowTideWalk.seeded(2);
        assertEquals(a.hours(), b.hours());
        assertEquals(a.safest(), b.safest());
        assertThrows(IllegalArgumentException.class, () -> new LowTideWalk(4, 1, 2, 3));
        assertThrows(IllegalArgumentException.class, () -> new LowTideWalk(1, -1));
    }

    @Test
    void windowsMatchBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            LowTideWalk w = LowTideWalk.seeded(seed);
            int best = Integer.MAX_VALUE;
            for (int s = 0; s + w.walkHours() <= w.hours(); s++) {
                assertEquals(brute(w, s), w.danger(s), "deque == brute force, seed " + seed + " hour " + s);
                best = Math.min(best, brute(w, s));
            }
            assertEquals(best, w.safest(), "seed " + seed);
        }
    }

    @Test
    void lowestHourIsNotSafest() {
        LowTideWalk w = almanac();
        assertEquals(3, w.safest());
        assertEquals(8, w.danger(5), "the walk through the 0 hour still meets 8");
    }

    @Test
    void deepWalkEarnsNoCredit() {
        LowTideWalk w = almanac();
        w.read("r");
        assertEquals(Outcome.DEEP, w.walk("w1", 5));
        assertEquals(String.format(KeeperTideLines.DEEP, 5, 8, 3), w.talk("t1"));
        assertEquals("walk", w.quest().currentStep().type(), "no credit for a deep walk");
    }

    @Test
    void guards() {
        LowTideWalk w = almanac();
        assertEquals(Outcome.IGNORED, w.walk("", 3));
        assertEquals(Outcome.NOT_THERE, w.walk("e0", 7));
        assertEquals(Outcome.NOT_THERE, w.walk("e0", -1));
        assertEquals(Outcome.DEEP, w.walk("e1", 0));
        assertEquals(Outcome.DUPLICATE, w.walk("e1", 3));
    }

    @Test
    void questDeepThenSafeThenKeeper() {
        LowTideWalk w = almanac();
        assertEquals(String.format(KeeperTideLines.GREETING, 9, 3), w.talk("t0"));
        w.read("r0");
        assertEquals(Outcome.DEEP, w.walk("w1", 5));
        assertEquals(Outcome.SAFE, w.walk("w2", 3));
        assertEquals(KeeperTideLines.THANKS, w.talk("t2"));
        assertNull(w.quest().currentStep());
        assertEquals(KeeperTideLines.DONE, w.talk("t3"));
    }
}
