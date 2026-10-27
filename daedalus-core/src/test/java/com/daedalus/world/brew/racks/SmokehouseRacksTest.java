// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.racks;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.racks.SmokehouseRacks.Outcome;
import org.junit.jupiter.api.Test;

class SmokehouseRacksTest {
    /** Brute force: try every side on every rack opened so far or a new one. */
    static int brute(SmokehouseRacks s) {
        return place(s, 0, new int[s.sides()], 0);
    }

    static int place(SmokehouseRacks s, int i, int[] onRack, int open) {
        if (i == s.sides()) {
            return open;
        }
        int best = Integer.MAX_VALUE;
        for (int r = 0; r <= open && r < s.sides(); r++) {
            if (onRack[r] + s.side(i) <= s.load()) {
                onRack[r] += s.side(i);
                best = Math.min(best, place(s, i + 1, onRack, Math.max(open, r + 1)));
                onRack[r] -= s.side(i);
            }
        }
        return best;
    }

    /** First fit in order uses 3 racks; the best is 2 (5+3+2, 4+3+3). */
    static SmokehouseRacks catchOfDay() {
        return new SmokehouseRacks(10, 5, 4, 3, 3, 3, 2);
    }

    @Test
    void seededCatchIsDeterministic() {
        SmokehouseRacks a = SmokehouseRacks.seeded(3);
        SmokehouseRacks b = SmokehouseRacks.seeded(3);
        assertEquals(a.sides(), b.sides());
        assertEquals(a.side(0), b.side(0));
        assertThrows(IllegalArgumentException.class, () -> new SmokehouseRacks(10, 11));
        assertThrows(IllegalArgumentException.class, () -> new SmokehouseRacks(10));
    }

    @Test
    void fewestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            SmokehouseRacks s = SmokehouseRacks.seeded(seed);
            assertEquals(brute(s), s.fewest(), "subset DP == brute force, seed " + seed);
        }
    }

    @Test
    void firstFitInOrderIsNotBest() {
        SmokehouseRacks s = catchOfDay();
        assertEquals(2, s.fewest(), "5+3+2 and 4+3+3");
        assertEquals(Outcome.WASTEFUL, s.hang("ff", 0, 0, 1, 1, 1, 2), "first fit: 5+4, 3+3+3, 2");
        assertEquals(3, s.racksUsed());
    }

    @Test
    void overloadEarnsNoCredit() {
        SmokehouseRacks s = catchOfDay();
        s.weigh("w");
        assertEquals(Outcome.OVERLOAD, s.hang("h1", 0, 0, 0, 1, 1, 1));
        assertEquals(0, s.overRack());
        assertEquals(String.format(KeeperRackLines.OVERLOAD, 0), s.talk("t1"));
        assertEquals("hang", s.quest().currentStep().type(), "no credit for an overload");
    }

    @Test
    void guards() {
        SmokehouseRacks s = catchOfDay();
        assertEquals(Outcome.IGNORED, s.hang("", 0, 1, 0, 1, 1, 0));
        assertEquals(Outcome.NOT_THERE, s.hang("e0", 0, 1));
        assertEquals(Outcome.NOT_THERE, s.hang("e0", 0, 1, 0, 1, 1, 6));
        assertEquals(Outcome.WELL, s.hang("e1", 0, 1, 0, 1, 1, 0));
        assertEquals(Outcome.DUPLICATE, s.hang("e1", 0, 0, 0, 0, 0, 0));
    }

    @Test
    void questWastefulThenWellThenKeeper() {
        SmokehouseRacks s = catchOfDay();
        assertEquals(String.format(KeeperRackLines.GREETING, 6, 10), s.talk("t0"));
        s.weigh("w0");
        assertEquals(Outcome.WASTEFUL, s.hang("h1", 0, 0, 1, 1, 1, 2));
        assertEquals(String.format(KeeperRackLines.WASTEFUL, 3, 2), s.talk("t1"));
        assertEquals(Outcome.WELL, s.hang("h2", 0, 1, 0, 1, 1, 0));
        assertEquals(KeeperRackLines.THANKS, s.talk("t2"));
        assertNull(s.quest().currentStep());
        assertEquals(KeeperRackLines.DONE, s.talk("t3"));
    }
}
